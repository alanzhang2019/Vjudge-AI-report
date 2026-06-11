import unittest
from web_app import _init_report_hides_table, _get_conn


class TestReportHidesSchema(unittest.TestCase):
    def test_idempotent_create(self):
        _init_report_hides_table()
        # 再次调用不抛
        _init_report_hides_table()
        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='report_hides'"
            ).fetchone()
            self.assertIsNotNone(row)
            cols = [r["name"] for r in conn.execute("PRAGMA table_info(report_hides)").fetchall()]
            self.assertIn("task_id", cols)
            self.assertIn("hide_pdf", cols)
            self.assertIn("hide_html", cols)
            self.assertIn("ref_uid", cols)
        finally:
            conn.close()
