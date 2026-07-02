import os
import json
import argparse
import math
import re
import hashlib
import time
import urllib.request
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Any, Callable

from env_loader import load_dotenv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from rich.console import Console
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from openai import OpenAI
import pyLuogu
from pyLuogu.errors import AuthenticationError, ForbiddenError, RequestError
from examples.export_for_ai import (
    DETAIL_FETCH_SAMPLE_LIMIT_FAILED,
    DETAIL_FETCH_SAMPLE_LIMIT_PASSED,
    _build_tag_maps,
    _summarize,
    _pick_record_for_problem,
)

import markdown as md

load_dotenv(Path(__file__).resolve().parent / ".env")
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

console = Console()
DEFAULT_REPORT_MD = "luogu_coach_report.md"
DEFAULT_REPORT_HTML = "luogu_coach_report.html"
DEFAULT_REPORT_PDF = "luogu_coach_report.pdf"
DEFAULT_ASSETS_DIR = "luogu_report_assets"

DIAGNOSTIC_FRAMEWORK = """
【能力评估参考框架】（请对照此框架对用户进行诊断和分级建议）：
1. S级 - 计数与组合推导：赛时容易先写DFS/枚举，缺乏“统计对象集合”思维。需强化：组合数/容斥/DP/生成函数。
2. S级 - 图论建模与最短路变形：模板能写但建图边含义不稳，差分约束/分层图易卡。需强化：图的语义定义、最短路树。
3. A级 - 数据结构维护不变量：基础线段树能做，多标记易WA。需强化：节点信息明确数学定义、merge/pushdown的代数正确性。
4. A级 - DP 状态设计与优化：常规DP能写，维度多易爆复杂度。需强化：树形/区间/状压DP，单调队列优化。
5. A级 - 部分分升级能力：赛时能拿部分分，但不会倒推。需强化：从小n、小值域、树退化等子任务倒推正解。
6. B级 - 高级字符串结构：KMP/Hash有基础，自动机/SAM不稳定。需强化：节点代表的集合、Fail树/link的含义。
7. B级 - 计算几何：缺模板，少边界意识。需强化：向量/叉积、凸包、扫描线基础与eps处理。
8. B级 - 网络流/匹配：缺乏模式识别。需强化：建图谱系、最小割模型、费用流。
9. S级 - 复盘与错因沉淀：盲目改代码AC后就过。需强化：四段式复盘（赛时模型、错因、正解性质、代码不变量）。
"""


def find_chinese_font_path() -> str | None:
    def _try_download_lxgw_wenkai(dest_dir: Path) -> str | None:
        auto = os.environ.get("LUOGU_REPORT_AUTO_FONT_DOWNLOAD", "").strip().lower() in {"1", "true", "yes", "on"}
        if not auto:
            return None

        dest_dir.mkdir(parents=True, exist_ok=True)
        version = "1.520"
        zip_name = f"lxgw-wenkai-v{version}.zip"
        url = f"https://github.com/lxgw/LxgwWenKai/releases/download/v{version}/{zip_name}"
        expected_sha256 = "3a763543bec896e3c1badc9808bc804116a5e3d26f9f9592dacc834c9e799d8c"
        zip_path = dest_dir / zip_name
        extracted_font = dest_dir / "LXGWWenKai-Regular.ttf"

        if extracted_font.exists():
            return str(extracted_font)

        if zip_path.exists():
            try:
                h = hashlib.sha256()
                with open(zip_path, "rb") as f:
                    for chunk in iter(lambda: f.read(1024 * 1024), b""):
                        h.update(chunk)
                if h.hexdigest().lower() != expected_sha256:
                    zip_path.unlink(missing_ok=True)
            except Exception:
                try:
                    zip_path.unlink(missing_ok=True)
                except Exception:
                    pass

        if not zip_path.exists():
            tmp_path = dest_dir / (zip_name + ".tmp")
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "luogu-ai-report/1.0"})
                with urllib.request.urlopen(req, timeout=20) as resp, open(tmp_path, "wb") as out:
                    while True:
                        buf = resp.read(1024 * 1024)
                        if not buf:
                            break
                        out.write(buf)
                h = hashlib.sha256()
                with open(tmp_path, "rb") as f:
                    for chunk in iter(lambda: f.read(1024 * 1024), b""):
                        h.update(chunk)
                if h.hexdigest().lower() != expected_sha256:
                    tmp_path.unlink(missing_ok=True)
                    return None
                tmp_path.replace(zip_path)
            except Exception:
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass
                return None

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                member = f"lxgw-wenkai-v{version}/LXGWWenKai-Regular.ttf"
                if member not in zf.namelist():
                    return None
                tmp_extract = dest_dir / (extracted_font.name + ".tmp")
                with zf.open(member) as src, open(tmp_extract, "wb") as dst:
                    dst.write(src.read())
                tmp_extract.replace(extracted_font)
            return str(extracted_font) if extracted_font.exists() else None
        except Exception:
            return None

    env_font = os.environ.get("CHINESE_FONT_PATH") or os.environ.get("LUOGU_REPORT_FONT_PATH")
    if env_font and os.path.exists(env_font):
        return env_font

    local_candidates: list[str] = []
    try:
        base = Path(__file__).resolve().parent
        downloaded = _try_download_lxgw_wenkai(base / "assets" / "fonts")
        if downloaded and os.path.exists(downloaded):
            return downloaded
        local_candidates.extend(
            [
                str(base / "assets" / "fonts" / "NotoSansCJKsc-Regular.otf"),
                str(base / "assets" / "fonts" / "NotoSansSC-Regular.otf"),
                str(base / "assets" / "fonts" / "SourceHanSansCN-Regular.otf"),
                str(base / "assets" / "fonts" / "wqy-zenhei.ttc"),
                str(base / "assets" / "fonts" / "LXGWWenKai-Regular.ttf"),
            ]
        )
    except Exception:
        pass

    candidates = [
        *local_candidates,
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyh.ttf",
        r"C:\Windows\Fonts\msyhbd.ttf",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simkai.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJKsc-Regular.otf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/arphic/ukai.ttc",
        "/usr/share/fonts/truetype/arphic/uming.ttc",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    try:
        from matplotlib import font_manager

        preferred_families = [
            "Noto Sans CJK SC",
            "Noto Sans SC",
            "Source Han Sans CN",
            "WenQuanYi Zen Hei",
            "WenQuanYi Micro Hei",
            "Microsoft YaHei",
            "SimHei",
            "PingFang SC",
            "Arial Unicode MS",
        ]
        for family in preferred_families:
            try:
                fp = font_manager.FontProperties(family=family)
                font_file = font_manager.findfont(fp, fallback_to_default=False)
                if font_file and os.path.exists(font_file):
                    return font_file
            except Exception:
                continue
    except Exception:
        pass
    try:
        from matplotlib import font_manager

        keywords = (
            "notosanscjk",
            "notosanssc",
            "sourcehansans",
            "noto sans cjk",
            "noto sans sc",
            "wqy",
            "wenquanyi",
            "droidsansfallback",
            "arphic",
            "ukai",
            "uming",
            "simhei",
            "msyh",
            "yahei",
            "pingfang",
        )
        for font_path in font_manager.findSystemFonts(fontpaths=None, fontext="ttf") + font_manager.findSystemFonts(fontpaths=None, fontext="ttc") + font_manager.findSystemFonts(fontpaths=None, fontext="otf"):
            lower = font_path.lower()
            if any(k in lower for k in keywords) and os.path.exists(font_path):
                return font_path
    except Exception:
        pass
    return None


def configure_matplotlib_font() -> str | None:
    font_path = find_chinese_font_path()
    family_fallback = [
        "Noto Sans CJK SC",
        "Noto Sans SC",
        "Source Han Sans CN",
        "WenQuanYi Zen Hei",
        "WenQuanYi Micro Hei",
        "Microsoft YaHei",
        "SimHei",
        "PingFang SC",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    if font_path:
        try:
            from matplotlib import font_manager

            font_manager.fontManager.addfont(font_path)
            font_name = font_manager.FontProperties(fname=font_path).get_name()
            plt.rcParams["font.sans-serif"] = [font_name, *family_fallback]
        except Exception:
            plt.rcParams["font.sans-serif"] = family_fallback
    else:
        plt.rcParams["font.sans-serif"] = family_fallback
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 12
    plt.rcParams["axes.titlesize"] = 14
    plt.rcParams["axes.labelsize"] = 12
    plt.rcParams["xtick.labelsize"] = 11
    plt.rcParams["ytick.labelsize"] = 11
    return font_path


def register_pdf_font() -> str:
    font_path = find_chinese_font_path()
    if font_path:
        try:
            pdfmetrics.registerFont(TTFont("CoachChinese", font_path))
            return "CoachChinese"
        except Exception:
            pass
    return "Helvetica"


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


# v3.11.0 · 洛谷官方 9 档难度中文标签 + 配色 (与 luogu.com.cn 网页端"难易度统计"完全对齐)
# 实际取数发现: problemset_open API(difficulty 0-7,合并版) 与 学员练习数据 / 网页端
# 难易度统计(difficulty 0-8,9 档版) 不一致。学员提交数据已升级到 9 档,
# 但旧版命名/循环范围还是 0-7 共 8 档, 导致 difficulty>=3 的标签全部错位 1 档、
# difficulty=8 越界归到"暂无评定"、最后一档题数(NOI/NOI+/CTS)被丢弃。
# 本表按 9 档展开, 顺序与洛谷网页一致, 颜色按洛谷网页标签色取值。
DIFFICULTY_NAME_MAP = {
    0: "暂无评定",
    1: "入门",
    2: "普及-",
    3: "普及",
    4: "普及+/提高-",
    5: "提高",
    6: "提高+/省选-",
    7: "省选/NOI-",
    8: "NOI/NOI+/CTS",
}

DIFFICULTY_COLOR_MAP = {
    0: "#9CA3AF",
    1: "#FE4C61",
    2: "#F39C12",
    3: "#FFC116",
    4: "#52C41A",
    5: "#52C41A",   # 提高 (与洛谷网页"提高"绿保持一致)
    6: "#3498DB",
    7: "#9D4EDD",
    8: "#0E1D69",   # NOI/NOI+/CTS (与原 NOI/NOI+/CTSC 深蓝保持一致)
}

DIFFICULTY_TEXT_COLOR_MAP = {
    0: "#111827",
    1: "#FFFFFF",
    2: "#111827",
    3: "#111827",
    4: "#FFFFFF",
    5: "#FFFFFF",
    6: "#FFFFFF",
    7: "#FFFFFF",
    8: "#FFFFFF",
}

TAG_CHART_PALETTE = [
    "#52C41A",
    "#3498DB",
    "#9D4EDD",
    "#FE4C61",
    "#F39C12",
    "#14B8A6",
    "#FFC116",
    "#0EA5E9",
]


def _render_progress_bar(percentage: float, color: str, width_px: int = 150) -> str:
    pct = max(0.0, min(100.0, float(percentage)))
    return (
        f'<span style="display:inline-block;width:{width_px}px;height:12px;'
        'background:#E5E7EB;border-radius:9999px;overflow:hidden;vertical-align:middle;">'
        f'<span style="display:block;width:{pct:.1f}%;height:12px;background:{color};"></span>'
        "</span>"
    )


def get_difficulty_style(level: int) -> tuple[str, str, str]:
    return (
        DIFFICULTY_NAME_MAP.get(level, str(level)),
        DIFFICULTY_COLOR_MAP.get(level, "#4B5563"),
        DIFFICULTY_TEXT_COLOR_MAP.get(level, "#FFFFFF"),
    )


def summarize_average_difficulty(difficulty_histogram: dict) -> dict[str, str | int | float]:
    total = 0
    weighted = 0
    for key, value in difficulty_histogram.items():
        if str(key).isdigit():
            level = int(key)
            if level <= 0:
                continue
            total += int(value)
            weighted += level * int(value)

    average_value = weighted / total if total else 0.0
    candidate_levels = [k for k in DIFFICULTY_NAME_MAP.keys() if int(k) > 0]
    nearest_level = min(candidate_levels, key=lambda level: abs(level - average_value)) if total and candidate_levels else 0
    label, color, text_color = get_difficulty_style(nearest_level)
    return {
        "average_value": average_value,
        "nearest_level": nearest_level,
        "label": label,
        "color": color,
        "text_color": text_color,
    }


def render_star_rating_html(stars: str) -> str:
    filled_count = stars.count("⭐")
    empty_count = stars.count("☆")
    total_count = filled_count + empty_count
    if total_count == 0 or total_count > 5:
        return stars

    star_items = []
    for ch in stars:
        if ch == "⭐":
            star_items.append('<span style="color:#F5C542;text-shadow:0 1px 0 rgba(0,0,0,0.18);">★</span>')
        elif ch == "☆":
            star_items.append('<span style="color:#94A3B8;">★</span>')
        else:
            star_items.append(ch)

    return (
        '<span style="display:inline-flex;align-items:center;gap:2px;'
        'padding:2px 8px;border-radius:9999px;background:#111827;'
        'border:1px solid #374151;box-shadow:inset 0 1px 0 rgba(255,255,255,0.06);'
        'font-size:1.02em;line-height:1.1;vertical-align:middle;">'
        + "".join(star_items)
        + f'<span style="margin-left:6px;color:#CBD5E1;font-size:12px;font-weight:700;">{filled_count}/{total_count}</span>'
        "</span>"
    )


def split_practice_problems(practice) -> tuple[list[pyLuogu.ProblemSummary], list[pyLuogu.ProblemSummary]]:
    practice_problems = list(getattr(practice, "problems", []) or [])
    if practice_problems:
        passed = [p for p in practice_problems if getattr(p, "accepted", False)]
        failed = [p for p in practice_problems if getattr(p, "submitted", False) and not getattr(p, "accepted", False)]
        if passed or failed:
            return passed, failed

    raw = practice.data if isinstance(getattr(practice, "data", None), dict) else None
    passed: list[pyLuogu.ProblemSummary] = []
    failed: list[pyLuogu.ProblemSummary] = []
    passed_ids: set[str] = set()

    for key, target, accepted in (("passed", passed, True), ("submitted", failed, False), ("failed", failed, False)):
        items = raw.get(key) if isinstance(raw, dict) else None
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            pid = item.get("pid")
            if not pid:
                continue
            pid = str(pid)
            if accepted:
                passed_ids.add(pid)
            elif pid in passed_ids:
                continue
            target.append(
                pyLuogu.ProblemSummary(
                    {
                        "pid": pid,
                        "title": item.get("title") or item.get("name") or "",
                        "difficulty": item.get("difficulty"),
                        "type": item.get("type"),
                        "submitted": True,
                        "accepted": accepted,
                        "tags": item.get("tags") or [],
                        "totalSubmit": item.get("totalSubmit"),
                        "totalAccepted": item.get("totalAccepted"),
                        "flag": item.get("flag"),
                        "fullScore": item.get("fullScore"),
                    }
                )
            )
    return passed, failed


def collect_record_dicts(items: list[dict]) -> list[dict]:
    records: list[dict] = []
    for item in items:
        record = item.get("record")
        if isinstance(record, dict) and record.get("submitTime"):
            records.append(record)
    return records


def summarize_detail_fetch_stats(
    passed_items: list[dict] | None,
    failed_items: list[dict] | None,
    detail_fetch_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    items = list(passed_items or []) + list(failed_items or [])
    stats = {
        "total_items": len(items),
        "source_code_success": 0,
        "summary_only": 0,
        "detail_requested": 0,
        "detail_skipped": 0,
        "detail_errors": 0,
        "pure_error_records": 0,
        "blocker_reason": "",
    }
    for item in items:
        record = item.get("record")
        if not isinstance(record, dict):
            continue
        if record.get("_detail_requested"):
            stats["detail_requested"] += 1
        if record.get("sourceCode"):
            stats["source_code_success"] += 1
            continue
        if record.get("submitTime"):
            stats["summary_only"] += 1
        if record.get("_detail_skipped"):
            stats["detail_skipped"] += 1
            if not stats["blocker_reason"]:
                stats["blocker_reason"] = str(record.get("_detail_skipped") or "")
        if record.get("_detail_error"):
            stats["detail_errors"] += 1
            if not stats["blocker_reason"]:
                stats["blocker_reason"] = str(record.get("_detail_error") or "")
        if record.get("error") and not record.get("submitTime"):
            stats["pure_error_records"] += 1
            if not stats["blocker_reason"]:
                stats["blocker_reason"] = str(record.get("error") or "")

    if isinstance(detail_fetch_state, dict) and detail_fetch_state.get("last_detail_error"):
        stats["blocker_reason"] = str(detail_fetch_state.get("last_detail_error") or stats["blocker_reason"])
    return stats


def build_detail_fetch_overview(detail_fetch_stats: dict | None) -> dict[str, Any]:
    stats = detail_fetch_stats or {}
    total_items = int(stats.get("total_items", 0))
    source_code_success = int(stats.get("source_code_success", 0))
    summary_only = int(stats.get("summary_only", 0))
    detail_skipped = int(stats.get("detail_skipped", 0))
    pure_error_records = int(stats.get("pure_error_records", 0))
    blocker_reason = str(stats.get("blocker_reason") or "")

    if total_items <= 0:
        status_label = "未抓取详情"
        status_bg = "#E5E7EB"
        status_fg = "#374151"
    elif pure_error_records > 0:
        status_label = "存在失败"
        status_bg = "#FEE2E2"
        status_fg = "#991B1B"
    elif detail_skipped > 0:
        status_label = "已触发止损"
        status_bg = "#FEF3C7"
        status_fg = "#92400E"
    elif source_code_success > 0:
        status_label = "抓取稳定"
        status_bg = "#DCFCE7"
        status_fg = "#166534"
    else:
        status_label = "仅摘要保底"
        status_bg = "#DBEAFE"
        status_fg = "#1D4ED8"

    return {
        "status_label": status_label,
        "status_bg": status_bg,
        "status_fg": status_fg,
        "source_code_success": source_code_success,
        "summary_only": summary_only,
        "detail_skipped": detail_skipped,
        "pure_error_records": pure_error_records,
        "blocker_reason": blocker_reason or "无",
    }


def describe_behavior_fetch_error(exc: Exception) -> str:
    if isinstance(exc, AuthenticationError):
        return "未登录或 Cookies 已失效，无法读取提交记录列表"
    if isinstance(exc, ForbiddenError):
        return f"无权访问提交记录列表：{exc}"
    if isinstance(exc, RequestError):
        if getattr(exc, "status_code", None) == 429:
            return "请求提交记录过于频繁，请稍后重试"
        return f"请求提交记录失败：{exc}"
    message = str(exc).strip()
    if message:
        return message
    return "未获取到有效提交记录"


def enrich_problem_tags(
    luogu: pyLuogu.luoguAPI,
    problems: list[pyLuogu.ProblemSummary],
    *,
    max_fetch: int | None = None,
    progress_callback: Callable[[int, int, int], None] | None = None,
) -> int:
    """
    为缺失 tags 的题目按需补全标签。
    优先使用 practice.problems 自带标签；只有为空时才走 problem_detail 兜底。
    返回本次成功补全的题目数量。

    progress_callback(fetched, enriched, total_missing) 在每道题处理完后调用，
    用于向前端实时反馈标签抓取进度；传 None 则不回调。

    v3.9.14 · 增加 per-problem 标签持久化缓存（_PROBLEM_TAGS_CACHE_FILE），
    同一道题再次生成报告时直接命中缓存，避免每次都打洛谷 API。
    之前每次重试都重新抓 100+ 道题详情，慢且易触发风控。
    """
    enriched = 0
    fetched = 0
    cache: dict[str, list[int]] = {}
    persistent_cache: dict[str, list[int]] = _load_problem_tags_cache()  # v3.9.14

    # 先一次性统计需要补全的题目总数，方便前端显示 "X/Y" 进度
    missing_indices = [
        i for i, p in enumerate(problems)
        if not list(getattr(p, "tags", []) or [])
    ]
    total_missing = len(missing_indices)
    if progress_callback is not None:
        try:
            progress_callback(0, 0, total_missing)
        except Exception:
            pass

    for idx, problem in enumerate(problems):
        existing_tags = list(getattr(problem, "tags", []) or [])
        if existing_tags:
            continue
        if max_fetch is not None and fetched >= max_fetch:
            break

        pid = str(getattr(problem, "pid", "") or "")
        if not pid:
            continue

        try:
            # v3.9.14 · 先看进程内 cache（同一调用内去重）
            if pid not in cache:
                # v3.9.14 · 再看持久化磁盘 cache（跨调用/跨重试命中）
                if pid in persistent_cache and persistent_cache[pid]:
                    cache[pid] = list(persistent_cache[pid])
                else:
                    fetched += 1
                    detail = luogu.get_problem(pid)
                    problem_detail = getattr(detail, "problem", None)
                    cache[pid] = list(getattr(problem_detail, "tags", []) or [])
                    # v3.9.14 · 写回持久化 cache（即便为空也写，避免反复打空题）
                    persistent_cache[pid] = cache[pid]
            if cache[pid]:
                problem.tags = list(cache[pid])
                enriched += 1
        except Exception:
            continue

        if progress_callback is not None:
            try:
                progress_callback(fetched, enriched, total_missing)
            except Exception:
                pass

    # v3.9.14 · 把本轮新增的 tags 写回磁盘
    if fetched > 0 or any(cache):
        try:
            _save_problem_tags_cache(persistent_cache)
        except Exception:
            pass

    return enriched


# ========== v3.9.14 · per-problem 标签持久化缓存（解决重试重抓） ==========
# 全局共享：_ROOT/.source_cache/_problem_tags.json
# 格式：{"P1000": [1, 2, 3], "P1001": [4, 5], ...}
# 洛谷题目标签基本不变（管理员改标签才会动），TTL = 永久
_PROBLEM_TAGS_CACHE_FILE = Path(__file__).parent / ".source_cache" / "_problem_tags.json"
_PROBLEM_TAGS_CACHE_LOCK = __import__("threading").Lock()  # 写并发保护


def _load_problem_tags_cache() -> dict[str, list[int]]:
    """读取 _PROBLEM_TAGS_CACHE_FILE → {pid: [tag_id, ...]}"""
    if not _PROBLEM_TAGS_CACHE_FILE.exists():
        return {}
    try:
        payload = json.loads(_PROBLEM_TAGS_CACHE_FILE.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {}
        out: dict[str, list[int]] = {}
        for k, v in payload.items():
            if not isinstance(v, list):
                continue
            try:
                out[str(k)] = [int(x) for x in v if x is not None]
            except (TypeError, ValueError):
                continue
        return out
    except Exception:
        return {}


def _save_problem_tags_cache(cache: dict[str, list[int]]) -> None:
    """原子写：先写 .tmp → os.replace 防止半文件"""
    _PROBLEM_TAGS_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _PROBLEM_TAGS_CACHE_LOCK:
        # 合并已有（避免被覆盖丢条目）
        existing = _load_problem_tags_cache()
        existing.update(cache)
        tmp = _PROBLEM_TAGS_CACHE_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, _PROBLEM_TAGS_CACHE_FILE)


def fetch_behavior_analysis(luogu: pyLuogu.luoguAPI, uid: int, fallback_items: list[dict] | None = None) -> dict:
    from behavior_analyzer import analyze_submission_behavior

    raw_records: list[dict] = []
    last_error = None
    for page in range(1, 26):
        try:
            record_list = luogu.get_record_list(page=page, uid=uid, user=str(uid))
            page_records = getattr(record_list, "records", None) or getattr(record_list, "data", None) or []
            normalized_records = [
                rec.to_json() if hasattr(rec, "to_json") else rec
                for rec in page_records
            ]
        except Exception as e:
            last_error = describe_behavior_fetch_error(e)
            break

        if not normalized_records:
            break
        raw_records.extend(normalized_records)
        if len(normalized_records) < 20 or len(raw_records) >= 1000:
            break

    if raw_records:
        behavior = analyze_submission_behavior(raw_records)
        behavior["_source"] = "record_list"
        if last_error:
            behavior["_warning"] = last_error
        return behavior

    fallback_records = collect_record_dicts(fallback_items or [])
    if fallback_records:
        behavior = analyze_submission_behavior(fallback_records)
        behavior["_source"] = "record_detail_fallback"
        if last_error:
            behavior["_warning"] = last_error
        return behavior

    return {"error": last_error or "未获取到有效提交记录"}


def repair_behavior_analysis_from_items(export_data: dict) -> dict:
    behavior = export_data.get("behavior_analysis", {}) or {}
    if behavior and "error" not in behavior and behavior.get("personality_scores"):
        return behavior

    fallback_records = collect_record_dicts(
        list(export_data.get("passed_items", []) or []) + list(export_data.get("failed_items", []) or [])
    )
    if not fallback_records:
        return behavior or {"error": "未获取到有效提交记录"}

    from behavior_analyzer import analyze_submission_behavior

    repaired = analyze_submission_behavior(fallback_records)
    repaired["_source"] = "record_detail_fallback_repaired"
    if behavior.get("_warning"):
        repaired["_warning"] = str(behavior["_warning"])
    elif behavior.get("error"):
        repaired["_warning"] = str(behavior["error"])
    export_data["behavior_analysis"] = repaired
    return repaired


def _level_status_for_gesp(
    level_info: dict,
    top_tags_map: dict[str, int],
    diff_hist: dict[str | int, int],
    passed_levels: set[int],
    level: int,
) -> tuple[str, str, int, str]:
    """v3.9.66 · 计算学员在某个 GESP 级别下的状态。

    Returns:
        (status_emoji_text, core_tags_matched, max_diff_ac, risk_text)
    """
    core_tags = level_info.get("core_tags") or []
    themes = level_info.get("themes") or []
    max_diff = int(level_info.get("max_difficulty") or 1)

    # 1) 真考直通：学员 GESP 真考已通过该级（最权威）
    if level in passed_levels:
        return ("🟢已掌握", len(core_tags), 0, "GESP 真考已通过（最权威）")

    # 2) 计算 core_tags 在学员 top_tags 里的命中数
    matched_tags = [t for t in core_tags if t in top_tags_map]
    matched_n = len(matched_tags)
    coverage = matched_n / max(1, len(core_tags))

    # 3) 计算学员在该级要求难度区间内 AC 题数（d ≤ max_diff）
    max_diff_ac = 0
    for d in range(1, max_diff + 1):
        max_diff_ac += int(diff_hist.get(str(d), diff_hist.get(d, 0)))

    if max_diff_ac == 0 and matched_n == 0:
        status = "🔴未接触"
        risk = "学员在洛谷上未训练过该级任何题目，AI 估算无依据"
    elif coverage >= 0.8 and max_diff_ac >= 30:
        status = "🟢已掌握"
        risk = f"已覆盖 {matched_n}/{len(core_tags)} 核心 tag，难度覆盖充分（{max_diff_ac} 题）"
    elif coverage >= 0.5 and max_diff_ac >= 10:
        status = "🟡部分掌握"
        risk = f"覆盖 {matched_n}/{len(core_tags)} tag，建议补齐缺失项"
    elif matched_n >= 1 or max_diff_ac >= 1:
        status = "🟠薄弱"
        risk = f"仅覆盖 {matched_n}/{len(core_tags)} tag，难度覆盖偏少（{max_diff_ac} 题）"
    else:
        status = "🔴未接触"
        risk = "无 GESP 真考 + 无洛谷相关 tag 训练"

    return (status, matched_n, max_diff_ac, risk)


def build_gesp_trusted_data_summary_md(
    export_data: dict,
    target_level: int = 1,
    highest_passed: int = 0,
) -> str:
    """v3.9.66 · GESP 报告专用可信块。

    跟 NOI 版（`build_trusted_data_summary_md`）的关键区别：
      1. **不再注入 NOI 4 级（入门/提高/省选/NOI）知识树**——GESP 报告按 8 级展开
      2. 新增"GESP 8 级知识地图"表，1-8 级全列
      3. 每级显示：主题 / 关键知识点（top 3） / 学员状态 / 核心 tag 覆盖 / 难度覆盖 / 风险点
      4. 状态判定优先级：GESP 真考 > 洛谷 tag 覆盖 + 难度覆盖 > 默认未接触

    Args:
        export_data: 与 NOI 版共享的 export_data
        target_level: 学员目标 GESP 级别（1-8），用于高亮目标行
        highest_passed: 学员已通过的最高 GESP 级别（0=无），用于状态判断

    Returns:
        str: Markdown 字符串，包含 "## 数据校准与真实统计" 主标题
    """
    student_info = export_data.get("student_info", {}) or {}
    eval_time = str(student_info.get("eval_time") or "")
    summary = export_data.get("summary", {}) or {}
    diff_hist = summary.get("difficulty_histogram", {}) or {}

    # 解析 top_tags → {tag_name: count} 映射
    top_tags_list = summary.get("top_algorithm_tags", []) or summary.get("top_tags", []) or []
    top_tags_map: dict[str, int] = {}
    for item in top_tags_list:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("id") or "").strip()
            count = int(item.get("count", 0) or 0)
            if name:
                top_tags_map[name] = top_tags_map.get(name, 0) + count

    passed_levels = set(int(x) for x in (highest_passed and [highest_passed]) or [])

    # 难度分布统计 (v3.11.0 扩展为 0-8 共 9 档, 与洛谷网页"难易度统计"对齐)
    total_ac = 0
    for d in range(1, 9):
        total_ac += int(diff_hist.get(str(d), diff_hist.get(d, 0)))
    total_ac = total_ac or 1

    lines = [
        "## 数据校准与真实统计（GESP 8 级版）",
        f"- 报告生成时间：{eval_time or '未知'}",
        f"- 测评体系：**GESP**（1-8 级）· 目标级别：**GESP {target_level} 级** · 已通过最高级：{highest_passed or '暂无'}",
        "",
        "> ⚠️ v3.9.66 · 本节按 **GESP 1-8 级官方考纲** 展示学员覆盖度，"
        "不再使用 NOI/CSP 4 级（入门/提高/省选/NOI）体系。"
        "GESP 1-3 级（基础编程 / 顺序分支 / 数组字符串 / 排序函数）在洛谷上题目较少，"
        "若学员 GESP 真考已通过，**直接信任**真考结果；若仅看洛谷数据，"
        "**不要轻易判定『未掌握』**——可能只是没在洛谷上训练。",
        "",
        "### 难度分布（程序生成）",
        '<table><thead><tr><th>洛谷难度</th><th>题数</th><th>占比</th><th>分布图</th></tr></thead><tbody>',
    ]

    for level in range(1, 9):  # v3.11.0 扩展为 0-8 共 9 档
        count = int(diff_hist.get(str(level), diff_hist.get(level, 0)))
        name = DIFFICULTY_NAME_MAP[level]
        color = DIFFICULTY_COLOR_MAP[level]
        pct = count * 100 / total_ac
        badge = (
            f'<span style="display:inline-block;padding:2px 10px;border-radius:6px;'
            f'background:{color};color:#fff;font-weight:600;">{name}</span>'
        )
        lines.append(
            "<tr>"
            f"<td>{badge}</td>"
            f"<td>{count}</td>"
            f"<td>{pct:.1f}%</td>"
            f"<td>{_render_progress_bar(pct, color)} <span style=\"margin-left:8px;\">{pct:.1f}%</span></td>"
            "</tr>"
        )
    lines.extend(["</tbody></table>", ""])

    # ===== 核心：GESP 8 级知识地图 =====
    lines.extend([
        "### GESP 8 级知识地图 · 学员覆盖度",
        '<table><thead><tr>'
        '<th>级别</th><th>名称</th><th>主题</th><th>学员状态</th>'
        '<th>核心 tag 覆盖</th><th>难度覆盖</th><th>风险 / 备注</th>'
        '</tr></thead><tbody>',
    ])

    for lv in range(1, 9):
        info = GESP_LEVELS[lv]
        status, matched_n, max_diff_ac, risk = _level_status_for_gesp(
            info, top_tags_map, diff_hist, passed_levels, lv,
        )
        core_tags = info.get("core_tags") or []
        themes = info.get("themes") or []
        max_diff = int(info.get("max_difficulty") or 1)
        total_core = len(core_tags)

        # 目标级别行高亮
        row_style = ""
        if lv == target_level:
            row_style = ' style="background:#FEF3C7;border-left:4px solid #F59E0B;" '
        elif lv < target_level:
            row_style = ' style="background:#F0FDF4;" '  # 浅绿：已通过或目标前的级别
        elif lv == target_level + 1:
            row_style = ' style="background:#EFF6FF;" '  # 浅蓝：下一跳级目标

        # 核心 tag 显示：已匹配 / 总数
        if total_core == 0:
            tag_cov_cell = "—"
        else:
            pct = matched_n * 100 / total_core
            tag_cov_cell = (
                f'<span style="font-weight:600;">{matched_n}/{total_core}</span>'
                f'<br><span style="color:#6b7280;font-size:11px;">{pct:.0f}%</span>'
            )

        # 难度覆盖
        if max_diff_ac == 0:
            diff_cell = '<span style="color:#9ca3af;">0 题</span>'
        elif max_diff_ac >= 30:
            diff_cell = f'<span style="color:#16A34A;font-weight:600;">{max_diff_ac} 题</span>'
        else:
            diff_cell = f'{max_diff_ac} 题'

        # 主题 + 关键知识点提示
        themes_str = " / ".join(themes[:3]) + ("…" if len(themes) > 3 else "")

        # 学员状态徽章
        if "🟢" in status:
            status_badge = (
                f'<span style="display:inline-block;padding:2px 10px;border-radius:10px;'
                f'background:#16A34A;color:#fff;font-size:12px;font-weight:600;">{status}</span>'
            )
        elif "🟡" in status:
            status_badge = (
                f'<span style="display:inline-block;padding:2px 10px;border-radius:10px;'
                f'background:#CA8A04;color:#fff;font-size:12px;font-weight:600;">{status}</span>'
            )
        elif "🟠" in status:
            status_badge = (
                f'<span style="display:inline-block;padding:2px 10px;border-radius:10px;'
                f'background:#EA580C;color:#fff;font-size:12px;font-weight:600;">{status}</span>'
            )
        elif "🔴" in status:
            status_badge = (
                f'<span style="display:inline-block;padding:2px 10px;border-radius:10px;'
                f'background:#DC2626;color:#fff;font-size:12px;font-weight:600;">{status}</span>'
            )
        else:
            status_badge = status

        # 目标级标记
        lv_name = info.get("name", f"GESP {lv} 级")
        if lv == target_level:
            lv_name = f"🎯 **{lv_name}**（目标）"
        elif highest_passed and lv == highest_passed:
            lv_name = f"✅ {lv_name}"

        lines.append(
            f"<tr{row_style}>"
            f"<td><strong>{lv}</strong></td>"
            f"<td>{lv_name}</td>"
            f"<td style=\"font-size:12px;color:#374151;\">{themes_str}</td>"
            f"<td>{status_badge}</td>"
            f"<td>{tag_cov_cell}</td>"
            f"<td>≤{DIFFICULTY_NAME_MAP.get(max_diff, '?')}: {diff_cell}</td>"
            f"<td style=\"font-size:12px;color:#4b5563;\">{risk}</td>"
            "</tr>"
        )

    lines.extend([
        "</tbody></table>",
        "",
        "- 口径说明：",
        "  - **学员状态**判定优先级：`GESP 真考` > `洛谷核心 tag 覆盖度 × 难度覆盖` > 默认未接触；",
        "  - **核心 tag 覆盖** = 学员洛谷做题数据中匹配该级 `core_tags` 的数量 / 该级 `core_tags` 总数；",
        "  - **难度覆盖** = 学员 AC 题数中，难度 ≤ 该级 `max_difficulty` 的题目总数；",
        "  - **GESP 1-3 级**（基础编程 / 顺序分支 / 数组字符串）在洛谷上可用题源较少，"
        "若学员 GESP 真考已通过，**直接信任**真考结果；",
        "  - 🎯 黄色行 = 目标级别，✅ 绿色行 = 学员已通过最高级。",
    ])

    return "\n".join(lines)


def _build_gesp_difficulty_section_md(export_data: dict) -> str:
    """v3.9.66 · GESP 报告的"难度分布"小节（NOI 版用的是"水平研判"，这里保留）"""
    summary = export_data.get("summary", {}) or {}
    hist = summary.get("difficulty_histogram", {}) or {}
    solved = int(export_data.get("solved_count", 0))
    failed = int(export_data.get("failed_count", 0))
    total_attempted = solved + failed

    def _count(levels: list[int]) -> int:
        s = 0
        for lv in levels:
            s += int(hist.get(str(lv), hist.get(lv, 0)))
        return s

    z1 = _count([1, 2, 3])
    z2 = _count([4, 5])
    z3 = _count([6])
    z4 = _count([7])
    z_total = max(1, z1 + z2 + z3 + z4)

    def _pct(v: int) -> str:
        return f"{(v * 100 / z_total):.1f}%"

    avg_info = summarize_average_difficulty(hist)
    avg_label = str(avg_info.get("label") or "")

    lines = [
        "## 3. 难度分布与水平研判（GESP 版）",
        "",
        "![](assets/difficulty_histogram.png)",
        "",
        "![](assets/status_ratio.png)",
        "",
        f"- 平均难度：{avg_label}（均值 {float(avg_info.get('average_value') or 0):.2f}）",
        f"- 题目覆盖区间：入门~普及/提高-(1-3) {z1} 题（{_pct(z1)}）；"
        f"普及+/提高~提高+/省选-(4-5) {z2} 题（{_pct(z2)}）；"
        f"省选/NOI-(6) {z3} 题（{_pct(z3)}）；"
        f"NOI/NOI+/CTSC(7) {z4} 题（{_pct(z4)}）。",
    ]
    if total_attempted > 0:
        lines.append(f"- 通过/未通过：已通过 {solved} 题，未通过 {failed} 题（总尝试 {total_attempted}）。")
    lines.append("")
    lines.append("> 💡 GESP 备考口径：学员在洛谷上的难度分布只是参考，"
                "GESP 真考级别才是最权威的能力基线。GESP 1-3 级（基础编程）的题目"
                "在洛谷上少，建议以真考分 + 官方考纲为主，不要被洛谷数据误导。")
    return "\n".join(lines)


def build_trusted_data_summary_md(export_data: dict) -> str:
    student_info = export_data.get("student_info", {}) or {}
    eval_time = str(student_info.get("eval_time") or "")
    summary = export_data.get("summary", {}) or {}
    difficulty_histogram = summary.get("difficulty_histogram", {}) or {}
    level_experience = summary.get("level_experience", {}) or {}
    detail_fetch_stats = export_data.get("detail_fetch_stats", {}) or {}
    syllabus_eval = export_data.get("syllabus_evaluation", {}) or {}

    total = 0
    for level in range(1, 9):  # v3.11.0 扩展为 0-8 共 9 档
        total += int(difficulty_histogram.get(str(level), difficulty_histogram.get(level, 0)))
    total = total or 1
    lines = [
        "## 数据校准与真实统计",
        f"- 报告生成时间：{eval_time or '未知'}",
    ]
    lines.extend([
        "",
        "### 难度分布（程序生成）",
        '<table><thead><tr><th>洛谷难度</th><th>题数</th><th>占比</th><th>分布图</th></tr></thead><tbody>',
    ])

    for level in range(1, 9):  # v3.11.0 扩展为 0-8 共 9 档
        count = int(difficulty_histogram.get(str(level), difficulty_histogram.get(level, 0)))
        name = DIFFICULTY_NAME_MAP[level]
        color = DIFFICULTY_COLOR_MAP[level]
        pct = count * 100 / total
        badge = (
            f'<span style="display:inline-block;padding:2px 10px;border-radius:6px;'
            f'background:{color};color:#fff;font-weight:600;">{name}</span>'
        )
        lines.append(
            "<tr>"
            f"<td>{badge}</td>"
            f"<td>{count}</td>"
            f"<td>{pct:.1f}%</td>"
            f"<td>{_render_progress_bar(pct, color)} <span style=\"margin-left:8px;\">{pct:.1f}%</span></td>"
            "</tr>"
        )
    lines.extend([
        "</tbody></table>",
    ])
    lines.extend(
        [
            "",
            "### 知识点覆盖统计表（按算法标签）",
            '<table><thead><tr><th>级别</th><th>已覆盖/总数</th><th>覆盖率</th><th>掌握度分布</th></tr></thead><tbody>',
        ]
    )

    for key, label in (
        ("csp_j", "入门级（CSP-J）"),
        ("csp_s", "提高级（CSP-S）"),
        ("provincial", "省选级"),
        ("noi", "NOI级"),
    ):
        group = syllabus_eval.get(key, {}) or {}
        stats = group.get("stats", {}) or {}
        detail_list = group.get("details", []) or []
        total_topics = int(stats.get("total", 0))
        covered = total_topics - int(stats.get("空白", 0))
        coverage = group.get("coverage", 0)
        # "掌握度分布"列：本意是展示这一级别分组下，**所有**知识点 topic
        # 按掌握度（精通/熟练/入门/初窥/空白）的分布，颜色用绿色深浅，与知识树果子一致。
        # 注意：与"已覆盖/总数"列的对应关系是——
        #   精通 + 熟练 + 入门 + 初窥 = "已覆盖"（AC ≥ 1）
        #   空白 = "未覆盖"（AC = 0）
        #   总数 = 上述 5 档合计
        m1 = m2 = m3 = m4 = m5 = 0
        # v3.9.48 · 5 档分别收集知识点名字（用于"掌握度分布"列展示明细）
        by_level: dict[str, list[str]] = {"精通": [], "熟练": [], "入门": [], "初窥": [], "空白": []}
        for item in detail_list:
            if not isinstance(item, dict):
                continue
            ac = int(item.get("ac_count", 0) or 0)
            topic = str(item.get("topic", "")).strip()
            level = _level_for_ac(ac)
            if not topic:
                continue
            by_level.setdefault(level, []).append(topic)
            if level == "精通":
                m1 += 1
            elif level == "熟练":
                m2 += 1
            elif level == "入门":
                m3 += 1
            elif level == "初窥":
                m4 += 1
            else:
                m5 += 1

        def _chip(color: str, n: int, lbl: str, topics: list[str], *, fg: str = "#fff", bd: str = "") -> str:
            """v3.9.49 · chip 顶部显示「N项 + 全部知识点名」（不再截断）
            v3.9.48 旧版只显示前 2 个 + "…"，用户反馈"应该列出全部知识点明细"。
            现改为：count 在前，下面 <br> 换行后逐个列出全部 topics，
            CSS 用 max-width + word-wrap 兜底，避免长行撑爆。
            """
            border_style = f"border:1px solid {bd};" if bd else ""
            # tooltip 仍保留（鼠标 hover 看全）
            tip = "、".join(topics) if topics else "（无）"
            topic_html = ""
            if topics:
                topic_html = (
                    "<br><span style=\"font-size:10px;font-weight:400;"
                    "line-height:1.45;display:inline-block;max-width:240px;"
                    "word-break:break-all;\">"
                    + "、".join(topics)
                    + "</span>"
                )
            return (
                f'<span title="{tip}" style="display:inline-block;padding:3px 8px;'
                f'border-radius:6px;background:{color};color:{fg};'
                f'{border_style}'
                f'font-size:11px;font-weight:600;margin:2px 4px 2px 0;cursor:help;'
                f'vertical-align:top;text-align:left;">'
                f'{lbl} {n}项{topic_html}</span>'
            )

        details = (
            _chip("#14532D", m1, "精通", by_level["精通"])
            + _chip("#166534", m2, "熟练", by_level["熟练"])
            + _chip("#16A34A", m3, "入门", by_level["入门"])
            + _chip("#86EFAC", m4, "初窥", by_level["初窥"], fg="#064E3B", bd="#4ADE80")
            + _chip("#FFFFFF", m5, "空白", by_level["空白"], fg="#6B7280", bd="#9CA3AF")
        )
        lines.append(f"<tr><td><strong>{label.split('（')[0].replace('级','')}</strong></td><td>{covered}/{total_topics}</td><td>{coverage}%</td><td>{details}</td></tr>")

    lines.extend(
        [
            "</tbody></table>",
            "",
            "- 口径说明：",
            "  - 行 = 级别（入门/提高/省选/NOI），列 = 已覆盖/总数、覆盖率、**掌握度分布**。",
            "  - **掌握度分布**展示该级别下所有知识点 topic 按掌握度 5 档（精通/熟练/入门/初窥/空白）的分布，颜色用绿色深浅：精通近黑→熟练深绿→入门标准绿→初窥浅绿→空白白。",
            "  - 与前一列的对应：精通 + 熟练 + 入门 + 初窥 = “已覆盖”（AC ≥ 1）；空白 = “未覆盖”（AC = 0）；5 档合计 = “总数”。",
            "- 备注：本表只根据题目的算法标签评估知识点覆盖，表示“接触过”，不等于“熟练掌握”。",
        ]
    )

    # ------------------------------------------------------------------
    # 掌握度判定标准小节（独立 H2）
    # 重要：必须用 H2 而非 H3。normalize_report_markdown 会用
    # "^## 知识点覆盖统计表（按算法标签）..." 整块吞掉 AI 重复生成的统计表，
    # "掌握度判定标准"作为同级 H2 不会被吞，会原样保留。
    # ------------------------------------------------------------------
    def _legend_chip(c: dict, name: str) -> str:
        """无数字的纯色块图例（用于判定标准表的"颜色图例"列）。"""
        border = f"border:1px solid {c.get('bd','')};" if c.get('bd') else ""
        return (
            f'<span style="display:inline-block;padding:2px 12px;'
            f'border-radius:6px;background:{c["fill"]};color:{c["fg"]};'
            f'{border}font-size:12px;font-weight:600;">{name}</span>'
        )

    lines.append("")
    lines.append("## 掌握度判定标准（5 档）")
    lines.append(
        '<table><thead><tr>'
        '<th>掌握度</th><th>判定标准（AC 题目数）</th><th>颜色图例</th>'
        '</tr></thead><tbody>'
    )
    for name, rule in _MASTERY_RULES:
        chip = _legend_chip(_MASTERY_COLOR[name], name)
        lines.append(
            f'<tr><td><strong>{name}</strong></td><td>{rule}</td><td>{chip}</td></tr>'
        )
    lines.append("</tbody></table>")
    lines.append(
        "- 口径说明：5 档阈值是『知识点覆盖统计表』中『掌握度分布』列的统一判定标准；"
        "AC = 实际通过的题目数（去重）；『空白』档使用灰色警示色，提示该知识点未接触。"
    )

    # 知识树图谱（HTML 块，python-markdown 会原样保留到最终 HTML）
    # 关键：包一层 page-break + 大标题，让它独占一页、视觉上不会被表格吞掉
    # 注：python-markdown 默认不解析 <div> 内的 markdown 语法，所以直接用 <h2>
    lines.append("")
    lines.append('<div style="page-break-before:always;margin-top:24px;">')
    lines.append('<h2 style="font-size:1.45rem;font-weight:700;color:#065F46;border-bottom:3px solid #10B981;padding-bottom:8px;margin:18px 0 12px 0;">🌳 知识树图谱（按算法标签 · 掌握度可视化）</h2>')
    lines.append("")
    lines.append('<p style="color:#6B7280;font-size:14px;margin:6px 0 14px 0;">下图按 4 个竞赛级别（CSP-J / CSP-S / 省选 / NOI）展示所有考纲知识点的掌握度。果子**大小 + 颜色**都按"掌握度"用绿色深浅表示（精通近黑 / 熟练深绿 / 入门绿 / 初窥浅绿 / 空白白）。把鼠标悬停在果子上可查看 AC 题目数、掌握等级与关联题目的难度。</p>')
    lines.append(build_knowledge_tree_html(syllabus_eval))
    lines.append('</div>')

    return "\n".join(lines)


# 果子视觉映射：单轴 + 渐变
#   颜色（绿色深浅）→ 掌握度 5 档：精通近黑 / 熟练深绿 / 入门绿 / 初窥浅绿 / 空白白
#   大小 → 掌握度（冗余维度，便于色弱辨识）
# 难度信息（1-7）从果子的视觉上完全撤除，只在 hover 提示文字里展示。

# 难度（1-7，0=无数据）→ 颜色档
# 用途仅剩：(1) 报告里"题目难度分布"直方图，(2) 知识树果子 hover 提示文字。
# **果子本身的填色不再使用 _DIFF_TIER**，改用 _MASTERY_COLOR（掌握度绿深浅），
# 所以这里只保留 hover 提示用的"name"字段。
# 洛谷官方 7 档难度名：暂无评定、入门、普及-、普及/提高-、普及+/提高、提高+/省选-、省选/NOI-、NOI/NOI+/CTSC
_DIFF_TIER: dict[int, dict] = {
    0: dict(name="未知", fill="#9CA3AF", fg="#FFFFFF", bd="#6B7280"),
    1: dict(name="入门", fill="#F5222D", fg="#FFFFFF", bd="#A8071A"),
    2: dict(name="普及-", fill="#FA541C", fg="#FFFFFF", bd="#AD3811"),
    3: dict(name="普及/提高-", fill="#FAAD14", fg="#FFFFFF", bd="#AD8B14"),
    4: dict(name="提高+/提高", fill="#52C41A", fg="#FFFFFF", bd="#389E0D"),
    5: dict(name="提高+/省选-", fill="#1890FF", fg="#FFFFFF", bd="#096DD9"),
    6: dict(name="省选/NOI-", fill="#722ED1", fg="#FFFFFF", bd="#531DAB"),
    7: dict(name="NOI/NOI+/CTSC", fill="#2F54EB", fg="#FFFFFF", bd="#1D39C4"),
}

# 掌握度 5 档 → AC 题目数判定阈值（单一来源）
# 顺序敏感：判定时从高到低匹配（精通 → 空白），与 _MASTERY_VIS / _MASTERY_COLOR 对齐。
# 报告中的"掌握度判定标准"小节直接读取本表渲染，_level_for_ac() 同步遵守。
# 备注：AC = 实际通过的题目数（去重），与"知识点覆盖统计表"中的 AC 口径一致。
_MASTERY_RULES: list[tuple[str, str]] = [
    ("精通", "AC ≥ 20 道"),
    ("熟练", "10 ≤ AC ≤ 19"),
    ("入门", "3  ≤ AC ≤ 9"),
    ("初窥", "1  ≤ AC ≤ 2"),
    ("空白", "AC = 0（警示色：未接触该知识点）"),
]

# 掌握度 → 果子半径（r 越大 = AC 越多 = 掌握越好）
# 最小 r=6 仍清晰可辨；最大 r=18
_MASTERY_VIS: dict[str, dict] = {
    "精通": dict(r=18, fs=12, fw=700),
    "熟练": dict(r=15, fs=11, fw=700),
    "入门": dict(r=12, fs=11, fw=600),
    "初窥": dict(r=9,  fs=10, fw=500),
    "空白": dict(r=7,  fs=9,  fw=400),
}

# 掌握度 → 果子颜色（fill/fg/bd）
# 需求：果子颜色按"掌握度"用绿色深浅表示，5 档映射：
#   精通 = 深绿近黑（Tailwind green-900）
#   熟练 = 深绿      (Tailwind green-800)
#   入门 = 标准绿    (Tailwind green-600)
#   初窥 = 浅绿      (Tailwind green-300)
#   空白 = 纯白      (深绿边框区分)
# 关键决策：放弃之前的"难度色（红/橙/绿/蓝/深蓝）"映射，难度信息
# 通过知识树分支分类、图例说明等其它维度展示，避免果子颜色维度重复。
_MASTERY_COLOR: dict[str, dict] = {
    "精通": dict(fill="#14532D", fg="#FFFFFF", bd="#052E16"),  # 深绿近黑
    "熟练": dict(fill="#166534", fg="#FFFFFF", bd="#14532D"),  # 深绿
    "入门": dict(fill="#16A34A", fg="#FFFFFF", bd="#166534"),  # 标准绿
    "初窥": dict(fill="#86EFAC", fg="#064E3B", bd="#4ADE80"),  # 浅绿
    "空白": dict(fill="#FFFFFF", fg="#6B7280", bd="#9CA3AF"),  # 白底+灰边+灰字
}
# 题目难度 → 颜色（与图例 5 档严格一致）
# 关键修复：之前当题目难度=1（入门）时会把"空白"也染成红色，违反图例。
# 现在新增"掌握度优先"分支：若 level=="空白" 或 level=="初窥"，用 _MASTERY_COLOR；
# 否则用难度色 _DIFF_TIER。


# 知识点 → 分类的关键词映射（树形分组用）
# 顺序敏感：先匹配先赢，所以"图论"要在"数据结构"之前以避免"树"被错配
# v3.9.40 · 补全缺失关键词（4 个级别都受益）：
#   - 基础实现：Flood Fill、前缀和、差分、离散化、离线、随机化
#   - 数据结构：栈/队列/链表/二叉树/哈夫曼/BST + 笛卡尔/虚树/LCT/圆方树/k-d/替罪羊/WBLT/析合
#   - 图论：图遍历、匈牙利/二分图匹配、2-SAT、上下界、KM、次短路
#   - 字符串：拉链式关键词已覆盖
#   - 数学/数论：gcd/素数/筛法/排列/组合/杨辉 + 同余/费马/逆元/扩展欧几里得/快速幂
#                 /容斥/卡特兰/鸽巢/二项式/莫比乌斯/Burnside/Polya/BSGS/单位根/单纯形
#                 /Pollard-Rho/Miller-Rabin/杜教筛/Min_25筛/FWT/四边形不等式/位集合
#   - 搜索/DFS：迭代加深
_CATEGORY_KEYWORDS = (
    ("基础实现", ["模拟", "枚举", "排序", "高精度", "进制", "字符串基础", "递推", "分治", "构造",
                 "前缀和", "差分", "flood", "填充", "离散化", "离线", "随机化",
                 "位运算", "位操作", "进制转换"]),
    ("搜索/DFS", ["搜索", "dfs", "bfs", "回溯", "剪枝", "递归", "双向搜索", "启发式", "迭代加深", "a*"]),
    ("动态规划", ["dp", "动态规划", "背包", "区间dp", "树形dp", "状压", "数位dp", "记忆化", "概率dp", "四边形不等式"]),
    ("贪心/二分", ["贪心", "二分", "倍增", "三分", "中位数"]),
    # 图遍历/次短路/2-SAT/上下界/匈牙利/KM 关键词必须在"数据结构"之前
    ("图论", ["图遍历", "图的遍历", "图", "最短路", "dijkstra", "floyd", "spfa", "tarjan", "lca", "并查集",
             "网络流", "二分图", "匹配", "拓扑", "差分约束", "最小生成树", "mst", "基环树", "欧拉",
             "次短路", "2-sat", "上下界", "km算法", "匈牙利"]),
    # 数据结构：含"bst/二叉搜索树"必须在"二叉树"前（避免"二叉树遍历"被错配"bst"）
    # v3.9.50 · 补 stl 关键词（CSP-J 常见考点）
    ("数据结构", ["bst", "二叉搜索树", "哈夫曼", "栈", "队列", "链表", "二叉树",
                 "线段树", "树状数组", "堆", "单调栈", "单调队列", "平衡树", "st表", "treap", "splay", "红黑树",
                 "字典树", "trie", "树链剖分", "树剖", "树分治", "cdq", "kdtree", "kd树", "k-d", "树套树", "跳表", "左偏树",
                 "笛卡尔树", "虚树", "lct", "link-cut", "圆方树", "替罪羊", "wblt", "析合树",
                 "分块", "莫队",
                 "bitset", "位集合", "stl"]),
    ("字符串", ["kmp", "字符串", "hash", "sam", "后缀", "manacher", "ac自动机", "回文", "z函数", "最小表示"]),
    # 数学/数论：把"gcd/素数/筛法/排列/组合/杨辉"等基础数论关键词补全 + 高级数论/代数
    ("数学/数论", ["gcd", "最大公约数", "辗转相除", "素数", "质数", "筛法", "杨辉", "组合", "排列",
                  "数学", "数论", "计数", "概率", "期望", "博弈", "矩阵", "高斯消元", "线性基",
                  "生成函数", "多项式", "fft", "ntt", "中国剩余", "原根",
                  "同余", "费马", "逆元", "扩展欧几里得", "exgcd", "快速幂",
                  "容斥", "卡特兰", "鸽巢", "二项式",
                  "莫比乌斯", "反演", "burnside", "polya", "bsgs", "大步小步",
                  "单位根", "单纯形",
                  "pollard", "rho", "miller", "rabin", "杜教筛", "min_25", "fwt"]),
    ("计算几何", ["几何", "凸包", "旋转卡壳", "半平面交", "辛普森", "扫描线", "pick"]),
    ("其他", []),  # 兜底
)


def _classify_topic(topic: str) -> str:
    """把一个知识点名归类到上面的 9 个分类中。"""
    t = str(topic or "").lower()
    for cat, kws in _CATEGORY_KEYWORDS:
        for kw in kws:
            if kw and kw.lower() in t:
                return cat
    return "其他"


def _level_for_ac(ac_count: int) -> str:
    # ⚠️ 阈值与 _MASTERY_RULES 强绑定，修改时务必同步更新二者
    # （"掌握度判定标准"小节和"知识点覆盖统计表-掌握度分布"列都基于此）。
    if ac_count >= 20:
        return "精通"
    if ac_count >= 10:
        return "熟练"
    if ac_count >= 3:
        return "入门"
    if ac_count >= 1:
        return "初窥"
    return "空白"


def _build_one_tree_svg(
    icon: str,
    title: str,
    cat_topics: list,
    *,
    width: int = 460,
) -> str:
    """把一个竞赛级别画成一棵"真正的树"（SVG：树干 + 树枝 + 果子）。

    Parameters
    ----------
    icon : str
        级别前的 emoji（🌱/🌿/🌳/🏆）
    title : str
        级别名（CSP-J 入门 / CSP-S 提高 / 省选级 / NOI 级）
    cat_topics : list
        已按"掌握度从高到低"排好序的 [(cat, [(topic, ac, level), ...]), ...]
        排在最上面的是掌握度最高的分类。
    width : int
        SVG 宽度（px）。树高根据分类数自适应。v3.6 缩小到 460（之前 680），
        配合 2×2 网格让 4 棵树一页并排展示。

    设计
    ----
    - 中央树干（SVG 正中，棕色三层叠加 + 顶部 5 簇绿叶）
    - 主分支从中央向左右两侧**扇形展开**（奇偶交替），避免全在一侧像耙子
    - 长度因子：上层分支短、下层分支长，整体呈下宽上窄的圆锥轮廓
    - 树根处一条棕色虚线 + 草尖，模拟"地面"
    - 每条主分支 = 一个算法分类，Q 二次贝塞尔曲线，弯曲更明显
    - 分支上点缀几片小绿叶（装饰用）
    - 分支末端挂一排"果子" = 知识点
        - 半径 r 越大 → 掌握越好（6px 空白 → 18px 精通）
        - 颜色越深（灰 → 浅蓝 → 浅绿 → 中绿 → 深绿）→ 掌握越好
        - 果子中心写 AC 数（半径够大才写，避免溢出）
        - 果子下方写知识点名（>4 字拆两行）
    - 分类小帽（深色药丸）挂在分支根处上沿，靠树干一侧
    - 树干不透明度最低；果子最显眼
    """
    if not cat_topics:
        return (
            '<div style="color:#9CA3AF;text-align:center;'
            'padding:30px 0;font-size:12px;">（该级别暂无知识点数据）</div>'
        )

    # 布局常量（v3.6 紧凑化：BRANCH_H 88→56, FRUIT_W 56→38）
    HEADER_H = 24          # 顶部留白（给树冠+最顶部分类帽留余地）
    BRANCH_H = 56          # 每条主分支占的高度（紧凑 36%，让树更矮）
    BOTTOM_PAD = 22
    # v3.9.51 · 上游 build_knowledge_tree_html 已经按 AC 降序排好，
    #   并对 >28 个的分类做了拆分。这里不再做 MAX_FRUITS 截断 + 排序，
    #   直接信任传入的 topics 顺序。MAX_FRUITS 保留作为防御性兜底（>200 才截）。
    MAX_FRUITS = 200
    COMPACT_THRESHOLD = 6  # 6+ 果子进入紧凑模式
    TINY_THRESHOLD = 8     # 8+ 果子进入极紧凑模式
    # v3.9.51 · 增加更紧凑的级别：>20 进入"超紧凑"模式（果子半径 60%）
    ULTRA_TINY_THRESHOLD = 20
    FRUIT_W = 38           # 标准模式果子水平间距
    FRUIT_W_MIN = 22       # 紧凑模式最小间距（更紧凑，确保 30+ 果子也能放下）
    FRUIT_W_ULTRA = 16     # 超紧凑模式最小间距（>20 果子时用）
    SIDE_MARGIN = 18       # 边距（略减）

    n_branches = len(cat_topics)
    height = HEADER_H + n_branches * BRANCH_H + BOTTOM_PAD

    # 树干几何：居中
    trunk_x = width // 2
    ground_y = HEADER_H + 6
    trunk_top = ground_y + 4
    trunk_bottom = height - 12
    half_w = width // 2 - SIDE_MARGIN  # 一侧可用的最大水平距离

    svg: list[str] = []
    # 用百分比宽度，避免 PDF 渲染时被裁切
    svg.append(
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="auto" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'style="display:block;max-width:100%;margin:0 auto;" '
        f'font-family="-apple-system, BlinkMacSystemFont, \'PingFang SC\', '
        f'\'Microsoft YaHei\', sans-serif">'
    )

    # 背景渐变（淡绿天 → 白）
    grad_id = f"sky_{title[:3].replace(' ', '')}"
    svg.append(
        f'<defs><linearGradient id="{grad_id}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="#F0FDF4"/>'
        f'<stop offset="1" stop-color="#FFFFFF"/>'
        f'</linearGradient></defs>'
    )
    svg.append(
        f'<rect x="0" y="0" width="{width}" height="{ground_y + 2}" '
        f'fill="url(#{grad_id})"/>'
    )

    # 地面（虚线 + 草尖）
    svg.append(
        f'<line x1="0" y1="{ground_y}" x2="{width}" y2="{ground_y}" '
        f'stroke="#A89878" stroke-width="1.5" stroke-dasharray="2 3"/>'
    )
    for gx in range(8, width, 22):
        svg.append(
            f'<line x1="{gx}" y1="{ground_y}" x2="{gx - 2}" '
            f'y2="{ground_y + 5}" stroke="#86EFAC" stroke-width="1.2"/>'
        )

    # 树干（外深 → 中棕 → 内高光，三层叠加出立体感）
    trunk_path = (
        f'M {trunk_x} {trunk_bottom} '
        f'C {trunk_x + 1.5} {(trunk_top + trunk_bottom) * 0.7} '
        f'{trunk_x - 1.5} {(trunk_top + trunk_bottom) * 0.3} '
        f'{trunk_x} {trunk_top}'
    )
    svg.append(
        f'<path d="{trunk_path}" stroke="#3F2410" stroke-width="18" '
        f'fill="none" stroke-linecap="round"/>'
    )
    svg.append(
        f'<path d="{trunk_path}" stroke="#6B4423" stroke-width="13" '
        f'fill="none" stroke-linecap="round"/>'
    )
    svg.append(
        f'<path d="{trunk_path}" stroke="#A07A50" stroke-width="6" '
        f'fill="none" stroke-linecap="round" opacity="0.55"/>'
    )

    # 树冠（一簇小绿叶 + 一颗大果子装饰在树顶，强化"树"的形象）
    canopy_y = trunk_top - 4
    for cx, cy, rr in [(trunk_x - 12, canopy_y, 9), (trunk_x + 10, canopy_y - 4, 11),
                       (trunk_x - 2, canopy_y - 12, 10), (trunk_x + 16, canopy_y + 4, 7),
                       (trunk_x - 16, canopy_y + 5, 7)]:
        svg.append(
            f'<ellipse cx="{cx}" cy="{cy}" rx="{rr}" ry="{rr * 0.75:.2f}" '
            f'fill="#4ADE80" opacity="0.85"/>'
        )
        svg.append(
            f'<ellipse cx="{cx - rr * 0.3:.2f}" cy="{cy - rr * 0.3:.2f}" '
            f'rx="{rr * 0.35:.2f}" ry="{rr * 0.2:.2f}" '
            f'fill="#FFFFFF" opacity="0.45"/>'
        )

    # 主分支 = 分类；按 cat_topics 顺序（已排好）从下往上画
    branch_zone = trunk_bottom - trunk_top - 14
    n_branches = len(cat_topics)

    # v3.9.50 · 真正左右交替：i=0(最上)→左, i=1→右, i=2→左 ... 一棵"真·树"。
    # 之前 v3.9.48 的"前半左、后半右"会让 4 根树枝挤在一侧像耙子，视觉完全不像树。
    # 交替后：n=6 → 3L+3R, n=7 → 4L+3R, n=8 → 4L+4R, n=9 → 5L+4R, 天然平衡。
    # 特例：n=1 时 i=0 → 左（保持原行为）
    for i, (cat, topics) in enumerate(cat_topics):
        # 分支 y：均匀分布（i=0 在最上，越往下 i 越大）
        by = trunk_top + 7 + (i + 0.5) * (branch_zone / n_branches)
        # v3.9.50 · 真正左右交替（之前是 i >= half_n）
        going_right = (i % 2 == 1) if n_branches > 1 else False
        # 长度因子：i=0（最上）最短，i=n-1（最下）最长；形成下宽上窄的圆锥
        if n_branches > 1:
            length_factor = 0.62 + 0.38 * i / (n_branches - 1)
        else:
            length_factor = 1.0

        # 防御性截断（理论不会触发，因为上游已拆分；仅当数据异常时兜底）
        topics_sorted = list(topics)[:MAX_FRUITS]
        hidden = max(0, len(topics) - len(topics_sorted))
        n_fruits = len(topics_sorted)
        if n_fruits == 0:
            continue

        # 计算本侧最大可用水平距离（按 length_factor 缩放）
        max_extent = half_w * length_factor

        # v3.9.51 · 紧凑度自适应（四档）：
        #   - n_fruits < 6：标准模式，fw = FRUIT_W(38)
        #   - 6 <= n_fruits < 8：紧凑模式，fw 自适应压到 FRUIT_W_MIN(22) 以上
        #   - 8 <= n_fruits < 20：极紧凑模式，fw 更小 + 果子半径 70%
        #   - n_fruits >= 20：超紧凑模式，fw=FRUIT_W_ULTRA(16) + 果子半径 60%
        if n_fruits >= ULTRA_TINY_THRESHOLD:
            compact_mode = "ultra_tiny"
            fw = max(FRUIT_W_ULTRA, (max_extent - 20) / max(1, n_fruits - 1))
            r_factor = 0.6    # 果子半径 60%
            fs_factor = 0.85  # AC 数字略小
            label_fs = 7.0    # 知识点名字体
        elif n_fruits >= TINY_THRESHOLD:
            compact_mode = "tiny"
            fw = max(FRUIT_W_MIN, (max_extent - 24) / max(1, n_fruits - 1))
            r_factor = 0.7    # 果子半径 70%
            fs_factor = 0.9   # AC 数字略小
            label_fs = 7.5    # 知识点名字体
        elif n_fruits >= COMPACT_THRESHOLD:
            compact_mode = "compact"
            fw = max(FRUIT_W_MIN, (max_extent - 30) / max(1, n_fruits - 1))
            r_factor = 0.85
            fs_factor = 0.95
            label_fs = 8.0
        else:
            compact_mode = "standard"
            if n_fruits > 1:
                ideal_span = (n_fruits - 1) * FRUIT_W
                if ideal_span > max_extent - 30:
                    fw = max(FRUIT_W_MIN, (max_extent - 30) / max(1, n_fruits - 1))
                else:
                    fw = FRUIT_W
            else:
                fw = 0
            r_factor = 1.0
            fs_factor = 1.0
            label_fs = 8.5

        if going_right:
            # 分支起点/终点
            branch_start_x = trunk_x + 7
            first_fruit_x = trunk_x + 22
            last_fruit_x = first_fruit_x + (n_fruits - 1) * fw
            branch_end_x = last_fruit_x + 12
            ctrl_x = (branch_start_x + branch_end_x) / 2
            ctrl_y = by - 22
            branch_path = (
                f'M {branch_start_x} {by} '
                f'Q {ctrl_x} {ctrl_y} {branch_end_x} {by - 1}'
            )
            # 分类 chip 锚点（在分支"内侧"，即靠近树干的左侧）
            chip_x = trunk_x + 14
        else:
            # 镜像：分支从树干左侧出发
            branch_start_x = trunk_x - 7
            first_fruit_x = trunk_x - 22
            last_fruit_x = first_fruit_x - (n_fruits - 1) * fw
            branch_end_x = last_fruit_x - 12
            ctrl_x = (branch_start_x + branch_end_x) / 2
            ctrl_y = by - 22
            branch_path = (
                f'M {branch_start_x} {by} '
                f'Q {ctrl_x} {ctrl_y} {branch_end_x} {by - 1}'
            )
            # 分类 chip 锚点（在分支"内侧"，即靠近树干的右侧）
            chip_x = trunk_x - 14

        # 主分支曲线（阴影 + 主色，双层叠加）
        svg.append(
            f'<path d="{branch_path}" stroke="#5C3A1E" stroke-width="6" '
            f'fill="none" stroke-linecap="round"/>'
        )
        svg.append(
            f'<path d="{branch_path}" stroke="#8B7355" stroke-width="3" '
            f'fill="none" stroke-linecap="round" opacity="0.7"/>'
        )

        # 分支上的几片小叶子（装饰，给点绿意；只画在分支前段，不挤到果子下面）
        for lx_frac, lrot in [(0.32, -28), (0.55, 24)]:
            lx = branch_start_x + (branch_end_x - branch_start_x) * lx_frac
            ly = by - (5 if lrot > 0 else 7)
            if going_right:
                if lx < first_fruit_x - 6 and lx < branch_end_x - 8:
                    svg.append(
                        f'<ellipse cx="{lx}" cy="{ly}" rx="4" ry="2" '
                        f'fill="#4ADE80" opacity="0.75" '
                        f'transform="rotate({lrot} {lx} {ly})"/>'
                    )
            else:
                if lx > first_fruit_x + 6 and lx > branch_end_x + 8:
                    svg.append(
                        f'<ellipse cx="{lx}" cy="{ly}" rx="4" ry="2" '
                        f'fill="#4ADE80" opacity="0.75" '
                        f'transform="rotate({-lrot} {lx} {ly})"/>'
                    )

        # 分类小帽（深色药丸 + 白字，挂在分支根处上沿）
        # 关键修复：之前 y=by-24 会让 chip 底（y=by-8）和最大果子（r=18, 顶 y=by-20）
        # 垂直方向 12px 重叠，导致 chip 文字被果子盖住。把 chip 整体上移到 by-34，
        # 让 chip 底（y=by-18）刚好不超过最大果子顶（y=by-20），不再被遮挡。
        chip_w = max(40, len(cat) * 9 + 16)
        if going_right:
            chip_left = chip_x
        else:
            chip_left = chip_x - chip_w
        svg.append(
            f'<rect x="{chip_left}" y="{by - 34}" width="{chip_w}" '
            f'height="16" rx="8" fill="#1F2937" opacity="0.92"/>'
        )
        svg.append(
            f'<text x="{chip_left + chip_w / 2:.1f}" y="{by - 22}" '
            f'font-size="10" font-weight="700" fill="#FFFFFF" '
            f'text-anchor="middle">{cat}</text>'
        )

        # 果子们
        for j, (topic, ac, level, difficulty) in enumerate(topics_sorted):
            if going_right:
                fx = first_fruit_x + j * fw
            else:
                fx = first_fruit_x - j * fw
            fy = by - 2
            # 颜色规则（最终统一）：**果子颜色按"掌握度"用绿色深浅表示**——
            #   精通=深绿近黑 / 熟练=深绿 / 入门=标准绿 / 初窥=浅绿 / 空白=白
            # 难度信息不再在果子颜色里展示（避免与掌握度维度重复），
            # 改在 hover 提示（full_info）和图例的文字说明里展示。
            mt = _MASTERY_VIS.get(level, _MASTERY_VIS["空白"])
            # v3.9.50 · 紧凑模式：果子半径按 r_factor 缩放
            r = max(4, mt["r"] * r_factor)   # 最小 4px，保证小果子仍可见
            mc = _MASTERY_COLOR.get(level, _MASTERY_COLOR["空白"])
            fill = mc["fill"]
            fg = mc["fg"]
            bd = mc["bd"]
            diff_label = _DIFF_TIER.get(difficulty, _DIFF_TIER[0])["name"]
            # 完整信息（hover/assistive 显示）：保留难度
            full_info = (
                f"{topic} · AC {ac} · {level} · 难度[{diff_label}]"
            )
            # 果柄（短竖线，从果子底部到分支）
            svg.append(
                f'<line x1="{fx}" y1="{fy + r}" '
                f'x2="{fx}" y2="{fy + r + 4}" '
                f'stroke="#5C3A1E" stroke-width="1.5"/>'
            )
            # 果子本体（带 <title> 鼠标悬停看完整信息）
            svg.append(
                f'<circle cx="{fx}" cy="{fy}" r="{r}" '
                f'fill="{fill}" stroke="{bd}" '
                f'stroke-width="1.4">'
                f'<title>{full_info}</title>'
                f'</circle>'
            )
            # 高光（左上）
            svg.append(
                f'<ellipse cx="{fx - r * 0.32:.2f}" '
                f'cy="{fy - r * 0.4:.2f}" '
                f'rx="{r * 0.35:.2f}" ry="{r * 0.22:.2f}" '
                f'fill="#FFFFFF" opacity="0.5"/>'
            )
            # 果子内写 AC 数（半径 >= 8 才写，紧凑模式下半径小，跳过）
            if r >= 8:
                svg.append(
                    f'<text x="{fx}" y="{fy + 4}" font-size="{mt["fs"] * fs_factor:.1f}" '
                    f'font-weight="{mt["fw"]}" fill="{fg}" '
                    f'text-anchor="middle">{ac}</text>'
                )
            # 果子下写知识点名
            # 规则：<=4 字直接显示；5+ 字拆两行
            # v3.9.50 · 紧凑模式：>=6 果子时 2+ 字也尝试拆两行，缩 font-size 到 label_fs
            topic_chars = list(topic)
            n = len(topic_chars)
            # 紧凑模式：>2 字就拆两行（避免横向占太宽）
            if compact_mode == "standard":
                if n <= 4:
                    lines = ["".join(topic_chars)]
                else:
                    mid = (n + 1) // 2
                    lines = ["".join(topic_chars[:mid]), "".join(topic_chars[mid:])]
            else:
                if n <= 2:
                    lines = ["".join(topic_chars)]
                else:
                    mid = (n + 1) // 2
                    lines = ["".join(topic_chars[:mid]), "".join(topic_chars[mid:])]
            label_y_start = fy + r + 12
            for li, line in enumerate(lines):
                svg.append(
                    f'<text x="{fx}" y="{label_y_start + li * 9}" '
                    f'font-size="{label_fs}" font-weight="600" fill="#1F2937" '
                    f'text-anchor="middle">{line}</text>'
                )

        # 被截掉的 "+N"
        # v3.9.35 · 修复两侧 +N 都被 viewBox 剪掉的问题：
        #  - 左侧：原来 branch_end_x - 4 (≈ x=2) + anchor=end → 文字推到 x=-15，被剪
        #  - 右侧：原来 branch_end_x + 4 (≈ x=458) + anchor=start → 文字推到 x=480，被剪
        # 修复：两侧都留 24px 边界（min/max + 边距），保证 "+N" 永远完整可见
        if hidden > 0:
            if going_right:
                overflow_x = min(branch_end_x + 4, width - 24)
                anchor = "start"
            else:
                overflow_x = max(branch_end_x - 4, 24)
                anchor = "end"
            svg.append(
                f'<text x="{overflow_x}" y="{by + 3}" font-size="10" '
                f'fill="#9CA3AF" font-style="italic" '
                f'text-anchor="{anchor}">+{hidden}</text>'
            )

    svg.append('</svg>')
    return '\n'.join(svg)


def build_knowledge_tree_html(syllabus_eval: dict) -> str:
    """渲染 4 棵独立的"真·知识树"（SVG：每棵一个竞赛级别）。

    每棵树 = 1 个竞赛级别（CSP-J / CSP-S / 省选 / NOI）：
        - 棕色树干
        - 分类作为主分支（带小绿叶装饰）
        - 知识点作为果子挂枝头
        - 果子大小 + 颜色（绿深浅） = 掌握度
        - 鼠标悬停：显示 AC 题目数 / 掌握等级 / 关联题目难度

    返回完整 HTML（含图例、说明、4 棵树）。"
    """
    group_keys = (
        ("csp_j", "CSP-J 入门", "🌱"),
        ("csp_s", "CSP-S 提高", "🌿"),
        ("provincial", "省选级", "🌳"),
        ("noi", "NOI 级", "🏆"),
    )

    # ---------- 图例 1：大小=掌握度 ----------
    # 关键修复：图例每个点用掌握度自身的颜色（绿深浅），跟真果子一致。
    legend_size: list[str] = []
    for name in ("精通", "熟练", "入门", "初窥", "空白"):
        mt = _MASTERY_VIS[name]
        r = mt["r"]
        col = _MASTERY_COLOR.get(name, _MASTERY_COLOR["空白"])
        dot_fill = col["fill"]
        dot_stroke = col["bd"]
        legend_size.append(
            f'<span style="display:inline-flex;align-items:center;'
            f'gap:5px;margin-right:12px;">'
            f'<svg width="{r * 2 + 4}" height="{r * 2 + 4}" '
            f'viewBox="-{r + 2} -{r + 2} {r * 2 + 4} {r * 2 + 4}" '
            f'xmlns="http://www.w3.org/2000/svg">'
            f'<circle r="{r}" fill="{dot_fill}" stroke="{dot_stroke}" '
            f'stroke-width="1.2"/>'
            f'<ellipse cx="{-r * 0.32:.2f}" cy="{-r * 0.4:.2f}" '
            f'rx="{r * 0.35:.2f}" ry="{r * 0.22:.2f}" '
            f'fill="#FFFFFF" opacity="0.5"/>'
            f'</svg>'
            f'<span style="font-size:11px;color:#1F2937;">{name}</span>'
            f'</span>'
        )

    legend = (
        '<div style="background:#F9FAFB;border:1px solid #E5E7EB;'
        'border-radius:6px;padding:10px 14px;margin:0 0 14px 0;'
        'font-size:11px;color:#374151;">'
        '<div style="display:flex;flex-wrap:wrap;align-items:center;'
        'gap:6px;">'
        '<span style="font-weight:700;color:#1F2937;margin-right:6px;">'
        '� 果子大小 + 颜色 = 掌握度（绿色深浅：精通近黑→熟练深绿→入门标准绿→初窥浅绿→空白白）'
        '</span>'
        + ''.join(legend_size)
        + '</div>'
        '</div>'
    )

    # ---------- 4 棵树（v3.6 改为 2×2 网格 · 一页并排 2 棵）----------
    # 每棵：醒目标题条（级别 + 图标 + 大字号 + 彩色背景 + 边框）
    tree_blocks: list[str] = []
    for idx, (key, title, icon) in enumerate(group_keys):
        group = syllabus_eval.get(key, {}) or {}
        details = group.get("details", []) or []
        stats = group.get("stats", {}) or {}
        coverage = group.get("coverage", 0)
        total = int(stats.get("total", 0))
        blank = int(stats.get("空白", 0))
        lit = total - blank

        # 按分类聚合
        # tuple 顺序: (topic, ac, level, difficulty)
        cat_to_topics: dict[str, list[tuple[str, int, str, int]]] = {}
        cat_order: list[str] = []
        for item in details:
            topic = str(item.get("topic", "")).strip()
            if not topic:
                continue
            ac = int(item.get("ac_count", 0) or 0)
            level = _level_for_ac(ac)
            difficulty = int(item.get("difficulty", 0) or 0)
            cat = _classify_topic(topic)
            if cat not in cat_to_topics:
                cat_to_topics[cat] = []
                cat_order.append(cat)
            cat_to_topics[cat].append((topic, ac, level, difficulty))

        # 排序：分类按"该分类最高 AC 数"降序（强的分类画在树上更高位置）
        def _cat_score(cat: str) -> int:
            return max((t[1] for t in cat_to_topics[cat]), default=0)

        cat_topics = [(c, cat_to_topics[c]) for c in cat_order]
        cat_topics.sort(key=lambda kv: _cat_score(kv[0]), reverse=True)

        # v3.9.51 · 拆分超大分类：单分类 >28 个知识点时拆成多个子分支，
        #   确保所有知识点都能被展示（之前会被 +N 截断）。
        #   - 子分类标签 = 父分类 + 角标①②…
        #   - 子分类内按 AC 降序排（强项在前）
        MAX_FRUITS_PER_BRANCH = 28
        expanded_cat_topics: list[tuple[str, list]] = []
        for cat, topics in cat_topics:
            topics_sorted = sorted(topics, key=lambda t: -t[1])
            if len(topics_sorted) <= MAX_FRUITS_PER_BRANCH:
                expanded_cat_topics.append((cat, topics_sorted))
                continue
            n_chunks = (len(topics_sorted) + MAX_FRUITS_PER_BRANCH - 1) // MAX_FRUITS_PER_BRANCH
            # 拆分时尽量让**强项集中在第 1 个子分支**（高 AC），其它均分
            # 这里直接按 AC 降序均分即可
            for ci in range(n_chunks):
                chunk = topics_sorted[ci * MAX_FRUITS_PER_BRANCH:(ci + 1) * MAX_FRUITS_PER_BRANCH]
                # 角标：用①②③ 简洁不占空间
                subscript = "①②③④⑤⑥⑦⑧⑨"[ci] if ci < 9 else f"({ci+1})"
                label = f"{cat}{subscript}" if n_chunks > 1 else cat
                expanded_cat_topics.append((label, chunk))
        cat_topics = expanded_cat_topics

        svg = _build_one_tree_svg(icon, title, cat_topics)

        # 该棵树的统计条
        meta = (
            f'已点亮 <b style="color:#059669;font-weight:700;">{lit}</b>'
            f' / {total}（{coverage}%）'
        )

        # v3.6 醒目标题：级别色编码（按竞赛级别从浅到深）
        # CSP-J 浅绿 / CSP-S 中绿 / 省选 深绿 / NOI 金色
        level_colors = {
            "CSP-J 入门": ("#10B981", "#D1FAE5", "#065F46"),   # 浅绿
            "CSP-S 提高": ("#059669", "#A7F3D0", "#064E3B"),   # 中绿
            "省选级":     ("#047857", "#6EE7B7", "#022C22"),    # 深绿
            "NOI 级":     ("#D97706", "#FDE68A", "#78350F"),    # 金色
        }
        border_c, bg_c, text_c = level_colors.get(title, ("#10B981", "#F0FDF4", "#065F46"))

        tree_blocks.append(
            f'<div class="kt-tree-block" style="'
            f'background:#FFFFFF;border:2px solid {border_c};'
            f'border-radius:8px;padding:8px 10px;margin:0;">'
            # 醒目标题条：级别 emoji + 名称 + 统计
            f'<div style="display:flex;justify-content:space-between;'
            f'align-items:center;background:{bg_c};border-left:5px solid {border_c};'
            f'padding:6px 10px;margin:0 0 6px 0;border-radius:4px;">'
            f'<span style="font-size:16px;font-weight:800;color:{text_c};'
            f'letter-spacing:0.5px;">{icon} {title} · 知识树</span>'
            f'<span style="font-size:11px;color:{text_c};font-weight:600;">{meta}</span>'
            f'</div>'
            f'{svg}'
            f'</div>'
        )

    # v3.6 2×2 网格：前 2 棵一行，后 2 棵一行（每行 2 棵并排）
    # 在小屏自动降为 1 列
    return (
        '<div class="kt-section" style="margin:8px 0 18px 0;">'
        '<h2 style="font-size:18px;font-weight:700;color:#065F46;'
        'border-left:5px solid #10B981;padding:6px 0 6px 10px;'
        'margin:0 0 8px 0;background:#F0FDF4;border-radius:0 6px 6px 0;">'
        '🌳 知识树图谱（按竞赛级别 · 果子大小/颜色 = 掌握度）</h2>'
        '<p style="font-size:12px;color:#4B5563;margin:0 0 10px 0;'
        'line-height:1.6;">下图为按 4 个竞赛级别（CSP-J / CSP-S / 省选 / '
        'NOI）分别画出的 4 棵"知识树"（<b>2×2 并排</b>，每棵带级别色编码）。'
        '每棵树上，<b>主干</b>代表该级别，<b>分支</b>代表算法分类（基础实现 / '
        '搜索 · DFS / 动态规划 / 贪心 · 二分 / 图论 / 数据结构 / 字符串 / '
        '数学 · 数论 / 计算几何 / 其他），<b>果子</b>就是该分类下的具体知识点。'
        '<b>果子越大、颜色越深</b> = 该知识点 AC 数越多 = 掌握越好；'
        '灰色小果子 = 该知识点尚未接触（AC=0）。</p>'
        + legend
        # 2×2 网格：grid-template-columns:repeat(2, 1fr)，gap:8px
        + '<div style="display:grid;grid-template-columns:repeat(2, 1fr);'
        'gap:10px;align-items:start;'
        '@media (max-width:768px){grid-template-columns:1fr;}'
        '">'
        + ''.join(tree_blocks)
        + '</div>'
        + '</div>'
    )


# 重建场景：先抹掉已注入的可信块，再走 normalize_report_markdown 重新注入。
# strip 范围：
#   1) 从 H2「数据校准与真实统计」开始 → H2「掌握度判定标准（5 档）」之前
#      （统计表部分）。GESP 版块内没有此 H2，所以 fallback 到 H1（`^\s*#\s`）边界。
#   2) 再单独抹掉 H2「掌握度判定标准（5 档）」及其后续 5 档表 + 「🌳 知识树图谱」HTML 块
#      （NOI 版会在这里塞 4 棵 SVG 树；GESP 版则没有此块）
# v3.9.66 · 同时兼容 GESP 版「数据校准与真实统计（GESP 8 级版）」标题
# v3.9.66 · 修 GESP 块无 `## 掌握度判定标准` 锚点时被 `\Z` 贪婪吞 H1 的 bug
_TRUSTED_BLOCK_RE = re.compile(
    r"(?ms)^##\s*数据校准与真实统计(?:（GESP 8 级版）)?\s*\n.*?(?=^##\s*掌握度判定标准|^\s*#\s|\Z)"
)
# 抹除「掌握度判定标准（5 档）」表 + 之后紧邻的「🌳 知识树图谱」HTML 块
# （NOI 4 棵 SVG 树嵌在三层 div 里：最外层 page-break div → kt-section → kt-grid）
# 需要匹配到第三个 `</div>` 之后才能完整抹除。
# GESP 块内没有此标题，跳过即可。
_KT_SECTION_RE = re.compile(
    r"(?ms)^##\s*掌握度判定标准[^\n]*\n.*?(?:🌳\s*知识树图谱.*?(?:</div>\s*){3,}|^\s*#\s|\Z)"
)


def remove_injected_trusted_block(report_md: str) -> str:
    """重建场景辅助：抹掉已注入的可信块，剩余 AI 内容交给 normalize_report_markdown
    重新注入最新代码生成的版本。

    Prompt 已禁止 AI 写这些标题，所以抹掉 inject 不会误伤 AI 内容。

    v3.9.66 · 同时兼容 GESP 版的"## 数据校准与真实统计（GESP 8 级版）"标题。
    v3.9.66 · 同时抹除"## 掌握度判定标准"之后的 5 档表 + NOI 4 棵 SVG 树。
    """
    if "## 数据校准与真实统计" not in report_md:
        return report_md
    md = _TRUSTED_BLOCK_RE.sub("", report_md, count=1)
    if "## 掌握度判定标准" in md:
        md = _KT_SECTION_RE.sub("", md, count=1)
    return md


# v3.9.67 · GESP 报告专用：抹除 LLM 在主体里可能输出的"8 级知识地图"表
# 用户实测：模型凭印象写"GESP 一级 100% 覆盖"、与末尾程序化表"GESP 一级 0/5 tag"打架
# 规则：只抹 GESP 报告里、报告主体（非末尾程序化小节）、LLM 输出的那张 8 级表
# 保留末尾"## 数据校准与真实统计（GESP 8 级版）"里的程序化版本（那是真相源）
_LLM_GESP_8LEVEL_HEADINGS = [
    r"#{1,6}\s*(?:【|‹)?\s*GESP\s*8\s*级知识地图[^#\n]*",  # 含 8 级知识地图 标题
    r"#{1,6}\s*(?:【|‹)?\s*学员覆盖度\s*[\-·—]?\s*GESP\s*8\s*级[^#\n]*",
    r"#{1,6}\s*【GESP\s*8\s*级知识地图[^#\n]*】",
]
_LLM_GESP_8LEVEL_RE = re.compile(
    r"(?ms)^(#{1,6}\s*(?:【|‹)?\s*GESP\s*8\s*级知识地图[^#\n]*\n)"  # 标题
    r"(?:.*?\n)*?"                                                          # 标题到表格之间的描述段
    r"(?:\|[^\n]*\|[ \t]*\n)+"                                              # 至少 1 行 markdown 表格行
    r"[^\n]*\n?"                                                            # 表尾说明（可选）
)


def _strip_llm_gesp_8level_table(report_md: str) -> str:
    """v3.9.67 · 抹除 GESP 报告里 LLM 主体中的"8 级知识地图"表

    实现策略（保守，不误伤）：
      1) 用一段保守 regex 匹配 "## ... GESP 8 级知识地图 ..." 整段标题 + 后续行；
      2) 抹除范围：标题行 + 后续行，直到下一个 # 标题或文件末尾；
      3) 末尾"## 数据校准与真实统计（GESP 8 级版）"小节不会被抹，
         因为它在独立的 # 标题下，与 LLM 8 级表无关联。
    """
    if "GESP 8 级知识地图" not in report_md:
        return report_md
    # 抹除规则：找到含 8 级知识地图 的标题（允许标题前有"二、"等编号）→ 抹到下一个标题前
    new_md = re.sub(
        r"(?ms)^[ \t]*#{1,6}[ \t]*[^\n]*?GESP[ \t]*8[ \t]*级知识地图[^\n]*\n"  # 标题行（允许前面有"二、"等任意文本）
        r"(?:[^\n]*\n)*?"  # 后续行（非贪婪）
        r"(?=^[ \t]*#{1,6}[ \t]*\S|\Z)",  # 直到下一个 # 标题或文件末尾
        "",
        report_md,
    )
    return new_md


def normalize_report_markdown(
    report_md: str,
    export_data: dict,
    exam_type: str = "noi_csp",
    target_gesp_level: int = 1,
    gesp_highest_passed: int = 0,
) -> str:
    """对 AI 输出做最小必要的纠偏，锁定难度名称并修正明显错误表述。

    调用次数语义：
    - 第一次（输入 = AI 原始输出）：做 strip 清洗 + 注入可信块
    - 第二次（输入 = 已注入过可信块的 report.md）：**整段直接返回**，避免把"已注入的
      知识点覆盖统计表/知识树"被 strip 误吞（这是上一版"幂等修复"的副作用）
    - 重建场景：调用方应先 `remove_injected_trusted_block()` 再走本函数

    v3.9.66 · 新增 exam_type 分支：
      - "noi_csp"（默认）：注入 NOI 4 级（入门/提高/省选/NOI）知识树（原行为）
      - "gesp"：注入 GESP 8 级知识地图（新行为，不再注入 NOI 4 级知识树）
    """
    _is_gesp = str(exam_type or "noi_csp").strip().lower() == "gesp"

    # 幂等：已注入过可信块 → 跳过 strip + 跳过 inject，原样返回
    if _is_gesp:
        # GESP 版：检测是否已注入过 GESP 版可信块
        if (
            "## 数据校准与真实统计（GESP 8 级版）" in report_md
        ):
            return report_md
    else:
        if (
            "## 数据校准与真实统计" in report_md
            and "知识树图谱（按算法标签" in report_md
        ):
            return report_md

    normalized = report_md

    # v3.9.66 · GESP 版不再 strip "知识树"——因为 prompt 禁止 AI 写，且 GESP 版
    # 不会注入 NOI 知识树。NOI 版继续按 v3.9.48 行为 strip 掉 AI 误重复生成的统计表/树。
    if not _is_gesp:
        normalized = re.sub(
            r"(?ms)^\s{0,3}#{2,6}\s*知识点覆盖统计表（按算法标签）\s*\n+.*?(?=^\s{0,3}#{2,6}\s|\Z)",
            "",
            normalized,
        )
        normalized = re.sub(
            r"(?ms)^\s{0,3}#{2,6}\s*知识点覆盖表（按算法标签统计）\s*\n+.*?(?=^\s{0,3}#{2,6}\s|\Z)",
            "",
            normalized,
        )
        normalized = re.sub(
            r"(?ms)^\s{0,3}#{2,6}\s*知识树[^\n]*\n+.*?(?=^\s{0,3}#{2,6}\s|\Z)",
            "",
            normalized,
        )

    for idx, name in DIFFICULTY_NAME_MAP.items():
        normalized = re.sub(rf"难度\s*{idx}\b", name, normalized)
        normalized = re.sub(rf"难度{idx}\b", name, normalized)

    eval_time = str((export_data.get("student_info", {}) or {}).get("eval_time") or "").strip()
    if not eval_time:
        eval_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    if eval_time:
        date_only = eval_time.split(" ")[0]
        normalized = re.sub(r"(诊断日期[：:]\s*)([^\n<]+)", rf"\1{date_only}", normalized)
        normalized = re.sub(r"(\*\*生成时间\*\*[:：]\s*)([^\n<]+)", rf"\1{eval_time}", normalized)
        normalized = re.sub(r"(\*\*报告生成时间\*\*[:：]\s*)([^\n<]+)", rf"\1{eval_time}", normalized)
        normalized = re.sub(r"((?<!\*)生成时间(?!\*)[：:]\s*)([^\n<]+)", rf"\1{eval_time}", normalized)
        normalized = re.sub(r"((?<!\*)报告生成时间(?!\*)[：:]\s*)([^\n<]+)", rf"\1{eval_time}", normalized)
        normalized = re.sub(r"(<strong>\s*生成时间\s*</strong>\s*[：:]\s*)([^<\n]+)", rf"\1{eval_time}", normalized, flags=re.I)
        normalized = re.sub(r"(<strong>\s*报告生成时间\s*</strong>\s*[：:]\s*)([^<\n]+)", rf"\1{eval_time}", normalized, flags=re.I)
        normalized = normalized.replace("2025年4月", eval_time)

    behavior = export_data.get("behavior_analysis", {}) or {}
    if behavior and "error" not in behavior:
        time_points = sum(int(v) for v in (behavior.get("time_slot_distribution", {}) or {}).values())
        if time_points > 0:
            normalized = re.sub(r"无时间戳数据[^。！!\n]*[。！!]?", "已获取真实提交时间戳数据，并完成时段分布统计。", normalized)
            normalized = normalized.replace("无法分析。根据大量AC的记录，推测训练是其日常生活的重要组成。", "已依据真实提交时间戳、活跃天数与时段分布完成分析。")

    normalized = normalized.replace("一发入魂率", "首次 AC 通过分布")
    normalized = normalized.replace("一发入魂", "首次 AC 通过")

    def _build_difficulty_chart_section_md() -> str:
        summary = export_data.get("summary", {}) or {}
        hist = summary.get("difficulty_histogram", {}) or {}
        solved = int(export_data.get("solved_count", 0))
        failed = int(export_data.get("failed_count", 0))
        total_attempted = solved + failed

        def _count(levels: list[int]) -> int:
            s = 0
            for lv in levels:
                s += int(hist.get(str(lv), hist.get(lv, 0)))
            return s

        z1 = _count([1, 2, 3])
        z2 = _count([4, 5])
        z3 = _count([6])
        z4 = _count([7])
        z_total = max(1, z1 + z2 + z3 + z4)

        def _pct(v: int) -> str:
            return f"{(v * 100 / z_total):.1f}%"

        avg_info = summarize_average_difficulty(hist)
        avg_label = str(avg_info.get("label") or "")

        lines = [
            "## 3. 难度分布与水平研判",
            "",
            "![](assets/difficulty_histogram.png)",
            "",
            "![](assets/status_ratio.png)",
            "",
            f"- 平均难度：{avg_label}（均值 {float(avg_info.get('average_value') or 0):.2f}）",
            f"- 题目覆盖区间：入门~普及/提高-(1-3) {z1} 题（{_pct(z1)}）；普及+/提高~提高+/省选-(4-5) {z2} 题（{_pct(z2)}）；省选/NOI-(6) {z3} 题（{_pct(z3)}）；NOI/NOI+/CTSC(7) {z4} 题（{_pct(z4)}）。",
        ]
        if total_attempted > 0:
            lines.append(f"- 通过/未通过：已通过 {solved} 题，未通过 {failed} 题（总尝试 {total_attempted}）。")
        lines.append("")
        lines.append("结论：以难度分布与通过比例为准，当前训练重心应优先覆盖 4-6 档的典型模型题，避免只在 1-3 档堆题量。")
        return "\n".join(lines)

    # 用"图表 + 程序生成说明"替换 AI 的 ASCII 条形图段落，避免乱码/难读
    # v3.9.66 · GESP 版使用专门的"难度分布（GESP 版）"小节标题
    if _is_gesp:
        normalized = re.sub(
            r"(?ms)^\s{0,3}#{2,6}\s*3\.\s*难度分布[^\n]*\n+.*?(?=^\s{0,3}#{2,6}\s|\Z)",
            _build_gesp_difficulty_section_md(export_data) + "\n\n",
            normalized,
        )
    else:
        normalized = re.sub(
            r"(?ms)^\s{0,3}#{2,6}\s*3\.\s*难度分布与水平研判\s*\n+.*?(?=^\s{0,3}#{2,6}\s|\Z)",
            _build_difficulty_chart_section_md() + "\n\n",
            normalized,
        )

    # v3.9.67 · GESP 报告防御：LLM 万一还在主体里输出了"8 级知识地图"表（用户已实测
    # 看到模型凭印象写 100% 覆盖、跟末尾程序化表 0/5 tag 打架），这里强制抹除。
    if _is_gesp:
        normalized = _strip_llm_gesp_8level_table(normalized)

    # v3.9.66 · 注入可信块：NOI 版 vs GESP 版
    if _is_gesp:
        trusted_block = build_gesp_trusted_data_summary_md(
            export_data,
            target_level=int(target_gesp_level or 1),
            highest_passed=int(gesp_highest_passed or 0),
        )
    else:
        trusted_block = build_trusted_data_summary_md(export_data)

    heading_match = re.match(r"^(# .+\n+)", normalized)
    if heading_match:
        head = heading_match.group(1)
        tail = normalized[len(head):]
        return f"{head}{trusted_block}\n\n{tail}"
    return f"{trusted_block}\n\n{normalized}"


def _build_evolution_prompt(export_data: dict) -> str:
    """v3.9.39 + v3.9.43 · 提交代码考古（多版 diff）喂给 AI 的 prompt 构造器。

    v3.9.43 关键改进：禁止"代码丢失 / 历史代码丢失 / 源码丢失"误导性措辞。
    真实情况：源码缓存**有数据**（`web_app.py` 已抓到 1143+ 条 `<uid>/<pid>.json`），
    只是 v3.9.39「代码考古」需要「同一道题多次提交」才能做 diff，
    对于「一提交就 AC」的好学生，`selected_problems` 自然为空。
    原措辞「无代码考古数据」太短，AI 经常脑补成「历史代码全部丢失」，
    给用户造成「bug 丢数据」的误解。

    Returns:
        str: 喂给 AI 的 prompt 片段。
    """
    evolution_data = export_data.get("submission_evolution", {}) or {}
    if evolution_data.get("selected_problems"):
        try:
            from submission_evolution import evolution_to_prompt_block
            return evolution_to_prompt_block(evolution_data)
        except Exception as _evol_e:
            return f"（代码考古数据格式化失败：{_evol_e}）"

    # ----- v3.9.43 · 无多次提交时的友好 fallback -----
    _total_records = sum(
        len(items) for items in (
            export_data.get("passed_items", []) or [],
            export_data.get("failed_items", []) or [],
        )
    )
    _no_diff_note = (
        f"（v3.9.43 · 提示：未抓取到该用户同一道题多次提交的源码记录，"
        f"无法做「逐版 diff」分析；"
        f"但本份报告已抓取 {_total_records} 条提交记录的源码，"
        f"位于「提交行为分析」和「代码风格」章节。）"
    )
    _no_misleading_warn = (
        "（请在 7.5 节输出「代码风格观察」子章节，"
        "引用「提交行为分析」中的 1-2 段代码片段，"
        "分析命名 / 缩进 / 结构 / 算法风格；"
        "**严禁使用「代码丢失」「历史代码丢失」「源码丢失」等措辞**——"
        "这些表述严重误导用户，会让人以为是 bug 丢数据。）"
    )
    return _no_diff_note + "\n" + _no_misleading_warn


def _build_report_prompt(export_data: dict) -> str:
    """v3.9.43 · 单元测试 hook（从 generate_ai_report 里抽出以便单测）。

    当前仅测试用：调用 _build_evolution_prompt 并把结果嵌到一个最小化的
    7.5 节 prompt 框架里。生产路径走 generate_ai_report 不会用到本函数。
    """
    evolution_prompt = _build_evolution_prompt(export_data)
    return (
        "### 7.5 提交代码考古（v3.9.39 · 多版源码 diff · 重点分析）\n"
        + evolution_prompt
    )


def compute_ability_scores(export_data: dict) -> dict[str, int]:
    summary = export_data.get("summary", {}) or {}
    top_tags = summary.get("top_algorithm_tags", []) or summary.get("top_tags", []) or []
    difficulty_histogram = summary.get("difficulty_histogram", {}) or {}
    solved_count = int(export_data.get("solved_count", 0))
    failed_count = int(export_data.get("failed_count", 0))

    keyword_map = {
        "基础实现": [],
        "搜索 / DFS": ["dfs", "搜索", "回溯", "枚举", "树遍历"],
        "动态规划": ["dp", "背包", "区间", "树形", "状压"],
        # v3.9.43 修复：去掉裸关键词 "树"（会把"树形 DP"/"线段树"/"字典树"等
        # 数据结构和 DP 标签全部误算进图论）。改为更明确的"图遍历/树的遍历/树的直径
        # /树的重心/基环树"等图论专属写法，LCA/树形DP 等各自走 lca/dp 关键词。
        "图论": ["图", "tarjan", "lca", "最短路", "并查集", "网络流", "匹配",
                "图遍历", "树的遍历", "树的直径", "树的重心", "基环树"],
        "数据结构": ["线段树", "树状数组", "bit", "堆", "单调", "平衡树", "st表", "数据结构"],
        "字符串 / 数学": ["字符串", "kmp", "hash", "trie", "sam", "数论", "数学", "组合", "计数", "贪心", "构造", "证明"],
    }

    difficulty_total = 0
    weighted = 0
    for key, value in difficulty_histogram.items():
        if str(key).isdigit():
            difficulty_total += int(value)
            weighted += int(key) * int(value)
    avg_difficulty = weighted / difficulty_total if difficulty_total else 0

    scores: dict[str, int] = {}
    for ability, keywords in keyword_map.items():
        score = 35 + min(20, solved_count * 2) - min(12, failed_count * 2)
        if ability == "基础实现":
            score = 48 + min(28, solved_count * 2) + int(avg_difficulty * 4)
        for item in top_tags:
            tag_name = str(item.get("name") or "").lower()
            count = int(item.get("count", 0))
            if any(keyword in tag_name for keyword in keywords):
                score += min(18, count * 2)
        if ability in {"动态规划", "图论", "数据结构", "字符串 / 数学"}:
            score += int(avg_difficulty * 3)
        scores[ability] = max(20, min(95, int(score)))
    return scores


def generate_chart_images(export_data: dict, output_dir: str) -> dict[str, str]:
    ensure_dir(output_dir)
    plt.style.use("default")
    configure_matplotlib_font()
    repair_behavior_analysis_from_items(export_data)

    chart_paths: dict[str, str] = {}
    summary = export_data.get("summary", {}) or {}
    difficulty_histogram = summary.get("difficulty_histogram", {}) or {}
    top_tags = summary.get("top_algorithm_tags", []) or summary.get("top_tags", []) or []
    solved_count = int(export_data.get("solved_count", 0))
    failed_count = int(export_data.get("failed_count", 0))

    difficulty_meta = {level: get_difficulty_style(level) for level in DIFFICULTY_NAME_MAP}

    def _get_hist_count(key: int | str) -> int:
        if key in difficulty_histogram:
            return int(difficulty_histogram[key])
        skey = str(key)
        return int(difficulty_histogram.get(skey, 0))

    numeric_levels = []
    other_keys = []
    for k in difficulty_histogram.keys():
        ks = str(k)
        if ks.isdigit():
            level = int(ks)
            # v3.11.21q · 洛谷官方 7 档 (1-7), 数据里偶尔出现 8/9/10 (旧题/超纲),
            # 越界题归并到 7 档 (最高档 NOI/NOI+/CTSC), 避免图表出现 "8"/"9" 这种乱码标签
            if level > 7:
                level = 7
            if level > 0:
                numeric_levels.append(level)
        else:
            other_keys.append(ks)

    numeric_levels = sorted(set(numeric_levels))
    other_keys = sorted(set(other_keys))

    if numeric_levels or other_keys:
        labels: list[str] = []
        values: list[int] = []
        colors: list[str] = []

        for level in numeric_levels:
            name, color, _ = difficulty_meta.get(level, (str(level), "#4C78A8", "#FFFFFF"))
            labels.append(name)
            values.append(_get_hist_count(level))
            colors.append(color)

        for k in other_keys:
            labels.append(k)
            values.append(_get_hist_count(k))
            colors.append("#4C78A8")

        fig, ax = plt.subplots(figsize=(8.6, 5.0), facecolor="#FFFFFF")
        x = list(range(len(labels)))
        bars = ax.bar(x, values, color=colors, width=0.68, edgecolor="none")
        ax.set_title("题目难度分布（按洛谷难度等级）")
        ax.set_xlabel("难度")
        ax.set_ylabel("题目数量")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=12)
        ax.yaxis.grid(True, linestyle="--", linewidth=0.8, color="#E5E7EB")
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#CBD5E1")
        ax.spines["bottom"].set_color("#CBD5E1")
        max_value = max(values) if values else 0
        total_count = sum(values)
        for idx, (bar, value) in enumerate(zip(bars, values)):
            pct = (value / total_count * 100) if total_count else 0
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + max(max_value * 0.03, 0.12),
                f"{value} 题\n{pct:.1f}%",
                ha="center",
                va="bottom",
                fontsize=11,
                color=colors[idx],
                fontweight="bold",
            )
        fig.tight_layout()
        difficulty_path = os.path.join(output_dir, "difficulty_histogram.png")
        fig.savefig(difficulty_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        chart_paths["difficulty"] = difficulty_path

    fig, ax = plt.subplots(figsize=(6.4, 4.4), facecolor="#FFFFFF")
    counts = [solved_count, failed_count]
    labels = ["已通过", "未通过"]
    colors_list = ["#52C41A", "#FE4C61"]
    if sum(counts) == 0:
        counts = [1]
        labels = ["暂无数据"]
        colors_list = ["#BAB0AC"]
    ax.pie(
        counts,
        labels=labels,
        autopct="%1.0f%%",
        startangle=90,
        colors=colors_list,
        wedgeprops={"width": 0.45, "edgecolor": "#FFFFFF"},
        textprops={"fontsize": 12},
    )
    ax.set_title("通过 / 未通过占比")
    fig.tight_layout()
    status_path = os.path.join(output_dir, "status_ratio.png")
    fig.savefig(status_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    chart_paths["status"] = status_path

    selected_tags = top_tags[:8]
    if selected_tags:
        fig, ax = plt.subplots(figsize=(8.4, 5.0), facecolor="#FFFFFF")
        tag_names = [str(item.get("name") or item.get("id")) for item in selected_tags][::-1]
        tag_counts = [int(item.get("count", 0)) for item in selected_tags][::-1]
        tag_colors = [TAG_CHART_PALETTE[idx % len(TAG_CHART_PALETTE)] for idx in range(len(tag_names))]
        bars = ax.barh(tag_names, tag_counts, color=tag_colors, edgecolor="none")
        ax.set_title("高频算法标签 Top 8")
        ax.set_xlabel("出现次数")
        ax.xaxis.grid(True, linestyle="--", linewidth=0.8, color="#E5E7EB")
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#CBD5E1")
        ax.spines["bottom"].set_color("#CBD5E1")
        for idx, (bar, value) in enumerate(zip(bars, tag_counts)):
            ax.text(value + 0.1, idx, str(value), va="center", fontsize=11, color=tag_colors[idx], fontweight="bold")
        fig.tight_layout()
        tags_path = os.path.join(output_dir, "top_tags.png")
        fig.savefig(tags_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        chart_paths["tags"] = tags_path

    ability_scores = compute_ability_scores(export_data)
    radar_labels = list(ability_scores.keys())
    radar_values = [ability_scores[key] for key in radar_labels]
    if radar_labels:
        angles = [n / float(len(radar_labels)) * 2 * math.pi for n in range(len(radar_labels))]
        angles += angles[:1]
        radar_plot_values = radar_values + radar_values[:1]
        fig = plt.figure(figsize=(6.6, 6.2))
        ax = plt.subplot(111, polar=True)
        ax.set_theta_offset(math.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_thetagrids([angle * 180 / math.pi for angle in angles[:-1]], radar_labels, fontsize=11)
        ax.set_ylim(0, 100)
        zone_colors = [
            (0, 40, "#FDECEC"),
            (40, 65, "#FFF3E0"),
            (65, 85, "#E8F4FF"),
            (85, 100, "#E7F6EC"),
        ]
        zone_angles = [n / 180.0 * math.pi for n in range(361)]
        for start, end, zone_color in zone_colors:
            ax.fill_between(zone_angles, start, end, color=zone_color, alpha=0.35)
        ax.plot(angles, radar_plot_values, color="#4C78A8", linewidth=2)
        ax.fill(angles, radar_plot_values, color="#4C78A8", alpha=0.25)
        ax.set_rgrids([20, 40, 60, 80, 100], angle=90, fontsize=10, color="#8A96A3")
        ax.set_title("能力雷达图", pad=18)
        radar_path = os.path.join(output_dir, "ability_radar.png")
        fig.savefig(radar_path, dpi=180, bbox_inches="tight")
        plt.close(fig)
        chart_paths["radar"] = radar_path
        
    # 生成性格画像雷达图
    behavior_data = export_data.get("behavior_analysis", {})
    personality_scores = behavior_data.get("personality_scores", {})
    if personality_scores:
        p_labels = list(personality_scores.keys())
        p_values = [personality_scores[k] for k in p_labels]
        angles = [n / float(len(p_labels)) * 2 * math.pi for n in range(len(p_labels))]
        angles += angles[:1]
        p_plot_values = p_values + p_values[:1]
        
        fig = plt.figure(figsize=(6.6, 6.2))
        ax = plt.subplot(111, polar=True)
        ax.set_theta_offset(math.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_thetagrids([angle * 180 / math.pi for angle in angles[:-1]], p_labels, fontsize=12)
        ax.set_ylim(0, 100)
        
        # 性格雷达图配色使用偏橙色/活力的色调
        zone_colors = [
            (0, 40, "#F3F4F6"),
            (40, 60, "#E5E7EB"),
            (60, 80, "#FEF3C7"),
            (80, 100, "#FEF08A"),
        ]
        zone_angles = [n / 180.0 * math.pi for n in range(361)]
        for start, end, zone_color in zone_colors:
            ax.fill_between(zone_angles, start, end, color=zone_color, alpha=0.35)
            
        ax.plot(angles, p_plot_values, color="#D97706", linewidth=2.5)
        ax.fill(angles, p_plot_values, color="#F59E0B", alpha=0.3)
        ax.set_rgrids([20, 40, 60, 80, 100], angle=90, fontsize=10, color="#9CA3AF")
        ax.set_title("性格特质雷达图", pad=18, fontsize=12, fontweight="bold", color="#92400E")
        
        p_radar_path = os.path.join(output_dir, "personality_radar.png")
        fig.savefig(p_radar_path, dpi=180, bbox_inches="tight")
        plt.close(fig)
        chart_paths["personality_radar"] = p_radar_path

    # 生成首次 AC 提交次数分布柱状图
    ac_submit_distribution = behavior_data.get("ac_submit_distribution", {})
    if ac_submit_distribution:
        def _dist_get(mapping: dict, key: int) -> int:
            if key in mapping:
                return int(mapping[key])
            return int(mapping.get(str(key), 0))

        # 将字符串键转换为整数排序
        keys = []
        for k in ac_submit_distribution.keys():
            try:
                keys.append(int(k))
            except ValueError:
                pass
        keys.sort()
        
        # 准备 x 和 y 轴数据，合并 >= 10 的部分
        labels = []
        values = []
        count_10_plus = 0
        total_ac = sum(ac_submit_distribution.values())
        
        for k in keys:
            if k >= 10:
                count_10_plus += _dist_get(ac_submit_distribution, k)
            else:
                labels.append(str(k))
                values.append(_dist_get(ac_submit_distribution, k))
                
        if count_10_plus > 0:
            labels.append("10+")
            values.append(count_10_plus)

        if labels:
            fig, ax = plt.subplots(figsize=(8, 4.5))
            # 设置颜色：第一发是深蓝色，其他是浅蓝色
            colors = ["#2563EB" if l == "1" else "#93C5FD" for l in labels]
            bars = ax.bar(labels, values, color=colors, edgecolor="none")
            ax.set_title("首次 AC 提交次数分布", fontsize=12, fontweight="bold")
            ax.set_xlabel("AC 所需提交次数")
            ax.set_ylabel("题目数")
            
            # 在柱子上添加文字标签
            for bar, value in zip(bars, values):
                percentage = (value / total_ac * 100) if total_ac > 0 else 0
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                        f"{value}\n({percentage:.0f}%)",
                        ha="center", va="bottom", fontsize=10)
                        
            fig.tight_layout()
            ac_dist_path = os.path.join(output_dir, "ac_submit_distribution.png")
            fig.savefig(ac_dist_path, dpi=180, bbox_inches="tight")
            plt.close(fig)
            chart_paths["ac_submit_distribution"] = ac_dist_path

    return chart_paths


def build_html_and_pdf(
    report_md: str,
    export_data: dict,
    html_path: str,
    pdf_path: str,
    chart_paths: dict[str, str],
    export_pdf: bool = True,
) -> None:
    # 扩展 markdown，支持表格
    report_html = md.markdown(report_md, extensions=['tables', 'fenced_code'])
    report_html = re.sub(
        r"((?:⭐|☆){1,5})",
        lambda m: render_star_rating_html(m.group(1)),
        report_html,
    )
    
    # 替换错题分页
    # 在 6. **【未通过题目专属题解（从暴力到正解）】** 后面的 h3 题目标题前插入分页符
    report_html = re.sub(r'(<h3>Problem)', r'<div class="page-break"></div>\1', report_html)

    # 动态为表格中的“当前等级”和“优先级”添加圆角徽章颜色样式
    # 使用正则匹配 td 标签里的特定文字，加上 span 标签
    badge_style_base = "display:inline-block;padding:2px 8px;border-radius:9999px;border:1px solid;font-size:12px;font-weight:700;line-height:1.2;white-space:nowrap;"
    badge_styles = {
        "green": badge_style_base + "background:#DCFCE7;color:#166534;border-color:#86EFAC;",
        "orange": badge_style_base + "background:#FFEDD5;color:#9A3412;border-color:#FDBA74;",
        "red": badge_style_base + "background:#FEE2E2;color:#991B1B;border-color:#FCA5A5;",
        "gray": badge_style_base + "background:#F3F4F6;color:#374151;border-color:#D1D5DB;",
    }
    risk_legend_html = '<p style="margin:0 0 12px 0;color:#6b7280;font-size:13px;">优先级说明：S（高/立即处理） · A（中/近期处理） · B（低/可后置）。</p>'
    risk_legend_inserted = False

    level_rules = [
        (re.compile(r"(短板|明显短板|偏弱|弱|无涉及|未涉及|缺失|不会|没涉及|没有涉及|基础弱)", re.I), "red"),
        (re.compile(r"(中等偏稳|有基础|基础稳|待强化|会但赛时成本高|需要加强|高级弱|易错|不熟)", re.I), "orange"),
        (re.compile(r"(稳|强项|覆盖充分|中上|优秀|熟练|稳定)", re.I), "green"),
    ]

    def _clean_cell_inner(inner: str) -> str:
        inner = re.sub(r"</?p[^>]*>", "", inner, flags=re.I)
        inner = re.sub(r"<[^>]+>", "", inner)
        return inner.strip()

    def _wrap_td_inner(td_html: str, display_text: str, style_key: str) -> str:
        m = re.match(r"<td(?P<attrs>[^>]*)>(?P<inner>.*)</td>", td_html, flags=re.S | re.I)
        if not m:
            return td_html
        attrs = m.group("attrs") or ""
        return f'<td{attrs}><span style="{badge_styles[style_key]}">{display_text}</span></td>'

    def _process_table(table_html: str) -> str:
        nonlocal risk_legend_inserted
        is_ability_table = bool(
            re.search(r"<th[^>]*>\s*能力块\s*</th>", table_html, flags=re.I)
            and re.search(r"<th[^>]*>\s*当前等级\s*</th>", table_html, flags=re.I)
        )
        is_risk_table = bool(
            re.search(r"<th[^>]*>\s*优先级\s*</th>", table_html, flags=re.I)
            and re.search(r"<th[^>]*>\s*风险项\s*</th>", table_html, flags=re.I)
        )
        if not (is_ability_table or is_risk_table):
            return table_html

        def _row_repl(m: re.Match) -> str:
            row = m.group(0)
            if "<th" in row:
                return row
            tds = re.findall(r"<td[^>]*>.*?</td>", row, flags=re.S | re.I)
            if not tds:
                return row

            if is_ability_table:
                col_idx = 1
                if len(tds) <= col_idx:
                    return row
                target_td = tds[col_idx]
                inner = re.sub(r"^<td[^>]*>|</td>$", "", target_td, flags=re.S | re.I)
                text = _clean_cell_inner(inner)
                if not text:
                    return row
                style_key = None
                for rule, key in level_rules:
                    if rule.search(text):
                        style_key = key
                        break
                if not style_key:
                    return row
                new_td = _wrap_td_inner(target_td, text, style_key)
                return row.replace(target_td, new_td, 1)

            col_idx = 0
            if len(tds) <= col_idx:
                return row
            target_td = tds[col_idx]
            inner = re.sub(r"^<td[^>]*>|</td>$", "", target_td, flags=re.S | re.I)
            text = _clean_cell_inner(inner)
            normalized = (text or "").strip().upper()
            mapping = {
                "S": ("S（高/立即处理）", "red"),
                "A": ("A（中/近期处理）", "orange"),
                "B": ("B（低/可后置）", "green"),
            }
            if normalized not in mapping:
                return row
            label, style_key = mapping[normalized]
            new_td = _wrap_td_inner(target_td, label, style_key)
            return row.replace(target_td, new_td, 1)

        processed = re.sub(r"<tr>.*?</tr>", _row_repl, table_html, flags=re.S | re.I)
        if is_risk_table and not risk_legend_inserted:
            risk_legend_inserted = True
            return processed + risk_legend_html
        return processed

    report_html = re.sub(r"<table[^>]*>.*?</table>", lambda m: _process_table(m.group(0)), report_html, flags=re.S | re.I)

    # 准备模板数据
    summary = export_data.get("summary", {}) or {}
    difficulty_histogram = summary.get("difficulty_histogram", {}) or {}
    avg_difficulty_info = summarize_average_difficulty(difficulty_histogram)
    avg_difficulty = f"{float(avg_difficulty_info['average_value']):.1f}"
    detail_fetch_overview = build_detail_fetch_overview(export_data.get("detail_fetch_stats", {}) or {})
    
    top_tag = "暂无"
    top_tags = summary.get("top_algorithm_tags", []) or summary.get("top_tags", []) or []
    if top_tags:
        top_tag = str(top_tags[0].get("name") or top_tags[0].get("id"))

    # 渲染 HTML
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('report_template.html')
    html_dir = Path(html_path).resolve().parent
    
    def _chart_src(value: str) -> str:
        if not value:
            return ""
        if value.startswith("data:"):
            return value
        if value.startswith("file:///") or value.startswith("http://") or value.startswith("https://"):
            return value
        p = Path(value)
        if not p.exists():
            return value
        resolved = p.resolve()
        try:
            relative = resolved.relative_to(html_dir)
            return relative.as_posix()
        except ValueError:
            try:
                return resolved.relative_to(html_dir.parent).as_posix()
            except ValueError:
                return resolved.as_uri()

    chart_srcs = {k: _chart_src(v) for k, v in chart_paths.items()}

    rendered_html = template.render(
        export_data=export_data,
        report_html=report_html,
        chart_paths=chart_srcs,
        avg_difficulty=avg_difficulty,
        avg_difficulty_label=str(avg_difficulty_info["label"]),
        avg_difficulty_color=str(avg_difficulty_info["color"]),
        avg_difficulty_text_color=str(avg_difficulty_info["text_color"]),
        detail_fetch_overview=detail_fetch_overview,
        top_tag=top_tag
    )

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(rendered_html)

    if not export_pdf:
        return

    # 导出为 PDF
    console.print("[cyan]正在调用 Playwright 将 HTML 导出为高质量 PDF...[/cyan]")
    temp_pdf_path = f"{pdf_path}.tmp"
    try:
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            # 加上 file:// 协议访问本地 HTML
            file_url = f"file:///{os.path.abspath(html_path).replace(os.sep, '/')}"
            page.goto(file_url)
            page.wait_for_load_state("networkidle")
            page.pdf(
                path=temp_pdf_path,
                format="A4",
                print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}
            )
            browser.close()
        os.replace(temp_pdf_path, pdf_path)
    except Exception as e:
        if os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
            except OSError:
                pass
        console.print(f"[red]PDF 导出失败（Playwright 错误），请确保已运行 `playwright install chromium`。\n错误详情：{e}[/red]")

def load_or_prompt_openai_config():
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_ADMIN_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    
    if not key:
        console.print(Panel("[yellow]OpenAI API Key not found.[/yellow]\nThis tool requires an OpenAI-compatible API key to evaluate your code and generate suggestions.\nIt supports any third-party platform that provides OpenAI-compatible endpoints (e.g., DeepSeek, Moonshot, SiliconFlow, etc.).", title="Configuration"))
        key = Prompt.ask("Please enter your API Key")
        os.environ["OPENAI_API_KEY"] = key.strip()
        
    if not base_url:
        base_url_input = Prompt.ask("Please enter the API Base URL (leave blank for default OpenAI: https://api.openai.com/v1)")
        if base_url_input.strip():
            os.environ["OPENAI_BASE_URL"] = base_url_input.strip()
            base_url = base_url_input.strip()
            
    # Also ask for model if base URL is provided since different platforms have different model names
    model_name = os.environ.get("OPENAI_MODEL_NAME")
    if not model_name:
        default_model = "gpt-4o" if not base_url else ""
        model_input = Prompt.ask(f"Please enter the model name to use (leave blank for default: {default_model})")
        if model_input.strip():
            os.environ["OPENAI_MODEL_NAME"] = model_input.strip()
        else:
            os.environ["OPENAI_MODEL_NAME"] = default_model
            
    return key, base_url, os.environ.get("OPENAI_MODEL_NAME")

def load_or_prompt_cookies():
    cookie_file = Path("cookies.json")
    if cookie_file.exists():
        try:
            return pyLuogu.LuoguCookies.from_file(str(cookie_file))
        except Exception as e:
            console.print(f"[red]Failed to load cookies.json: {e}[/red]")
            
    console.print(Panel("[yellow]Luogu Cookies not found.[/yellow]\nTo fetch your submissions, we need your Luogu cookies.", title="Configuration"))
    client_id = Prompt.ask("Enter your __client_id cookie value")
    uid = Prompt.ask("Enter your _uid cookie value")
    
    cookies = pyLuogu.LuoguCookies({
        "__client_id": client_id.strip(),
        "_uid": uid.strip()
    })
    
    with open("cookies.json", "w", encoding="utf-8") as f:
        json.dump(cookies.to_json(), f, indent=2)
        
    return cookies

def _trim_to_safe_boundary(text: str | None) -> str:
    """把已生成的 partial 文本修剪到最后一个完整行，避免把半句话喂给模型续写。"""
    if not text:
        return ""
    text = text.rstrip()
    if not text:
        return ""
    # 优先尝试切到最后一个 "## " / "### " 之类的二级标题处，作为天然分段点
    boundary_candidates: list[int] = []
    for marker in ("\n## ", "\n### ", "\n#### "):
        idx = text.rfind(marker)
        if idx > 0:
            boundary_candidates.append(idx + 1)  # +1 保留换行符
    # 退化到最后一个换行
    last_newline = text.rfind("\n")
    if last_newline > 0:
        boundary_candidates.append(last_newline + 1)
    if not boundary_candidates:
        return text
    cut = max(boundary_candidates)
    # 至少要保留 80% 内容，否则保守地只切到最后一个换行
    if cut < int(len(text) * 0.2):
        return text
    return text[:cut].rstrip() + "\n"


# ============================================================
# v3.9.64 · GESP 考纲知识结构（CCF GESP C++&Python 1-8 级）
# 来源：GESP 官方认证标准
# ============================================================
GESP_LEVELS: dict[int, dict] = {
    1: {
        "name": "GESP 一级 · 编程入门",
        "themes": ["计算机基础", "IDE 使用", "顺序/分支/循环", "基本数据类型", "基本运算"],
        "key_points": [
            "计算机硬件组成（CPU / 内存 / I/O）",
            "Dev C++ / PyCharm 等 IDE 使用（编辑 / 编译 / 调试）",
            "cin / cout / scanf / printf 输入输出",
            "标识符 / 关键字 / 常量 / 变量",
            "int / long long / float / double / char / bool",
            "if / if-else / switch / 三目运算",
            "for / while / do-while + break / continue",
        ],
        "max_difficulty": 1,  # 入门
        "core_tags": ["顺序结构", "分支结构", "循环结构", "基本 I/O", "变量与类型"],
    },
    2: {
        "name": "GESP 二级 · 基础程序设计",
        "themes": ["存储与网络", "流程图", "ASCII 编码", "类型转换", "多层嵌套", "数学函数"],
        "key_points": [
            "ROM / RAM / Cache 区别",
            "TCP/IP 四层模型 / IP 地址",
            "流程图绘制方法（顺序/分支/循环）",
            "ASCII 编码与转换（'0'=48, 'A'=65, 'a'=97, 空格=32）",
            "强制类型转换 + 隐式类型转换",
            "多层分支 / 多层循环 嵌套",
            "abs / sqrt / max / min / 随机数函数",
        ],
        "max_difficulty": 2,  # 普及-
        "core_tags": ["类型转换", "ASCII", "嵌套循环", "数学函数", "流程图"],
    },
    3: {
        "name": "GESP 三级 · 数据编码与基础算法",
        "themes": ["原码/反码/补码", "进制转换", "位运算", "一维数组", "字符串", "枚举法", "模拟法"],
        "key_points": [
            "原码 / 反码 / 补码 概念",
            "二进制 / 八进制 / 十进制 / 十六进制 互转",
            "位运算：& | ~ ^ << >>",
            "C++ 一维数组 / Python 列表/字典/元组/集合",
            "字符串及其函数（大小写转换 / 搜索 / 分割 / 替换）",
            "枚举法（暴力穷举）",
            "模拟法（按题意逐步实现）",
        ],
        "max_difficulty": 2,  # 普及-
        "core_tags": ["位运算", "进制转换", "数组", "字符串", "枚举", "模拟"],
    },
    4: {
        "name": "GESP 四级 · 函数与排序",
        "themes": ["函数", "指针概念", "结构体", "二维数组", "递推", "排序算法", "文件读写", "异常处理"],
        "key_points": [
            "函数定义 / 调用 / 形参实参 / 作用域",
            "C++ 指针类型基本概念",
            "C++ 结构体 + Python 复合类型嵌套",
            "二维 / 多维数组",
            "递推算法（递推关系式推导）",
            "排序算法：冒泡 / 插入 / 选择 + 稳定性",
            "文件读写（重定向 / 文本文件）",
            "异常处理 try-catch",
        ],
        "max_difficulty": 3,  # 普及/提高-
        "core_tags": ["函数", "指针", "结构体", "二维数组", "递推", "排序", "文件读写"],
    },
    5: {
        "name": "GESP 五级 · 数论与链表",
        "themes": ["初等数论", "高精度", "链表", "素数筛", "二分", "贪心", "分治", "递归"],
        "key_points": [
            "辗转相除法（欧几里得算法）",
            "素数筛：埃氏筛 / 线性筛",
            "唯一分解定理",
            "高精度加 / 减 / 乘 / 除（数组模拟）",
            "单链表 / 双链表 / 循环链表",
            "二分查找 / 二分答案",
            "贪心算法",
            "分治算法（归并排序 / 快速排序）",
            "递归",
        ],
        "max_difficulty": 4,  # 普及+/提高
        "core_tags": ["数论", "素数筛", "链表", "高精度", "二分", "贪心", "分治", "递归"],
    },
    6: {
        "name": "GESP 六级 · 树与基础 DP",
        "themes": ["树结构", "哈夫曼", "DFS/BFS", "基础动态规划", "面向对象", "栈/队列"],
        "key_points": [
            "树的定义 / 构造 / 遍历",
            "哈夫曼树 / 哈夫曼编码",
            "完全二叉树 / 二叉排序树",
            "深度优先搜索（DFS）",
            "广度优先搜索（BFS）",
            "简单动态规划（一维 DP / 背包问题）",
            "面向对象：类的创建",
            "栈 / 队列 / 循环队列",
        ],
        "max_difficulty": 4,  # 普及+/提高
        "core_tags": ["树", "哈夫曼", "DFS", "BFS", "动态规划", "栈", "队列"],
    },
    7: {
        "name": "GESP 七级 · 图与复杂 DP",
        "themes": ["复杂动态规划", "图遍历", "图论基础", "哈希表", "数学库函数"],
        "key_points": [
            "复杂动态规划（二维 DP / 最值优化）",
            "图的定义与遍历",
            "图论基本算法（DFS / BFS / 泛洪算法）",
            "哈希表",
            "数学库常用函数（三角 / 对数 / 指数）",
        ],
        "max_difficulty": 5,  # 提高+/省选-
        "core_tags": ["动态规划", "图论", "哈希表", "DFS", "BFS", "泛洪"],
    },
    8: {
        "name": "GESP 八级 · 高级算法",
        # v3.9.65 · 严格按 CCF GESP C++&Python 八级标准（一）（1）-（8）补全，
        # 见 GESP考纲.pdf.txt 第 793-869 行。
        "themes": [
            "计数原理",
            "排列与组合",
            "杨辉三角",
            "倍增法",
            "代数与平面几何",
            "图论算法及综合应用",
            "算法时间/空间效率分析",
            "算法优化",
        ],
        "key_points": [
            # (1) 计数原理
            "加法原理（互斥事件的方案数 = 各方案数之和）",
            "乘法原理（分步事件的方案数 = 各步方案数之积）",
            "加法原理 vs 乘法原理的判定（分类 vs 分步）",
            # (2) 排列与组合
            "排列 A(n,k) = n! / (n-k)! 的定义与计算",
            "组合 C(n,k) = n! / (k! (n-k)!) 的定义与计算",
            "排列组合编程：枚举 / 递推 / 卢卡斯定理（入门）",
            "常见组合恒等式（C(n,k)=C(n,n-k)、杨辉递推）",
            # (3) 杨辉三角
            "杨辉三角（帕斯卡三角）的定义：C(n,k) = C(n-1,k-1) + C(n-1,k)",
            "杨辉三角的编程实现（递推 / 二维数组 / 单行滚动）",
            "杨辉三角与组合数的关系",
            # (4) 倍增法
            "倍增法（二分倍增）思想：用 2 的幂次拼出任意步长",
            "倍增法时间复杂度：O(log N) 次迭代",
            "ST 表 / 树上倍增 LCA 等典型倍增应用（概念）",
            # (5) 代数与平面几何（限初中数学）
            "一元一次方程的求解（编程实现：移项 + 系数化 1）",
            "二元一次方程组的求解（消元法 / 代入法）",
            "平面几何基础图形的面积：长方形 / 正方形 / 三角形 / 圆形 / 梯形",
            "基础平面几何概念（周长、面积、相似三角形入门）",
            # (6) 图论算法及综合应用
            "最小生成树（MST）概念：n 个点用 n-1 条边连通且权值和最小",
            "Kruskal 算法（按边权排序 + 并查集判环）",
            "Prim 算法（按点扩展，类 Dijkstra 思想）",
            "单源最短路径概念",
            "Dijkstra 算法（非负权图，O((n+m) log n)）",
            "SPFA / Bellman-Ford（含负权边的单源最短路）",
            "Floyd 多源最短路径（O(n³) 动态规划）",
            "图论综合应用：MST + 最短路、差分约束（入门概念）",
            # (7) 算法时间/空间效率分析
            "时间复杂度一般分析方法（循环层数 × 内层执行次数）",
            "空间复杂度一般分析方法（递归栈 / 数组 / 哈希表占用）",
            "排序算法（冒泡 / 插入 / 选择 / 归并 / 快速 / 堆排）复杂度对比",
            "查找算法（顺序 / 二分 / 哈希）复杂度对比",
            "树 / 图的遍历（DFS / BFS）复杂度：O(n+m)",
            "搜索算法（回溯 / BFS / DFS）复杂度",
            "分治算法（归并 / 快速排序）复杂度：O(n log n)",
            "动态规划（DP）算法的时间/空间复杂度",
            # (8) 算法优化
            "不同算法求解同一问题的复杂度差异（如：枚举求和 vs 等差数列公式）",
            "算法优化的一般方法：剪枝 / 预处理 / 哈希 / 二分 / 数学化简",
            "用数学知识优化算法：等差数列求和公式 n(a₁+aₙ)/2",
            "用数学知识优化算法：等比数列求和公式 a₁(1-qⁿ)/(1-q)",
            "用数学知识优化算法：前缀和 / 差分替代 O(n²) 区间操作",
        ],
        "max_difficulty": 6,  # 省选/NOI-
        "core_tags": [
            "组合数学", "排列组合", "杨辉三角", "倍增",
            "代数方程", "平面几何",
            "最小生成树", "最短路", "Dijkstra", "Floyd", "Kruskal", "Prim",
            "时间复杂度", "空间复杂度", "算法优化",
        ],
    },
}

# 难度名映射（与洛谷官方 7 档对齐）
DIFFICULTY_DISPLAY = {
    0: "暂无评定", 1: "入门", 2: "普及-", 3: "普及/提高-",
    4: "普及+/提高", 5: "提高+/省选-", 6: "省选/NOI-", 7: "NOI/NOI+/CTSC",
}


def _build_gesp_prompt(
    export_data: dict,
    luogu_uid: str,
    target_level: int,
    profile_block: str,
    gesp_history_block: str,
    vjudge_block: str = "（学员未绑定 VJudge,无跨平台数据。AtCoder 已弃用。）",
) -> str:
    """v3.9.64 · 构建 GESP 报告的 prompt（聚焦 8 级知识体系 + 备考路线图）"""
    import datetime as _dt
    current_time = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    # 把 GESP 8 级大纲注入 prompt
    gesp_outline_lines = []
    for lv in range(1, 9):
        info = GESP_LEVELS[lv]
        gesp_outline_lines.append(f"### {info['name']}")
        gesp_outline_lines.append(f"**主题**：{' / '.join(info['themes'])}")
        gesp_outline_lines.append(f"**核心 tags**：{' / '.join(info['core_tags'])}")
        gesp_outline_lines.append(f"**对应洛谷难度上限**：d ≤ {info['max_difficulty']}（{DIFFICULTY_DISPLAY.get(info['max_difficulty'], '?')}）")
        gesp_outline_lines.append("**关键知识点**：")
        for kp in info["key_points"]:
            gesp_outline_lines.append(f"  - {kp}")
        gesp_outline_lines.append("")
    gesp_outline_md = "\n".join(gesp_outline_lines)

    # 学员 GESP 历史
    solved = export_data.get("solved_count", 0)
    failed = export_data.get("failed_count", 0)
    summary = export_data.get("summary", {}) or {}
    diff_hist = summary.get("difficulty_histogram") or {}
    top_tags = summary.get("top_algorithm_tags") or summary.get("top_tags") or []

    # v3.9.74 · VJudge 跨平台数据块(取代 AtCoder)
    vjudge_data = export_data.get("vjudge_data") or {}
    if vjudge_data.get("linked"):
        vjudge_block = (
            f"- VJudge username: {vjudge_data.get('username','')}\n"
            f"- 昵称: {vjudge_data.get('nick','') or '(未设置)'}\n"
            f"- 已解决题数: {vjudge_data.get('solved_count', 0)}\n"
            f"- 总提交: {vjudge_data.get('total_submissions', 0)} | "
            f"AC {vjudge_data.get('total_ac', 0)} | "
            f"AC 率: {float(vjudge_data.get('ac_rate', 0))*100:.1f}%\n"
            f"- 各 OJ 分布: {vjudge_data.get('oj_distribution', '无')}\n"
            f"- 最近 5 个已解决题: {vjudge_data.get('recent_solved', '无')}\n"
            f"（说明: VJudge 跨平台汇总,用于评估多 OJ 活跃度,非 GESP 真考成绩。）"
        )
    else:
        vjudge_block = "（学员未绑定 VJudge,无跨平台数据。AtCoder 已弃用。）"

    # 学员已通过的级别（从 gesp_history_block 文本里用正则抽）
    import re as _re
    passed_levels = []
    for m in _re.finditer(r"GESP L(\d+).*?✅通过", gesp_history_block):
        passed_levels.append(int(m.group(1)))
    current_max = max(passed_levels) if passed_levels else 0

    return f"""你是一位顶级的青少年编程教师与 GESP 认证规划师，专注于帮中小学生系统化备战 CCF GESP 等级认证。
请你根据我提供的【GESP 8 级官方考纲】和【学员洛谷做题数据】，对学员进行 GESP 维度的深度诊断，并制定**冲刺目标级别**的备考路线图。

**报告生成时间**：{current_time}
**目标 GESP 级别**：{target_level} 级（{GESP_LEVELS.get(target_level, {}).get('name', '?')}）
> ⚠️ v3.9.65 · 本目标级别由系统按"就高不就低"原则自动判定，优先级：
>   1) 学员 GESP 真考最高级 + 该级最近分（CCF 跳级规则：60-89 → N+1；90+ → N+2；封顶 8）
>   2) 学员自录最高级（兜底）
>   3) 洛谷通过题数 AI 估算
>   4) 全新学员默认 1 级
> 如果学员已通过较高 GESP 级（≥ 3 级），**不要再建议下调到 1 级去"打基础"**——可以直接基于目标级别做备考路线图，并显式给出"保底通过 1 级（如有需要）+ 跳级冲高"双策略。

### GESP 8 级官方考纲（CCF 2025 版）
{gesp_outline_md}

### 学员学籍档案
{profile_block or "（无档案数据）"}

### 学员 GESP 真考历史
{gesp_history_block or "（暂无 GESP 真考记录，按全新学员处理）"}

### 学员当前洛谷做题统计
- 本次导出已通过题数：{solved}
- 本次导出未通过/卡住题数：{failed}
- 难度分布直方图：{json.dumps(diff_hist, ensure_ascii=False)}
- 偏好的算法标签 TOP：{json.dumps(top_tags, ensure_ascii=False)}

### 学员的跨平台做题画像（v3.9.74 · VJudge 取代 AtCoder,只读公开数据）
{vjudge_block}

### 重要：洛谷标签覆盖与 GESP 考纲的对应关系（v3.9.65 用户反馈）
- 洛谷上的题目标签主要围绕算法（DP / 图论 / 数论 / 数据结构）展开，**不是按 GESP 1-8 级考纲一一对应的**。
- 学员在 GESP 1-3 级（计算机基础 / 顺序分支循环 / 数组字符串 / 排序函数）这类"基础编程"知识点上**看起来"未接触/空白"**，
  **不一定是真实薄弱**——很可能只是没在洛谷上训练过这些基础题。
- 学员的真实能力以"GESP 真考级别"为最权威依据（见上方"学员 GESP 真考历史"）。
  请在知识盲区诊断、训练计划、家长建议等章节中**显式区分**：
  - ✅ 真考已通过的级别（直接信任）
  - 🔍 洛谷数据可观测的薄弱（要练）
  - ⚠️ 洛谷数据缺失的级别（先验证再判断，不要直接判"未掌握"）

请你输出一份**专为 GESP 备考**的结构化 Markdown 报告，必须包含以下章节（顺序固定）。风格要求：
 - **不要复刻 NOI-CSP 报告的"6 维雷达图"**——GESP 报告是按 8 级知识地图展开的；
 - **不要把"目标级别 1 级 / 入门"当默认起点**——目标级别已自动校准为学员实际能力对应的级别；
 - 难度名称必须使用洛谷官方口径：入门 / 普及- / 普及/提高- / 普及+/提高 / 提高+/省选- / 省选/NOI- / NOI/NOI+/CTSC；
 - 等级前缀符号使用 🟢已掌握 | 🟡部分掌握 | 🟠薄弱 | 🔴未接触 | ⚪不要求 | ⚠️数据缺失；
 - 表格优先，少用长段落；每节结尾用 `<p class="text-blue-700 font-semibold">建议：...</p>` 收口。

**v3.9.67 · 重要红线：禁止输出"GESP 8 级知识地图"表**

本报告末尾会由代码自动注入一张**程序化的、基于真实洛谷做题数据**的 8 级知识地图
（位于 `## 数据校准与真实统计（GESP 8 级版）` 小节）。如果模型在报告主体也生成
一张，会出现两张表数据自相矛盾的 bug（模型凭印象写 100% 覆盖、程序化表写
0/5 tag，家长看不懂）。所以：

- **禁止**在报告主体输出"8 级知识地图 · 学员覆盖度"这种完整 8 行表；
- **禁止**在分析段落中伪造"GESP X 级已掌握 N%"等覆盖率数据；
- 如确需在分析中提到 1-8 级状态，**只能写"详见末尾数据校准小节"**，不允许列出
  8 行 8 列的具体覆盖百分比。

 1. **【GESP 进度总览】**
    用 Markdown 表格输出学员的 GESP 进度：`| 维度 | 状态 | 数据依据 |`
    **必须包含 6 行**（顺序固定）：
    1) 学员已通过最高级别  2) 最近一次考试分  3) 距目标级别 {target_level} 还差几级  4) 是否能免 CSP-J 初赛  5) 是否能免 CSP-S 初赛  6) 建议最近一次考试时间
    状态列用 emoji 徽章（✅/❌/⏳）+ 简短文字。

 2. **【目标级别（{target_level} 级）知识盲区诊断】**
    针对目标级别 `{target_level}` 的所有 key_points（见上方 GESP 大纲），逐一对照学员洛谷做题数据：
    - 列出 **3-5 个学员已掌握** 的关键点（写"已掌握"，并给出 1-2 道题号证明）；
    - 列出 **3-5 个学员未掌握 / 薄弱** 的关键点（写"未掌握/薄弱"，并说明数据证据：从未 AC 过相关 tag / 难度达不到 / 提交卡在某个题型）；
    - 输出一段 80-150 字的"学员 vs 目标级别差距"诊断文字。

 3. **【从当前级别到目标级别 · 6 个月备考路线图】**
    按月分阶段（如果当前级别 0 / 1 / 2，每阶段 2 个月；如果 3+，每阶段 1-2 个月），输出训练计划表：
    `| 阶段 | 月份 | 主攻级别 | 核心知识点 | 推荐题单（洛谷题号） | 验收标准 |`
    **至少 3 行**（不能只写 1 阶段敷衍）。每阶段：
    - **主攻级别**：明确写出 GESP X 级；
    - **核心知识点**：从 GESP 大纲里挑 3-5 个该阶段必须搞定的 key_points；
    - **推荐题单**：每阶段给 3-5 道洛谷题号（按 Pxxxx 格式），并简述推荐理由（不超过 20 字）；
    - **验收标准**：用什么方式判断"该阶段完成"（如：模拟考分数 ≥ 80 / 关键 tag 题量 ≥ 30 / 历年真题通过率 ≥ 60%）。

 4. **【训练弱项 TOP 5 · 优先突破】**
    输出 Markdown 表格：`| 排名 | 弱项 | 触发场景 | 训练方法 | 推荐资源 |`
    **必须 5 行**。弱项从第 2 节的"未掌握"清单里挑，按"提分性价比"排序（S > A > B）。每行训练方法要具体到"每天刷几道、刷多久"。

 5. **【GESP 报名 & 考试策略建议】**
    - **下次报名建议**：GESP 一年 4 次（3/6/9/12 月），根据学员当前进度推荐最佳报名月份；
    - **模拟考建议**：考前 1 个月怎么刷真题（年份 + 套数）；
    - **跳级策略**：学员是否适合跳级（90+ 分的判定），如果当前已通过级别 ≥ 4，建议尝试跳级 1-2 级；
    - **考前心理建设**：1-2 句鼓励性文字。

 6. **【核心建议（家长可执行版）】**
    列出 5-8 条核心建议，按优先级排序（🔴紧急 / 🟡重要 / 🟢建议）。重点告诉家长"接下来 1 个月 / 3 个月 / 6 个月要做什么"，避免空话。例如：
    - 🔴 紧急：未来 2 周内完成 5 道 GESP 5 级真题，记录错题
    - 🟡 重要：每周固定 4 小时算法训练 + 1 小时真题模拟
    - 🟢 建议：报名 6 月 GESP 5 级，目标 80+

 7. **【风险提示】**
    - 列出 2-3 条"学员接下来 3 个月最大的潜在风险"（如：难度断层 / 心理瓶颈 / 时间投入不足）；
    - 每条风险给出"规避方案"。
"""


def generate_gesp_report(
    export_data: dict,
    api_key: str,
    base_url: str | None,
    model_name: str,
    *,
    output_path: str | None = None,
    resume_prefix: str | None = None,
    luogu_uid: str = "",
    target_level: int = 1,
) -> str:
    """v3.9.64 · 生成 GESP 备考报告（参照 GESP 1-8 级官方考纲）

    与 generate_ai_report 的关键区别：
      1. 报告主体按 GESP 8 级展开，不复用"6 维雷达图 / 风险诊断表"；
      2. 学员的 GESP 真考历史 + 洛谷做题数据 + 目标级别 三方对照；
      3. 给出 6 个月备考路线图 + 弱项 TOP 5 + 报名考试策略。

    Args:
        export_data: 选手数据导出结构（与 generate_ai_report 共享）
        api_key: OpenAI 兼容 API Key
        base_url: 可选第三方 Base URL
        model_name: 模型名
        output_path: 流式增量写入文件
        resume_prefix: 续写前缀
        luogu_uid: 洛谷 UID，用于拉学员档案 + GESP 真考历史
        target_level: 用户选择的目标 GESP 级别（1-8）
    """
    if not str(api_key or "").strip():
        raise ValueError("未配置 OpenAI API Key")

    # 拉学员档案 + GESP 真考历史
    profile_block = ""
    gesp_history_block = ""
    if luogu_uid:
        try:
            from task_store import _get_conn as _ts_get_conn
            conn = _ts_get_conn()
            try:
                stu_row = conn.execute(
                    "SELECT id, real_name, gender, birth_date, school, city, grade, province "
                    "FROM students WHERE luogu_uid = ?",
                    (str(luogu_uid).strip(),),
                ).fetchone()
                if stu_row:
                    sd = dict(stu_row)
                    sid_int = int(sd.get("id") or 0)
                    age_str = ""
                    if sd.get("birth_date"):
                        try:
                            from datetime import date as _date
                            y, m, d = [int(x) for x in str(sd["birth_date"]).split("-")[:3]]
                            today = _date.today()
                            age = today.year - y - ((today.month, today.day) < (m, d))
                            age_str = f"{age}岁"
                        except Exception:
                            age_str = str(sd.get("birth_date") or "")
                    profile_lines = [
                        f"- 姓名：{sd.get('real_name') or '未填'}",
                        f"- 性别/年龄：{'男' if (sd.get('gender') or '').upper() == 'M' else '女' if (sd.get('gender') or '').upper() == 'F' else '未填'} / {age_str or '未填'}",
                        f"- 学校：{sd.get('school') or '未填'}",
                        f"- 城市/年级：{sd.get('city') or '未填'} / {sd.get('grade') or '未填'}",
                    ]
                    profile_block = "\n".join(profile_lines)

                # GESP 真考历史
                gesp_lines = []
                try:
                    for g in conn.execute(
                        "SELECT g.registered_level, g.actual_score, g.passed, "
                        "       g.certificate_no, c.name AS exam_name, c.exam_date, c.data_year "
                        "FROM gesp_exams g LEFT JOIN competitions c ON c.id = g.exam_id "
                        "WHERE g.student_id = ? ORDER BY COALESCE(c.exam_date, g.award_year || '-12-31') DESC",
                        (sid_int,),
                    ).fetchall():
                        gd = dict(g)
                        passed = "✅通过" if gd.get("passed") else "❌未通过"
                        score = f"{gd.get('actual_score')}分" if gd.get("actual_score") else "未记录分数"
                        gesp_lines.append(
                            f"  - GESP L{gd.get('registered_level')} · {gd.get('exam_name') or gd.get('data_year') or '?'} · {passed} · {score}"
                        )
                except Exception as _ge:
                    import logging as _lg
                    _lg.getLogger("luogu_evaluator").error(
                        f"[v3.9.64 /generate_gesp_report] 查 GESP 失败 sid={sid_int}: {_ge}",
                        exc_info=True,
                    )
                if gesp_lines:
                    gesp_history_block = "\n".join(gesp_lines)
                else:
                    gesp_history_block = "（暂无 GESP 真考记录，按全新学员处理）"
            finally:
                conn.close()
        except Exception as _e:
            import logging as _lg
            _lg.getLogger("luogu_evaluator").error(
                f"[v3.9.64 /generate_gesp_report] 拉档案失败 uid={luogu_uid}: {_e}",
                exc_info=True,
            )

    # v3.9.74 · VJudge 跨平台数据块(取代 AtCoder)→ 喂给 GESP 报告
    vjudge_data = export_data.get("vjudge_data") or {}
    if vjudge_data.get("linked"):
        vjudge_block = (
            f"- VJudge username: {vjudge_data.get('username','')}\n"
            f"- 昵称: {vjudge_data.get('nick','') or '(未设置)'}\n"
            f"- 已解决题数: {vjudge_data.get('solved_count', 0)}\n"
            f"- 总提交: {vjudge_data.get('total_submissions', 0)} | "
            f"AC {vjudge_data.get('total_ac', 0)} | "
            f"AC 率: {float(vjudge_data.get('ac_rate', 0))*100:.1f}%\n"
            f"- 各 OJ 分布: {vjudge_data.get('oj_distribution', '无')}\n"
            f"- 最近 5 个已解决题: {vjudge_data.get('recent_solved', '无')}\n"
            f"（说明: VJudge 跨平台汇总,用于评估多 OJ 活跃度,非 GESP 真考成绩。）"
        )
    else:
        vjudge_block = "（学员未绑定 VJudge,无跨平台数据。AtCoder 已弃用。）"

    # 构建 prompt
    prompt = _build_gesp_prompt(
        export_data, luogu_uid, target_level, profile_block, gesp_history_block,
        vjudge_block=vjudge_block,
    )

    # 续写模式追加
    if resume_prefix:
        trimmed = _trim_to_safe_boundary(resume_prefix)
        if trimmed:
            prompt = prompt + f"""

---

### 续写模式（重要）
以下是**已经生成的开头**（可能因网络中断/超时而中止），请你**直接从该前缀的下一个字符开始续写剩余部分**：
- **不要重复输出已有内容**
- **不要写"以下是..."、"好的"、"我继续"等开场白**
- 保持与已有内容**完全一致**的 Markdown 风格、章节顺序

[已生成内容开始]
{trimmed}
[已生成内容结束]
"""

    system_prompt = (
        "你是顶级的青少年编程教师与 GESP 认证规划师，"
        "熟悉 CCF GESP 1-8 级考纲与 C++/Python 双语言教学，"
        "擅长把抽象算法知识拆解为中小学生可吸收的训练计划。"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    client_kwargs = {
        "api_key": api_key,
        "timeout": 1800.0,
    }
    if base_url:
        client_kwargs["base_url"] = base_url
    client = OpenAI(**client_kwargs)

    if output_path:
        # 复用流式生成逻辑
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        initial_content = _trim_to_safe_boundary(resume_prefix) if resume_prefix else ""
        collected: list[str] = []
        with open(output_path, "w", encoding="utf-8") as f:
            if initial_content:
                f.write(initial_content)
                f.flush()
            try:
                stream = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    stream=True,
                    timeout=1800.0,
                )
                for chunk in stream:
                    if not chunk.choices:
                        continue
                    content_piece = getattr(chunk.choices[0].delta, "content", None) or ""
                    if content_piece:
                        collected.append(content_piece)
                        f.write(content_piece)
                        f.flush()
            except Exception:
                raise
        full_content = initial_content + "".join(collected)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_content)
        return full_content

    # 非流式
    response = client.chat.completions.create(
        model=model_name, messages=messages, timeout=1800.0
    )
    return response.choices[0].message.content or ""


def generate_ai_report(
    export_data: dict,
    api_key: str,
    base_url: str | None,
    model_name: str,
    *,
    output_path: str | None = None,
    resume_prefix: str | None = None,
    luogu_uid: str = "",
) -> str:
    """生成 AI Markdown 报告。

    Args:
        export_data: 选手数据导出结构
        api_key: OpenAI 兼容 API Key
        base_url: 可选的第三方 Base URL
        model_name: 模型名
        output_path: 若提供，token 会以流式增量写入该文件，断连时 partial 留在文件里
        resume_prefix: 若提供，作为"已生成的开头"喂给模型，要求其直接续写
        luogu_uid: v3.8 · 洛谷 UID，用于拉取学员档案（GESP/CSP 奖项 + 政策匹配）注入 prompt
    """
    from syllabus_matcher import format_syllabus_report, load_syllabus_context

    repair_behavior_analysis_from_items(export_data)

    client_kwargs = {
        "api_key": api_key,
        "timeout": 1800.0,  # 30 分钟读超时，避免大报告被中途断开
    }
    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)
    
    solved_count = export_data.get("solved_count", 0)
    failed_count = export_data.get("failed_count", 0)
    summary = export_data.get("summary", {})

    # 提取代码样本（通过的题）
    passed_samples = []
    for item in export_data.get("passed_items", []):
        record = item.get("record")
        if record and isinstance(record, dict) and record.get("sourceCode"):
            passed_samples.append(f"### Problem {item['problem']['pid']} - {item['problem']['title']} (Passed)\n```cpp\n{record['sourceCode'][:800]}\n```\n")
        if len(passed_samples) >= 3:
            break

    # 提取未通过/做错的题
    failed_samples = []
    for item in export_data.get("failed_items", []):
        record = item.get("record")
        pid = item['problem']['pid']
        title = item['problem']['title']
        code_str = ""
        if record and isinstance(record, dict) and record.get("sourceCode"):
            code_str = f"User's failed code snippet:\n```cpp\n{record['sourceCode'][:800]}\n```\n"
        failed_samples.append(f"### Problem {pid} - {title} (Attempted but NOT passed)\n{code_str}")
        if len(failed_samples) >= 5: # Limit failed examples
            break

    # 行为分析数据
    behavior_data = export_data.get("behavior_analysis", {})
    behavior_summary = ""
    if behavior_data and "error" not in behavior_data:
        from behavior_analyzer import format_behavior_summary
        behavior_summary = format_behavior_summary(behavior_data)
    else:
        behavior_summary = f"**提交行为分析**: {behavior_data.get('error', '未获取到提交记录数据。')}"

    # 代码风格静态分析
    from code_analyzer import analyze_code_style, format_code_analysis
    code_records = []
    for item in export_data.get("passed_items", []) + export_data.get("failed_items", []):
        if "record" in item and isinstance(item["record"], dict):
            code_records.append(item["record"])
    
    code_analysis_data = analyze_code_style(code_records)
    code_analysis_summary = format_code_analysis(code_analysis_data)

    # v3.9.39 · 提交代码考古（多版 diff）喂给 AI
    evolution_prompt = _build_evolution_prompt(export_data)

    # 大纲对标数据
    syllabus_eval = export_data.get("syllabus_evaluation", {})
    syllabus_summary = ""
    if syllabus_eval:
        syllabus_summary = format_syllabus_report(syllabus_eval)
    else:
        syllabus_summary = "**大纲知识点对标**: 未获取到评估数据。"

    # 六维评分
    six_dim = export_data.get("six_dimension_scores", {})
    six_dim_text = ""
    if six_dim:
        six_dim_text = "| 维度 | 评分 |\n|------|------|\n"
        for dim, score in six_dim.items():
            six_dim_text += f"| {dim} | {score} |\n"

    syllabus_context_info = load_syllabus_context(max_chars=20000)
    syllabus_context = ""
    if syllabus_context_info.get("content"):
        source_path = syllabus_context_info.get("path") or "未知路径"
        syllabus_context = (
            f"【2025 大纲真实来源】{syllabus_context_info.get('source')} | {source_path}\n"
            f"{syllabus_context_info['content']}\n\n"
        )

    import datetime
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    difficulty_guide = """
洛谷难度映射请严格使用以下标准名称，不要写“难度1/难度2”：
- 0: 暂无评定（灰色）
- 1: 入门（红色）
- 2: 普及-（橙色）
- 3: 普及/提高-（黄色）
- 4: 普及+/提高（绿色）
- 5: 提高+/省选-（蓝色）
- 6: 省选/NOI-（紫色）
- 7: NOI/NOI+/CTSC（黑色）
"""

    # v3.8 · 拉取学员完整档案 + GESP/CSP 奖项 + 当地政策匹配，注入 prompt
    profile_block = ""
    policy_block = ""
    if luogu_uid:
        try:
            from task_store import _get_conn as _ts_get_conn, match_school_for_student
            conn = _ts_get_conn()
            try:
                stu_row = conn.execute(
                    "SELECT id, real_name, gender, birth_date, school, city, grade "
                    "FROM students WHERE luogu_uid = ?",
                    (str(luogu_uid).strip(),),
                ).fetchone()
                if stu_row:
                    sd = dict(stu_row)
                    sid_int = int(sd.get("id") or 0)
                    # 年龄换算
                    age_str = ""
                    if sd.get("birth_date"):
                        try:
                            from datetime import date as _date
                            y, m, d = [int(x) for x in str(sd["birth_date"]).split("-")[:3]]
                            today = _date.today()
                            age = today.year - y - ((today.month, today.day) < (m, d))
                            age_str = f"{age}岁"
                        except Exception:
                            age_str = str(sd.get("birth_date") or "")
                    # GESP 真考历史
                    gesp_lines = []
                    for g in conn.execute(
                        "SELECT g.registered_level, g.actual_score, g.passed, "
                        "       c.name AS exam_name, c.data_year "
                        "FROM gesp_exams g LEFT JOIN competitions c ON c.id = g.exam_id "
                        "WHERE g.student_id = ? ORDER BY c.event_date DESC",
                        (sid_int,),
                    ).fetchall():
                        gd = dict(g)
                        passed = "✅通过" if gd.get("passed") else "❌未通过"
                        score = f"{gd.get('actual_score')}分" if gd.get("actual_score") else "未记录分数"
                        gesp_lines.append(
                            f"  - GESP L{gd.get('registered_level')} · {gd.get('exam_name') or gd.get('data_year') or '?'} · {passed} · {score}"
                        )
                    # CSP/NOIP/NOI 奖项
                    award_lines = []
                    for a in conn.execute(
                        "SELECT competition_type, award_level, award_year, actual_score, province "
                        "FROM csp_awards WHERE student_id = ? ORDER BY award_year DESC",
                        (sid_int,),
                    ).fetchall():
                        ad = dict(a)
                        type_label = {
                            "csp_j_pre": "CSP-J 初赛", "csp_j_final": "CSP-J 复赛",
                            "csp_s_pre": "CSP-S 初赛", "csp_s_final": "CSP-S 复赛",
                            "noip_1": "NOIP 普及组", "noi_bronze": "NOI 铜牌",
                            "noi_silver": "NOI 银牌", "noi_gold": "NOI 金牌",
                        }.get(ad.get("competition_type") or "", ad.get("competition_type") or "?")
                        level_label = {
                            "excellent": "优秀", "first": "一等", "second": "二等",
                            "third": "三等", "bronze": "铜牌", "silver": "银牌", "gold": "金牌",
                        }.get(ad.get("award_level") or "", ad.get("award_level") or "?")
                        score = f" · {ad.get('actual_score')}分" if ad.get("actual_score") else ""
                        prov = f" · {ad.get('province')}" if ad.get("province") else ""
                        award_lines.append(
                            f"  - {ad.get('award_year')} {type_label} {level_label}{score}{prov}"
                        )
                    profile_block_lines = [
                        f"- 姓名：{sd.get('real_name') or '未填'}",
                        f"- 性别/年龄：{'男' if (sd.get('gender') or '').upper() == 'M' else '女' if (sd.get('gender') or '').upper() == 'F' else '未填'} / {age_str or '未填生日'}",
                        f"- 学校：{sd.get('school') or '未填'}",
                        f"- 城市/年级：{sd.get('city') or '未填'} / {sd.get('grade') or '未填'}",
                    ]
                    if gesp_lines:
                        profile_block_lines.append("- GESP 真考历史：")
                        profile_block_lines.extend(gesp_lines)
                    if award_lines:
                        profile_block_lines.append("- CSP/NOIP/NOI 获奖历史：")
                        profile_block_lines.extend(award_lines)
                    elif not gesp_lines:
                        profile_block_lines.append("- 暂无 GESP/CSP/NOIP/NOI 比赛记录")
                    profile_block = "\n".join(profile_block_lines)

                    # 当地政策匹配
                    try:
                        match = match_school_for_student(sd)
                        match_lines = [
                            f"- 学段：{match.get('stage_label') or '未识别'}",
                            f"- 省份/城市：{match.get('province') or '未识别'} / {match.get('city') or '未填'}",
                            f"- 升学路径：{match.get('match_type_label') or '暂无匹配'}",
                        ]
                        ms = match.get("matches") or []
                        if ms:
                            match_lines.append("- 可冲刺目标学校（前 3）：")
                            for m in ms[:3]:
                                psum = (m.get("policy_summary") or "").strip()
                                if len(psum) > 60:
                                    psum = psum[:60] + "…"
                                req = m.get("requires_competition") or "无明确门槛"
                                match_lines.append(f"  · {m.get('school_name')}（需 {req}）")
                        policy_block = "\n".join(match_lines)
                    except Exception:
                        pass
            finally:
                conn.close()
        except Exception as _prof_e:
            profile_block = f"（档案拉取失败：{_prof_e}）"

    # v3.9.74 · VJudge 跨平台数据块(取代 AtCoder)→ 喂给 AI 的 prompt 片段
    vjudge_data = export_data.get("vjudge_data") or {}
    if vjudge_data.get("linked"):
        vjudge_block = (
            f"- VJudge username: {vjudge_data.get('username','')}\n"
            f"- 昵称: {vjudge_data.get('nick','') or '(未设置)'}\n"
            f"- 已解决题数: {vjudge_data.get('solved_count', 0)}\n"
            f"- 总提交: {vjudge_data.get('total_submissions', 0)} | "
            f"AC {vjudge_data.get('total_ac', 0)} | WA {vjudge_data.get('total_wa', 0)} | "
            f"AC 率: {float(vjudge_data.get('ac_rate', 0))*100:.1f}%\n"
            f"- 各 OJ 分布: {vjudge_data.get('oj_distribution', '无')}\n"
            f"- 最近 5 个已解决题: {vjudge_data.get('recent_solved', '无')}\n"
            f"（说明: VJudge 跨平台汇总数据,只反映公开的 recent 提交,"
            f"用于评估选手在多 OJ 上的综合活跃度,而非权威成绩。)"
        )
    else:
        vjudge_block = (
            "（学员未绑定 VJudge,无跨平台数据。建议在报告中提示学员去"
            "/me 页面绑定,以便后续报告能提供多 OJ 视角。AtCoder 已弃用。）"
        )

    prompt = f"""
你是一位顶级的算法竞赛金牌教练。我导出了一位选手的近期洛谷做题记录（包括已通过和尝试但未通过的题目代码）。
请你根据我提供的【能力评估参考框架】以及【官方考纲】，对他进行深度的诊断，并针对他【未做完/做错的题目】给出极具启发性的题解。

**报告生成时间**：{current_time}

{DIAGNOSTIC_FRAMEWORK}

{difficulty_guide}

{syllabus_context}

### 选手学籍档案（来自 self_register 表单 · v3.8 增强）
{profile_block or "（无档案数据，可能未注册或仅游客模式）"}

### 当地升学政策 + 目标学校政策（v3.8 增强）
{policy_block or "（无政策匹配数据）"}

### 选手的跨平台做题画像（v3.9.74 · VJudge 取代 AtCoder,只读公开数据）
{vjudge_block}

### 选手的全局数据统计
- 本次导出中已通过题数: {solved_count}
- 本次导出中未通过/卡住题数: {failed_count}
- 卡题数（定义：同一道题提交>=3次且最终未AC）: {len((behavior_data or {}).get('stuck_problems', [])) if isinstance(behavior_data, dict) else 0}
- 难度分布直方图: {json.dumps(summary.get('difficulty_histogram'))}
- 偏好的算法标签: {json.dumps(summary.get('top_algorithm_tags') or summary.get('top_tags'))}

### 六维能力评分
{six_dim_text if six_dim_text else '未计算'}

### 提交行为深度分析
{behavior_summary}

### 大纲知识点对标
{syllabus_summary}

{code_analysis_summary}

### 选手最近通过的代码样本（用于评估代码习惯）
{''.join(passed_samples) if passed_samples else '暂无代码'}

### 选手未做完/尝试失败的题目（重点出题解部分）
{''.join(failed_samples) if failed_samples else '暂无未通过的题目'}

### 提交代码考古（v3.9.39 · 多版源码 diff · 重点分析）
{evolution_prompt}

请你输出一份结构化的 Markdown 辅导报告，必须包含以下部分。在生成 Markdown 时，请务必使用以下视觉元素增强表现力：
 - 评分请使用黄色星级，如 ⭐⭐⭐⭐☆ (使用 ⭐ 和 ☆)
 - 难度名称必须使用洛谷官方口径，如“入门 / 普及- / 普及+/提高 / 提高+/省选- / 省选/NOI-”，严禁写“难度1/难度2”
 - 不要生成黑白字符图表或黑白直方图；如果需要表达占比或难度，请优先使用 HTML 彩色徽章、彩色表格，或直接引用上方图表结论
 - 等级前缀符号请使用 🟢精通 | 🟡熟练 | 🟠入门 | 🔵初窥 | 🔴空白
 - 各处点评或结论段落，请使用 `<p class="text-blue-700 font-semibold">解读：...</p>` 样式包装。
 - 整个报告尽可能以 Markdown 表格、区块等图表化、直观的形式呈现，少用长篇大论的文字。

 1. **【选手概览与性格画像】**：
    基于提交行为数据，提炼选手的性格画像。**必须**用 Markdown 表格输出，表格列固定为：`| 性格维度 | 星级评分 | 拟人化评价 | 数据证据 |`。
    **必须包含 6 行**（顺序固定，不允许合并或省略任意一行）：
    1) 坚韧度  2) 完美主义  3) 冒险精神  4) 自律性  5) 调试耐心  6) 作息规律
    严禁把多行合并成一格（例如把"自律性"和"作息规律"合并为"自律性与规律性"），也严禁用列表/段落代替表格。
    星级使用 ⭐⭐⭐⭐⭐/⭐⭐⭐⭐☆/⭐⭐⭐☆☆/⭐⭐☆☆☆/⭐☆☆☆☆☆ 五档（与雷达图六个维度的口径一一对应）。
    每行数据证据栏必须引用具体数字（如提交时段、卡题次数、AC率、重交间隔等），不要写"数据不足"。

 2. **【提交行为深度分析】**：
    基于提供的提交行为数据，以表格和重点解读的形式，深入分析用户的提交习惯。必须包含以下子模块：
    - **死磕题目 TOP (提交次数最多)**：列出提交次数最多的几道题，分析原因。
     - **首次 AC 情况**：分析首次通过和多次尝试后通过的比例。
    - **其他显著行为特征**：如单日高强度刷题记录、长耗时题目等。
    (注意：此部分请用表格展示数据，并在表下附上 `<p class="text-blue-700 font-semibold">特征：...</p>`)

 3. **【难度分布与水平研判】**：
    分析选手的难度分布特征，判断其处于哪个阶段（入门/普及/提高/省选）。必须使用洛谷官方难度名称：暂无评定、入门、普及-、普及/提高-、普及+/提高、提高+/省选-、省选/NOI-、NOI/NOI+/CTSC。严禁输出“难度1/难度2/难度3”。

 4. **【六维能力雷达表与诊断】（评分 × 等级必须一一对应 · v3.9.63 防"假高分"硬约束）**：
      输出 Markdown 表格，评估选手在六大维度的状态：`| 能力块 | 评分 | 当前等级 | 数据证据 | 已经具备 |`
      六大维度：基础算法、数据结构、图论、动态规划、字符串、数学。

      ★★★★★ **【硬约束 1：评分 = 等级对应表，严禁"低等级给高分"】** ★★★★★
      ```
        🟢 精通   →  85 ≤ 评分 ≤ 100
        🟡 熟练   →  70 ≤ 评分 ≤ 84
        🟠 入门   →  50 ≤ 评分 ≤ 69    （绝不能给 70+，图例会立刻判错）
        🔵 初窥   →  30 ≤ 评分 ≤ 49
        🔴 空白   →   0 ≤ 评分 <  30
      ```
      抽出的"当前等级"列必须从该维度"做过题的最高难度"推出，与"评分"列必须落在同一档。
      例：图论维度只 AC 过 d≤3（入门/普及-/普及/提高-）的题 → 等级必须写 🟠入门，评分必须 ≤ 69，
        绝不能因为"做得多"就给 91 分（这叫"假高分"，海报/榜单会立刻暴露）。

      ★★★★★ **【硬约束 2：难度加权打分（防刷简单题刷出高分）】** ★★★★★
      同等数量下难度越深分越高；低难度题做再多也不能突破等级上限：
      ```
        d=1（入门）         1 题 = 0.5 分（仅算"接触"，无等级资格）
        d=2-3（普及- / 普及/提高-） 1 题 = 1-2 分
        d=4-5（普及+/提高 / 提高+/省选-）1 题 = 3-5 分
        d=6+（省选/NOI- / NOI/NOI+/CTSC）1 题 = 6-10 分
      ```
      反例：某个选手"模拟 38 / 贪心 22 / 排序 20" 80 题全是 d≤2 → 基础算法 ≤ 50 分（入门档上限），
        不能再按"题多就给 80+ 分"。若 d≥3 的题占比 < 20% → 整维度硬性封顶 60。

      ★★★★★ **【硬约束 3：等级判定的"硬证据"是最高难度，不是题数】** ★★★★★
      ```
        🟢 精通 = 核心 tag 在 d≥5 上有 AC（必须真的写过 NOI 级别题）
        🟡 熟练 = 核心 tag 在 d≥3 上有 AC（普及+/提高 上有真本事）
        🟠 入门 = 核心 tag 在 d≤3 上有 AC（仅接触，没到提高）
        🔵 初窥 = 核心 tag 仅在 d≤2 上 AC
        🔴 空白 = 核心 tag 无 AC
      ```

      诊断段落必须先自检"是否有假高分"，有就要主动指出（例："此六维雷达图存在'假高分'现象，
      X 维度 91 分实质应为 50-60 分（入门档），掩盖了在 d≥4 上的无力"）。

  5. **【考纲精准定级与知识点盲区】**（根据提供的 NOI大纲 2025版）：
     - **当前对应等级水平**：明确指出该选手目前处于 CSP-J / CSP-S / 省选 / NOI 哪个阶段。
     - **知识点强弱项**：严格对照考纲中的知识点名词，列出其掌握得最好的 3 个考点，以及最薄弱的 3 个考点（使用 🟢🟡🔴 标注）。
     - **训练盲区**：指出他在当前等级中"完全没有涉及/刷题数据中缺失"的必考知识点。
     - **知识点覆盖与树状图**：不要再写知识点覆盖统计表或知识树（这些由程序自动生成，放在"数据校准与真实统计"小节）。你只需要在本节用 1-2 段话点评"哪些大分支（4 大等级）覆盖得好、哪些几乎为零，并给 1-2 条具体训练建议"即可。
     - **题目级别经历表**：单独说明做过多少道 CSP-S / 省选 / NOI 级别题，按来源标签与难度双证据解释，不要与知识点覆盖混为一谈。

  6. **【风险诊断与训练闭环表】**：
     输出 Markdown 表格：`| 优先级 | 风险项 | 触发场景 | 比赛症状 | 根因判断 | 训练专题 | 验收标准 |`
     - 行数至少 5 行，优先级使用 `S/A/B`。
     - 这个表必须是高度可执行的训练方案。

  7. **【代码质量与工程习惯深度分析】**：基于《源码静态风格分析》及代码样本，提供一份来自资深架构师视角的 Review。分析代码长度、宏定义习惯（如 `#define int long long`）、IO 优化、命名、STL 容器使用情况等。指出 2 个优点和 3 个必须改掉的坏习惯。

  7.5 **【提交代码考古：思维漏洞与逐版改进（重点分析）】**（v3.9.39 新增 · **必须包含 4 个 H3 子章节**）：
     **这是本次报告的核心章节**，基于系统自动抓取的 TOP 5 高频多次提交题目的多版源码 diff 时间线。要求：
     - **必须 1 个 markdown 表格 + 4 个 H3 子章节**，输出顺序固定为：
       a) **【7.5.1 逐次提交改进点（diff 时间线）】**：用表格列出每道题每版的状态变迁 + 代码字节数 + 关键 diff；每版在表格下方用 1-2 句话点出"他这一版实际改了什么、效果如何"（如："v2 把边界 n=1 加上特判，v1 漏掉"）。
       b) **【7.5.2 思维漏洞分类（按错误模式）】**：把上述题目中的失败版本归类成 5-8 个**反复出现的**思维漏洞，每个漏洞用 emoji（🔁）+ 名称（如"🔁 边界 n=1 漏判"） + 该选手出现次数 + 一段话解释根因。
       c) **【7.5.3 未被发现的根因（深挖卡题）】**：从多次未AC 或 N 次WA/TLE 仍未通过的题里，挑 2-3 道深挖："他一直在改 X，但真正的根因是 Y"。明确指出"他 N 次重交仍未发现真因"。
       d) **【7.5.4 学习建议（书 / 题单 / 训练）】**：针对每个思维漏洞给 1-2 本书 / 题单（带洛谷题号）/ 训练方法（具体到周计划）。
     - **严禁**只输出表格就完事；**严禁**把 4 个子章节合并为 1 段。
     - 每张表前必须用 `<p class="text-blue-700 font-semibold">观察：...</p>` 引导。
     - 如果数据里没有任何多次提交的题，输出"（该学员尚无多次提交的题目，建议继续训练 1-2 个月后再生成此报告）"并结束本章节，**不要**编造题目。

  8. **【定制训练题单（6个月路线图）】**：
     根据上述大纲盲区和薄弱项，定制一份分阶段的训练计划：
     - 第一阶段（Month 1-2）：巩固基础，补齐短板
     - 第二阶段（Month 3-4）：数据结构/算法突破
     - 第三阶段（Month 5-6）：提速与稳定
     每个阶段包含具体知识点 + 推荐题目（带洛谷题号）。

  9. **【核心建议（优先级排序）】**：
     列出 5-8 条核心建议，按优先级排序（🔴紧急 / 🟡重要 / 🟢建议）。例如：`🔴 紧急: 补加 ios::sync_with_stdio(false) 防止大数据 TLE`。

  10. **【未通过题目专属题解（从暴力到正解）】**：针对上面列出的"未做完/尝试失败的题目"，逐一出题解。
    - 绝不能直接给出最优解！
    - 必须严格遵循**"从暴力到正解的思考过程"**：
      a) **AI 题解摘要**：一句话点出这道题的核心思路或坑点。
      b) 暴力思路怎么想？（复杂度是多少，能拿多少部分分？）
      c) 瓶颈在哪里？（时间卡在哪，空间卡在哪？）
      d) 关键性质/不变量观察（Key Observation）。
      e) 最终正解的推导与核心代码结构。
      f) **推荐同类题**：推荐 1-2 道涉及相同考点或技巧的洛谷题目（标明题号和简要推荐理由）。
 """

    # 续写模式：在 prompt 末尾追加"已有开头，直接续写"指令
    if resume_prefix:
        trimmed_prefix = _trim_to_safe_boundary(resume_prefix)
        if trimmed_prefix:
            prompt = prompt + f"""

---

### 续写模式（重要）
以下是**已经生成的开头**（可能因网络中断/超时而中止），请你**直接从该前缀的下一个字符开始续写剩余部分**：
- **不要重复输出已有内容**（前缀已包含的内容一律不要再写一遍）
- **不要写"以下是..."、"好的"、"我继续"等开场白或导语**
- 保持与已有内容**完全一致**的 Markdown 风格、章节顺序、视觉元素（星级、徽章等）
- 如果你认为已有内容已经基本完整，请**直接输出 `===REPORT_COMPLETE===`** 单独一行作为收尾

[已生成内容开始]
{trimmed_prefix}
[已生成内容结束]
"""

    system_prompt = (
        "你是顶级算法竞赛教练，极其擅长引导学生通过“暴力-观察-优化”的过程推导正解，"
        "且熟悉各种算法训练框架。"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    if output_path:
        # 流式生成：把 token 实时写盘，断连时 partial 会留在文件里
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        initial_content = _trim_to_safe_boundary(resume_prefix) if resume_prefix else ""
        collected_chunks: list[str] = []
        collected_reasoning_chunks: list[str] = []  # v3.9.13 · DeepSeek-R1 推理链
        with open(output_path, "w", encoding="utf-8") as f:
            if initial_content:
                f.write(initial_content)
                f.flush()
            try:
                stream = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    stream=True,
                    timeout=1800.0,
                )
                for chunk in stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    # v3.9.13 · 兼容 DeepSeek-R1 推理模型：delta 同时含 reasoning_content（思考链）
                    # 和 content（最终答案）。普通模型只有 content（reasoning_content 始终为 None）。
                    # 我们把 reasoning 也单独存一份，作为 content 为空时的兜底。
                    reasoning_piece = getattr(delta, "reasoning_content", None) or ""
                    if reasoning_piece:
                        collected_reasoning_chunks.append(reasoning_piece)
                    content_piece = getattr(delta, "content", None) or ""
                    if content_piece:
                        collected_chunks.append(content_piece)
                        f.write(content_piece)
                        f.flush()
            except Exception:
                # 不吞异常：让上层 retry 捕获，但 partial 已经在文件里
                raise
        # v3.9.13 · 优先用 content（最终答案）；如 R1 推理模型 max_tokens 不够时 content 为空，
        # fallback 到 reasoning_content（思考链也有参考价值）
        full_content = initial_content + "".join(collected_chunks)
        full_reasoning = "".join(collected_reasoning_chunks)
        if not full_content.strip() and full_reasoning.strip():
            print(
                f"[WARN] 流式响应只含 reasoning_content（{len(full_reasoning)} 字符）"
                f"· content 为空 · 推测 max_tokens 太小被 R1 思考链耗尽 · fallback to reasoning",
                flush=True,
            )
            full_content = full_reasoning
        # 流式成功后做一次归一化（替换 AI 编的 ASCII 表/难度名/日期等），再覆盖回文件
        normalized = normalize_report_markdown(full_content, export_data)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(normalized)
        return normalized

    # 非流式：保持旧行为，方便 CLI 单独跑测
    response = client.chat.completions.create(
        model=model_name, # 使用用户指定的模型
        messages=messages,
        timeout=1800.0,
    )
    content = response.choices[0].message.content or ""
    return normalize_report_markdown(content, export_data)


# ============================================================
# v3.10.0.4 · VJudge 主轴 AI 报告生成(全 vjudge 模式)
#   - 不依赖洛谷 practice / passed_items / failed_items / behavior_analysis
#   - 仅用 vjudge_data + 学员基础信息 + solved 列表
#   - prompt 模板专为跨平台 OJ 画像设计
#   - 输出 MD (流式,可断连续写)
# ============================================================

# v3.10.0.4 · VJudge 报告 prompt 框架
VJUDGE_DIAGNOSTIC_FRAMEWORK = """
【VJudge 跨平台能力评估框架】

VJudge (https://vjudge.net) 是一个"虚拟判题平台",会聚拢 100+ OJ
(Codeforces、AtCoder、洛谷、POJ、HDU、SPOJ、UVa …) 的提交记录,
对一名算法竞赛选手的"真实"竞技画像,比单一 OJ 更有代表性。

请基于学员的 VJudge 公开数据,做以下维度的评估：

1. **跨平台活跃度**:
   - 总 AC 数 vs 总提交数 → AC 率(判断"尝试后能否独立做对"的核心信号)
   - 注册时长 vs 总提交 → 反映"刷题密度"(高密度 = 备赛期;低密度 = 兴趣型)

2. **OJ 分布画像**:
   - 如果已解决题集中在 Codeforces/AtCoder:偏"国际赛路径",英语题干理解 OK
   - 如果集中在洛谷/POJ/HDU:偏"国内路径",更熟悉中文题干
   - 单一 OJ 占 >80% = 单一生态;≥3 个 OJ = 跨平台型,适应力强

3. **难度与稳定性**:
   - 提交/AC 比 > 3.0 = 死磕型(可能缺方法论,建议学套路)
   - 提交/AC 比 1.0-2.0 = 高效型(读题准,一两次就能 AC)
   - 提交/AC 比 < 1.5 且 AC 数 < 10 = 新手期,需引导正确起步方向

4. **成长性判断**:
   - 7d/30d/all AC 数(若可获取) → 是否有近期的爬升
   - 已解决题列表的 OJ 来源多样性 → 视野宽度

【输出要求】
请使用 Markdown 表格 / HTML 徽章 / 颜色,保持报告的可视化风格。
"""


def _build_vjudge_report_messages(
    export_data: dict,
    resume_prefix: str | None = None,
) -> list[dict]:
    """v3.10.0.4 · 构造 VJudge 报告的 messages(给 OpenAI Chat API)。

    不读洛谷 practice / behavior / syllabus,只读:
      - export_data['student_info']   {real_name, grade, city, school, ...}
      - export_data['vjudge_data']    {username, nick, total_submissions, total_ac,
                                       ac_rate, solved_count, oj_distribution,
                                       recent_solved, ...}
    """
    from datetime import datetime as _dt

    si = export_data.get("student_info") or {}
    vj = export_data.get("vjudge_data") or {}

    # 学员基础信息
    profile_lines = [
        f"- 姓名：{si.get('real_name') or '未填'}",
        f"- 短 ID：{si.get('short_id') or '未生成'}",
        f"- 学校：{si.get('school') or '未填'}",
        f"- 城市/年级：{si.get('city') or '未填'} / {si.get('grade') or '未填'}",
        f"- GESP 已通过最高级：{si.get('gesp_highest_passed') or '未参加'}",
    ]
    profile_block = "\n".join(profile_lines)

    # VJudge 数据块(取代洛谷的"全局统计"段)
    # v3.10.0.5 · recent_solved 已是 markdown 表格字符串(由 web_app 端拼接),
    # oj_distribution 也已带真实分布,不再回退到"未公开"占位。
    vjudge_block = (
        f"- VJudge username: {vj.get('username','')}\n"
        f"- 昵称: {vj.get('nick','') or '(未设置)'}\n"
        f"- 注册时间: {vj.get('register_time','') or '未知(新版本 VJudge 不再直接暴露注册日期)'}\n"
        f"- 总 AC 数: {vj.get('total_ac', 0)}\n"
        f"- 总提交数: {vj.get('total_submissions', 0)}\n"
        f"- 总尝试 OJ 数: {vj.get('oj_count', 0)}\n"
        f"- AC 率: {float(vj.get('ac_rate', 0))*100:.1f}%\n"
        f"- 各 OJ 解决数分布: {vj.get('oj_distribution') or '（暂无 OJ 维度数据）'}\n"
        f"- 最近已解决题(最多 20 条,直接来自 VJudge 已抓取列表):\n{vj.get('recent_solved') or '（暂未抓到已解决题列表,请检查 VJudge 抓取是否完成）'}"
    )

    # 学员类型判定(让 AI 知道这是"低数据"还是"丰富数据")
    ac_n = int(vj.get("total_ac", 0) or 0)
    if ac_n == 0:
        data_tier = "**🆕 全新学员(VJudge 0 AC)** · 报告侧重『起步方向建议』和『刷题策略入门』"
    elif ac_n < 10:
        data_tier = f"**🌱 入门期学员(VJudge {ac_n} AC)** · 报告侧重『基础巩固』+『易错题套路』"
    elif ac_n < 50:
        data_tier = f"**🌿 进阶期学员(VJudge {ac_n} AC)** · 报告侧重『专题突破』+『难度跃迁』建议"
    else:
        data_tier = f"**🌳 资深学员(VJudge {ac_n} AC)** · 报告侧重『冲刺瓶颈』+『高质量训练』建议"

    current_time = _dt.now().strftime("%Y-%m-%d %H:%M:%S")

    system_prompt = (
        "你是一位顶级的算法竞赛金牌教练,熟悉国内(NOI/CSP/GESP)与国际"
        "(ICPC/Codeforces/AtCoder)多 OJ 体系。你的报告风格:数据驱动、表格化、"
        "可直接打印给家长与学员本人。"
    )

    user_prompt = f"""
请基于以下**VJudge 跨平台公开数据**,为这位学员生成一份**完整的 VJudge 跨平台 AI 测评报告**。

**报告生成时间**：{current_time}

{VJUDGE_DIAGNOSTIC_FRAMEWORK}

{data_tier}

### 学员基础档案
{profile_block}

### 学员 VJudge 跨平台数据(全量)
{vjudge_block}

### 输出结构要求(必须按顺序输出,不允许缺漏)

1. **【学员概览】**
   - 用 Markdown 表格汇总:姓名、年级、VJudge username、总 AC、总提交、AC 率、活跃 OJ 数

2. **【VJudge 跨平台画像】**
   - 用 Markdown 表格展示各 OJ 解决数(用 HTML 徽章,OJ 名做超链接到 vjudge.net/user/{vj.get('username','')})
   - 解读:这个分布反映了什么训练路径偏好?

3. **【提交效率分析】**
   - 提交/AC 比 = total_submissions / total_ac(若 total_ac=0,标 N/A)
   - 解读:高效型 / 死磕型 / 新手期?
   - 给出 1-2 条针对性建议

4. **【已解决题列表(精选 10-20 条)】**
   - 用 Markdown 表格展示(列:OJ | 题号 | 标题 | AC 时间)
   - 直接复用上方"学员 VJudge 跨平台数据"段给出的"最近已解决题"表(已是 markdown 表格)
   - **重要:绝对不要写"未公开 / 暂未获取 / 待补充"**,数据已在 prompt 里完整给出
   - 解读:这些题透露了学员的"兴趣方向"和"难度上限"
     (按 OJ/题号/标题做类型/难度推测;若不熟悉某道题,只基于"已 AC 事实"做中性结论,
      例如"已完成 N 道题,说明该学员已稳定进入 X 难度区间",不要瞎编具体知识点)

5. **【水平研判】**
   - 根据 AC 数 + OJ 分布 + 题难度,给出"当前阶段"判断(入门/普及/提高/省选)
   - 给出 1 条最值得投入的方向建议

6. **【后续 4 周训练计划(可执行版)】**
   - 表格列:周次 | 主题 | 目标 OJ | 题目数量 | 推荐题型 | 验收标准
   - 4 行(W1-W4)
   - 必须有"验收标准"(可量化的:AC 率、通过题数、难度上限)

7. **【家长可见的总结】**
   - 一段 200 字内的总结,直白易懂,无术语
   - 末尾:"📌 家长下一步":可执行的家庭行动(2-3 条)

### 视觉规范
 - 评分/进度用 🟢🟡🟠🔴🔵 色块
 - 难度名称用洛谷官方口径:入门 / 普及- / 普及+/提高 / 提高+/省选- / 省选/NOI-
 - 不要用长段落,所有结论用表格 + 短解读
 - 解读段落用 `<p class="text-blue-700 font-semibold">解读：...</p>` 包装
 - 报告全程中文
"""

    messages = [
        {"role": "system", "content": system_prompt},
    ]
    if resume_prefix:
        # 续写模式:把已生成的开头作为 assistant 已写部分
        messages.append({"role": "assistant", "content": resume_prefix})
        messages.append({
            "role": "user",
            "content": "继续。请从上一段结尾直接续写,不要重复,不要重新生成标题。"
        })
    else:
        messages.append({"role": "user", "content": user_prompt})

    return messages


def generate_vjudge_report(
    export_data: dict,
    api_key: str,
    base_url: str | None,
    model_name: str,
    *,
    output_path: str | None = None,
    resume_prefix: str | None = None,
) -> str:
    """v3.10.0.4 · 生成 VJudge 跨平台 AI 报告(全 vjudge 模式)。

    与 generate_ai_report 的区别:
      - 不依赖洛谷 practice / passed_items / failed_items / behavior_analysis / syllabus
      - prompt 框架专为 VJudge 公开数据设计
      - 流式写入 output_path(可断连续写)
      - 输入仅需 export_data['student_info'] + export_data['vjudge_data']
    """
    from openai import OpenAI

    if not str(api_key or "").strip():
        raise ValueError("未配置 OpenAI API Key")

    client_kwargs = {
        "api_key": api_key,
        "timeout": 1800.0,
    }
    if base_url:
        client_kwargs["base_url"] = base_url
    client = OpenAI(**client_kwargs)

    messages = _build_vjudge_report_messages(export_data, resume_prefix=resume_prefix)

    # 流式
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        full_content_parts: list[str] = []
        try:
            stream = client.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=True,
                timeout=1800.0,
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    piece = chunk.choices[0].delta.content
                    full_content_parts.append(piece)
                    with open(output_path, "a", encoding="utf-8") as f:
                        f.write(piece)
        except Exception as e:
            # partial 留在文件里,方便 resume
            print(f"[v3.10.0.4] vjudge report stream interrupted: {e}", file=sys.stderr)
        full_content = "".join(full_content_parts)
        return full_content

    # 非流式
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        timeout=1800.0,
    )
    return response.choices[0].message.content or ""


def generate_parent_subscribe(
    report_md: str,
    export_data: dict,
    api_key: str,
    base_url: str | None,
    model_name: str,
    luogu_uid: str = "",
) -> str:
    """v3.5.2 · 家长订阅版（真 AI 二次生成，非视图层）

    以同一份学员的洛谷 AI 报告（report.md）为上下文，让 AI 重新写一份
    "家长视角"的深度分析报告：
      1. 学习进度评估（家长能听懂的语言）
      2. 学习规划建议（短/中/长期）
      3. OI 决策支持（升学科普、强基窗口、风险提示）
      4. 家校沟通清单（教练沟通的具体问题）
      5. 重点观察项（家长接下来 1 个月的关注点）

    5 个维度跟家长订阅版 UI 卡片一一对应，但内容是 AI 真正生成的，
    而不是模板里硬编码的占位文本。

    v3.8 · 增强：注入学员档案（GESP/CSP/NOIP/NOI 奖项 + 当地政策匹配 +
    目标学校政策），让家长版 AI 真正"懂孩子"，避免空话。
    """
    from openai import OpenAI
    import datetime
    import json as _json
    import sqlite3 as _sqlite3

    if not str(api_key or "").strip():
        raise ValueError("未配置 OpenAI API Key")

    # 截取最近 N 字符的 report.md 作为上下文（避免超长 prompt）
    # 4 级标题、表格、清单都有助于 AI 抓住要点
    context_md = report_md or ""
    if len(context_md) > 24_000:
        # 优先保留前 8K（开头结论）+ 关键章节（搜索特定 H2）+ 后 8K
        head = context_md[:8_000]
        tail = context_md[-8_000:]
        # 抽出所有 H2 段落
        import re as _re
        h2_blocks = _re.findall(
            r"(?ms)^## .+?(?=^## |\Z)", context_md[8_000:-8_000]
        )
        middle = "\n\n".join(h2_blocks[:6])  # 最多 6 段
        context_md = head + "\n\n...[中间省略]...\n\n" + middle + "\n\n" + tail

    # 选手基础信息（不带 PII）
    student = export_data.get("student_info", {}) or {}
    gesp = export_data.get("gesp_history", {}) or {}
    solved = export_data.get("solved_count", 0)
    failed = export_data.get("failed_count", 0)

    # v3.8 · 拉取学员完整档案 + 奖项 + GESP 成绩 + 当地政策匹配
    profile_block = ""
    policy_block = ""
    if luogu_uid:
        try:
            from task_store import _get_conn as _ts_get_conn, match_school_for_student
            conn = _ts_get_conn()
            try:
                # 学籍档案（含性别、生日、学校、城市、年级）v3.9 增强：加 province
                stu_row = conn.execute(
                    "SELECT id, real_name, gender, birth_date, school, city, grade, province "
                    "FROM students WHERE luogu_uid = ?",
                    (str(luogu_uid).strip(),),
                ).fetchone()
                if stu_row:
                    sd = dict(stu_row)
                    sid_int = int(sd.get("id") or 0)
                    # 年龄换算
                    age_str = ""
                    if sd.get("birth_date"):
                        try:
                            from datetime import date as _date
                            y, m, d = [int(x) for x in str(sd["birth_date"]).split("-")[:3]]
                            today = _date.today()
                            age = today.year - y - ((today.month, today.day) < (m, d))
                            age_str = f"{age}岁（出生 {sd['birth_date']}）"
                        except Exception:
                            age_str = str(sd.get("birth_date") or "")
                    # 同步取 GESP 真考历史
                    # v3.9.50 · 修 bug：之前用 `c.event_date` 但 competitions 表实际是 `exam_date`，
                    # 导致整个 try 块 raise 被外层 except 静默吞掉，profile_block 退化为
                    # "暂无 GESP/CSP/NOIP/NOI 比赛记录"，AI 报告永远显示"暂未参加 GESP/CSP"。
                    # 现在改用正确列名 + 失败时记 ERROR 日志，不静默吞错。
                    gesp_lines = []
                    try:
                        for g in conn.execute(
                            "SELECT g.registered_level, g.actual_score, g.passed, "
                            "       g.certificate_no, g.exam_id, c.name AS exam_name, c.exam_date, c.data_year "
                            "FROM gesp_exams g LEFT JOIN competitions c ON c.id = g.exam_id "
                            "WHERE g.student_id = ? ORDER BY COALESCE(c.exam_date, g.award_year || '-12-31') DESC",
                            (sid_int,),
                        ).fetchall():
                            gd = dict(g)
                            passed = "✅通过" if gd.get("passed") else "❌未通过"
                            score = f"{gd.get('actual_score')}分" if gd.get("actual_score") else "未记录分数"
                            gesp_lines.append(
                                f"  - GESP L{gd.get('registered_level')} · {gd.get('exam_name') or gd.get('data_year') or '?'} · {passed} · {score}"
                            )
                    except Exception as _ge:
                        import logging as _lg
                        _lg.getLogger("luogu_evaluator").error(
                            f"[v3.9.50 /generate_parent_subscribe] 查 GESP 失败 sid={sid_int}: {_ge}",
                            exc_info=True,
                        )
                    # 同步取 CSP/NOIP/NOI 奖项
                    # v3.9.50 · 同上：兜底 + 日志，避免单个 query 失败导致整个档案拉取断流
                    award_lines = []
                    try:
                        for a in conn.execute(
                            "SELECT competition_type, award_level, award_year, actual_score, province, certificate_no "
                            "FROM csp_awards WHERE student_id = ? ORDER BY award_year DESC",
                            (sid_int,),
                        ).fetchall():
                            ad = dict(a)
                            type_label = {
                                "csp_j_pre": "CSP-J 初赛", "csp_j_final": "CSP-J 复赛",
                                "csp_s_pre": "CSP-S 初赛", "csp_s_final": "CSP-S 复赛",
                                "noip_1": "NOIP 普及组", "noi_bronze": "NOI 铜牌",
                                "noi_silver": "NOI 银牌", "noi_gold": "NOI 金牌",
                            }.get(ad.get("competition_type") or "", ad.get("competition_type") or "?")
                            level_label = {
                                "excellent": "优秀", "first": "一等", "second": "二等",
                                "third": "三等", "bronze": "铜牌", "silver": "银牌", "gold": "金牌",
                            }.get(ad.get("award_level") or "", ad.get("award_level") or "?")
                            score = f" · {ad.get('actual_score')}分" if ad.get("actual_score") else ""
                            prov = f" · {ad.get('province')}" if ad.get("province") else ""
                            award_lines.append(
                                f"  - {ad.get('award_year')} {type_label} {level_label}{score}{prov}"
                            )
                    except Exception as _ce:
                        import logging as _lg
                        _lg.getLogger("luogu_evaluator").error(
                            f"[v3.9.50 /generate_parent_subscribe] 查 CSP/NOIP/NOI 失败 sid={sid_int}: {_ce}",
                            exc_info=True,
                        )
                    profile_block_lines = [
                        f"- 姓名：{sd.get('real_name') or '未填'}",
                        f"- 性别/年龄：{'男' if (sd.get('gender') or '').upper() == 'M' else '女' if (sd.get('gender') or '').upper() == 'F' else '未填'} / {age_str or '暂未填生日'}",
                        f"- 学校：{sd.get('school') or '暂未填学校'}",
                        f"- 城市/省份：{sd.get('city') or '暂未填城市'} / {sd.get('province') or '暂未填省份'}",
                        f"- 年级：{sd.get('grade') or '未填'}",
                        f"- 累计洛谷：通过 {solved} 题，未通过 {failed} 题",
                    ]
                    if gesp_lines:
                        profile_block_lines.append("- GESP 真考历史：")
                        profile_block_lines.extend(gesp_lines)
                    if award_lines:
                        profile_block_lines.append("- CSP/NOIP/NOI 获奖历史：")
                        profile_block_lines.extend(award_lines)
                    elif not gesp_lines:
                        profile_block_lines.append("- 暂无 GESP/CSP/NOIP/NOI 比赛记录（可能未参加或未录入）")
                    profile_block = "\n".join(profile_block_lines)

                    # 当地升学政策 + 目标学校政策匹配
                    try:
                        match = match_school_for_student(sd)
                        match_lines = [
                            f"- 学段：{match.get('stage_label') or '未识别'}（{match.get('stage') or '?'}）",
                            f"- 省份/城市：{match.get('province') or '未识别'} / {match.get('city') or '未填'}",
                            f"- 升学路径类型：{match.get('match_type_label') or '暂无匹配'}",
                        ]
                        ms = match.get("matches") or []
                        if ms:
                            match_lines.append(f"- 可冲刺的目标学校（按优先级，前 5 个）：")
                            for m in ms[:5]:
                                psum = (m.get("policy_summary") or "").strip()
                                # 截断长策略文本
                                if len(psum) > 80:
                                    psum = psum[:80] + "…"
                                req = m.get("requires_competition") or "无明确获奖门槛"
                                match_lines.append(
                                    f"  · {m.get('school_name')}（需要 {req}）· {psum or '详见政策原文'}"
                                )
                        else:
                            match_lines.append("- 暂无系统内置的匹配学校，建议家长到当地教育局/目标校官网查询当年招生简章")
                        policy_block = "\n".join(match_lines)
                    except Exception as _pe:
                        policy_block = f"（政策匹配失败：{_pe}）"
            finally:
                conn.close()
        except Exception as _prof_e:
            profile_block = f"（档案拉取失败：{_prof_e}）"
            policy_block = ""

    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    system_prompt = (
        "你是一位资深的 OI（信息学奥林匹克）家庭顾问，擅长把孩子的 OI 学习状况"
        "翻译成家长能理解的语言，给出**具体可执行**的学习规划与决策建议。\n"
        "你的读者是**家长**（可能没有编程背景），写作风格要：\n"
        "  - 避免堆砌术语，必要时用一句白话解释\n"
        "  - 给出**具体动作**（如『每周刷 10 道贪心』），不要『加强训练』这种空话\n"
        "  - 涉及未来时间点用『距您家孩子还有 N 年』\n"
        "  - 决策建议必须给 2-3 个分支，**不要假设一定要走 OI**\n"
        "**根据**下方【选手完整档案】和【当地升学政策】中的现有数据自然生成报告：\n"
        "  - 学校/城市/年级/年龄 → 影响升学窗口与目标校选择\n"
        "  - GESP/CSP/NOIP/NOI 历年奖项 → 影响『已具备什么能力 / 还要补什么』\n"
        "  - 当地升学政策 + 目标学校政策 → 章节 3 引用政策原文，给家长『具体哪所学校要什么奖』\n"
        "  - 已通过/未通过题数 → 评估学习曲线\n"
        "  - 字段未填（如未参加 GESP）→ 用『该学员暂未参加』表述，**不要**输出'数据缺失/拉取失败/校验失败'等任何警示性文字\n"
        "  - 当地政策未匹配到具体学校 → 推荐家长查看当地教育局/目标校官网当年招生简章\n"
        "**严禁**输出以下任何内容：\n"
        "  - ✗『档案数据校验』类提示\n"
        "  - ✗『数据拉取失败』类提示\n"
        "  - ✗『无法引用 X 信息』类警告\n"
        "  - ✗『报告仅供参考』类免责声明（章节 5 末尾统一加一行水印即可）\n"
        "  - ✗『AI 无法保证准确性』类自谦话术\n"
        "输出格式：Markdown，必须严格按以下 5 个 H2 章节输出，缺一不可：\n"
        "## 1. 学习进度评估（家长版）\n"
        "## 2. 学习规划建议（短/中/长期）\n"
        "## 3. OI 决策支持（升学/政策窗口）\n"
        "## 4. 家校沟通清单（建议问教练的 5-7 个问题）\n"
        "## 5. 重点观察项（接下来 1 个月家长关注什么）\n"
        "**严禁**输出这 5 个章节之外的任何 H1/H2 标题。\n"
        "在文末用一行 `> AI 估算 · 仅供参考 · 数据生成于 <时间>` 注明水印。"
    )

    user_prompt = (
        f"【选手基础信息（来自洛谷）】\n"
        f"- 城市/年级：{student.get('city', '未填')} / {student.get('grade', '未填')}\n"
        f"- 累计通过题目：{solved}，未通过：{failed}\n"
        f"- GESP 历史摘要：{gesp if gesp else '无'}\n"
        f"\n【选手完整档案（来自 self_register 表单 · 必须引用）】\n"
        f"```\n{profile_block or '（无档案数据，可能未注册或未填写 GESP/CSP 奖项）'}\n```\n"
        f"\n【当地升学政策 + 目标学校政策匹配（家长版核心数据）】\n"
        f"```\n{policy_block or '（无政策匹配数据）'}\n```\n"
        f"\n【同一份洛谷 AI 报告（节选，作为上下文）】\n"
        f"```markdown\n{context_md}\n```\n"
        f"\n【生成时间】{current_time}\n"
        f"\n请按 system 提示的 5 个章节生成 Markdown 报告，"
        f"在第 1/3 章**显式引用**【选手完整档案】和【当地升学政策】中的具体数据（如学校名、城市、奖项年份、目标校名）。"
    )

    client_kwargs = {"api_key": api_key, "timeout": 1800.0}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = OpenAI(**client_kwargs)

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.6,
        max_tokens=4000,
    )
    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise ValueError("AI 返回空内容")
    # 家长版**不**走 normalize_report_markdown（避免被注入数据校准/知识树）
    # 它的定位就是"AI 纯文本 + 家长友好语言"
    return content


def extract_problems_from_practice(practice_data, key: str):
    problems = []
    if isinstance(practice_data, dict):
        items = practice_data.get(key)
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict): continue
                pid = item.get("pid")
                if pid:
                    problems.append(
                        pyLuogu.ProblemSummary({
                            "pid": str(pid),
                            "title": item.get("title") or item.get("name") or "",
                            "difficulty": item.get("difficulty"),
                            "type": item.get("type"),
                            "tags": item.get("tags") or [],
                        })
                    )
    return problems

def main():
    parser = argparse.ArgumentParser(description="Luogu AI Evaluator - Coach Edition")
    parser.add_argument("--max-passed", type=int, default=10, help="Number of passed problems to fetch")
    parser.add_argument("--max-failed", type=int, default=5, help="Number of failed/unsolved problems to fetch")
    parser.add_argument("--report-md", default=DEFAULT_REPORT_MD, help="Markdown report output path")
    parser.add_argument("--report-pdf", default=DEFAULT_REPORT_PDF, help="PDF report output path")
    parser.add_argument("--assets-dir", default=DEFAULT_ASSETS_DIR, help="Directory for generated chart assets")
    args = parser.parse_args()
    
    console.print(Panel.fit("[bold cyan]Welcome to the Luogu AI Evaluator (Coach Edition)[/bold cyan]\n[dim]Incorporating Advanced Diagnostic Framework & Step-by-Step Editorials[/dim]"))
    
    # 收集学生信息
    console.print("\n[bold]为了生成更正式的报告，请填写测评基础信息（直接回车可跳过）：[/bold]")
    student_name = Prompt.ask("姓名", default="未知选手")
    school = Prompt.ask("学校", default="未知学校")
    grade = Prompt.ask("年级", default="未知年级")
    
    api_key, base_url, model_name = load_or_prompt_openai_config()
    cookies = load_or_prompt_cookies()
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        task = progress.add_task("[cyan]Connecting to Luogu API...", total=None)
        
        try:
            luogu = pyLuogu.luoguAPI(cookies=cookies)
            me = luogu.me()
            uid = int(me.uid)
            progress.update(task, description=f"[green]Connected as User ID: {uid}[/green]")
            
            tag_by_id, type_by_id = _build_tag_maps(luogu)
            practice = luogu.get_user_practice(uid)
            
            from behavior_analyzer import compute_six_dimension_scores
            from syllabus_matcher import evaluate_all_topics

            all_passed_problems, all_failed_problems = split_practice_problems(practice)
            progress.update(task, description="[cyan]Backfilling missing problem tags when needed...")
            enrich_problem_tags(luogu, all_passed_problems)
            all_passed_problems.sort(key=lambda p: (p.difficulty if p.difficulty is not None else 10, p.pid), reverse=True)
            passed_problems = all_passed_problems[:args.max_passed]
            all_failed_problems.sort(key=lambda p: (p.difficulty if p.difficulty is not None else 10, p.pid), reverse=True)
            failed_problems = all_failed_problems[:args.max_failed]
            
            progress.update(task, description=f"[cyan]Fetching submissions for {len(passed_problems)} passed and {len(failed_problems)} failed problems...")
            
            detail_fetch_state: dict[str, object] = {}
            passed_items = []
            for idx, problem in enumerate(passed_problems):
                try:
                    record = _pick_record_for_problem(
                        luogu=luogu,
                        uid=uid,
                        pid=problem.pid,
                        max_records_to_try=2,
                        require_source_code=idx < DETAIL_FETCH_SAMPLE_LIMIT_PASSED,
                        detail_fetch_state=detail_fetch_state,
                    )
                except Exception as e:
                    record = {"error": str(e)}
                passed_items.append({"problem": problem.to_json(), "record": record})
                
            failed_items = []
            for idx, problem in enumerate(failed_problems):
                try:
                    record = _pick_record_for_problem(
                        luogu=luogu,
                        uid=uid,
                        pid=problem.pid,
                        max_records_to_try=2,
                        require_source_code=idx < DETAIL_FETCH_SAMPLE_LIMIT_FAILED,
                        detail_fetch_state=detail_fetch_state,
                    )
                except Exception as e:
                    record = {"error": str(e)}
                failed_items.append({"problem": problem.to_json(), "record": record})

            progress.update(task, description="[cyan]Fetching recent submissions for behavior analysis...")
            behavior_analysis = fetch_behavior_analysis(luogu, uid, passed_items + failed_items)
            behavior_analysis = repair_behavior_analysis_from_items(
                {
                    "passed_items": passed_items,
                    "failed_items": failed_items,
                    "behavior_analysis": behavior_analysis,
                }
            )
            detail_fetch_stats = summarize_detail_fetch_stats(passed_items, failed_items, detail_fetch_state)

            summary = _summarize(all_passed_problems, tag_by_id=tag_by_id)
            # 构建 tag → 题目难度列表（用于估算每个知识点的平均难度）
            # 关键修复：prob.tags 是 List[int]（tag ID），而 top_tags 的 name 是中文名，
            # 之前用 str(tag) 作为 key 会得到 "1"/"353" 这种 ID 串，跟中文 name 匹配不上。
            # 必须用 tag_by_id 把 ID 转成中文名，否则 _match_topic 永远匹配失败。
            tag_difficulty_map: dict[str, list[int]] = {}
            for prob in all_passed_problems:
                d = getattr(prob, "difficulty", None)
                if d is None or d <= 0:
                    continue
                try:
                    di = int(d)
                except (TypeError, ValueError):
                    continue
                if di <= 0:
                    continue
                for tag in (getattr(prob, "tags", None) or []):
                    try:
                        tag_id = int(tag)
                    except (TypeError, ValueError):
                        continue
                    tag_name = str(tag_by_id.get(tag_id) or "").strip()
                    if not tag_name:
                        continue
                    tag_difficulty_map.setdefault(tag_name, []).append(di)
            syllabus_evaluation = evaluate_all_topics(
                summary.get("top_algorithm_tags", []) or summary.get("top_tags", []),
                tag_difficulty_map=tag_difficulty_map,
            )
            six_dim_scores = compute_six_dimension_scores(
                {"solved_count": len(all_passed_problems), "summary": summary},
                behavior_analysis if "error" not in behavior_analysis else {},
            )
            
            import datetime
            export_data = {
                "student_info": {
                    "name": student_name,
                    "school": school,
                    "grade": grade,
                    "eval_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                },
                "solved_count": len(all_passed_problems),
                "failed_count": len(all_failed_problems),
                "summary": summary,
                "passed_items": passed_items,
                "failed_items": failed_items,
                "detail_fetch_stats": detail_fetch_stats,
                "behavior_analysis": behavior_analysis,
                "syllabus_evaluation": syllabus_evaluation,
                "six_dimension_scores": six_dim_scores,
            }
            
            progress.update(task, description=f"[cyan]Analyzing with {model_name} (Applying diagnostic framework & generating editorials)...")
            report_md = generate_ai_report(export_data, api_key, base_url, model_name)
            progress.update(task, description="[green]Analysis complete!")
            
        except Exception as e:
            console.print(f"[red]Error during execution: {e}[/red]")
            return

    console.print("\n")
    console.print(Panel(Markdown(report_md), title="[bold magenta]AI Evaluation & Coaching Report[/bold magenta]"))

    with open(args.report_md, "w", encoding="utf-8") as f:
        f.write(report_md)

    chart_paths = generate_chart_images(export_data, args.assets_dir)
    build_html_and_pdf(report_md, export_data, DEFAULT_REPORT_HTML, args.report_pdf, chart_paths)

    console.print(f"\n[green]Markdown 报告已保存到 {os.path.abspath(args.report_md)}[/green]")
    console.print(f"[green]HTML 报告已保存到 {os.path.abspath(DEFAULT_REPORT_HTML)}[/green]")
    console.print(f"[green]PDF 报告已保存到 {os.path.abspath(args.report_pdf)}[/green]")
    if chart_paths:
        console.print(f"[green]图表资源已保存到 {os.path.abspath(args.assets_dir)}[/green]")

if __name__ == "__main__":
    main()
