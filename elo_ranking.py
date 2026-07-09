"""elo_ranking.py - v3.13 · 洛谷 ELO 等级分排行榜前 10 名
============================================================
设计目标:
  - admin 粘贴 luogu ELO 页面 HTML 源码 (用户本地浏览器能访问, server 端 403)
  - server 解析 HTML 提取 top 10 (uid/姓名/分数/排名)
  - 存入 SQLite, 公开页面 /ranking/elo 展示卡片
  - 每个 top 10 用户如果在本平台生成过报告, 复用显示
  - 否则显示「该用户暂未生成报告」+ 洛谷主页链接
"""
from __future__ import annotations

import json
import re
import sqlite3
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
