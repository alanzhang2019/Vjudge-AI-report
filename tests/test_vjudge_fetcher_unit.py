"""
v3.9.74 · VJudge fetcher 单元测试
不依赖网络: 测试纯解析函数(username 校验/HTML 解析/数据清洗)
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import vjudge_fetcher
from vjudge_fetcher import (
    is_username_valid,
    parse_vjudge_user_page,
    parse_vjudge_solved_page,
    _clean_int,
    _clean_float,
    FetchError,
)


class TestIsUsernameValid(unittest.TestCase):
    def test_valid(self):
        for u in ("alice", "TLE_AC_DIAMOND", "abc123", "x-y-z", "a" * 30):
            self.assertTrue(is_username_valid(u), u)

    def test_invalid_short(self):
        self.assertFalse(is_username_valid("ab"))
        self.assertFalse(is_username_valid(""))

    def test_invalid_too_long(self):
        self.assertFalse(is_username_valid("a" * 31))

    def test_invalid_chars(self):
        for u in ("alice@home", "alice space", "中文", "alice!@#"):
            self.assertFalse(is_username_valid(u), u)

    def test_with_dash(self):
        # 允许连字符(VJudge 真实用户名风格)
        self.assertTrue(is_username_valid("test-user"))


class TestCleanInt(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(_clean_int("123"), 123)
        self.assertEqual(_clean_int("1,234"), 1234)
        self.assertEqual(_clean_int(" 42 "), 42)

    def test_negative(self):
        self.assertEqual(_clean_int("-5"), -5)

    def test_empty(self):
        self.assertEqual(_clean_int(""), 0)
        self.assertEqual(_clean_int("abc"), 0)


class TestCleanFloat(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(_clean_float("0.3"), 0.3)
        self.assertEqual(_clean_float("30%"), 30.0)
        self.assertEqual(_clean_float("12,345.67"), 12345.67)

    def test_empty(self):
        self.assertEqual(_clean_float(""), 0.0)


class TestParseVjudgeUserPage(unittest.TestCase):
    def test_empty_html(self):
        r = parse_vjudge_user_page("")
        self.assertEqual(r["total_ac"], 0)
        self.assertEqual(r["oj_stats"], {})

    def test_with_nick_in_h3(self):
        html = """
        <html><head><title>vjudge - alice_2024</title></head>
        <body>
        <h3>alice_2024<small>female</small></h3>
        <span title="2023-05-15 10:30:00">2023-05-15</span>
        <table><tr><th>OJ</th><th>Solved</th></tr>
        <tr><td><a href="/user/Codeforces">Codeforces</a></td><td>150</td></tr>
        <tr><td><a href="/user/AtCoder">AtCoder</a></td><td>80</td></tr>
        <tr><td><a href="/user/Luogu">Luogu</a></td><td>200</td></tr>
        <tr><td>Total Submissions | AC | WA | TLE | RE | CE</td>
            <td>500 | 430 | 50 | 10 | 5 | 5</td></tr>
        </table>
        </body></html>
        """
        r = parse_vjudge_user_page(html)
        self.assertEqual(r["nick"], "alice_2024")
        self.assertEqual(r["register_time"], "2023-05-15 10:30:00")
        self.assertEqual(r["oj_stats"]["Codeforces"], 150)
        self.assertEqual(r["oj_stats"]["AtCoder"], 80)
        self.assertEqual(r["oj_stats"]["Luogu"], 200)
        self.assertEqual(r["total_submissions"], 500)
        self.assertEqual(r["total_ac"], 430)
        self.assertEqual(r["total_wa"], 50)
        self.assertAlmostEqual(r["ac_rate"], 0.86, places=2)

    def test_malformed_no_crash(self):
        # 缺字段不应崩
        html = "<html><body><h3>test</h3></body></html>"
        r = parse_vjudge_user_page(html)
        self.assertEqual(r["nick"], "test")
        self.assertEqual(r["total_ac"], 0)

    def test_fallback_nick_from_title(self):
        html = """
        <html><head><title>vjudge - bob_99</title></head>
        <body></body></html>
        """
        r = parse_vjudge_user_page(html)
        self.assertEqual(r["nick"], "bob_99")


class TestParseVjudgeSolvedPage(unittest.TestCase):
    def test_empty(self):
        r = parse_vjudge_solved_page("")
        self.assertEqual(r, [])

    def test_no_table(self):
        r = parse_vjudge_solved_page("<html><body>empty</body></html>")
        self.assertEqual(r, [])

    def test_with_table(self):
        html = """
        <html><body>
        <table id="solvedTable">
        <tr><th>OJ</th><th>Problem</th><th>Time</th></tr>
        <tr>
            <td><a href="/problem/Codeforces/1234A">CF</a></td>
            <td><a href="/problem/Codeforces/1234A">Equalize</a></td>
            <td title="2024-06-01 10:00:00">2024-06-01</td>
        </tr>
        <tr>
            <td><a href="/problem/AtCoder/abc100_a">AC</a></td>
            <td><a href="/problem/AtCoder/abc100_a">Happy Birthday!</a></td>
            <td title="2024-05-15 08:30:00">2024-05-15</td>
        </tr>
        </table>
        </body></html>
        """
        r = parse_vjudge_solved_page(html, limit=10)
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0]["oj"], "Codeforces")
        self.assertEqual(r[0]["problem_id"], "1234A")
        self.assertEqual(r[1]["oj"], "AtCoder")
        self.assertEqual(r[1]["problem_id"], "abc100_a")

    def test_limit(self):
        # 200 条限制测试
        rows = "".join([
            f'<tr><td><a href="/problem/CF/{i}A">CF{i}A</a></td>'
            f'<td><a href="/problem/CF/{i}A">P{i}</a></td>'
            f'<td title="2024-01-01">2024-01-01</td></tr>'
            for i in range(500)
        ])
        html = f"<html><body><table id='solvedTable'><tr><th>O</th><th>P</th><th>T</th></tr>{rows}</table></body></html>"
        r = parse_vjudge_solved_page(html, limit=200)
        self.assertEqual(len(r), 200)


class TestFetchError(unittest.TestCase):
    def test_basic(self):
        e = FetchError("hello")
        self.assertEqual(str(e), "hello")
        self.assertIsNone(e.status)

    def test_with_status(self):
        e = FetchError("vjudge 404", status=404)
        self.assertEqual(e.status, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
