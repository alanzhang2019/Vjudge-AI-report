"""elo_ranking.py - v3.13 · 洛谷 ELO 等级分排行榜前 10 名
============================================================
设计目标:
  - admin 一次性在 /admin/elo/settings 粘贴自己的洛谷 cookies (__client_id + _uid)
  - 后台线程每 N 小时自动调 pyLuogu.get_elo_ranking, 写 DB
  - /ranking/elo 公开页面展示最新快照
  - 兜底: 如果自动抓取失败, admin 还可在 /admin/elo/upload 粘贴 HTML 源码
  - 每个 top 10 用户如果在本平台生成过报告, 复用显示
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 提取用户链接和用户名:  <a href="/user/366807">lgvc</a>
# 注意: 洛谷页面用户名可能在 <a> 之前/之后, 也可能被 <span> 包裹 (如 medal)
_RE_USER_LINK = re.compile(
    r'href="/user/(\d{6,10})"[^>]*>([^<]+)</a>',
    re.S
)

# 排名锚点: #1, #2 ... #46
_RE_RANK = re.compile(r'#(\d{1,3})\b')

# 提取分数 (3-4 位数字, 在 user link 之后 200 字符内)
_RE_RATING = re.compile(r'>(\d{3,4})<')


def _parse_elo_html(html: str, top_n: int = 10) -> List[Dict[str, Any]]:
    """从 luogu ELO ranking HTML 源码提取 top N (默认 10) 用户

    洛谷页面结构 (从 WebFetch 推断, 简化 markdown 渲染后):
      #1 [lgvc](https://www.luogu.com.cn/user/366807)
      2943
      2026-04-18 / 【LGR-282-Div.1】洛谷 4 月月赛 II & 蓬莱人形 Round 2
      2936  7
      65

      #2 [hos_lyric](https://www.luogu.com.cn/user/530741)
      2935

    但用户粘贴的 HTML 源码内部结构可能更复杂 (含 <a> 标签, etc.).
    我们用一个更宽松的解析: 找 #N 位置 -> 在前后 1500 字符内找 /user/<uid>,
    然后在 /user/<uid> 附近 500 字符内找 rating (3-4 位数字).

    Returns:
        [
            {"rank": 1, "uid": 366807, "name": "lgvc", "rating": 2943, "color": "red"},
            ...
        ]
    """
    results: List[Dict[str, Any]] = []
    seen_uids = set()

    for m in re.finditer(r'#(\d{1,3})\b', html):
        rank = int(m.group(1))
        # 找后面 1500 字符内的 /user/<uid> 链接
        tail = html[m.end():m.end() + 1500]
        # 注意: Luogu uid 最短 5 位 (如 10703), 最长 10 位
        user_m = re.search(r'href="/user/(\d{1,12})"[^>]*>([^<]+)</a>', tail)
        if not user_m:
            # 尝试 markdown 格式: [name](https://www.luogu.com.cn/user/uid)
            user_m = re.search(r'\((\d{1,12})\)', tail)  # 洛谷 markdown 链接
            if not user_m:
                continue
            uid = int(user_m.group(1))
            name = "?"
        else:
            uid = int(user_m.group(1))
            name = user_m.group(2).strip()

        if uid in seen_uids:
            continue
        seen_uids.add(uid)

        # 找 rating: 在 user link 后面 600 字符内的 3-4 位数字
        # 注意: user_m.end() 是 tail 内的位置, 需加 m.end() 偏移回到 html 内
        link_end_in_html = m.end() + user_m.end()
        ctx = html[link_end_in_html:link_end_in_html + 600]
        rating = 0
        for rm in re.finditer(r'\b(\d{3,4})\b', ctx):
            val = int(rm.group(1))
            if 500 <= val <= 5000:  # ELO 合理范围
                rating = val
                break
        color = _rating_to_color(rating)
        results.append({
            "rank": rank,
            "uid": uid,
            "name": name,
            "rating": rating,
            "color": color,
        })
        if len(results) >= top_n:
            break
    return results


def _rating_to_color(rating: int) -> str:
    """洛谷 color tier (类似 codeforces)
    gray(<1200) green(<1400) cyan(<1600) blue(<1900) purple(<2100) yellow(<2400) orange(<2600) red(<3000) legendary
    """
    if rating < 1200: return "gray"
    if rating < 1400: return "green"
    if rating < 1600: return "cyan"
    if rating < 1900: return "blue"
    if rating < 2100: return "purple"
    if rating < 2400: return "yellow"
    if rating < 2600: return "orange"
    if rating < 3000: return "red"
    return "legendary"


_COLOR_HEX = {
    "gray": "#9ca3af",
    "green": "#22c55e",
    "cyan": "#06b6d4",
    "blue": "#3b82f6",
    "purple": "#a855f7",
    "yellow": "#eab308",
    "orange": "#f97316",
    "red": "#ef4444",
    "legendary": "#dc2626",
}

_COLOR_LABEL = {
    "gray": "灰",
    "green": "绿",
    "cyan": "青",
    "blue": "蓝",
    "purple": "紫",
    "yellow": "黄",
    "orange": "橙",
    "red": "红",
    "legendary": "传奇",
}

_COLOR_BG_CLASS = {
    "gray": "bg-gray-100 text-gray-700",
    "green": "bg-green-100 text-green-700",
    "cyan": "bg-cyan-100 text-cyan-700",
    "blue": "bg-blue-100 text-blue-700",
    "purple": "bg-purple-100 text-purple-700",
    "yellow": "bg-yellow-100 text-yellow-700",
    "orange": "bg-orange-100 text-orange-700",
    "red": "bg-red-100 text-red-700",
    "legendary": "bg-gradient-to-r from-red-500 to-yellow-500 text-white",
}


def get_color_hex(color: str) -> str:
    return _COLOR_HEX.get(color, "#9ca3af")


def get_color_label(color: str) -> str:
    return _COLOR_LABEL.get(color, color)


def get_color_bg_class(color: str) -> str:
    return _COLOR_BG_CLASS.get(color, "bg-gray-100 text-gray-700")


# ---------- DB 操作 ----------

ELO_SCHEMA = """
CREATE TABLE IF NOT EXISTS elo_top10 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rank INTEGER NOT NULL,
    uid INTEGER NOT NULL,
    name TEXT NOT NULL,
    rating INTEGER DEFAULT 0,
    color TEXT DEFAULT 'gray',
    snapshot_at TEXT NOT NULL,
    UNIQUE(snapshot_at, uid)
);
CREATE INDEX IF NOT EXISTS idx_elo_top10_uid ON elo_top10(uid);
CREATE INDEX IF NOT EXISTS idx_elo_top10_snapshot ON elo_top10(snapshot_at DESC);

-- v3.13b · admin 一次性保存的洛谷 cookies, 用于后台自动抓取 ELO 排行榜
-- 单行表 (id=1), 每次 save_admin_cookies() 会覆盖
CREATE TABLE IF NOT EXISTS elo_admin_cookies (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    client_id TEXT NOT NULL,
    luogu_uid TEXT NOT NULL,
    c3vk TEXT DEFAULT '',
    saved_at TEXT NOT NULL,
    last_used_at TEXT,
    last_status TEXT,
    last_message TEXT
);

-- v3.13b · 自动抓取历史, 方便排查
CREATE TABLE IF NOT EXISTS elo_fetch_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fetched_at TEXT NOT NULL,
    source TEXT NOT NULL,           -- 'auto' / 'manual_api' / 'manual_html'
    ok INTEGER NOT NULL,            -- 0/1
    user_count INTEGER DEFAULT 0,
    duration_ms INTEGER DEFAULT 0,
    message TEXT
);
CREATE INDEX IF NOT EXISTS idx_elo_fetch_log_time ON elo_fetch_log(fetched_at DESC);
"""


def _get_conn(db_path: str) -> sqlite3.Connection:
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    return c


def init_elo_schema(db_path: str) -> None:
    c = _get_conn(db_path)
    c.executescript(ELO_SCHEMA)
    c.commit()
    c.close()


def save_elo_snapshot(db_path: str, top_users: List[Dict[str, Any]], snapshot_at: str) -> int:
    """保存一次 top 10 快照, 返回 snapshot_id (即最新 snapshot_at 的 id)"""
    c = _get_conn(db_path)
    # 先删旧 snapshot (只保留最新一次)
    c.execute("DELETE FROM elo_top10")
    for u in top_users:
        c.execute(
            "INSERT INTO elo_top10 (rank, uid, name, rating, color, snapshot_at) VALUES (?, ?, ?, ?, ?, ?)",
            (u["rank"], u["uid"], u["name"], u["rating"], u["color"], snapshot_at),
        )
    c.commit()
    snap_id = c.execute("SELECT MAX(id) FROM elo_top10").fetchone()[0]
    c.close()
    return snap_id


def get_latest_elo_top10(db_path: str) -> List[Dict[str, Any]]:
    """获取最新一次快照的 top 10"""
    c = _get_conn(db_path)
    # 取最新 snapshot_at
    latest = c.execute("SELECT MAX(snapshot_at) FROM elo_top10").fetchone()[0]
    if not latest:
        c.close()
        return []
    rows = c.execute(
        "SELECT rank, uid, name, rating, color, snapshot_at FROM elo_top10 WHERE snapshot_at=? ORDER BY rank ASC",
        (latest,),
    ).fetchall()
    c.close()
    return [dict(r) for r in rows]


def get_snapshot_meta(db_path: str) -> Optional[Dict[str, Any]]:
    """获取最新 snapshot 的元信息 (snapshot_at + 用户数)"""
    c = _get_conn(db_path)
    latest = c.execute("SELECT MAX(snapshot_at), COUNT(*) FROM elo_top10").fetchone()
    c.close()
    if not latest or not latest[0]:
        return None
    return {"snapshot_at": latest[0], "count": latest[1]}


def find_user_report(db_path: str, luogu_uid: int) -> Optional[Dict[str, Any]]:
    """在 tasks 表里找该 uid 最新一份成功生成的报告 (status=done, html 非空)

    Returns: {"task_id": ..., "html_path": ..., "solved_count": ..., "created_at": ...} or None
    """
    c = _get_conn(db_path)
    row = c.execute(
        "SELECT task_id, html, solved_count, failed_count, created_at, student_name FROM tasks WHERE luogu_uid=? AND status='done' AND html != '' ORDER BY created_at DESC LIMIT 1",
        (str(luogu_uid),),
    ).fetchone()
    c.close()
    if not row:
        return None
    return dict(row)


# ---------- v3.13b · admin cookies + 自动抓取 ----------

def save_admin_cookies(
    db_path: str,
    client_id: str,
    luogu_uid: str,
    c3vk: str = "",
) -> Dict[str, Any]:
    """保存 admin 的洛谷 cookies (单行覆盖). client_id/_uid 是必填."""
    if not client_id or not luogu_uid:
        raise ValueError("client_id 和 luogu_uid 不能为空")
    saved_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    c = _get_conn(db_path)
    c.execute("DELETE FROM elo_admin_cookies")
    c.execute(
        "INSERT INTO elo_admin_cookies (id, client_id, luogu_uid, c3vk, saved_at) VALUES (1, ?, ?, ?, ?)",
        (client_id.strip(), str(luogu_uid).strip(), (c3vk or "").strip(), saved_at),
    )
    c.commit()
    c.close()
    return {"saved_at": saved_at, "client_id": client_id[:8] + "...", "luogu_uid": luogu_uid}


def get_admin_cookies(db_path: str) -> Optional[Dict[str, Any]]:
    """获取 admin cookies, 不存在返回 None"""
    c = _get_conn(db_path)
    row = c.execute("SELECT * FROM elo_admin_cookies WHERE id=1").fetchone()
    c.close()
    return dict(row) if row else None


def delete_admin_cookies(db_path: str) -> bool:
    c = _get_conn(db_path)
    cur = c.execute("DELETE FROM elo_admin_cookies WHERE id=1")
    c.commit()
    c.close()
    return cur.rowcount > 0


def update_admin_cookies_status(db_path: str, status: str, message: str = "") -> None:
    """每次抓取后, 记录 last_status/last_message/last_used_at"""
    used_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    c = _get_conn(db_path)
    c.execute(
        "UPDATE elo_admin_cookies SET last_used_at=?, last_status=?, last_message=? WHERE id=1",
        (used_at, status, message[:500]),
    )
    c.commit()
    c.close()


def log_fetch(db_path: str, source: str, ok: bool, user_count: int, duration_ms: int, message: str = "") -> None:
    """记录一次抓取"""
    c = _get_conn(db_path)
    c.execute(
        "INSERT INTO elo_fetch_log (fetched_at, source, ok, user_count, duration_ms, message) VALUES (?, ?, ?, ?, ?, ?)",
        (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), source, 1 if ok else 0, user_count, duration_ms, message[:500]),
    )
    c.commit()
    c.close()


def get_recent_fetch_log(db_path: str, limit: int = 10) -> List[Dict[str, Any]]:
    c = _get_conn(db_path)
    rows = c.execute(
        "SELECT fetched_at, source, ok, user_count, duration_ms, message FROM elo_fetch_log ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    c.close()
    return [dict(r) for r in rows]


def _normalize_elo_api_response(api_resp: Any, top_n: int = 10) -> List[Dict[str, Any]]:
    """把 pyLuogu.get_elo_ranking 返回值转成 [{rank, uid, name, rating, color}, ...]

    api_resp 通常是 RankingListRequestResponse 对象, 有 .users 属性
    每个 user 是 RankingUser (TypedDict), 含 uid/name/rating 字段
    """
    results: List[Dict[str, Any]] = []
    # RankingListRequestResponse 类似 dict-like (Pydantic-like)
    if api_resp is None:
        return results
    if isinstance(api_resp, dict):
        users = api_resp.get("users") or []
    else:
        users = getattr(api_resp, "users", None) or []
    for i, u in enumerate(users[:top_n], start=1):
        if isinstance(u, dict):
            uid = int(u.get("uid") or 0)
            name = (u.get("name") or "").strip() or "?"
            rating = int(u.get("rating") or 0)
        else:
            uid = int(getattr(u, "uid", 0) or 0)
            name = (getattr(u, "name", "") or "?").strip() or "?"
            rating = int(getattr(u, "rating", 0) or 0)
        if uid <= 0:
            continue
        results.append({
            "rank": i,
            "uid": uid,
            "name": name,
            "rating": rating,
            "color": _rating_to_color(rating),
        })
    return results


def try_fetch_elo_via_api(db_path: str, source: str = "auto") -> Dict[str, Any]:
    """用 admin cookies 调 pyLuogu.get_elo_ranking, 写 DB

    Returns: {
        "ok": bool,
        "users": [...],
        "message": str,
        "duration_ms": int,
        "cf_blocked": bool,  # v3.13b · True 表示 Cloudflare 拦了服务器 IP (与 cookies 无关)
    }
    """
    t0 = time.time()
    cookies_row = get_admin_cookies(db_path)
    if not cookies_row:
        msg = "未配置 admin cookies, 跳过自动抓取"
        log_fetch(db_path, source, False, 0, int((time.time() - t0) * 1000), msg)
        return {"ok": False, "users": [], "message": msg, "duration_ms": int((time.time() - t0) * 1000), "cf_blocked": False}

    # 懒加载 pyLuogu, 避免循环依赖
    try:
        import pyLuogu
    except ImportError as e:
        msg = f"pyLuogu 导入失败: {e}"
        log_fetch(db_path, source, False, 0, int((time.time() - t0) * 1000), msg)
        return {"ok": False, "users": [], "message": msg, "duration_ms": int((time.time() - t0) * 1000), "cf_blocked": False}

    client_id = cookies_row.get("client_id", "")
    luogu_uid = cookies_row.get("luogu_uid", "")
    c3vk = cookies_row.get("c3vk", "")
    cookies_dict = {"__client_id": client_id, "_uid": str(luogu_uid)}
    if c3vk:
        cookies_dict["C3VK"] = c3vk

    try:
        cookies = pyLuogu.LuoguCookies(cookies_dict)
        api = pyLuogu.luoguAPI(cookies=cookies)
        resp = api.get_elo_ranking(page=1)
        users = _normalize_elo_api_response(resp, top_n=10)
        duration_ms = int((time.time() - t0) * 1000)
        if not users:
            msg = f"pyLuogu 返回空 users (duration={duration_ms}ms)"
            update_admin_cookies_status(db_path, "fail_empty", msg)
            log_fetch(db_path, source, False, 0, duration_ms, msg)
            return {"ok": False, "users": [], "message": msg, "duration_ms": duration_ms, "cf_blocked": False}
        snapshot_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        save_elo_snapshot(db_path, users, snapshot_at)
        msg = f"抓取成功, 共 {len(users)} 人"
        update_admin_cookies_status(db_path, "ok", msg)
        log_fetch(db_path, source, True, len(users), duration_ms, msg)
        return {"ok": True, "users": users, "message": msg, "duration_ms": duration_ms, "cf_blocked": False}
    except Exception as e:
        duration_ms = int((time.time() - t0) * 1000)
        err_short = f"{type(e).__name__}: {str(e)[:200]}"
        # v3.13b · 诊断: pyLuogu 抛 ForbiddenError 时, 真正原因是 Cloudflare 拦了 server IP
        # 而不是 cookies 失效 (cookies 有效时, Cloudflare 仍然先 ban IP 再 ban cookies)
        is_cf = "Forbidden" in err_short or "403" in err_short
        update_admin_cookies_status(
            db_path,
            "fail_cf_blocked" if is_cf else "fail",
            err_short,
        )
        log_fetch(db_path, source, False, 0, duration_ms, err_short)
        return {"ok": False, "users": [], "message": err_short, "duration_ms": duration_ms, "cf_blocked": is_cf}


# ---------- v3.13b · 后台定时调度器 ----------

_ELO_FETCH_INTERVAL_SEC = 6 * 3600  # 6 小时一次
_elo_scheduler_started = False
_elo_scheduler_lock = threading.Lock()
_module_logger = logging.getLogger("elo_ranking")


def _elo_scheduler_loop() -> None:
    """后台线程主循环: 启动后 30s 跑一次, 之后每 6h 跑一次"""
    _module_logger.info("[v3.13b/elo] scheduler started, interval=6h")
    # 启动后稍等 30s, 避免和 web 启动抢资源
    time.sleep(30)
    while True:
        try:
            result = try_fetch_elo_via_api("/app/data/tasks.db", source="auto")
            _module_logger.info(f"[v3.13b/elo] auto fetch: ok={result.get('ok')} msg={result.get('message')}")
        except Exception as e:
            _module_logger.error(f"[v3.13b/elo] scheduler tick err: {e}")
        time.sleep(_ELO_FETCH_INTERVAL_SEC)


def start_elo_scheduler() -> bool:
    """web_app 启动时调用, 启动后台抓取线程 (只启一次)"""
    global _elo_scheduler_started
    with _elo_scheduler_lock:
        if _elo_scheduler_started:
            return False
        t = threading.Thread(target=_elo_scheduler_loop, name="elo-auto-fetcher", daemon=True)
        t.start()
        _elo_scheduler_started = True
        _module_logger.info("[v3.13b/elo] scheduler thread spawned")
        return True
