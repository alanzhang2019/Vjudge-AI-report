"""
v3.9.74 · AtCoder 卡片移除 + VJudge 卡片兜底 smoke test
- 验证 AtCoder 卡片相关元素已从模板移除
- 验证 atcoder_ctx 缺失时模板不崩(走 VJudge unlinked 兜底)
"""

import unittest
import tempfile
import os
from pathlib import Path

_TMP_DIR = tempfile.mkdtemp(prefix="atcoder_card_rm_")
os.environ["TASK_DB_PATH"] = os.path.join(_TMP_DIR, "tasks.db")

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import task_store
task_store.DB_PATH = Path(os.environ["TASK_DB_PATH"])
task_store.init_db()
task_store.init_vjudge_tables()

import web_app
app = web_app.app
app.config["TESTING"] = True
STUDENT_ME_HTML = web_app.STUDENT_ME_HTML


def _render(atcoder_ctx=None, vjudge_ctx=None) -> str:
    """渲染学生主页模板(AtCoder 应已无卡片)。"""
    from flask import render_template_string
    return render_template_string(
        STUDENT_ME_HTML,
        student={"real_name": "Alice", "luogu_uid": "123456",
                 "province": "北京", "city": "北京", "gender": "M", "grade": "G6",
                 "grade_label": "高一", "registered_via": "manual"},
        token="123456",
        progress={}, has_parent_sub=False,
        award_summary={}, csp_award_types=[], csp_award_levels=[],
        csp_award_types_dict={}, csp_award_levels_dict={},
        commerce_hidden=False,
        achievements={"six_dim": {}, "mistakes": []},
        mistake_count=0, report_htmls=[], my_rank={},
        latest_noi_csp_card={"exists": False, "type": "noi_csp"},
        latest_gesp_card={"exists": False, "type": "gesp"},
        latest_parent_subscribe_card={"exists": False, "type": "parent_subscribe"},
        primary_exam_type="noi_csp",
        primary_exam_type_for_share="noi_csp",
        vjudge_ctx=vjudge_ctx if vjudge_ctx is not None else {"link_status": "unlinked"},
    )


class AtcoderCardRemoved(unittest.TestCase):
    """v3.9.74 · AtCoder 卡片已被 VJudge 取代,这里验"已移除"。"""

    def setUp(self):
        self.app_ctx = app.app_context()
        self.app_ctx.push()
        self.req_ctx = app.test_request_context("/me/123456")
        self.req_ctx.push()

    def tearDown(self):
        self.req_ctx.pop()
        self.app_ctx.pop()

    def test_no_atcoder_card_id(self):
        html = _render()
        # 旧 atcoder 卡片 ID/标题/动作/字段全没了
        self.assertNotIn('id="atcoderCard"', html)
        self.assertNotIn("/link-atcoder", html)
        self.assertNotIn("/unlink-atcoder", html)
        self.assertNotIn("/refresh-atcoder", html)
        self.assertNotIn('name="handle"', html)
        self.assertNotIn("atcoder_ctx", html)

    def test_no_atcoder_specific_captions(self):
        html = _render()
        # 这些是 AtCoder 卡片专属文案
        self.assertNotIn("历史最高", html)
        self.assertNotIn("参赛场数", html)
        self.assertNotIn("已 AC 题数", html)
        self.assertNotIn("红色 / 蓝色 / 青色", html)
        self.assertNotIn("/api/atcoder/", html)

    def test_vjudge_card_present(self):
        html = _render()
        # VJudge 卡片元素
        for marker in ['id="vjudgeCard"', "VJudge username",
                       'action="/link-vjudge"', "绑定并抓取", "VJudge 跨平台数据"]:
            if marker not in html:
                self.fail(f"marker {marker!r} not in HTML (len={len(html)})")
        # 全过
        self.assertIn("VJudge", html)

    def test_vjudge_polling_in_pending_state(self):
        # 验证 pending 状态才有 /api/vjudge/ 轮询
        html = _render(vjudge_ctx={"link_status": "pending", "username": "alice"})
        self.assertIn("/api/vjudge/", html)
        self.assertIn("_poll()", html)

    def test_no_atcoder_ctx_arg_renders_ok(self):
        """v3.9.74 · 模板不应该再依赖 atcoder_ctx,缺它也能渲染(走 VJudge 兜底)。"""
        html = _render()
        self.assertIn('id="vjudgeCard"', html)
        self.assertIn("VJudge username", html)

    def test_vjudge_unlinked_no_crash(self):
        html = _render(vjudge_ctx={"link_status": "unlinked"})
        self.assertIn("VJudge username", html)
        self.assertIn("绑定并抓取", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
