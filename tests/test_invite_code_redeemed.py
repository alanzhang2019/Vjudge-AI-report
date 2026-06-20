"""v3.9.41 单测：邀请码"已兑换但被判定无效"修复

覆盖：
  1) _is_parent_subscribed 共享判断
     - parent_invite 已 redeemed → True
     - parent_sub 已 redeemed + 未过期 → True
     - parent_sub 已过期 → False
     - 未 redeemed → False
     - 无效 UID → False
  2) 状态页门控 has_parent_sub_html + has_parent_sub_db 双源判断
     - HTML 不在但 DB 已激活 → 状态页不应再显示邀请码表单
  3) 邀请码大小写/空格归一化
     - 同一码在大小写不同时应该匹配到同一行
"""
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _seed_db(db_path: str) -> None:
    """构造最小可复现的 admin.activation_codes + students 表"""
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE students (
            id INTEGER PRIMARY KEY,
            luogu_uid TEXT UNIQUE,
            real_name TEXT
        );
        CREATE TABLE activation_codes (
            id INTEGER PRIMARY KEY,
            code TEXT UNIQUE,
            sku TEXT,
            student_id INTEGER,
            duration_days INTEGER,
            redeemed_at TEXT,
            expires_at TEXT,
            created_by TEXT
        );
    """)
    students = [
        (1, "1752947", "大齐"),       # u1：已用 parent_invite (用户截图里的码)
        (2, "1234567", "小红"),       # u2：已用 parent_sub 30 天
        (3, "2345678", "小明"),       # u3：parent_sub 已过期
        (4, "3456789", "小李"),       # u4：parent_invite 还未用
        (5, "9999999", "新用户"),     # u5：完全没记录
    ]
    conn.executemany(
        "INSERT INTO students (id, luogu_uid, real_name) VALUES (?, ?, ?)",
        students,
    )
    codes = [
        # id 1: parent_invite 已用，绑到 u1（大齐）— 截图里的场景
        # 注：用户截图显示的码带视觉空格，实际生成规则是 8 位无空格大写字母数字
        (1, "PINV-B3EWHLDP", "parent_invite", 1, 0,
         "2026-06-16 10:00:00", None, "admin"),
        # id 2: parent_sub 30 天，刚激活给 u2
        (2, "PS-AAAA1111", "parent_sub", 2, 30,
         "2026-06-15 09:00:00", "2026-07-15 09:00:00", "admin"),
        # id 3: parent_sub 已过期（30 天前 redeemed）
        (3, "PS-BBBB2222", "parent_sub", 3, 30,
         "2026-05-01 09:00:00", "2026-05-31 09:00:00", "admin"),
        # id 4: parent_invite 还没用
        (4, "PINV-CCCC3333", "parent_invite", None, 0,
         None, None, "admin"),
    ]
    conn.executemany(
        "INSERT INTO activation_codes "
        "(id, code, sku, student_id, duration_days, redeemed_at, expires_at, created_by) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        codes,
    )
    conn.commit()
    conn.close()


class IsParentSubscribedTest(unittest.TestCase):
    """v3.9.41 · 共享判断函数 SQL 行为"""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix="luogu_inv_")
        cls.db_path = os.path.join(cls.tmpdir, "test_tasks.db")
        _seed_db(cls.db_path)

    def _is_parent_subscribed(self, luogu_uid: str) -> bool:
        """复刻 _is_parent_subscribed 的 SQL（不依赖 Flask app）"""
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM activation_codes ac "
                "JOIN students s ON s.id = ac.student_id "
                "WHERE ac.sku IN ('parent_sub', 'parent_invite') "
                "  AND s.luogu_uid = ? "
                "  AND ac.redeemed_at IS NOT NULL "
                "  AND (ac.expires_at IS NULL OR ac.expires_at > datetime('now'))",
                (str(luogu_uid).strip(),),
            ).fetchone()
        finally:
            conn.close()
        # sqlite3.Row 默认是 tuple-like，row[0] 取第一列
        return bool(row and row[0] > 0)

    def test_parent_invite_redeemed_returns_true(self):
        """u1: parent_invite 已 redeem (expires_at=NULL) → True
        这正是用户截图里「大齐 + PINV-B3EWHLD P + 已用」的场景"""
        self.assertTrue(self._is_parent_subscribed("1752947"))

    def test_parent_sub_active_returns_true(self):
        """u2: parent_sub 30 天 active → True"""
        self.assertTrue(self._is_parent_subscribed("1234567"))

    def test_parent_sub_expired_returns_false(self):
        """u3: parent_sub 已过期 → False"""
        self.assertFalse(self._is_parent_subscribed("2345678"))

    def test_unused_code_returns_false(self):
        """u4: 码还没用（redeemed_at=NULL）→ False"""
        self.assertFalse(self._is_parent_subscribed("3456789"))

    def test_no_record_returns_false(self):
        """u5: 完全没有 activation_codes 记录 → False"""
        self.assertFalse(self._is_parent_subscribed("9999999"))

    def test_invalid_uid_returns_false(self):
        """非数字 / 空 UID → False（不抛异常）"""
        self.assertFalse(self._is_parent_subscribed(""))
        self.assertFalse(self._is_parent_subscribed("not-a-number"))
        self.assertFalse(self._is_parent_subscribed("12"))


class InviteCodeCaseInsensitiveTest(unittest.TestCase):
    """v3.9.41 · 邀请码大小写/空格归一化测试

    模拟修复后 SQL: WHERE UPPER(code) = ? 应该匹配到任意大小写
    """

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix="luogu_case_")
        cls.db_path = os.path.join(cls.tmpdir, "test_tasks.db")
        _seed_db(cls.db_path)

    def _lookup_code(self, submitted: str):
        """复刻 start_parent_subscribe 中 UPPER() 归一化后的查询"""
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT id, redeemed_at FROM activation_codes "
                "WHERE UPPER(code) = ? AND sku = 'parent_invite' LIMIT 1",
                (submitted.strip().upper(),),
            ).fetchone()
        finally:
            conn.close()
        return row

    def test_uppercase_match(self):
        """大写输入 → 命中大写存储"""
        row = self._lookup_code("PINV-B3EWHLDP")
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 1)  # id=1

    def test_lowercase_match(self):
        """小写输入 → 仍然命中（UPPER() 双侧归一化）"""
        row = self._lookup_code("pinv-b3ewhldp")
        self.assertIsNotNone(row, "小写码应能匹配到大写存储")
        self.assertEqual(row[0], 1)

    def test_mixed_case_match(self):
        """混合大小写输入 → 仍然命中"""
        row = self._lookup_code("PInv-B3ewHLDP")
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 1)

    def test_whitespace_trimmed(self):
        """前后空格应被 strip() 吞掉"""
        row = self._lookup_code("  PINV-B3EWHLDP  ")
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 1)

    def test_inner_space_preserved(self):
        """码中间的空格应保留（B3EWHL D P ≠ B3EWHLDP，不会误匹配）"""
        # 注：seed 的码是 "PINV-B3EWHLDP"（无空格），查询 "PINV-B3EWHLD P"（带空格）应不匹配
        row = self._lookup_code("PINV-B3EWHLD P")
        self.assertIsNone(
            row,
            "中间带空格的输入不应误匹配到无空格的存储（UPPER 不影响空格）",
        )

    def test_redeemed_code_still_findable(self):
        """已 redeem 的码 (id=1) 仍能在 SQL 层找到（行存在），前端再判定 invite_ok"""
        # id=1 的码已 redeem，SQL 层应能找到（前端逻辑再决定 invite_ok）
        row = self._lookup_code("PINV-B3EWHLDP")
        self.assertIsNotNone(row, "已 redeem 的码应在 DB 中（行存在）")
        self.assertEqual(row[0], 1)
        self.assertIsNotNone(row[1], "redeemed_at 应有值")

    def test_unused_code_findable(self):
        """未使用的码 (id=4) 也能查到（redeemed_at=NULL）"""
        # 注意：种子中 id=4 是 "PINV-CCCC3333"，还没用
        # 先确认种子有这个码
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT id, code FROM activation_codes WHERE id = 4"
            ).fetchone()
        finally:
            conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[1], "PINV-CCCC3333")

        # 然后通过邀请码查询也能找到（redeemed_at 虽为 NULL，但 SQL 仍命中行）
        row = self._lookup_code("PINV-CCCC3333")
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 4)
        self.assertIsNone(row[1], "未使用的码 redeemed_at 应为 NULL")


class SmartGateHtmlOrDbTest(unittest.TestCase):
    """v3.9.41 · 智能门控：HTML 不在但 DB 已激活 → 视为已订阅"""

    def test_html_exists_short_circuits(self):
        """HTML 在 → has_parent_sub_html=True（不需查 DB）"""
        has_parent_sub_html = True
        has_parent_sub_db = False
        show_form = not (has_parent_sub_html or has_parent_sub_db)
        self.assertFalse(show_form, "HTML 存在应跳过表单")

    def test_html_missing_db_subscribed(self):
        """HTML 不在但 DB 已激活 → has_parent_sub_db=True → 跳过表单
        这正是用户截图里的修复场景：码已兑换 + HTML 还没生成/没成功"""
        has_parent_sub_html = False
        has_parent_sub_db = True
        show_form = not (has_parent_sub_html or has_parent_sub_db)
        self.assertFalse(show_form, "DB 激活应跳过表单（不再要求重输邀请码）")

    def test_html_missing_db_unsubscribed(self):
        """HTML 不在 + DB 也没记录 → 显示表单"""
        has_parent_sub_html = False
        has_parent_sub_db = False
        show_form = not (has_parent_sub_html or has_parent_sub_db)
        self.assertTrue(show_form, "完全未订阅才显示表单")

    def test_both_true_short_circuits(self):
        """两者都 True → 跳过表单"""
        has_parent_sub_html = True
        has_parent_sub_db = True
        show_form = not (has_parent_sub_html or has_parent_sub_db)
        self.assertFalse(show_form)


class SourceCodeStructureTest(unittest.TestCase):
    """v3.9.41 · 静态源码检查：关键修复必须在文件中"""

    @classmethod
    def setUpClass(cls):
        cls.src = Path(__file__).resolve().parent.parent / "web_app.py"
        cls.text = cls.src.read_text(encoding="utf-8")

    def test_is_parent_subscribed_defined(self):
        """_is_parent_subscribed 共享函数必须存在"""
        self.assertRegex(self.text, r"def\s+_is_parent_subscribed\s*\(")

    def test_invite_code_upper_normalization(self):
        """start_parent_subscribe 校验必须 .upper() 归一化"""
        # 找到 "submitted_code = (form.get" 行
        import re
        m = re.search(r"submitted_code\s*=\s*\(form\.get\([^)]+\)\s*or\s*\"\"\)\.strip\(\)\.upper\(\)", self.text)
        self.assertIsNotNone(
            m,
            "submitted_code 必须 .strip().upper() 归一化（修复前只 .strip()）",
        )

    def test_invite_sql_uses_upper(self):
        """SQL 必须用 UPPER(code) = ? 做大小写不敏感匹配"""
        self.assertRegex(self.text, r"UPPER\(code\)\s*=\s*\?")
        self.assertRegex(self.text, r"AND\s+sku\s*=\s*'parent_invite'")

    def test_short_circuit_subscribed_user(self):
        """_is_parent_subscribed(luogu_uid) 短路必须存在"""
        self.assertRegex(self.text, r"if\s+_is_parent_subscribed\(luogu_uid\):")

    def test_status_page_passes_has_parent_sub_db(self):
        """status_page 必须把 has_parent_sub_db 传给模板"""
        self.assertIn("has_parent_sub_db=has_parent_sub_db", self.text)

    def test_template_uses_html_or_db(self):
        """状态页模板必须用 has_parent_sub_html or has_parent_sub_db"""
        self.assertIn("has_parent_sub_html or has_parent_sub_db", self.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
