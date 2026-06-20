"""
v3.9.73 · AtCoder 解析层单测(无网络,纯 HTML 喂入)

覆盖:
  - parse_atcoder_user_page(完整 / 无 rating / 404 / 多语言)
  - parse_atcoder_ac_list_page
  - parse_atcoder_submissions_page
  - _rating_to_rank 全段位
  - is_handle_valid 正反例
  - compute_ac_highlights 排序
  - get_atcoder_context 在 link_status=stale 时正确派生
"""

import unittest
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import tempfile

# 让 tests/ 跑时能 import 根目录的模块
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from atcoder_fetcher import (
    is_handle_valid,
    parse_atcoder_user_page,
    parse_atcoder_ac_list_page,
    parse_atcoder_submissions_page,
    _rating_to_rank,
    _parse_datetime_atcoder,
    compute_ac_highlights,
    ParseError,
    RANK_COLORS,
    RANK_ZH,
)


# ===========================================================================
# Fixture HTML 模板(基于 AtCoder 实际结构,2024 年长期观察)
# ===========================================================================

USER_PAGE_NORMAL = """
<html><body>
<div id="main-container">
  <div class="row">
    <div class="col-sm-12">
      <table class="table table-bordered table-default">
        <tr><th>Username</th><td>tourist</td></tr>
        <tr><th>Rating</th><td>1500</td></tr>
        <tr><th>Highest Rating</th><td>1800</td></tr>
        <tr><th>Rated Matches</td><td>87</td></tr>
        <tr><th>Last Competed</th><td>2024-01-15 21:30:00+0900</td></tr>
        <tr><th>Affiliation</th><td>MIT</td></tr>
      </table>
    </div>
  </div>
</div>
</body></html>
"""

USER_PAGE_NO_RATING = """
<html><body>
<div id="main-container">
  <div class="row">
    <div class="col-sm-12">
      <table class="table table-bordered table-default">
        <tr><th>Username</th><td>newbie</td></tr>
        <tr><th>Rating</th><td>0</td></tr>
        <tr><th>Highest Rating</th><td>0</td></tr>
        <tr><th>Rated Matches</th><td>0</td></tr>
        <tr><th>Last Competed</th><td></td></tr>
        <tr><th>Affiliation</th><td></td></tr>
      </table>
    </div>
  </div>
</div>
</body></html>
"""

USER_PAGE_404 = """
<html><body>
<h1>404 Not Found</h1>
<p>ページが見つかりません</p>
</body></html>
"""

AC_LIST_PAGE = """
<html><body>
<table>
  <tr><th>Contest</th><th>Problem</th><th>Date</th><th>Language</th><th>Score</th></tr>
  <tr>
    <td><a href="/contests/abc300">AtCoder Beginner Contest 300</a></td>
    <td><a href="/contests/abc300/submissions/me">A - AtCoder Group Contest 2</a></td>
    <td>2024-01-15 21:30:00+0900</td>
    <td>C++ (GCC 11.2.0)</td>
    <td>100</td>
  </tr>
  <tr>
    <td><a href="/contests/arc150">AtCoder Regular Contest 150</a></td>
    <td><a href="/contests/arc150/submissions/me">D - Semi Common Multiple</a></td>
    <td>2024-02-01 22:00:00+0900</td>
    <td>Python (3.11.2)</td>
    <td>100</td>
  </tr>
</table>
</body></html>
"""

SUBMISSIONS_PAGE = """
<html><body>
<table>
  <tr><th>Time</th><th>Task</th><th>User</th><th>Language</th><th>Score</th><th>Code</th><th>Status</th></tr>
  <tr>
    <td>2024-01-15 21:30:00+0900</td>
    <td><a href="/contests/abc300/tasks/abc300_a">A - AtCoder Group Contest 2</a></td>
    <td>tourist</td>
    <td>C++</td>
    <td>100</td>
    <td><a href="/contests/abc300/submissions/12345">link</a></td>
    <td>AC</td>
  </tr>
  <tr>
    <td>2024-01-15 21:32:00+0900</td>
    <td><a href="/contests/abc300/tasks/abc300_b">B - Boring Sequence</a></td>
    <td>tourist</td>
    <td>C++</td>
    <td>0</td>
    <td><a href="/contests/abc300/submissions/12346">link</a></td>
    <td>WA</td>
  </tr>
</table>
</body></html>
"""


# ===========================================================================
# 1. handle 格式校验
# ===========================================================================

class TestHandleValid(unittest.TestCase):

    def test_valid_handles(self):
        for h in ("tourist", "alice", "bob_2024", "abc", "A" * 20, "x" * 3):
            self.assertTrue(is_handle_valid(h), f"应该通过: {h}")

    def test_invalid_handles(self):
        for h in ("", "ab", "a" * 21, "alice-bob", "alice.bob", "中国", "alice bob", None):
            self.assertFalse(is_handle_valid(h), f"应该拒绝: {h!r}")


# ===========================================================================
# 2. _rating_to_rank 全段位
# ===========================================================================

class TestRatingToRank(unittest.TestCase):

    def test_gray(self):
        self.assertEqual(_rating_to_rank(0), "gray")
        self.assertEqual(_rating_to_rank(399), "gray")

    def test_brown(self):
        self.assertEqual(_rating_to_rank(400), "brown")
        self.assertEqual(_rating_to_rank(799), "brown")

    def test_green(self):
        self.assertEqual(_rating_to_rank(800), "green")
        self.assertEqual(_rating_to_rank(1199), "green")

    def test_cyan(self):
        self.assertEqual(_rating_to_rank(1200), "cyan")
        self.assertEqual(_rating_to_rank(1599), "cyan")

    def test_blue(self):
        self.assertEqual(_rating_to_rank(1600), "blue")
        self.assertEqual(_rating_to_rank(1999), "blue")

    def test_yellow(self):
        self.assertEqual(_rating_to_rank(2000), "yellow")
        self.assertEqual(_rating_to_rank(2399), "yellow")

    def test_orange(self):
        self.assertEqual(_rating_to_rank(2400), "orange")
        self.assertEqual(_rating_to_rank(2799), "orange")

    def test_red(self):
        self.assertEqual(_rating_to_rank(2800), "red")
        self.assertEqual(_rating_to_rank(3500), "red")

    def test_rank_colors_have_8_levels(self):
        self.assertEqual(len(RANK_COLORS), 8)
        self.assertEqual(len(RANK_ZH), 8)


# ===========================================================================
# 3. parse_atcoder_user_page
# ===========================================================================

class TestParseUserPage(unittest.TestCase):

    def test_normal(self):
        result = parse_atcoder_user_page(USER_PAGE_NORMAL)
        self.assertEqual(result["rating"], 1500)
        self.assertEqual(result["highest_rating"], 1800)
        self.assertEqual(result["contests_count"], 87)
        # 段位: highest_rating 1800 → blue
        self.assertEqual(result["rank"], "blue")
        self.assertEqual(result["last_event_at"], "2024-01-15T21:30:00")

    def test_no_rating_new_account(self):
        result = parse_atcoder_user_page(USER_PAGE_NO_RATING)
        self.assertEqual(result["rating"], 0)
        self.assertEqual(result["highest_rating"], 0)
        self.assertEqual(result["rank"], "gray")
        self.assertEqual(result["contests_count"], 0)
        self.assertIsNone(result["last_event_at"])

    def test_404_raises_parse_error(self):
        with self.assertRaises(ParseError):
            parse_atcoder_user_page(USER_PAGE_404)

    def test_empty_html_returns_zero_profile(self):
        result = parse_atcoder_user_page("")
        self.assertEqual(result["rating"], 0)
        self.assertEqual(result["highest_rating"], 0)
        self.assertEqual(result["contests_count"], 0)


# ===========================================================================
# 4. parse_atcoder_ac_list_page
# ===========================================================================

class TestParseAcList(unittest.TestCase):

    def test_two_problems(self):
        results = parse_atcoder_ac_list_page(AC_LIST_PAGE)
        self.assertEqual(len(results), 2)
        # 第一条
        self.assertEqual(results[0]["contest_id"], "abc300")
        self.assertEqual(results[0]["problem_id"], "abc300_a")
        self.assertIn("Group Contest", results[0]["title"])
        self.assertEqual(results[0]["language"], "C++ (GCC 11.2.0)")
        self.assertEqual(results[0]["solved_at"], "2024-01-15T21:30:00")
        # 第二条
        self.assertEqual(results[1]["contest_id"], "arc150")
        self.assertEqual(results[1]["problem_id"], "arc150_d")

    def test_empty_page(self):
        results = parse_atcoder_ac_list_page("<html><body></body></html>")
        self.assertEqual(results, [])


# ===========================================================================
# 5. parse_atcoder_submissions_page
# ===========================================================================

class TestParseSubmissions(unittest.TestCase):

    def test_two_subs(self):
        results = parse_atcoder_submissions_page(SUBMISSIONS_PAGE)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["result"], "AC")
        self.assertEqual(results[0]["problem_id"], "abc300_a")
        self.assertEqual(results[0]["contest_id"], "abc300")
        self.assertEqual(results[0]["source_url"], "https://atcoder.jp/contests/abc300/submissions/12345")
        # 第二条 WA
        self.assertEqual(results[1]["result"], "WA")
        self.assertEqual(results[1]["problem_id"], "abc300_b")

    def test_empty(self):
        self.assertEqual(parse_atcoder_submissions_page(""), [])


# ===========================================================================
# 6. compute_ac_highlights 排序
# ===========================================================================

class TestComputeAcHighlights(unittest.TestCase):

    def test_sort_by_difficulty_desc(self):
        problems = [
            {"contest_id": "abc100", "problem_id": "abc100_a", "solved_at": "2024-01-01T00:00:00"},
            {"contest_id": "abc300", "problem_id": "abc300_f", "solved_at": "2024-03-01T00:00:00"},
            {"contest_id": "abc200", "problem_id": "abc200_c", "solved_at": "2024-02-01T00:00:00"},
        ]
        highlights = compute_ac_highlights(problems, limit=8)
        # f (1000) > c (400) > a (100)
        self.assertEqual(highlights[0]["problem_id"], "abc300_f")
        self.assertEqual(highlights[1]["problem_id"], "abc200_c")
        self.assertEqual(highlights[2]["problem_id"], "abc100_a")
        # difficulty 已附加
        self.assertEqual(highlights[0]["difficulty"], 1000)
        self.assertEqual(highlights[2]["difficulty"], 100)

    def test_limit(self):
        problems = [{"contest_id": "abc100", "problem_id": "abc100_a", "solved_at": "2024-01-01"}] * 20
        self.assertEqual(len(compute_ac_highlights(problems, limit=5)), 5)


# ===========================================================================
# 7. _parse_datetime_atcoder
# ===========================================================================

class TestParseDatetime(unittest.TestCase):

    def test_iso_with_tz(self):
        self.assertEqual(_parse_datetime_atcoder("2024-01-15 21:30:00+0900"), "2024-01-15T21:30:00")

    def test_iso_no_tz(self):
        self.assertEqual(_parse_datetime_atcoder("2024-01-15 21:30:00"), "2024-01-15T21:30:00")

    def test_date_only(self):
        self.assertEqual(_parse_datetime_atcoder("2024-01-15"), "2024-01-15T00:00:00")

    def test_empty(self):
        self.assertIsNone(_parse_datetime_atcoder(""))
        self.assertIsNone(_parse_datetime_atcoder(None))

    def test_unparseable_returns_raw(self):
        self.assertEqual(_parse_datetime_atcoder("garbage"), "garbage")


# ===========================================================================
# 8. task_store 集成(get_atcoder_context 派生 link_status='stale')
# ===========================================================================

class TestGetAtcoderContextStale(unittest.TestCase):
    """v3.9.73 · 验证陈旧派生逻辑。"""

    def setUp(self):
        # 用临时 SQLite,直接调 task_store 函数
        from task_store import init_db, init_atcoder_tables, _get_conn
        self.tmpdir = tempfile.mkdtemp()
        import os
        os.environ["TASK_DB_PATH"] = os.path.join(self.tmpdir, "tasks.db")
        # 重置 module-level DB_PATH
        import task_store
        task_store.DB_PATH = Path(os.environ["TASK_DB_PATH"])
        init_db()
        init_atcoder_tables()

    def test_stale_derivation(self):
        from task_store import _get_conn, get_atcoder_context
        conn = _get_conn()
        try:
            # 插一个学生,绑 handle,数据 8 天前
            eight_days_ago = (datetime.now() - timedelta(days=8)).isoformat(timespec="seconds")
            conn.execute("""
                INSERT INTO students (luogu_uid, real_name, atcoder_handle)
                VALUES ('123456', 'test', 'tourist')
            """)
            conn.execute("""
                INSERT INTO student_atcoder_data (
                    student_id, handle, rating, highest_rating, rank,
                    link_status, last_fetched_at
                ) VALUES (
                    1, 'tourist', 1500, 1800, 'blue', 'ok', ?
                )
            """, (eight_days_ago,))
            conn.commit()
        finally:
            conn.close()

        ctx = get_atcoder_context("123456")
        self.assertEqual(ctx["link_status"], "stale")
        self.assertEqual(ctx["rating"], 1500)
        self.assertEqual(ctx["rank_zh"], "蓝色")

    def test_unlinked(self):
        from task_store import init_db, get_atcoder_context, _get_conn
        # 没绑 handle
        conn = _get_conn()
        try:
            conn.execute("INSERT INTO students (luogu_uid, real_name) VALUES ('999', 'nobody')")
            conn.commit()
        finally:
            conn.close()
        ctx = get_atcoder_context("999")
        self.assertEqual(ctx["link_status"], "unlinked")
        self.assertEqual(ctx["rating"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
