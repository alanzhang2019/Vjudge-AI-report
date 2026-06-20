"""v3.9.6 单测：关键赛事倒计时显示 5 个事件 + CSP-J/S 包含在内

覆盖三个核心点：
  1) SQL + 去重后必须包含 CSP-J 初赛 / CSP-S 初赛
  2) 海报 visible_events 截断 [:5] 后仍能看到 CSP-J/S
  3) 截断前的排序按 exam_date ASC（同日按 prefix 稳定）
"""
import os
import re
import sqlite3
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

# 测试不依赖 Flask 运行时，直接复用 web_app.py 的纯函数
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web_app import _shorten_comp_name  # noqa: E402


def _build_events_for_test(db_path: str) -> list:
    """复制 web_app.py _build_share_card_data 中的赛事查询 + 去重逻辑（v3.9.6 CSP-J/S 合并）"""
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT name, exam_date FROM competitions "
            "WHERE data_year = 2026 "
            "  AND exam_date >= date('now', '-7 days') "
            "  AND (name LIKE '%GESP%' OR name LIKE '%CSP%' "
            "       OR name LIKE '%NOIP%' OR name LIKE '%NOI%') "
            "ORDER BY exam_date"
        ).fetchall()
    finally:
        conn.close()

    today = date.today()

    def _group_key(name: str, display: str) -> str:
        if display.startswith("CSP-J") or display.startswith("CSP-S"):
            tail = display.split(" ", 1)[1] if " " in display else ""
            return f"CSP_{tail}"
        return display.split()[0] if display else ""

    # 第一遍：聚合
    grouped: dict = {}
    for ename, edate in rows:
        try:
            date.fromisoformat(edate)
        except Exception:
            continue
        display = _shorten_comp_name(ename)
        key = (edate, _group_key(ename, display))
        slot = grouped.setdefault(key, {"display": display, "has_j": False, "has_s": False})
        if "CSP-J" in ename:
            slot["has_j"] = True
        if "CSP-S" in ename:
            slot["has_s"] = True
    for key, slot in grouped.items():
        _, gk = key
        if gk.startswith("CSP_") and slot["has_j"] and slot["has_s"]:
            slot["display"] = f"CSP-J/S {gk.split('_', 1)[1]}"

    # 第二遍：按 SQL 顺序输出
    events = []
    seen: dict = {}
    for ename, edate in rows:
        try:
            d = date.fromisoformat(edate)
        except Exception:
            continue
        display = _shorten_comp_name(ename)
        key = (edate, _group_key(ename, display))
        if key in seen:
            continue
        seen[key] = True
        events.append({
            "name": ename,
            "display": grouped[key]["display"],
            "date": edate,
            "days": max(0, (d - today).days),
        })
    return events


def _seed_test_db(db_path: str) -> None:
    """构造一份最小可复现的测试数据：覆盖 GESP/NOI/CSP-J/S/NOIP 各类型"""
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE competitions (
            id INTEGER PRIMARY KEY,
            code TEXT UNIQUE,
            name TEXT,
            type TEXT,
            level INTEGER,
            exam_date DATE,
            registration_deadline DATE,
            target_audience TEXT,
            fee_cny INTEGER,
            source_url TEXT,
            data_year INTEGER,
            notes TEXT
        );
    """)
    rows = [
        ("GESP-2026-06-L1-4",  "GESP 等级认证（1-4 级夏考）", "gesp", 1, "2026-06-13"),
        ("GESP-2026-06-L5-6",  "GESP 等级认证（5-6 级夏考）", "gesp", 5, "2026-06-13"),
        ("NOI-2026",           "NOI 2026",                    "noi",  None, "2026-07-15"),
        ("GESP-2026-09-L1-4",  "GESP 等级认证（1-4 级秋考）", "gesp", 1, "2026-09-12"),
        ("GESP-2026-09-L7-8",  "GESP 等级认证（7-8 级秋考）", "gesp", 7, "2026-09-12"),
        ("CSP-J-1-2026",       "CSP-J 2026 第一轮（初赛）",   "csp_j1", None, "2026-09-19"),
        ("CSP-S-1-2026",       "CSP-S 2026 第一轮（初赛）",   "csp_s1", None, "2026-09-19"),
        ("CSP-J-2-2026",       "CSP-J 2026 第二轮（复赛）",   "csp_j2", None, "2026-10-31"),
        ("CSP-S-2-2026",       "CSP-S 2026 第二轮（复赛）",   "csp_s2", None, "2026-11-07"),
        ("NOIP-2026",          "NOIP 2026 全国赛",            "noip",  None, "2026-11-28"),
        ("GESP-2026-12-L1-4",  "GESP 等级认证（1-4 级冬考）", "gesp", 1, "2026-12-19"),
        ("GESP-2026-12-L5-8",  "GESP 等级认证（5-8 级冬考）", "gesp", 5, "2026-12-19"),
    ]
    conn.executemany(
        "INSERT INTO competitions (code, name, type, level, exam_date, data_year) "
        "VALUES (?, ?, ?, ?, ?, 2026)",
        rows,
    )
    conn.commit()
    conn.close()


class KeyEventsVisibleTest(unittest.TestCase):
    """v3.9.6 回归测试：5 行布局 + CSP-J/S 必须可见"""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix="luogu_evt_")
        cls.db_path = os.path.join(cls.tmpdir, "test_tasks.db")
        _seed_test_db(cls.db_path)
        cls.events = _build_events_for_test(cls.db_path)
        # 与 web_app.py 中的截断逻辑保持一致
        cls.visible = cls.events[:5]

    def test_sql_returns_csp_j_s(self):
        """SQL 原始行必须同时包含 CSP-J 1 与 CSP-S 1（数据层）"""
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT name FROM competitions "
                "WHERE data_year=2026 AND name LIKE '%CSP% 2026 第一轮%'"
            ).fetchall()
        finally:
            conn.close()
        names = [r[0] for r in rows]
        self.assertTrue(
            any("CSP-J 2026 第一轮" in n for n in names),
            f"CSP-J 1st round 缺失: {names}",
        )
        self.assertTrue(
            any("CSP-S 2026 第一轮" in n for n in names),
            f"CSP-S 1st round 缺失: {names}",
        )

    def test_csp_j_s_merged_into_one_row(self):
        """v3.9.6 · 同日 CSP-J+S 合并为单条 "CSP-J/S 初赛"，不重复占行"""
        csp_first = [e for e in self.events if e["date"] == "2026-09-19"]
        self.assertEqual(
            len(csp_first), 1,
            f"2026-09-19 期望 1 条合并事件，实际 {len(csp_first)}: {csp_first}",
        )
        self.assertEqual(csp_first[0]["display"], "CSP-J/S 初赛")

    def test_csp_j_s_round2_merged(self):
        """CSP-J 复赛 (10-31) + CSP-S 复赛 (11-07) 不同日，不应合并"""
        csp_finals = [e for e in self.events if e["display"].startswith("CSP-J/S 复赛")
                      or e["display"] in ("CSP-J 复赛", "CSP-S 复赛")]
        # 复赛在不同日，应各占 1 行
        self.assertEqual(
            len(csp_finals), 2,
            f"CSP 复赛 期望 2 条（不同日不合并），实际 {len(csp_finals)}: {csp_finals}",
        )

    def test_visible_window_includes_csp_merged(self):
        """海报 visible_events[:5] 截断后，CSP-J/S 合并行仍可见"""
        visible_names = [e["display"] for e in self.visible]
        self.assertEqual(len(self.visible), 5, "应显示 5 行事件")
        self.assertIn(
            "CSP-J/S 初赛", visible_names,
            f"[:5] 截断后合并的 CSP-J/S 初赛 不见了: {visible_names}",
        )

    def test_dedup_gesp_same_day(self):
        """同日 GESP 多个级别应合并为 1 条（夏考/秋考/冬考）"""
        gesp_events = [e for e in self.events if "GESP" in e["display"]]
        dates = [e["date"] for e in gesp_events]
        # 三个不同日期：夏(06-13) / 秋(09-12) / 冬(12-19)
        self.assertEqual(len(gesp_events), 3, f"GESP 应有 3 个去重后事件，实际 {len(gesp_events)}: {gesp_events}")

    def test_sort_is_ascending_by_date(self):
        """事件按 exam_date ASC 排序"""
        for i in range(len(self.events) - 1):
            self.assertLessEqual(
                self.events[i]["date"],
                self.events[i + 1]["date"],
                f"排序错位：{self.events[i]['date']} > {self.events[i+1]['date']}",
            )

    def test_shorten_comp_name_keeps_csp_prefix(self):
        """_shorten_comp_name 必须保留 CSP-J/S 关键前缀"""
        self.assertEqual(_shorten_comp_name("CSP-J 2026 第一轮（初赛）"), "CSP-J 初赛")
        self.assertEqual(_shorten_comp_name("CSP-S 2026 第一轮（初赛）"), "CSP-S 初赛")
        self.assertEqual(_shorten_comp_name("CSP-J 2026 第二轮（复赛）"), "CSP-J 复赛")
        self.assertEqual(_shorten_comp_name("CSP-S 2026 第二轮（复赛）"), "CSP-S 复赛")


class ShareCardLayoutTest(unittest.TestCase):
    """v3.9.6 静态源码检查：海报渲染层使用 [:5] + row_h=0.30 + zorder 保护 row 5"""

    @classmethod
    def setUpClass(cls):
        cls.src = Path(__file__).resolve().parent.parent / "web_app.py"
        cls.text = cls.src.read_text(encoding="utf-8")

    def test_visible_window_is_5(self):
        """web_app.py 海报渲染中 visible_events 必须截断 [:5]"""
        m = re.search(r"visible_events\s*=\s*\(data\.get\(\"events\"\)\s*or\s*\[\]\)\[:(\d+)\]", self.text)
        self.assertIsNotNone(m, "找不到 visible_events 截断行")
        self.assertEqual(
            m.group(1),
            "5",
            f"visible_events 应为 [:5]，当前 [:{m.group(1)}]",
        )

    def test_row_h_compact_for_5_rows(self):
        """row_h 应紧凑为 0.30 以容纳 5 行（默认 0.40 会与 QR 顶 2.50 重叠）"""
        m = re.search(r"row_h\s*=\s*([\d.]+)\s*#", self.text)
        self.assertIsNotNone(m, "找不到 row_h 紧凑布局注释")
        self.assertEqual(
            float(m.group(1)),
            0.30,
            f"row_h 应为 0.30，当前 {m.group(1)}",
        )

    def test_row5_zorder_protection(self):
        """row 5 徽章必须用 zorder 盖在 QR 白底之上"""
        self.assertIn("zorder", self.text, "row 5 未设置 zorder 会被 QR 白底覆盖")
        # 至少在 events loop 内的 patch 调用上看到 set_zorder
        self.assertRegex(self.text, r"ev_box\.set_zorder\(")
        self.assertRegex(self.text, r"ev_badge\.set_zorder\(")


if __name__ == "__main__":
    unittest.main(verbosity=2)
