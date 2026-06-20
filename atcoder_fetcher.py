"""
v3.9.73 · AtCoder 公开数据抓取 + 解析

模块定位:
  - parse_* : 纯函数,只吃 HTML 字符串,返回 raw dict(可在单测里喂假数据)
  - fetch_* : 真实网络抓取(M2 引入 httpx,带重试/限流/HTML 缓存)
  - 序列化层(persist_atcoder_data)在 task_store.py 里

AtCoder HTML 结构假设(基于长期观察的稳定结构):
  - 用户页: https://atcoder.jp/users/<handle>
      #main-container > .row > div.col-sm-12 table
      含 Rating / Highest Rating / Rated Matches / Last Competed / Affiliation
  - 比赛列表: https://atcoder.jp/users/<handle>/history
      表格: Date / Contest / Rank / Performance / Rating
  - AC 列表: https://atcoder.jp/users/<handle>?...&contestType=algo
      表格: Contest / Problem / Date / Language / Score (100)
  - 最近提交: https://atcoder.jp/contests/<id>/submissions?f.User=<handle>
"""

import re
import json
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


# ======================================================================
# 1. 段位色(对应 AtCoder 官方 rank 字符串)
# ======================================================================

# 段位 → (背景色, 前景色) 用于 UI chip 渲染
RANK_COLORS: dict[str, tuple[str, str]] = {
    "gray":   ("#808080", "#ffffff"),
    "brown":  ("#8B4513", "#ffffff"),
    "green":  ("#008000", "#ffffff"),
    "cyan":   ("#00CED1", "#ffffff"),
    "blue":   ("#0000FF", "#ffffff"),
    "yellow": ("#C0C000", "#000000"),
    "orange": ("#FF8C00", "#000000"),
    "red":    ("#FF0000", "#ffffff"),
}

# 段位 → 中文(给家长版报告)
RANK_ZH: dict[str, str] = {
    "gray":   "灰色",
    "brown":  "茶色",
    "green":  "绿色",
    "cyan":   "青色",
    "blue":   "蓝色",
    "yellow": "黄色",
    "orange": "橙色",
    "red":    "红色",
}


# ======================================================================
# 2. 验证 + 节流辅助
# ======================================================================

_HANDLE_RE = re.compile(r"^[a-zA-Z0-9_]{3,20}$")


def is_handle_valid(handle: str) -> bool:
    """v3.9.73 · AtCoder handle 格式校验。

    AtCoder 规则: 3-20 字符, 字母数字下划线, 不区分大小写(我们统一存原样)。
    """
    return bool(handle) and bool(_HANDLE_RE.match(handle))


# ======================================================================
# 3. HTML 解析(纯函数,无 IO)
# ======================================================================

def _extract_text(elem) -> str:
    """bs4 元素 → 干净文本(去首尾空白 + 合并多空格)。"""
    if elem is None:
        return ""
    return re.sub(r"\s+", " ", elem.get_text(" ", strip=True)).strip()


def _parse_datetime_atcoder(s: str) -> Optional[str]:
    """AtCoder 常见时间格式: '2024-01-15 21:30:00+0900' / ISO8601。

    统一返回 ISO8601(无时区),落库时给 report 用。
    """
    s = (s or "").strip()
    if not s:
        return None
    # 试 ISO
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=None).isoformat(timespec="seconds")
        except ValueError:
            continue
    return s  # 解析失败原样返回,UI 不崩


def _rating_to_rank(rating: int) -> str:
    """v3.9.73 · AtCoder 段位色(简化版)。

    实际规则: 0-399 gray, 400-799 brown, 800-1199 green, 1200-1599 cyan,
             1600-1999 blue, 2000-2399 yellow, 2400-2799 orange, 2800+ red
    """
    if rating <= 0:
        return "gray"
    if rating < 400:
        return "gray"
    if rating < 800:
        return "brown"
    if rating < 1200:
        return "green"
    if rating < 1600:
        return "cyan"
    if rating < 2000:
        return "blue"
    if rating < 2400:
        return "yellow"
    if rating < 2800:
        return "orange"
    return "red"


def parse_atcoder_user_page(html: str) -> dict:
    """v3.9.73 · 解析 https://atcoder.jp/users/<handle> 页面。

    返回 dict(空字段默认 0/''):
        rating, highest_rating, rank, contests_count,
        ac_problems_count, hard_ac_count, first_event_at, last_event_at
    抛 ParseError 表示页面结构不符预期。
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html or "", "html.parser")

    out = {
        "rating": 0,
        "highest_rating": 0,
        "rank": "gray",
        "contests_count": 0,
        "ac_problems_count": 0,
        "hard_ac_count": 0,
        "first_event_at": None,
        "last_event_at": None,
    }

    # 1. 用户主表(信息卡) - 通常第一个 .table / table.table-bordered / table.table-default
    # 实际: <table class="table table-bordered"><tr><th>Rating</th><td>1500</td></tr>...
    main_table = None
    for tbl in soup.find_all("table"):
        headers = [_extract_text(th).lower() for th in tbl.find_all("th")]
        if any("rating" in h for h in headers):
            main_table = tbl
            break
    if not main_table:
        # 没找到主表 = 可能是 404 页或空账号页
        if "404 Not Found" in html or "ページが見つかりません" in html:
            raise ParseError("AtCoder 用户页 404")
        # 空用户页(没参加过比赛)
        return out

    # 2. 遍历 th/td 提取 Rating
    for tr in main_table.find_all("tr"):
        th = _extract_text(tr.find("th"))
        td = _extract_text(tr.find("td"))
        if not th:
            continue
        th_low = th.lower()
        if th_low in ("rating", "現在の rating"):
            try:
                out["rating"] = int(re.sub(r"[^\d-]", "", td) or 0)
            except ValueError:
                pass
        elif "highest" in th_low and "rating" in th_low:
            try:
                out["highest_rating"] = int(re.sub(r"[^\d-]", "", td) or 0)
            except ValueError:
                pass
        elif "matches" in th_low or th_low in ("rated matches", "rated contests", "rated match"):
            try:
                out["contests_count"] = int(re.sub(r"[^\d]", "", td) or 0)
            except ValueError:
                pass
        elif "competed" in th_low or "last competed" in th_low:
            out["last_event_at"] = _parse_datetime_atcoder(td)
        elif "registered" in th_low or "first competed" in th_low:
            out["first_event_at"] = _parse_datetime_atcoder(td)

    # 3. 用 highest_rating 推段位(更准)
    out["rank"] = _rating_to_rank(max(out["rating"], out["highest_rating"]))

    return out


def parse_atcoder_ac_list_page(html: str) -> list[dict]:
    """v3.9.73 · 解析 AC 题目列表(单页)。

    AtCoder 用户页下方 AC 表格结构:
    <table>
      <tr><th>Contest</th><th>Problem</th><th>Date</th><th>Language</th><th>Score</th></tr>
      <tr><td><a href="/contests/abc300/tasks/abc300_a">AtCoder Beginner Contest 300</a></td>
          <td><a href="/contests/abc300/submissions/me/...">A - AtCoder Group Contest 2</a></td>
          <td>2024-01-15 21:30:00+0900</td><td>C++</td><td>100</td></tr>
    </table>

    返回: list of {contest_id, problem_id, title, language, solved_at}
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html or "", "html.parser")

    results: list[dict] = []
    for tbl in soup.find_all("table"):
        headers = [_extract_text(th).lower() for th in tbl.find_all("th")]
        if "contest" not in " ".join(headers):
            continue
        if "problem" not in " ".join(headers):
            continue
        if "score" not in " ".join(headers):
            continue
        # 找到对的那张表
        for tr in tbl.find_all("tr")[1:]:
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue
            contest_text = _extract_text(tds[0])
            # 提 contest_id 和 problem_id
            m = re.search(r"/contests/([a-z0-9_]+)/tasks/([a-z0-9_]+)", str(tds[1]))
            if not m:
                # 也试第二种: 提交链接
                m2 = re.search(r"/contests/([a-z0-9_]+)", contest_text + " " + str(tds[1]))
                if m2:
                    contest_id = m2.group(1)
                    problem_id = ""
                else:
                    continue
            else:
                contest_id, problem_id = m.group(1), m.group(2)
            title = contest_text  # 简化:把 contest 名当 title 占位
            # 找具体 problem 名(在 tds[1] 内,可能还有 .small/span)
            problem_text = _extract_text(tds[1])
            if problem_text and " - " in problem_text:
                # 格式: "A - AtCoder Group Contest 2" 提字母当 problem_id
                m3 = re.match(r"([A-Za-z])\s*-", problem_text)
                if m3 and not problem_id:
                    problem_id = f"{contest_id}_{m3.group(1).lower()}"
                title = problem_text.split(" - ", 1)[-1].strip()
            elif problem_text and not problem_id:
                title = problem_text
            # 日期/语言
            solved_at = _parse_datetime_atcoder(_extract_text(tds[2])) if len(tds) > 2 else None
            language = _extract_text(tds[3]) if len(tds) > 3 else ""
            results.append({
                "contest_id": contest_id,
                "problem_id": problem_id,
                "title": title,
                "language": language,
                "solved_at": solved_at,
            })
        break  # 只取第一张匹配的表
    return results


def parse_atcoder_submissions_page(html: str) -> list[dict]:
    """v3.9.73 · 解析比赛提交页(单页)。

    URL: https://atcoder.jp/contests/<id>/submissions?f.User=<handle>
    表格: Time / Task / User / Language / Score / Code / Status
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html or "", "html.parser")

    results: list[dict] = []
    for tbl in soup.find_all("table"):
        headers = [_extract_text(th).lower() for th in tbl.find_all("th")]
        if not (("time" in headers) and ("task" in headers) and ("status" in headers or "result" in headers)):
            continue
        for tr in tbl.find_all("tr")[1:]:
            tds = tr.find_all("td")
            if len(tds) < 4:
                continue
            submit_time = _parse_datetime_atcoder(_extract_text(tds[0]))
            # task 列: <a href="/contests/abc300/tasks/abc300_a">A - ...</a>
            task_a = tds[1].find("a")
            problem_id = ""
            contest_id = ""
            if task_a:
                m = re.search(r"/contests/([a-z0-9_]+)/tasks/([a-z0-9_]+)", str(task_a))
                if m:
                    contest_id, problem_id = m.group(1), m.group(2)
            # status
            result = _extract_text(tds[-1])  # 简化:取最后列
            # language
            language = _extract_text(tds[3]) if len(tds) > 3 else ""
            # source url: code 列在 headers 里有 "code",索引按表头顺序
            # Time(0) Task(1) User(2) Language(3) Score(4) Code(5) Status(6)
            source_url = ""
            try:
                code_idx = headers.index("code")
            except ValueError:
                code_idx = 5  # fallback
            if len(tds) > code_idx:
                code_a = tds[code_idx].find("a")
                if code_a:
                    href = code_a.get("href", "") or ""
                    if href and not href.startswith("http"):
                        href = "https://atcoder.jp" + href
                    source_url = href
            results.append({
                "contest_id": contest_id,
                "problem_id": problem_id,
                "result": result,
                "language": language,
                "submit_time": submit_time,
                "source_url": source_url,
            })
        break
    return results


def compute_ac_highlights(ac_problems: list[dict], limit: int = 8) -> list[dict]:
    """v3.9.73 · 从 AC 列表里挑高光(按难度倒序,无难度时按时间倒序)。

    实际 AtCoder 题目难度不是列表里直接给,这里只能用 contest_id 估算。
    简化规则:
      - abc_a/abc_b → 100
      - abc_c/abc_d → 400/600
      - abc_e/abc_f → 800/1000
      - arc/AGC 大题 → 1500+
    """
    def estimate_difficulty(p: dict) -> int:
        pid = (p.get("problem_id") or "").lower()
        if "_a" in pid or "_b" in pid:
            return 100
        if "_c" in pid:
            return 400
        if "_d" in pid:
            return 600
        if "_e" in pid:
            return 800
        if "_f" in pid or "_g" in pid:
            return 1000
        if pid.startswith("arc_") or pid.startswith("agc_"):
            return 1500
        return 200  # 默认

    enriched = []
    for p in ac_problems:
        e = dict(p)
        e["difficulty"] = estimate_difficulty(p)
        enriched.append(e)
    enriched.sort(key=lambda x: (x.get("difficulty", 0), x.get("solved_at", "")), reverse=True)
    return enriched[:limit]


# ======================================================================
# 4. 自定义异常
# ======================================================================

class ParseError(Exception):
    """v3.9.73 · AtCoder 页面结构变化或 404。"""
    pass


class FetchError(Exception):
    """v3.9.73 · 网络层错误(超时/5xx/限流/解析失败统一抛)。"""
    def __init__(self, msg: str, status: Optional[int] = None, retry_after: Optional[int] = None):
        super().__init__(msg)
        self.status = status
        self.retry_after = retry_after


# ======================================================================
# 5. 网络抓取(M2 实现)
# ======================================================================

# 全局 IP 限流(内存 dict,重启丢失可接受)
_IP_LAST_FETCH: dict[str, float] = {}
_IP_LOCK = __import__("threading").Lock()
GLOBAL_INTERVAL_SEC = 2.0   # 同一 IP 两次抓取最小间隔

# UA(常见浏览器,AtCoder 没风控)
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _ip_throttle() -> None:
    """v3.9.73 · 全局 IP 限流,防止对 AtCoder 触发频率保护。"""
    import time
    import threading as _t
    with _IP_LOCK:
        now = time.time()
        last = _IP_LAST_FETCH.get("__last__", 0.0)
        gap = now - last
        if gap < GLOBAL_INTERVAL_SEC:
            time.sleep(GLOBAL_INTERVAL_SEC - gap)
        _IP_LAST_FETCH["__last__"] = time.time()


def _httpx_get_with_retry(url: str, max_retries: int = 3) -> tuple[int, str, dict]:
    """v3.9.73 · httpx GET + 重试 + 错误分类。

    Returns:
        (status_code, body_text, headers)

    Raises:
        FetchError: 404/限流超时/重试耗尽/网络异常
    """
    import time
    import httpx
    last_exc: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            _ip_throttle()
            with httpx.Client(
                timeout=15.0,
                follow_redirects=True,
                headers={"User-Agent": _USER_AGENT, "Accept-Language": "en,ja;q=0.9"},
            ) as client:
                resp = client.get(url)
                if resp.status_code == 404:
                    raise FetchError(f"404 not found: {url}", status=404)
                if resp.status_code == 429:
                    # 读 Retry-After 头
                    ra = resp.headers.get("Retry-After", "60")
                    try:
                        retry_after = int(ra)
                    except ValueError:
                        retry_after = 60
                    if attempt < max_retries - 1:
                        logger.warning(f"[atcoder] 429 rate limited, sleep {retry_after}s")
                        time.sleep(min(retry_after, 120))
                        continue
                    raise FetchError(f"429 rate limited", status=429, retry_after=retry_after)
                if 500 <= resp.status_code < 600:
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    raise FetchError(f"{resp.status_code} server error", status=resp.status_code)
                return resp.status_code, resp.text, dict(resp.headers)
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            last_exc = e
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise FetchError(f"网络异常: {e}") from e
    raise FetchError(f"重试耗尽: {last_exc}")


def _save_raw_html(cache_dir: Path, handle: str, page: str, html: str) -> str:
    """v3.9.73 · 把原始 HTML 写到 cache_dir/<handle>/<page>_<ts>.html。

    返回相对路径(写库用)。
    """
    try:
        d = cache_dir / handle
        d.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        f = d / f"{page}_{ts}.html"
        f.write_text(html, encoding="utf-8")
        return str(f.relative_to(cache_dir)) if f.is_relative_to(cache_dir) else str(f)
    except Exception as e:
        logger.warning(f"[atcoder] save cache failed: {e}")
        return ""


def fetch_atcoder_profile(handle: str, cache_dir: Optional[Path] = None) -> dict:
    """v3.9.73 · 抓取 + 解析 + 缓存(三步一体)。

    Args:
        handle: 已校验过的 AtCoder handle
        cache_dir: raw HTML 缓存目录,None 表示不缓存(测试用)

    Returns:
        dict 至少含 fetch_status='ok',其他字段见 atcoder_persist_data 文档

    Raises:
        FetchError: 网络/限流/解析失败
    """
    if not is_handle_valid(handle):
        raise FetchError(f"handle 格式不合法: {handle}")

    cache_dir = cache_dir or (Path(__file__).resolve().parent / ".source_cache" / "atcoder")

    # 1. 用户主页
    user_url = f"https://atcoder.jp/users/{handle}"
    try:
        status, html, _ = _httpx_get_with_retry(user_url)
    except FetchError as e:
        if e.status == 404:
            raise FetchError(f"AtCoder 用户 {handle} 不存在", status=404) from e
        raise
    user_cache_path = _save_raw_html(cache_dir, handle, "user", html) if cache_dir else ""

    # 2. 解析 user 页
    try:
        user_data = parse_atcoder_user_page(html)
    except ParseError as e:
        raise FetchError(f"解析失败: {e}", status=200) from e

    # 3. AC 列表(单页就够,200 题够高光)
    ac_url = f"https://atcoder.jp/users/{handle}?contestType=algo"
    ac_problems: list[dict] = []
    try:
        _, ac_html, _ = _httpx_get_with_retry(ac_url)
        _save_raw_html(cache_dir, handle, "ac", ac_html) if cache_dir else ""
        ac_problems = parse_atcoder_ac_list_page(ac_html)
    except FetchError as e:
        # AC 列表抓不到不阻塞主体
        logger.warning(f"[atcoder] AC list fetch failed: {e}")

    # 4. 最近提交(最近 1 场比赛的提交页)
    recent_subs: list[dict] = []
    if ac_problems:
        latest_contest = ac_problems[-1].get("contest_id", "")
        if latest_contest:
            sub_url = f"https://atcoder.jp/contests/{latest_contest}/submissions?f.User={handle}"
            try:
                _, sub_html, _ = _httpx_get_with_retry(sub_url)
                _save_raw_html(cache_dir, handle, "subs", sub_html) if cache_dir else ""
                recent_subs = parse_atcoder_submissions_page(sub_html)[:10]
            except FetchError as e:
                logger.warning(f"[atcoder] subs fetch failed: {e}")

    # 5. 派生指标
    ac_count = len(ac_problems)
    hard_count = sum(1 for p in ac_problems if compute_ac_highlights([p], limit=1)[0].get("difficulty", 0) >= 2000)

    return {
        "handle": handle,
        "rating": user_data.get("rating", 0),
        "highest_rating": user_data.get("highest_rating", 0),
        "rank": user_data.get("rank", "gray"),
        "contests_count": user_data.get("contests_count", 0),
        "ac_problems_count": ac_count,
        "hard_ac_count": hard_count,
        "recent_contest_rate": 0,  # M2 简化:暂不算,留字段
        "first_event_at": user_data.get("first_event_at"),
        "last_event_at": user_data.get("last_event_at"),
        "ac_problems": ac_problems,
        "recent_subs": recent_subs,
        "fetch_status": "ok",
        "fetch_error": "",
        "raw_html_cache_path": user_cache_path,
    }


# ======================================================================
# 6. 后台 worker 循环(单线程,顺序处理 pending 任务)
# ======================================================================

_worker_thread = None
_worker_lock = __import__("threading").Lock()


def start_atcoder_worker() -> None:
    """v3.9.73 · 启动后台 worker 线程(单实例,daemon)。

    web_app 启动时调一次。worker 每 2s 轮询 atcoder_fetch_tasks 表。
    """
    import threading
    global _worker_thread
    with _worker_lock:
        if _worker_thread and _worker_thread.is_alive():
            return
        _worker_thread = threading.Thread(target=_atcoder_worker_loop, name="atcoder-worker", daemon=True)
        _worker_thread.start()
        logger.info("[v3.9.73] atcoder worker started")


def _atcoder_worker_loop() -> None:
    """v3.9.73 · worker 主循环:轮询 atcoder_fetch_tasks.pending,跑 fetch+persist。"""
    import time
    from task_store import (
        atcoder_pickup_pending_task,
        atcoder_finish_task,
        atcoder_persist_data,
        atcoder_mark_failed,
    )
    while True:
        try:
            task = atcoder_pickup_pending_task()
            if not task:
                time.sleep(2.0)
                continue
            task_id = task["task_id"]
            student_id = task["student_id"]
            handle = task["handle"]
            logger.info(f"[v3.9.73] atcoder worker picked up: {task_id} handle={handle}")
            try:
                raw = fetch_atcoder_profile(handle)
                atcoder_persist_data(student_id, handle, raw)
                atcoder_finish_task(task_id, "ok", "")
                logger.info(f"[v3.9.73] atcoder worker done: {task_id}")
            except FetchError as e:
                status = "rate_limited" if e.status == 429 else "failed"
                atcoder_mark_failed(student_id, str(e), status=status)
                atcoder_finish_task(task_id, status, str(e))
                logger.warning(f"[v3.9.73] atcoder worker failed: {task_id} {status} {e}")
            except Exception as e:
                atcoder_mark_failed(student_id, f"未知异常: {e}", status="failed")
                atcoder_finish_task(task_id, "failed", str(e))
                logger.exception(f"[v3.9.73] atcoder worker exception: {task_id}")
        except Exception as loop_exc:
            # 防御性:不要让 worker 死
            # v3.9.74 · 表还没初始化(如测试场景)就安静等 10s 再试,别刷屏
            err_str = str(loop_exc)
            if "no such table" in err_str or "unable to open" in err_str:
                time.sleep(10.0)
                continue
            logger.exception(f"[v3.9.73] worker loop error: {loop_exc}")
            try:
                time.sleep(5.0)
            except Exception:
                pass
