"""
v3.9.74 · VJudge 卡片模板渲染 smoke test
不依赖网络/真实学生,只验模板能跑通 + 6 种状态都正确切换。
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_TMP_DIR = tempfile.mkdtemp(prefix="vj_card_")
os.environ["TASK_DB_PATH"] = os.path.join(_TMP_DIR, "tasks.db")

import task_store
task_store.DB_PATH = Path(os.environ["TASK_DB_PATH"])
task_store.init_db()
task_store.init_vjudge_tables()

import web_app
app = web_app.app
app.config["TESTING"] = True
STUDENT_ME_HTML = web_app.STUDENT_ME_HTML


def _render(ctx: dict) -> str:
    from flask import render_template_string
    return render_template_string(
        STUDENT_ME_HTML,
        student={"real_name": "Alice", "luogu_uid": ctx.get("luogu_uid", "123456"),
                 "province": "北京", "city": "北京", "gender": "M", "grade": "G6",
                 "grade_label": "高一", "registered_via": "manual"},
        token=ctx.get("luogu_uid", "123456"),
        progress={},
        has_parent_sub=False,
        award_summary={},
        csp_award_types=[],
        csp_award_levels=[],
        csp_award_types_dict={},
        csp_award_levels_dict={},
        commerce_hidden=False,
        achievements={"six_dim": {}, "mistakes": []},
        mistake_count=0,
        report_htmls=[],
        my_rank={},
        latest_noi_csp_card={"exists": False, "type": "noi_csp"},
        latest_gesp_card={"exists": False, "type": "gesp"},
        latest_parent_subscribe_card={"exists": False, "type": "parent_subscribe"},
        primary_exam_type="noi_csp",
        primary_exam_type_for_share="noi_csp",
        vjudge_ctx=ctx,
    )


class VjudgeCardRender(unittest.TestCase):

    def setUp(self):
        self.app_ctx = app.app_context()
        self.app_ctx.push()
        self.req_ctx = app.test_request_context("/me/123456")
        self.req_ctx.push()

    def tearDown(self):
        self.req_ctx.pop()
        self.app_ctx.pop()

    def test_unlinked_renders_form(self):
        html = _render({
            "username": "", "nick": "",
            "total_submissions": 0, "total_ac": 0, "solved_count": 0,
            "link_status": "unlinked", "oj_stats": [], "recent_solved": [],
        })
        self.assertIn("绑定并抓取", html)
        self.assertIn('name="username"', html)
        self.assertIn('action="/link-vjudge"', html)

    def test_pending_renders_spinner(self):
        html = _render({
            "username": "alice_2024", "nick": "",
            "total_submissions": 0, "total_ac": 0, "solved_count": 0,
            "link_status": "pending", "oj_stats": [], "recent_solved": [],
        })
        self.assertIn("animate-spin", html)
        self.assertIn("正在抓取", html)
        self.assertIn("alice_2024", html)
        self.assertIn("_poll()", html)
        self.assertIn("/api/vjudge/", html)

    def test_ok_renders_metrics_and_oj(self):
        html = _render({
            "username": "alice_2024", "nick": "Alice 2024",
            "total_submissions": 500, "total_ac": 430, "total_wa": 50,
            "total_tle": 10, "total_re": 5, "total_ce": 5,
            "ac_rate": 0.86, "solved_count": 200,
            "link_status": "ok", "last_fetched_at": "2024-06-15T21:30:00",
            "oj_stats": [
                {"oj": "Codeforces", "count": 100},
                {"oj": "AtCoder", "count": 80},
                {"oj": "Luogu", "count": 20},
            ],
            "recent_solved": [
                {"oj": "Codeforces", "problem_id": "1234A", "title": "Equalize",
                 "ac_time": "2024-06-01T10:00:00"},
            ],
        })
        # 头部
        self.assertIn("alice_2024", html)
        self.assertIn("Alice 2024", html)
        # 4 列指标
        self.assertIn("AC 总数", html)
        self.assertIn("AC 率", html)
        self.assertIn("总提交", html)
        self.assertIn("WA 数", html)
        self.assertIn("430", html)
        self.assertIn("500", html)
        self.assertIn("50", html)
        self.assertIn("86%", html)  # 0.86 → 86%
        # 解决数大数字
        self.assertIn("200", html)
        # OJ 分布
        self.assertIn("Codeforces", html)
        self.assertIn("AtCoder", html)
        self.assertIn("Luogu", html)
        self.assertIn("来源 OJ 分布", html)
        # 最近 AC(默认折叠)
        self.assertIn("最近 5 个已解决题", html)
        # 状态徽章
        self.assertIn("已同步", html)
        # 时间
        self.assertIn("2024-06-15 21:30:00", html)
        # 按钮
        self.assertIn("🔄 刷新", html)
        self.assertIn("/refresh-vjudge", html)
        self.assertIn("🗑 解绑", html)
        self.assertIn("/unlink-vjudge", html)
        # 没有轮询脚本
        self.assertNotIn("_poll()", html)

    def test_stale_shows_warning(self):
        html = _render({
            "username": "alice_2024", "nick": "",
            "total_submissions": 0, "total_ac": 0, "solved_count": 0,
            "link_status": "stale", "last_fetched_at": "2024-01-01T00:00:00",
            "oj_stats": [], "recent_solved": [],
        })
        self.assertIn("数据陈旧", html)
        self.assertIn("7 天", html)

    def test_failed_shows_error(self):
        html = _render({
            "username": "alice_2024", "nick": "",
            "total_submissions": 0, "total_ac": 0, "solved_count": 0,
            "link_status": "failed", "fetch_error": "VJudge 404",
            "oj_stats": [], "recent_solved": [],
        })
        self.assertIn("抓取失败", html)
        self.assertIn("VJudge 404", html)

    def test_rate_limited_shows_warning(self):
        html = _render({
            "username": "alice_2024", "nick": "",
            "total_submissions": 0, "total_ac": 0, "solved_count": 0,
            "link_status": "rate_limited", "last_fetched_at": "2024-01-10T00:00:00",
            "oj_stats": [], "recent_solved": [],
        })
        self.assertIn("被限流", html)
        self.assertIn("冷却后自动重试", html)

    def test_empty_ctx_fallback(self):
        from flask import render_template_string
        html = render_template_string(
            STUDENT_ME_HTML,
            student={"real_name": "x", "luogu_uid": "1"},
            token="1",
            progress={}, has_parent_sub=False,
            award_summary={}, csp_award_types=[], csp_award_levels=[],
            csp_award_types_dict={}, csp_award_levels_dict={},
            commerce_hidden=False,
            achievements={"six_dim": {}, "mistakes": []},
            mistake_count=0, report_htmls=[], my_rank={},
            latest_noi_csp_card={"exists": False},
            latest_gesp_card={"exists": False},
            latest_parent_subscribe_card={"exists": False},
            primary_exam_type="noi_csp",
            primary_exam_type_for_share="noi_csp",
            vjudge_ctx={"link_status": "unlinked"},
        )
        self.assertIn("绑定并抓取", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
