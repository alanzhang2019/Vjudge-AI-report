import unittest
from pathlib import Path


class TestWebAppTemplate(unittest.TestCase):
    def test_index_template_includes_c3vk_cookie_field_and_instructions(self):
        root = Path(__file__).resolve().parents[1]
        content = (root / "web_app.py").read_text(encoding="utf-8")

        self.assertIn("C3VK", content)
        self.assertIn("https://www.luogu.com.cn", content)
        self.assertIn("Application(应用)", content)
        self.assertIn("Storage", content)
        self.assertIn("Cookies", content)
        self.assertIn("Name/Value", content)

