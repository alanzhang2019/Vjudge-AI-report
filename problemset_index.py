"""problemset_index.py - v3.11.0

洛谷官方公开题库 (problemset-open) 的本地缓存与查询层。

数据源:
    https://cdn.luogu.com.cn/problemset-open/latest.ndjson.gz
    一行一道题, NDJSON + gzip 压缩, ~26 MB, 16926+ 道题

字段 (节选):
    pid, type, difficulty, tags, title, background,
    description, inputFormat, outputFormat, hint,
    samples [{input, output}, ...],
    limits  {"time": [t1,...], "memory": [m1,...]},
    translations {"en": {...}, ...}

落地:
    .source_cache/problemset/
        ├─ latest.ndjson.gz     原始压缩文件 (CDN mirror)
        └─ index.json           紧凑索引 {pid: {title, difficulty, tags, samples, ...}}

公开 API:
    get_status()                  → dict, 给前端面板用
    ensure_ready(progress_cb)     → bool, 进程启动时调用,后台下载/构建
    download_and_build(cb)        → bool, 管理员手动触发
    get(pid)                      → dict | None
    get_many(pids)                 → dict[pid, dict]
    enrich_problem(problem)       → int (改动字段数)

设计目标:
    - 与 web_app.py 解耦, 不依赖 Flask
    - 失败时 soft-degrade: 拿不到数据时返回 None, 业务侧继续走原路径
    - 增量同步: 用 mtime/etag 判定"已最新",不每次都重新下载
"""
from __future__ import annotations

import gzip
import json
import logging
import os
import shutil
import tempfile
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


logger = logging.getLogger("problemset_index")

# ---------- 路径配置 ----------

CACHE_DIR = Path(__file__).parent / ".source_cache" / "problemset"
RAW_GZ_PATH = CACHE_DIR / "latest.ndjson.gz"
INDEX_PATH = CACHE_DIR / "index.json"
META_PATH = CACHE_DIR / "meta.json"  # 下载/构建的元信息 (size, sha, updated_at, count)

# 洛谷官方 CDN
PROBLEMSET_URL = "https://cdn.luogu.com.cn/problemset-open/latest.ndjson.gz"

# 下载超时 / 重试
DOWNLOAD_TIMEOUT = 90  # 秒
DOWNLOAD_CHUNK = 64 * 1024  # 64KB
DOWNLOAD_MAX_RETRIES = 2

# 索引里保留的字段 (其它用不到, 节省内存/磁盘)
INDEX_FIELDS = (
    "type",         # "P" | "CF" | "SP" | "AT" | ...
    "difficulty",   # 0-7 (官方 8 档) | null
    "tags",         # [int, ...]  标签 ID
    "title",        # 题目名
    "samples",      # 样例 I/O
    "limits",       # {"time":[...], "memory":[...]}
)

# 索引里额外补一个 i18n 标题 (有些报告需要英文版)
INDEX_FIELDS_I18N = ("translations",)  # 保留 translations.en.title


# v3.11.0 · 洛谷官方 8 档难度中文标签
# (参考: https://algobeatcontest.github.io/practice 的 diffMap)
DIFFICULTY_NAMES: tuple = (
    "暂无评定",      # 0
    "入门",          # 1
    "普及−",         # 2
    "普及/提高−",    # 3
    "普及+/提高",    # 4
    "提高+/省选−",   # 5
    "省选/NOI−",     # 6
    "NOI/NOI+/CTSC", # 7
)


def get_difficulty_name(level) -> str:
    """难度档 0-7 → 中文标签, 越界或 None 返回 '暂无评定'"""
    try:
        idx = int(level)
        if 0 <= idx < len(DIFFICULTY_NAMES):
            return DIFFICULTY_NAMES[idx]
    except (TypeError, ValueError):
        pass
    return DIFFICULTY_NAMES[0]


# ---------- 元信息 ----------

@dataclass
class IndexStatus:
    """当前缓存状态(给 /api/problemset-status 用)"""
    ready: bool = False
    raw_size_bytes: int = 0
    index_size_bytes: int = 0
    problem_count: int = 0
    last_download_iso: str = ""
    last_build_iso: str = ""
    last_error: str = ""
    source_url: str = PROBLEMSET_URL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ready": self.ready,
            "raw_size_bytes": self.raw_size_bytes,
            "index_size_bytes": self.index_size_bytes,
            "problem_count": self.problem_count,
            "last_download_iso": self.last_download_iso,
            "last_build_iso": self.last_build_iso,
            "last_error": self.last_error,
            "source_url": self.source_url,
        }


# ---------- 内存索引 ----------

_index_lock = threading.RLock()
_index_cache: Optional[Dict[str, Dict[str, Any]]] = None  # pid → 精简字段
_index_loaded_at: float = 0.0


def _ensure_dirs() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ---------- 状态查询 ----------

def get_status() -> Dict[str, Any]:
    """前端用的状态摘要, 始终同步返回(基于磁盘文件 + 内存状态)"""
    s = IndexStatus(source_url=PROBLEMSET_URL)
    try:
        s.raw_size_bytes = RAW_GZ_PATH.stat().st_size if RAW_GZ_PATH.exists() else 0
    except OSError:
        pass
    try:
        s.index_size_bytes = INDEX_PATH.stat().st_size if INDEX_PATH.exists() else 0
    except OSError:
        pass

    if META_PATH.exists():
        try:
            meta = json.loads(META_PATH.read_text(encoding="utf-8"))
            s.last_download_iso = meta.get("last_download_iso", "")
            s.last_build_iso = meta.get("last_build_iso", "")
            s.problem_count = int(meta.get("problem_count", 0) or 0)
            s.last_error = meta.get("last_error", "")
        except Exception as e:  # noqa: BLE001
            logger.debug("read meta.json failed: %s", e)

    with _index_lock:
        s.ready = _index_cache is not None and len(_index_cache) > 0
    if _index_cache is not None:
        s.problem_count = len(_index_cache)
    return s.to_dict()


# ---------- 下载 ----------

def _download(
    url: str,
    dest: Path,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    timeout: int = DOWNLOAD_TIMEOUT,
) -> None:
    """下载到 dest (gzip 文件),带进度回调 (downloaded_bytes, total_bytes)"""
    last_err: Optional[Exception] = None
    for attempt in range(1, DOWNLOAD_MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "vjudge-ai-report/3.11"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                total = int(r.headers.get("Content-Length", 0) or 0)
                tmp = dest.with_suffix(dest.suffix + ".part")
                downloaded = 0
                with open(tmp, "wb") as f:
                    while True:
                        chunk = r.read(DOWNLOAD_CHUNK)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_cb:
                            try:
                                progress_cb(downloaded, total)
                            except Exception:  # noqa: BLE001
                                pass
                os.replace(tmp, dest)
                return
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = e
            logger.warning("[problemset] download attempt %d/%d failed: %s",
                           attempt, DOWNLOAD_MAX_RETRIES, e)
            time.sleep(1.0 * attempt)
    raise RuntimeError(f"下载失败 (重试 {DOWNLOAD_MAX_RETRIES} 次): {last_err}")


# ---------- 解析 + 构建索引 ----------

def _build_index_from_gz(
    gz_path: Path,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    流式解压 + 解析 NDJSON, 构建 {pid: 精简字段} 索引。
    progress_cb(done, total)  按行数估算, total 不可知 → 传 -1
    """
    index: Dict[str, Dict[str, Any]] = {}
    n_lines = 0
    with gzip.open(gz_path, "rt", encoding="utf-8") as f:
        for line in f:
            n_lines += 1
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            pid = obj.get("pid")
            if not pid:
                continue
            entry: Dict[str, Any] = {k: obj.get(k) for k in INDEX_FIELDS if k in obj}
            # 补一个 difficulty_name(中文标签, 0-7 映射)
            entry["difficulty_name"] = get_difficulty_name(entry.get("difficulty"))
            # 保留英文标题(若有), 放进 translations 字段
            tr = obj.get("translations")
            if isinstance(tr, dict) and isinstance(tr.get("en"), dict):
                en_title = tr["en"].get("title")
                if en_title:
                    entry["title_en"] = en_title
            index[pid] = entry
            if progress_cb and n_lines % 2000 == 0:
                try:
                    progress_cb(n_lines, -1)
                except Exception:  # noqa: BLE001
                    pass
    if progress_cb:
        try:
            progress_cb(n_lines, n_lines)
        except Exception:  # noqa: BLE001
            pass
    return index


def _write_index_atomic(index: Dict[str, Dict[str, Any]], dest: Path) -> None:
    """原子写入 JSON(写 .part → replace)"""
    tmp = dest.with_suffix(dest.suffix + ".part")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, dest)


def _load_index_into_memory(path: Path) -> Dict[str, Dict[str, Any]]:
    """从 JSON 索引文件载入内存"""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.error("[problemset] index.json 解析失败: %s", e)
        return {}


# ---------- 公开 API: ensure_ready / download_and_build ----------

_ensure_lock = threading.Lock()
_ensure_started = False


def ensure_ready(
    progress_cb: Optional[Callable[[str, int, int], None]] = None,
    force_rebuild: bool = False,
) -> bool:
    """
    进程启动时调用: 第一次会后台启动一次 download+build,
    后续调用直接返回内存索引是否已就绪。

    progress_cb(stage, done, total):
        stage in {"download", "build", "ready", "error"}
    返回 True 表示本次调用过程中索引已经就绪(可能是从磁盘加载, 也可能是新构建)。
    """
    global _index_cache, _index_loaded_at, _ensure_started

    with _index_lock:
        if _index_cache is not None and not force_rebuild:
            if progress_cb:
                progress_cb("ready", len(_index_cache), len(_index_cache))
            return True

    # 已有索引文件 → 直接载入
    if INDEX_PATH.exists() and not force_rebuild:
        with _index_lock:
            _index_cache = _load_index_into_memory(INDEX_PATH)
            _index_loaded_at = time.time()
            ready = bool(_index_cache)
        if ready:
            logger.info("[problemset] 已加载本地索引: %d 题", len(_index_cache or {}))
            if progress_cb:
                progress_cb("ready", len(_index_cache or {}), len(_index_cache or {}))
        return ready

    # 第一次: 后台线程启动一次 download+build
    with _ensure_lock:
        global _ensure_started
        if not _ensure_started or force_rebuild:
            _ensure_started = True
            t = threading.Thread(
                target=_background_download_and_build,
                args=(progress_cb,),
                daemon=True,
                name="problemset-index-builder",
            )
            t.start()
        else:
            if progress_cb:
                progress_cb("ready", len(_index_cache or {}), len(_index_cache or {}))
        return _index_cache is not None


def download_and_build(
    progress_cb: Optional[Callable[[str, int, int], None]] = None,
    force_download: bool = False,
) -> bool:
    """
    同步执行: 下载 + 构建索引。
    force_download=True 时即使本地有缓存也重新下载(供管理员按钮用)。

    progress_cb(stage, done, total):
        stage in {"download", "build", "ready", "error"}
    """
    return _background_download_and_build(progress_cb, force_download=force_download, sync=True)


def _background_download_and_build(
    progress_cb: Optional[Callable[[str, int, int], None]],
    force_download: bool = False,
    sync: bool = False,
) -> bool:
    """
    实际执行: 下载 → 构建 → 写盘 → 载入内存。
    失败时只在 meta.json 写 last_error, 不抛。
    """
    global _index_cache, _index_loaded_at
    _ensure_dirs()

    def _cb(stage: str, done: int, total: int) -> None:
        if progress_cb:
            try:
                progress_cb(stage, done, total)
            except Exception:  # noqa: BLE001
                pass

    # 1) 下载
    need_download = force_download or not RAW_GZ_PATH.exists()
    if need_download:
        _cb("download", 0, 0)
        try:
            _download(PROBLEMSET_URL, RAW_GZ_PATH,
                      progress_cb=lambda d, t: _cb("download", d, t))
        except Exception as e:  # noqa: BLE001
            logger.exception("[problemset] 下载失败: %s", e)
            _write_meta({"last_error": f"download: {e}"})
            _cb("error", 0, 0)
            return False

    # 2) 解析 + 写索引
    _cb("build", 0, 0)
    try:
        index = _build_index_from_gz(
            RAW_GZ_PATH,
            progress_cb=lambda d, t: _cb("build", d, t),
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("[problemset] 解析失败: %s", e)
        _write_meta({"last_error": f"build: {e}"})
        _cb("error", 0, 0)
        return False

    _write_index_atomic(index, INDEX_PATH)
    with _index_lock:
        _index_cache = index
        _index_loaded_at = time.time()
    _write_meta({
        "last_download_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "last_build_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "problem_count": len(index),
        "last_error": "",
    })
    logger.info("[problemset] 索引就绪: %d 题", len(index))
    _cb("ready", len(index), len(index))
    return True


def _write_meta(extra: Dict[str, Any]) -> None:
    """追加/合并 meta.json"""
    base: Dict[str, Any] = {}
    if META_PATH.exists():
        try:
            base = json.loads(META_PATH.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            base = {}
    base.update(extra)
    tmp = META_PATH.with_suffix(".json.part")
    tmp.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, META_PATH)


# ---------- 查询 API ----------

def get(pid: str) -> Optional[Dict[str, Any]]:
    """单题查询, miss 时返回 None"""
    if not pid:
        return None
    with _index_lock:
        if _index_cache is None:
            # 尝试懒加载
            _ensure_index_loaded_locked()
        idx = _index_cache or {}
    return idx.get(pid)


def get_many(pids: List[str]) -> Dict[str, Dict[str, Any]]:
    """批量查询, miss 的 pid 不出现在结果里"""
    out: Dict[str, Dict[str, Any]] = {}
    if not pids:
        return out
    with _index_lock:
        if _index_cache is None:
            _ensure_index_loaded_locked()
        idx = _index_cache or {}
    for pid in pids:
        v = idx.get(pid)
        if v is not None:
            out[pid] = v
    return out


def _ensure_index_loaded_locked() -> None:
    """在 _index_lock 内调用: 尝试从磁盘载入"""
    global _index_cache, _index_loaded_at
    if _index_cache is not None:
        return
    if not INDEX_PATH.exists():
        return
    _index_cache = _load_index_into_memory(INDEX_PATH)
    _index_loaded_at = time.time()


# ---------- 给问题对象补全字段 ----------

def enrich_problem(problem: Any) -> int:
    """
    给 ProblemSummary-like 对象补全缓存里的字段。
    只补缺失的(已存在的字段不会被覆盖),所以可以放心多次调用。
    返回本次改动字段数。
    """
    pid = str(getattr(problem, "pid", "") or "")
    if not pid:
        return 0
    info = get(pid)
    if not info:
        return 0
    changed = 0
    # title
    if info.get("title") and not (getattr(problem, "title", "") or ""):
        try:
            problem.title = info["title"]
            changed += 1
        except Exception:  # noqa: BLE001
            pass
    # difficulty
    if info.get("difficulty") is not None and getattr(problem, "difficulty", None) is None:
        try:
            problem.difficulty = info["difficulty"]
            changed += 1
        except Exception:  # noqa: BLE001
            pass
    # difficulty_name (v3.11.0)
    cached_dn = info.get("difficulty_name")
    if cached_dn and not (getattr(problem, "difficulty_name", "") or ""):
        try:
            problem.difficulty_name = cached_dn
            changed += 1
        except Exception:  # noqa: BLE001
            pass
    # tags
    cached_tags = info.get("tags") or []
    if cached_tags and not (getattr(problem, "tags", []) or []):
        try:
            problem.tags = list(cached_tags)
            changed += 1
        except Exception:  # noqa: BLE001
            pass
    return changed


__all__ = [
    "PROBLEMSET_URL",
    "CACHE_DIR",
    "RAW_GZ_PATH",
    "INDEX_PATH",
    "DIFFICULTY_NAMES",
    "get_difficulty_name",
    "get_status",
    "ensure_ready",
    "download_and_build",
    "get",
    "get_many",
    "enrich_problem",
    "enrich_export_data",
]


# ---------- 给 export_data 补全 items ----------

def enrich_export_data(
    export_data: Dict[str, Any],
    *,
    max_items: int = 0,
) -> Dict[str, int]:
    """
    给 export_data 里的 passed_items / failed_items / records 补全缓存字段。
    只补缺失的(已有 title/difficulty/tags 的不会被覆盖)。

    max_items: 最多补多少题(0 = 不限), 用于极端大的报告场景。
    返回 {"passed": n, "failed": n, "records": n, "total_changed": n}
    """
    stats = {"passed": 0, "failed": 0, "records": 0, "total_changed": 0}
    if not isinstance(export_data, dict):
        return stats

    def _enrich_items(items: Any) -> int:
        if not isinstance(items, list):
            return 0
        n = 0
        for it in items:
            if not isinstance(it, dict):
                continue
            pid = str(it.get("pid") or "").strip()
            if not pid:
                continue
            info = get(pid)
            if not info:
                continue
            changed = 0
            # title (扁平 + 嵌套 problem 同步, 同时覆盖 ZIP 模式 (嵌套)
            # 和 HTML 源码模式 (扁平 + 嵌套) 的 item 结构)
            prob = it.get("problem") if isinstance(it.get("problem"), dict) else None
            if info.get("title") and not (it.get("title") or "").strip():
                it["title"] = info["title"]
                if prob is not None and not (prob.get("title") or "").strip():
                    prob["title"] = info["title"]
                changed += 1
            # difficulty
            if info.get("difficulty") is not None and it.get("difficulty") is None:
                it["difficulty"] = info["difficulty"]
                if prob is not None and prob.get("difficulty") is None:
                    prob["difficulty"] = info["difficulty"]
                changed += 1
            # difficulty_name (v3.11.0 · 中文标签)
            cached_dn = info.get("difficulty_name")
            if cached_dn and not (it.get("difficulty_name") or "").strip():
                it["difficulty_name"] = cached_dn
                if prob is not None and not (prob.get("difficulty_name") or "").strip():
                    prob["difficulty_name"] = cached_dn
                changed += 1
            # tags
            cached_tags = info.get("tags") or []
            if cached_tags and not (it.get("tags") or []):
                it["tags"] = list(cached_tags)
                if prob is not None and not (prob.get("tags") or []):
                    prob["tags"] = list(cached_tags)
                changed += 1
            n += changed
        return n

    for key, stat_key in (
        ("passed_items", "passed"),
        ("failed_items", "failed"),
        ("records", "records"),
    ):
        items = export_data.get(key)
        # max_items 限制(0 = 不限): 仅用于 records 这种可能很大的
        if max_items and isinstance(items, list) and len(items) > max_items:
            items = items[:max_items]
        changed = _enrich_items(items)
        stats[stat_key] = changed
        stats["total_changed"] += changed
    return stats
