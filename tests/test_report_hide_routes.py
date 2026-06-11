import unittest
from web_app import app


class TestServeReportVisibility(unittest.TestCase):
    def setUp(self):
        self.c = app.test_client()

    def test_pdf_returns_403_when_hidden(self):
        from web_app import _init_report_hides_table, _record_hide_pdf
        _init_report_hides_table()
        _record_hide_pdf("test_task_hide_001")
        r = self.c.get("/reports/test_task_hide_001/report.pdf")
        self.assertEqual(r.status_code, 403)
        body = r.data.decode("utf-8", errors="replace")
        self.assertIn("PDF", body)

    def test_html_returns_200_when_pdf_hidden(self):
        from web_app import _init_report_hides_table, _record_hide_pdf
        _init_report_hides_table()
        _record_hide_pdf("test_task_hide_002")
        r = self.c.get("/reports/test_task_hide_002/report.html")
        self.assertNotEqual(r.status_code, 403)
