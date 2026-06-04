import unittest
import importlib
import sys
import types
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


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
        self.assertIn('name="c3vk"', content)
        self.assertIn('name="c3vk" value="{{ form_values.c3vk }}" required', content)
        self.assertNotIn("C3VK（如有）", content)
        self.assertIn('formaction="/validate-cookies"', content)
        self.assertIn("校验 Cookies", content)

    def test_report_template_includes_detail_fetch_overview_cards(self):
        root = Path(__file__).resolve().parents[1]
        content = (root / "report_template.html").read_text(encoding="utf-8")

        self.assertIn("提交详情抓取概览", content)
        self.assertIn("detail_fetch_overview | default", content)
        self.assertIn("df.status_label", content)
        self.assertIn("df.source_code_success", content)
        self.assertIn("df.blocker_reason", content)

    def test_report_template_renders_without_detail_fetch_overview(self):
        root = Path(__file__).resolve().parents[1]
        env = Environment(loader=FileSystemLoader(str(root)))
        template = env.get_template("report_template.html")

        rendered = template.render(
            export_data={
                "student_info": {"name": "测试", "eval_time": "2026-06-03 12:00", "school": "学校", "grade": "年级"},
                "solved_count": 1,
                "failed_count": 0,
            },
            report_html="<h1>测试报告</h1>",
            chart_paths={},
            avg_difficulty="2.0",
            avg_difficulty_label="普及-",
            avg_difficulty_color="#52C41A",
            avg_difficulty_text_color="#FFFFFF",
            top_tag="贪心",
        )

        self.assertIn("提交详情抓取概览", rendered)
        self.assertIn("未抓取详情", rendered)
        self.assertIn("阻断原因", rendered)

    def test_web_app_formats_practice_auth_error_as_cookie_hint(self):
        root = Path(__file__).resolve().parents[1]
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))

        flask = types.ModuleType("flask")

        class DummyFlask:
            def __init__(self, *args, **kwargs):
                pass

            def route(self, *args, **kwargs):
                def deco(fn):
                    return fn
                return deco

        flask.Flask = DummyFlask
        flask.render_template_string = lambda *args, **kwargs: ""
        flask.request = types.SimpleNamespace(form={})
        flask.redirect = lambda value: value
        flask.url_for = lambda *args, **kwargs: ""
        flask.send_from_directory = lambda *args, **kwargs: ""

        original_flask = sys.modules.get("flask")
        original_web_app = sys.modules.pop("web_app", None)
        sys.modules["flask"] = flask
        try:
            web_app = importlib.import_module("web_app")
            from pyLuogu.errors import AuthenticationError

            message = web_app.describe_generation_error(AuthenticationError("Need Login"), "获取标签与练习数据")
            self.assertIn("Cookies 无效或已失效", message)
            self.assertIn("无法读取练习数据", message)
        finally:
            sys.modules.pop("web_app", None)
            if original_web_app is not None:
                sys.modules["web_app"] = original_web_app
            if original_flask is not None:
                sys.modules["flask"] = original_flask
            else:
                sys.modules.pop("flask", None)

    def test_web_app_rejects_missing_required_cookie_fields(self):
        root = Path(__file__).resolve().parents[1]
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))

        flask = types.ModuleType("flask")

        class DummyFlask:
            def __init__(self, *args, **kwargs):
                pass

            def route(self, *args, **kwargs):
                def deco(fn):
                    return fn
                return deco

        flask.Flask = DummyFlask
        flask.render_template_string = lambda *args, **kwargs: ""
        flask.request = types.SimpleNamespace(form={})
        flask.redirect = lambda value: value
        flask.url_for = lambda *args, **kwargs: ""
        flask.send_from_directory = lambda *args, **kwargs: ""

        original_flask = sys.modules.get("flask")
        original_web_app = sys.modules.pop("web_app", None)
        sys.modules["flask"] = flask
        try:
            web_app = importlib.import_module("web_app")

            with self.assertRaises(ValueError) as cm:
                web_app.build_cookie_dict({"client_id": "abc", "uid": "123", "c3vk": ""})

            self.assertIn("Cookies 参数为必填项", str(cm.exception))
            self.assertIn("C3VK", str(cm.exception))
        finally:
            sys.modules.pop("web_app", None)
            if original_web_app is not None:
                sys.modules["web_app"] = original_web_app
            if original_flask is not None:
                sys.modules["flask"] = original_flask
            else:
                sys.modules.pop("flask", None)

    def test_validate_cookies_reports_record_list_failure_clearly(self):
        root = Path(__file__).resolve().parents[1]
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))

        flask = types.ModuleType("flask")

        class DummyFlask:
            def __init__(self, *args, **kwargs):
                pass

            def route(self, *args, **kwargs):
                def deco(fn):
                    return fn
                return deco

        flask.Flask = DummyFlask
        flask.render_template_string = lambda *args, **kwargs: ""
        flask.request = types.SimpleNamespace(form={})
        flask.redirect = lambda value: value
        flask.url_for = lambda *args, **kwargs: ""
        flask.send_from_directory = lambda *args, **kwargs: ""

        original_flask = sys.modules.get("flask")
        original_web_app = sys.modules.pop("web_app", None)
        sys.modules["flask"] = flask
        try:
            web_app = importlib.import_module("web_app")
            from pyLuogu.errors import AuthenticationError

            class FakeMe:
                uid = 123

            class FakeAPI:
                def __init__(self, cookies=None):
                    self.cookies = cookies

                def me(self):
                    return FakeMe()

                def get_user_practice(self, uid):
                    return {"passedProblems": [], "submittedProblems": []}

                def get_record_list(self, **kwargs):
                    raise AuthenticationError("Need Login")

                def close(self):
                    return None

            web_app.pyLuogu.luoguAPI = FakeAPI
            result = web_app.validate_cookies({"client_id": "abc", "uid": "123", "c3vk": "xyz"})

            self.assertFalse(result["ok"])
            self.assertIn("无法读取提交记录", result["message"])
        finally:
            sys.modules.pop("web_app", None)
            if original_web_app is not None:
                sys.modules["web_app"] = original_web_app
            if original_flask is not None:
                sys.modules["flask"] = original_flask
            else:
                sys.modules.pop("flask", None)

    def test_validate_cookies_reports_success_summary(self):
        root = Path(__file__).resolve().parents[1]
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))

        flask = types.ModuleType("flask")

        class DummyFlask:
            def __init__(self, *args, **kwargs):
                pass

            def route(self, *args, **kwargs):
                def deco(fn):
                    return fn
                return deco

        flask.Flask = DummyFlask
        flask.render_template_string = lambda *args, **kwargs: ""
        flask.request = types.SimpleNamespace(form={})
        flask.redirect = lambda value: value
        flask.url_for = lambda *args, **kwargs: ""
        flask.send_from_directory = lambda *args, **kwargs: ""

        original_flask = sys.modules.get("flask")
        original_web_app = sys.modules.pop("web_app", None)
        sys.modules["flask"] = flask
        try:
            web_app = importlib.import_module("web_app")

            class FakeProblem:
                def __init__(self, pid, difficulty=1):
                    self.pid = pid
                    self.difficulty = difficulty

                def to_json(self):
                    return {"pid": self.pid, "difficulty": self.difficulty}

            class FakePractice:
                def __init__(self):
                    self.passedProblems = [FakeProblem("P1000")]
                    self.submittedProblems = [FakeProblem("P1001")]

            class FakeRecordList:
                records = [object(), object()]

            class FakeMe:
                uid = 123

            class FakeAPI:
                def __init__(self, cookies=None):
                    self.cookies = cookies

                def me(self):
                    return FakeMe()

                def get_user_practice(self, uid):
                    return FakePractice()

                def get_record_list(self, **kwargs):
                    return FakeRecordList()

                def close(self):
                    return None

            web_app.pyLuogu.luoguAPI = FakeAPI
            result = web_app.validate_cookies({"client_id": "abc", "uid": "123", "c3vk": "xyz"})

            self.assertTrue(result["ok"])
            self.assertIn("Cookies 校验通过", result["title"])
            self.assertIn("record/list", result["message"])
        finally:
            sys.modules.pop("web_app", None)
            if original_web_app is not None:
                sys.modules["web_app"] = original_web_app
            if original_flask is not None:
                sys.modules["flask"] = original_flask
            else:
                sys.modules.pop("flask", None)
