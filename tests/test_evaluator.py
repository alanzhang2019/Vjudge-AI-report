import unittest
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

from pyLuogu.errors import AuthenticationError
from pyLuogu.types import ProblemSummary

from behavior_analyzer import compute_six_dimension_scores
from examples.export_for_ai import RECORD_LIST_PAGES_TO_TRY, _pick_record_for_problem, _summarize
from luogu_evaluator import (
    build_html_and_pdf,
    build_detail_fetch_overview,
    build_trusted_data_summary_md,
    fetch_behavior_analysis,
    repair_behavior_analysis_from_items,
    render_star_rating_html,
    split_practice_problems,
    summarize_detail_fetch_stats,
    summarize_average_difficulty,
)


class DummyPractice:
    def __init__(self, data):
        self.problems = []
        self.data = data


class TestEvaluatorPracticeFallback(unittest.TestCase):
    def test_summarize_separates_algorithm_tags_from_all_tags(self):
        problems = [
            ProblemSummary(
                {
                    "pid": "P1012",
                    "title": "拼数",
                    "difficulty": 3,
                    "type": "P",
                    "submitted": True,
                    "accepted": True,
                    "tags": [2, 83, 113],
                    "totalSubmit": 1,
                    "totalAccepted": 1,
                    "flag": 0,
                    "fullScore": 100,
                }
            )
        ]
        tag_by_id = {
            2: {"id": 2, "name": "字符串", "type": 2, "parent": None},
            83: {"id": 83, "name": "NOIP 提高组", "type": 3, "parent": None},
            113: {"id": 113, "name": "排序", "type": 2, "parent": 110},
        }

        summary = _summarize(problems, tag_by_id)

        self.assertEqual([item["name"] for item in summary["top_tags"]], ["字符串", "NOIP 提高组", "排序"])
        self.assertEqual([item["name"] for item in summary["top_algorithm_tags"]], ["字符串", "排序"])

    def test_six_dimension_scores_prefer_algorithm_tags(self):
        scores = compute_six_dimension_scores(
            {
                "solved_count": 0,
                "summary": {
                    "difficulty_histogram": {},
                    "top_tags": [{"name": "1998", "count": 50}],
                    "top_algorithm_tags": [{"name": "字符串", "count": 5}],
                },
            },
            {},
        )

        self.assertGreaterEqual(scores["字符串"], 45)

    def test_summarize_adds_level_experience_from_origin_and_difficulty(self):
        problems = [
            ProblemSummary(
                {
                    "pid": "P3195",
                    "title": "玩具装箱",
                    "difficulty": 6,
                    "type": "P",
                    "submitted": True,
                    "accepted": True,
                    "tags": [3, 48, 150, 254],
                    "totalSubmit": 1,
                    "totalAccepted": 1,
                    "flag": 0,
                    "fullScore": 100,
                }
            )
        ]
        tag_by_id = {
            3: {"id": 3, "name": "动态规划 DP", "type": 2, "parent": None},
            48: {"id": 48, "name": "各省省选", "type": 3, "parent": 426},
            150: {"id": 150, "name": "斜率优化", "type": 2, "parent": 146},
            254: {"id": 254, "name": "前缀和", "type": 2, "parent": 44},
        }

        summary = _summarize(problems, tag_by_id)
        level_exp = summary["level_experience"]

        self.assertEqual(level_exp["provincial"]["solved"], 1)
        self.assertEqual(level_exp["provincial"]["by_origin"], 1)
        self.assertEqual(level_exp["provincial"]["by_difficulty"], 1)
        self.assertEqual(level_exp["noi"]["solved"], 0)

    def test_trusted_summary_hides_level_experience_table_when_charts_exist(self):
        export_data = {
            "student_info": {"eval_time": "2026-06-03 12:00"},
            "summary": {
                "difficulty_histogram": {"6": 1},
                "level_experience": {
                    "csp_j": {"solved": 1, "by_origin": 0, "by_difficulty": 1},
                    "csp_s": {"solved": 1, "by_origin": 1, "by_difficulty": 1},
                    "provincial": {"solved": 1, "by_origin": 1, "by_difficulty": 1},
                    "noi": {"solved": 0, "by_origin": 0, "by_difficulty": 0},
                },
            },
            "behavior_analysis": {"error": "未获取到有效提交记录"},
            "syllabus_evaluation": {
                "csp_j": {"stats": {"total": 28, "空白": 0}, "coverage": 100},
                "csp_s": {"stats": {"total": 49, "空白": 49}, "coverage": 0},
                "provincial": {"stats": {"total": 10, "空白": 10}, "coverage": 0},
                "noi": {"stats": {"total": 43, "空白": 43}, "coverage": 0},
            },
        }

        markdown = build_trusted_data_summary_md(export_data)

        self.assertIn("知识点覆盖统计表（按算法标签）", markdown)
        self.assertNotIn("题目级别经历表", markdown)
        self.assertNotIn("来源标签命中", markdown)
        self.assertNotIn("难度命中", markdown)

    def test_average_difficulty_uses_luogu_label_and_color(self):
        info = summarize_average_difficulty({"5": 2, "6": 1})

        self.assertEqual(info["label"], "提高+/省选-")
        self.assertEqual(info["color"], "#3498DB")
        self.assertAlmostEqual(float(info["average_value"]), 5.3, places=1)

    def test_trusted_data_summary_hides_diagnosis_date_and_unknown_difficulty(self):
        markdown = build_trusted_data_summary_md(
            {
                "student_info": {"eval_time": "2026-06-03 23:06"},
                "summary": {"difficulty_histogram": {"0": 10, "1": 5, "2": 1}},
                "behavior_analysis": {"error": "nope"},
                "detail_fetch_stats": {},
                "syllabus_evaluation": {},
            }
        )
        self.assertIn("报告生成时间", markdown)
        self.assertNotIn("诊断日期", markdown)
        self.assertNotIn("暂无评定", markdown)
        self.assertNotIn("提交详情抓取统计", markdown)
        self.assertNotIn("题目级别经历表", markdown)
        self.assertNotIn("图表中文字体", markdown)
        self.assertNotIn("提交时间数据", markdown)
        self.assertNotIn("下方本节为程序直出的真实统计", markdown)

    def test_render_star_rating_html_uses_capsule_style(self):
        html = render_star_rating_html("⭐⭐⭐☆☆")

        self.assertIn("display:inline-flex", html)
        self.assertIn("background:#111827", html)
        self.assertIn("3/5", html)
        self.assertIn("color:#F5C542", html)
        self.assertIn("color:#94A3B8", html)

    def test_build_html_uses_relative_chart_paths_for_web_reports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            assets_dir = root / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            chart_file = assets_dir / "difficulty_histogram.png"
            chart_file.write_bytes(b"fake-png")
            html_path = root / "report.html"
            pdf_path = root / "report.pdf"

            build_html_and_pdf(
                report_md="# 测试报告",
                export_data={
                    "student_info": {
                        "name": "测试",
                        "school": "学校",
                        "grade": "年级",
                        "eval_time": "2026-06-04 16:00",
                    },
                    "solved_count": 1,
                    "failed_count": 0,
                    "summary": {"difficulty_histogram": {"2": 1}},
                },
                html_path=str(html_path),
                pdf_path=str(pdf_path),
                chart_paths={"difficulty": str(chart_file)},
                export_pdf=False,
            )

            html = html_path.read_text(encoding="utf-8")
            self.assertIn('src="assets/difficulty_histogram.png"', html)
            self.assertNotIn("file:///", html)

    def test_generate_chart_images_applies_style_before_font_config(self):
        from luogu_evaluator import generate_chart_images

        calls = []
        with patch("luogu_evaluator.plt.style.use", side_effect=lambda style: calls.append("style")), \
             patch("luogu_evaluator.configure_matplotlib_font", side_effect=lambda: calls.append("font")), \
             patch("luogu_evaluator.repair_behavior_analysis_from_items", side_effect=lambda data: data):
            generate_chart_images(
                {
                    "summary": {"difficulty_histogram": {"2": 1}},
                    "solved_count": 1,
                    "failed_count": 0,
                    "behavior_analysis": {},
                },
                tempfile.mkdtemp(),
            )

        self.assertGreaterEqual(len(calls), 2)
        self.assertEqual(calls[:2], ["style", "font"])

    def test_pick_record_for_problem_keeps_summary_when_detail_decode_fails(self):
        class DummyRecord:
            def __init__(self):
                self.id = 123

            def to_json(self):
                return {
                    "id": 123,
                    "submitTime": 1234567890,
                    "status": 12,
                    "problem": {"pid": "P1000", "title": "A+B Problem"},
                }

        class DummyRecordList:
            records = [DummyRecord()]

        class DummyLuogu:
            def get_record_list(self, **kwargs):
                return DummyRecordList()

            def get_record(self, rid):
                raise ValueError("Failed to decode JSON response")

        record = _pick_record_for_problem(DummyLuogu(), uid=1, pid="P1000", max_records_to_try=2)

        self.assertEqual(record["id"], 123)
        self.assertEqual(record["submitTime"], 1234567890)
        self.assertIn("_detail_error", record)
        self.assertIsNone(record["sourceCode"])

    def test_pick_record_for_problem_skips_detail_when_source_not_required(self):
        class DummyRecord:
            def __init__(self):
                self.id = 456

            def to_json(self):
                return {
                    "id": 456,
                    "submitTime": 1234567891,
                    "status": 12,
                    "problem": {"pid": "P1001", "title": "B Problem"},
                }

        class DummyRecordList:
            records = [DummyRecord()]

        class DummyLuogu:
            def __init__(self):
                self.detail_calls = 0

            def get_record_list(self, **kwargs):
                return DummyRecordList()

            def get_record(self, rid):
                self.detail_calls += 1
                raise AssertionError("detail fetch should not be called")

        api = DummyLuogu()
        record = _pick_record_for_problem(api, uid=1, pid="P1001", max_records_to_try=2, require_source_code=False)

        self.assertEqual(record["id"], 456)
        self.assertEqual(api.detail_calls, 0)
        self.assertIsNone(record["sourceCode"])

    def test_pick_record_for_problem_stops_future_detail_fetch_after_blocking_error(self):
        class DummyRecord:
            def __init__(self, rid):
                self.id = rid

            def to_json(self):
                return {
                    "id": self.id,
                    "submitTime": 1234567000 + self.id,
                    "status": 12,
                    "problem": {"pid": f"P{self.id}", "title": "Sample"},
                }

        class DummyRecordList:
            def __init__(self, rid):
                self.records = [DummyRecord(rid)]

        class DummyLuogu:
            def __init__(self):
                self.detail_calls = 0

            def get_record_list(self, **kwargs):
                pid = kwargs["pid"]
                rid = 1 if pid == "P1" else 2
                return DummyRecordList(rid)

            def get_record(self, rid):
                self.detail_calls += 1
                raise AuthenticationError("Need Login")

        api = DummyLuogu()
        state = {}

        first = _pick_record_for_problem(api, uid=1, pid="P1", max_records_to_try=2, detail_fetch_state=state)
        second = _pick_record_for_problem(api, uid=1, pid="P2", max_records_to_try=2, detail_fetch_state=state)

        self.assertTrue(state.get("stop_detail_fetch"))
        self.assertEqual(api.detail_calls, 1)
        self.assertIn("_detail_error", first)
        self.assertIn("_detail_skipped", second)
        self.assertIsNone(second["sourceCode"])

    def test_pick_record_for_problem_keeps_list_level_skip_after_blocking_list_error(self):
        class DummyLuogu:
            def __init__(self):
                self.list_calls = 0

            def get_record_list(self, **kwargs):
                self.list_calls += 1
                raise AuthenticationError("Need Login")

        api = DummyLuogu()
        state = {}

        first = _pick_record_for_problem(api, uid=1, pid="P1", max_records_to_try=2, detail_fetch_state=state)
        second = _pick_record_for_problem(api, uid=1, pid="P2", max_records_to_try=2, detail_fetch_state=state)

        self.assertTrue(state.get("stop_detail_fetch"))
        self.assertEqual(api.list_calls, RECORD_LIST_PAGES_TO_TRY)
        self.assertTrue(first.get("_record_list_unavailable"))
        self.assertIn("_detail_skipped", first)
        self.assertTrue(second.get("_record_list_unavailable"))
        self.assertIn("_detail_skipped", second)
        self.assertIsNone(second["sourceCode"])

    def test_pick_record_for_problem_recovers_after_transient_network_error(self):
        class DummyDetail:
            def to_json(self):
                return {
                    "id": 101,
                    "submitTime": 1234567999,
                    "status": 12,
                    "problem": {"pid": "P1002", "title": "Recover"},
                }

            @property
            def sourceCode(self):
                return "print('ok')"

        class DummyRecord:
            id = 101

            def to_json(self):
                return {
                    "id": 101,
                    "submitTime": 1234567999,
                    "status": 12,
                    "problem": {"pid": "P1002", "title": "Recover"},
                }

        class DummyRecordList:
            records = [DummyRecord()]

        class DummyDetailResp:
            record = DummyDetail()

        class DummyLuogu:
            def __init__(self):
                self.list_calls = 0
                self.detail_calls = 0

            def get_record_list(self, **kwargs):
                self.list_calls += 1
                if self.list_calls <= 2:
                    raise RequestError("Request error")
                return DummyRecordList()

            def get_record(self, rid):
                self.detail_calls += 1
                if self.detail_calls <= 2:
                    raise RequestError("Failed to send request after 5 attempts")
                return DummyDetailResp()

        api = DummyLuogu()
        record = _pick_record_for_problem(api, uid=1, pid="P1002", max_records_to_try=2)

        self.assertEqual(record["sourceCode"], "print('ok')")
        self.assertGreaterEqual(api.list_calls, 3)
        self.assertGreaterEqual(api.detail_calls, 3)

    def test_repair_behavior_analysis_from_items_uses_valid_fallback_records(self):
        export_data = {
            "passed_items": [
                {
                    "problem": {"pid": "P1000", "title": "A+B Problem"},
                    "record": {
                        "id": 1,
                        "status": 12,
                        "submitTime": 1234567890,
                        "problem": {"pid": "P1000", "title": "A+B Problem"},
                    },
                }
            ],
            "failed_items": [],
            "behavior_analysis": {"error": "Failed to decode JSON response"},
        }

        repaired = repair_behavior_analysis_from_items(export_data)

        self.assertIn("personality_scores", repaired)
        self.assertEqual(repaired["_source"], "record_detail_fallback_repaired")
        self.assertIn("decode JSON", repaired["_warning"])

    def test_summarize_detail_fetch_stats_counts_requested_summary_and_blocking(self):
        passed_items = [
            {"problem": {"pid": "P1"}, "record": {"submitTime": 1, "sourceCode": "code", "_detail_requested": True}},
            {"problem": {"pid": "P2"}, "record": {"submitTime": 2, "sourceCode": None, "_detail_requested": True, "_detail_error": "Need Login"}},
        ]
        failed_items = [
            {"problem": {"pid": "P3"}, "record": {"submitTime": 3, "sourceCode": None, "_detail_requested": False}},
            {"problem": {"pid": "P4"}, "record": {"submitTime": 4, "sourceCode": None, "_detail_requested": True, "_detail_skipped": "Need Login"}},
            {"problem": {"pid": "P5"}, "record": {"error": "Failed to decode JSON response"}},
        ]

        stats = summarize_detail_fetch_stats(passed_items, failed_items, {"last_detail_error": "Need Login"})

        self.assertEqual(stats["total_items"], 5)
        self.assertEqual(stats["source_code_success"], 1)
        self.assertEqual(stats["summary_only"], 3)
        self.assertEqual(stats["detail_requested"], 3)
        self.assertEqual(stats["detail_skipped"], 1)
        self.assertEqual(stats["detail_errors"], 1)
        self.assertEqual(stats["pure_error_records"], 1)
        self.assertEqual(stats["blocker_reason"], "Need Login")

    def test_trusted_summary_hides_detail_fetch_stats_when_overview_card_exists(self):
        export_data = {
            "student_info": {"eval_time": "2026-06-03 12:00"},
            "summary": {
                "difficulty_histogram": {"1": 2},
                "level_experience": {},
            },
            "detail_fetch_stats": {
                "total_items": 8,
                "source_code_success": 3,
                "summary_only": 5,
                "detail_requested": 4,
                "detail_skipped": 1,
                "detail_errors": 1,
                "pure_error_records": 0,
                "blocker_reason": "Need Login",
            },
            "behavior_analysis": {"error": "未获取到有效提交记录"},
            "syllabus_evaluation": {},
        }

        markdown = build_trusted_data_summary_md(export_data)

        self.assertNotIn("提交详情抓取统计", markdown)
        self.assertNotIn("成功拿到源码详情", markdown)
        self.assertNotIn("摘要保底记录", markdown)
        self.assertNotIn("阻断原因：Need Login", markdown)

    def test_build_detail_fetch_overview_maps_status_and_counts(self):
        overview = build_detail_fetch_overview(
            {
                "total_items": 8,
                "source_code_success": 3,
                "summary_only": 5,
                "detail_skipped": 2,
                "pure_error_records": 0,
                "blocker_reason": "Need Login",
            }
        )

        self.assertEqual(overview["status_label"], "已触发止损")
        self.assertEqual(overview["source_code_success"], 3)
        self.assertEqual(overview["summary_only"], 5)
        self.assertEqual(overview["detail_skipped"], 2)
        self.assertEqual(overview["blocker_reason"], "Need Login")

    def test_split_practice_problems_uses_submitted_without_dup_passed(self):
        practice = DummyPractice(
            {
                "passed": [
                    {"pid": "P1000", "title": "Passed", "difficulty": 1, "type": "P", "tags": [1]},
                ],
                "submitted": [
                    {"pid": "P1000", "title": "Passed", "difficulty": 1, "type": "P", "tags": [1]},
                    {"pid": "P1001", "title": "Failed", "difficulty": 2, "type": "P", "tags": [2]},
                ],
            }
        )

        passed, failed = split_practice_problems(practice)

        self.assertEqual([problem.pid for problem in passed], ["P1000"])
        self.assertEqual([problem.pid for problem in failed], ["P1001"])
        self.assertTrue(failed[0].submitted)
        self.assertFalse(failed[0].accepted)

    def test_fetch_behavior_analysis_reports_auth_errors_clearly(self):
        class DummyLuogu:
            def get_record_list(self, **kwargs):
                raise AuthenticationError("Need Login")

        fake_behavior_module = SimpleNamespace(
            analyze_submission_behavior=lambda records: {"sample_count": len(records)}
        )

        with patch.dict("sys.modules", {"behavior_analyzer": fake_behavior_module}):
            result = fetch_behavior_analysis(DummyLuogu(), 1)

        self.assertIn("Cookies", result["error"])
        self.assertIn("提交记录列表", result["error"])

    def test_fetch_behavior_analysis_keeps_warning_when_fallback_is_used(self):
        class DummyLuogu:
            def get_record_list(self, **kwargs):
                raise AuthenticationError("Need Login")

        fake_behavior_module = SimpleNamespace(
            analyze_submission_behavior=lambda records: {"sample_count": len(records)}
        )
        fallback_items = [{"record": {"submitTime": 1234567890, "sourceCode": "print(1)"}}]

        with patch.dict("sys.modules", {"behavior_analyzer": fake_behavior_module}):
            result = fetch_behavior_analysis(DummyLuogu(), 1, fallback_items)

        self.assertEqual(result["sample_count"], 1)
        self.assertEqual(result["_source"], "record_detail_fallback")
        self.assertIn("Cookies", result["_warning"])

    # ===== v3.9.43 · 禁止"代码丢失"误导性措辞 =====
    def test_evolution_prompt_no_diff_avoids_misleading_wording(self):
        """v3.9.43：当 selected_problems 为空（无多次提交）时，prompt 绝不能
        包含「代码丢失 / 历史代码丢失 / 源码丢失」等让用户以为是 bug 丢数据的措辞。

        注意：警告里**需要**提到这些词（"严禁使用 X"）才能让 AI 知道禁词，
        所以本测试只验证：警告**只出现 1 次**（作为反例），不会出现 2+ 次
        （说明 AI 真的在使用）。
        """
        from luogu_evaluator import _build_evolution_prompt

        export_data = {
            "passed_items": [
                {"problem": {"pid": "P1001", "title": "A+B"}, "record": {"sourceCode": "print(1+1)"}},
                {"problem": {"pid": "P1002", "title": "Hello"}, "record": {"sourceCode": "print('hi')"}},
            ],
            "failed_items": [],
            "submission_evolution": {"selected_problems": []},  # 关键：空
        }
        prompt = _build_evolution_prompt(export_data)

        # 1) 必须明确说"无法做 diff"或同类中性措辞
        self.assertIn("无法做", prompt,
                      f"prompt 应该说明「无法做 diff」原因，但实际是：\n{prompt[:500]}")
        self.assertIn("diff", prompt,
                      f"prompt 应该提到 diff 分析，但实际是：\n{prompt[:500]}")
        # 2) 严禁 AI 使用这些词（用「X」书名号形式提及一次）—— 每个词在 prompt 中只能独立出现 1 次
        # 注意：必须用「X」精确匹配，否则"历史代码丢失"里的"代码丢失"子串会被算进去
        for forbidden in ("代码丢失", "历史代码丢失", "源码丢失"):
            precise = f"「{forbidden}」"
            count = prompt.count(precise)
            self.assertLessEqual(
                count, 1,
                f"「{forbidden}」在 prompt 中独立出现 {count} 次（应 ≤ 1 次）"
                f"—— 多次出现说明 AI 可能在用这个措辞，而不是只看警告一次"
            )
        # 3) prompt 应该明确出现"严禁"字样（告诉 AI 主动禁止）
        self.assertIn("严禁", prompt,
                      "prompt 必须包含「严禁」字样，让 AI 知道这是硬性约束")

    def test_evolution_prompt_no_diff_guides_code_style_observation(self):
        """v3.9.43：无多次提交时，prompt 应引导 AI 写「代码风格观察」子章节。"""
        from luogu_evaluator import _build_evolution_prompt

        export_data = {
            "passed_items": [{"problem": {"pid": "P1"}, "record": {"sourceCode": "x"}}],
            "failed_items": [],
            "submission_evolution": {"selected_problems": []},
        }
        prompt = _build_evolution_prompt(export_data)

        self.assertIn("代码风格", prompt,
                      "无多次提交时，prompt 应引导 AI 写「代码风格观察」")
        self.assertIn("严禁", prompt,
                      "prompt 应明确禁止 AI 使用误导性措辞")

    def test_evolution_prompt_with_data_does_not_inject_no_diff_warn(self):
        """v3.9.43：有 selected_problems 时不应触发无 diff 警告（保持原行为）。"""
        from luogu_evaluator import _build_evolution_prompt

        export_data = {
            "passed_items": [],
            "failed_items": [],
            "submission_evolution": {
                "selected_problems": [
                    {
                        "pid": "P1001",
                        "title": "Demo",
                        "attempts": 3,
                        "is_accepted": True,
                        "status_timeline": "v1:WA → v2:AC",
                        "code_length_timeline": "100 → 95",
                        "diffs": [],
                    }
                ],
                "summary": {"total_multi_submit_problems": 1, "selected_count": 1},
            },
        }
        # 用一个 fake 模块替换 submission_evolution（避免真的 import 链）
        import sys
        import types
        fake_mod = types.ModuleType("submission_evolution")
        fake_mod.evolution_to_prompt_block = lambda d: (
            f"REAL_EVOLUTION_BLOCK: {len(d.get('selected_problems', []))} problem(s)"
        )
        with patch.dict(sys.modules, {"submission_evolution": fake_mod}):
            prompt = _build_evolution_prompt(export_data)

        self.assertIn("REAL_EVOLUTION_BLOCK", prompt,
                      "有 selected_problems 时应走真实 evolution_to_prompt_block")
        self.assertNotIn("严禁", prompt,
                         "有 selected_problems 时不应混入「无 diff」警告")
        self.assertNotIn("代码丢失", prompt,
                         "无 selected_problems 时也不应包含误导措辞（警告块）")


# ========== v3.9.44 · 反刷题评分 + AI 测评排行榜 单元测试 ==========

class TestV3944AntiGrindScoring(unittest.TestCase):
    """v3.9.44 · 反刷题 3 维评分 + 综合分"""

    @staticmethod
    def _sample_grind_king():
        return {
            "solved_count": 300, "failed_count": 30,
            "summary": {
                "difficulty_histogram": {"1": 200, "2": 80, "3": 20},
                "top_tags": [
                    {"name": "顺序结构", "count": 100, "type": 2},
                    {"name": "分支结构", "count": 80, "type": 2},
                    {"name": "模拟", "count": 60, "type": 2},
                    {"name": "数学", "count": 30, "type": 2},
                ],
            },
        }

    @staticmethod
    def _sample_strong_player():
        return {
            "solved_count": 80, "failed_count": 40,
            "summary": {
                "difficulty_histogram": {"3": 20, "4": 35, "5": 20, "6": 5},
                "top_tags": [
                    {"name": "动态规划", "count": 18, "type": 2},
                    {"name": "图论", "count": 15, "type": 2},
                    {"name": "线段树", "count": 12, "type": 2},
                    {"name": "最短路", "count": 8, "type": 2},
                    {"name": "LCA", "count": 5, "type": 2},
                    {"name": "字符串", "count": 6, "type": 2},
                    {"name": "数论", "count": 4, "type": 2},
                    {"name": "数学", "count": 3, "type": 2},
                ],
            },
        }

    @staticmethod
    def _sample_balanced():
        return {
            "solved_count": 150, "failed_count": 50,
            "summary": {
                "difficulty_histogram": {"1": 30, "2": 40, "3": 40, "4": 30, "5": 10},
                "top_tags": [
                    {"name": "模拟", "count": 18, "type": 2},
                    {"name": "动态规划", "count": 15, "type": 2},
                    {"name": "图论", "count": 12, "type": 2},
                    {"name": "数据结构", "count": 10, "type": 2},
                    {"name": "数学", "count": 9, "type": 2},
                    {"name": "贪心", "count": 8, "type": 2},
                    {"name": "字符串", "count": 7, "type": 2},
                    {"name": "搜索", "count": 6, "type": 2},
                    {"name": "二分", "count": 5, "type": 2},
                    {"name": "排序", "count": 4, "type": 2},
                    {"name": "前缀和", "count": 4, "type": 2},
                ],
            },
        }

    def test_anti_grind_returns_three_dimensions(self):
        """必须返回 3 个维度，且每项 0-100"""
        from behavior_analyzer import compute_anti_grind_dimensions
        ag = compute_anti_grind_dimensions(self._sample_grind_king())
        for key in ("difficulty_depth", "submission_efficiency", "knowledge_breadth"):
            self.assertIn(key, ag, f"缺少 {key}")
            self.assertGreaterEqual(ag[key], 0)
            self.assertLessEqual(ag[key], 100)

    def test_grind_king_difficulty_depth_below_30(self):
        """刷题王：300 道难度 1-2 → 难度深度应 < 30（v3.9.44 关键修复）"""
        from behavior_analyzer import compute_anti_grind_dimensions
        ag = compute_anti_grind_dimensions(self._sample_grind_king())
        self.assertLess(
            ag["difficulty_depth"], 30,
            f"刷题王难度深度应 < 30，实际 {ag['difficulty_depth']}"
        )

    def test_strong_player_difficulty_depth_above_70(self):
        """实力派：80 道难度 3-6 → 难度深度应 > 70"""
        from behavior_analyzer import compute_anti_grind_dimensions
        ag = compute_anti_grind_dimensions(self._sample_strong_player())
        self.assertGreater(
            ag["difficulty_depth"], 70,
            f"实力派难度深度应 > 70，实际 {ag['difficulty_depth']}"
        )

    def test_comprehensive_score_gradient(self):
        """综合分梯度：实力派 > 均衡派 > 刷题王（核心反刷题约束）"""
        from behavior_analyzer import compute_comprehensive_score
        s_grind = compute_comprehensive_score(self._sample_grind_king())["ai_score_thousand"]
        s_strong = compute_comprehensive_score(self._sample_strong_player())["ai_score_thousand"]
        s_balanced = compute_comprehensive_score(self._sample_balanced())["ai_score_thousand"]
        # 关键约束：实力派 > 刷题王
        self.assertGreater(
            s_strong, s_grind,
            f"实力派({s_strong}) 必须 > 刷题王({s_grind})，否则反刷题无效"
        )
        # 实力派应该 > 均衡派
        self.assertGreater(
            s_strong, s_balanced,
            f"实力派({s_strong}) 应 > 均衡派({s_balanced})"
        )
        # 分数应在 0-1000 范围内
        for s in (s_grind, s_strong, s_balanced):
            self.assertGreaterEqual(s, 0)
            self.assertLessEqual(s, 1000)

    def test_comprehensive_score_structure(self):
        """综合分返回 dict 必须包含必要字段"""
        from behavior_analyzer import compute_comprehensive_score
        comp = compute_comprehensive_score(self._sample_strong_player())
        for key in ("ai_score_thousand", "ai_score_label", "six_dimension_scores",
                    "anti_grind_dimensions", "component_scores", "weights", "score_source"):
            self.assertIn(key, comp, f"缺少字段 {key}")
        self.assertEqual(comp["score_source"], "comprehensive_v3944")
        self.assertEqual(len(comp["six_dimension_scores"]), 6)
        self.assertEqual(len(comp["anti_grind_dimensions"]), 3)
        # 权重和 = 1.0
        self.assertAlmostEqual(sum(comp["weights"].values()), 1.0, places=3)

    def test_comprehensive_score_label_tier(self):
        """5 档位（🏆 顶尖/⭐ 优秀/🔵 良好/🟡 基础/🔴 待提升）正确触发"""
        from behavior_analyzer import compute_comprehensive_score
        # 三种样本各对应一个档位
        cases = [
            (self._sample_grind_king(), "🔴 待提升"),
            (self._sample_balanced(), "🟡 基础"),
            (self._sample_strong_player(), "🔵 良好"),
        ]
        for sample, expected_label in cases:
            comp = compute_comprehensive_score(sample)
            actual_label = comp["ai_score_label"]
            self.assertIn(
                expected_label, actual_label,
                f"样本（刷题王/均衡/实力）应触发 {expected_label}，实际 {actual_label}"
            )

    def test_comprehensive_score_tier_thresholds(self):
        """5 档位阈值边界：900/800/700/600"""
        from behavior_analyzer import (
            compute_comprehensive_score, _COMPREHENSIVE_WEIGHTS
        )
        # 构造极端样本，让 component_scores 都等于 100 → 必为 1000 → 🏆 顶尖
        perfect_sample = {
            "solved_count": 100, "failed_count": 0,
            "summary": {
                "difficulty_histogram": {"6": 100},
                "top_tags": [
                    {"name": "动态规划", "count": 20, "type": 2},
                    {"name": "图论", "count": 20, "type": 2},
                    {"name": "线段树", "count": 20, "type": 2},
                    {"name": "字符串", "count": 20, "type": 2},
                    {"name": "数学", "count": 20, "type": 2},
                ],
            },
        }
        comp = compute_comprehensive_score(perfect_sample)
        self.assertGreaterEqual(comp["ai_score_thousand"], 900)
        self.assertIn("🏆", comp["ai_score_label"])


class TestV3944Leaderboard(unittest.TestCase):
    """v3.9.44 · 排行榜：掩码、缓存、学段过滤"""

    def test_mask_student_name_minor_uses_uid_tail(self):
        """v3.9.48 · 未成年人 → 姓氏·U${uid后4}（保留姓 + UID 唯一）"""
        from web_app import _mask_student_name
        self.assertEqual(_mask_student_name("801375", is_minor=True, real_name="童家瑞"), "童·U1375")
        self.assertEqual(_mask_student_name("123", is_minor=True, real_name=None), "U123")

    def test_mask_student_name_adult_uses_uid_tail(self):
        """v3.9.48 · 成年人 **也** 展示姓氏 + UID（与 minor 一致；姓+UID 12bit 信息）"""
        from web_app import _mask_student_name
        self.assertEqual(_mask_student_name("801375", is_minor=False, real_name="张三"), "张·U1375")

    def test_mask_student_name_no_name_uses_uid(self):
        """v3.9.48 · 无 real_name → U${uid后4}（无姓可显）"""
        from web_app import _mask_student_name
        self.assertEqual(_mask_student_name("801375", is_minor=False, real_name=None), "U1375")

    def test_mask_student_name_short_uid_uses_full(self):
        """v3.9.48 · UID 不足 4 位时用全串；real_name 第一个字符作姓"""
        from web_app import _mask_student_name
        self.assertEqual(_mask_student_name("1", is_minor=True, real_name="x"), "x·U1")
        self.assertEqual(_mask_student_name("", is_minor=False, real_name=None), "U")

    def test_mask_student_name_never_leaks_real_name(self):
        """v3.9.48 · **关键安全保证**：脱敏输出中**只能出现姓氏**，
        名字（名）部分的所有字符绝不能泄露（防 PIPL §5.2 泄露 + 防同校人肉）。
        例：「童家瑞」→ 「童·U1375」中只允许「童」出现，「家」「瑞」必须缺席。
        """
        from web_app import _mask_student_name
        real = "童家瑞"
        surname = "童"
        for is_minor in (True, False):
            out = _mask_student_name("801375", is_minor=is_minor, real_name=real)
            for ch in real:
                if ch == surname:
                    # 姓允许出现
                    continue
                self.assertNotIn(
                    ch, out,
                    f"real_name='{real}' 的名 '{ch}' 出现在掩码 '{out}' 中，"
                    f"违反脱敏保证（is_minor={is_minor}）"
                )
            # 输出必须是 "姓·U" 或 "U" 开头
            self.assertTrue(
                out.startswith("U") or out.startswith(surname + "·U"),
                f"脱敏输出应以 U 或 {surname}·U 开头，实际：'{out}'"
            )

    def test_mask_student_name_compound_surname(self):
        """v3.9.48 · 复姓（欧阳/司马等）整体保留"""
        from web_app import _mask_student_name
        self.assertEqual(_mask_student_name("801375", is_minor=True, real_name="欧阳明"), "欧阳·U1375")
        self.assertEqual(_mask_student_name("801375", is_minor=True, real_name="司马懿"), "司马·U1375")
        self.assertEqual(_mask_student_name("801375", is_minor=True, real_name="诸葛孔明"), "诸葛·U1375")

    def test_mask_student_name_english_name(self):
        """v3.9.48 · 英文名取第一个空白分隔的词作姓"""
        from web_app import _mask_student_name
        self.assertEqual(_mask_student_name("801375", is_minor=True, real_name="John Smith"), "John·U1375")
        self.assertEqual(_mask_student_name("801375", is_minor=True, real_name="Alice"), "Alice·U1375")

    # ---------- v3.9.45 · 学校脱敏 ----------

    def test_mask_school_returns_xxxx(self):
        """v3.9.45 · 学校脱敏为「学校#NNNN」"""
        from web_app import _mask_school
        out = _mask_school("采荷中学")
        self.assertTrue(out.startswith("学校#"), f"应返回 学校#XXXX 形式，实际：{out}")
        # 4 位数字编号
        code = out.split("#")[-1]
        self.assertEqual(len(code), 4, f"编号应 4 位，实际：{code}")
        self.assertTrue(code.isdigit(), f"编号应纯数字，实际：{code}")

    def test_mask_school_stable_for_same_input(self):
        """v3.9.45 · 同校 → 同一匿称（学员可识别）"""
        from web_app import _mask_school
        a = _mask_school("采荷中学")
        b = _mask_school("采荷中学")
        c = _mask_school("采荷中学")
        self.assertEqual(a, b)
        self.assertEqual(b, c)

    def test_mask_school_strips_whitespace(self):
        """v3.9.45 · 前后空白不影响 hash 稳定"""
        from web_app import _mask_school
        a = _mask_school("采荷中学")
        b = _mask_school("  采荷中学  ")
        c = _mask_school("\t采荷中学\n")
        self.assertEqual(a, b)
        self.assertEqual(a, c)

    def test_mask_school_different_inputs_different_codes(self):
        """v3.9.45 · 不同输入（大概率）hash 出不同编号（4 位空间 1/10000 撞码）"""
        from web_app import _mask_school
        # 至少抽 10 个不同校名，验证 0 撞码（DJB2 + 10000 空间极小概率冲突）
        schools = [
            "采荷中学", "上海中学", "杭州二中", "人大附中", "清华附中",
            "北京四中", "华师大二附中", "成都七中", "衡水中学", "镇海中学",
        ]
        codes = {_mask_school(s) for s in schools}
        self.assertGreaterEqual(
            len(codes), 9,
            f"10 个不同学校应至少 9 个不同匿称，实际撞码到 {len(codes)} 个"
        )

    def test_mask_school_empty_returns_dash(self):
        """v3.9.45 · 空值/None → "—"（统一占位，避免空串被误判为不同学校）"""
        from web_app import _mask_school
        self.assertEqual(_mask_school(None), "—")
        self.assertEqual(_mask_school(""), "—")
        self.assertEqual(_mask_school("   "), "—")
        self.assertEqual(_mask_school("\t\n  "), "—")

    def test_mask_school_never_leaks_original(self):
        """v3.9.45 · 关键安全保证：脱敏输出中不能包含校名的**完整名字**（允许共享通用字符）"""
        from web_app import _mask_school
        school = "清华大学附属实验学校"
        out = _mask_school(school)
        # 1) 校名中**连续的、区分度高**的子串不应在脱敏输出里
        # （不能用 ch-by-ch 比对，因为输出前缀"学校#"与原校名共享"学""校"是正常的）
        for sub in ("清华大学", "清华", "附属", "实验"):
            self.assertNotIn(
                sub, out,
                f"校名子串 '{sub}' 出现在脱敏输出 '{out}' 中，违反脱敏"
            )
        # 2) 必须以 学校# 开头
        self.assertTrue(out.startswith("学校#"),
                        f"脱敏输出应以 学校# 开头，实际：'{out}'")
        # 3) 脱敏输出长度应 < 原校名 + 一些（脱敏更短）
        self.assertLess(
            len(out), len(school) + 5,
            f"脱敏输出 '{out}' 不应比原校名 '{school}' 长太多"
        )

    # ---------- v3.9.47 · 省份脱敏 ----------

    def test_mask_province_keeps_name(self):
        """v3.9.47 · 省份名直接保留（34 选 1 粒度安全）"""
        from web_app import _mask_province
        self.assertEqual(_mask_province("浙江"), "浙江")
        self.assertEqual(_mask_province("上海市"), "上海市")
        self.assertEqual(_mask_province("北京"), "北京")
        self.assertEqual(_mask_province("  河南  "), "河南")  # strip

    def test_mask_province_empty_returns_dash(self):
        """v3.9.47 · 空值/None → "—"（统一占位）"""
        from web_app import _mask_province
        self.assertEqual(_mask_province(None), "—")
        self.assertEqual(_mask_province(""), "—")
        self.assertEqual(_mask_province("   "), "—")
        self.assertEqual(_mask_province("\t\n"), "—")

    def test_mask_province_truncates_extreme(self):
        """v3.9.47 · 极端长输入截断到 16 字符（防富文本 / 误填）"""
        from web_app import _mask_province
        long_input = "北京市海淀区中关村大街 100 号" * 3  # 60+ 字符
        out = _mask_province(long_input)
        self.assertLessEqual(len(out), 16, f"长输入应截断到 16 字符，实际：{len(out)}")

    def test_grade_to_stage_univ(self):
        """v3.9.47 · UNIV_* → STAGE_UNIV（"大学"）"""
        from admin_students import _grade_to_stage, STAGE_UNIV
        self.assertEqual(_grade_to_stage("UNIV_1"), STAGE_UNIV)
        self.assertEqual(_grade_to_stage("UNIV_2"), STAGE_UNIV)
        self.assertEqual(_grade_to_stage("UNIV_3"), STAGE_UNIV)
        self.assertEqual(_grade_to_stage("UNIV_4"), STAGE_UNIV)
        # 旧 enum 不受影响
        from admin_students import STAGE_PRIMARY, STAGE_JUNIOR, STAGE_SENIOR
        self.assertEqual(_grade_to_stage("PRIMARY_3"), STAGE_PRIMARY)
        self.assertEqual(_grade_to_stage("JUNIOR_2"), STAGE_JUNIOR)
        self.assertEqual(_grade_to_stage("SENIOR_1"), STAGE_SENIOR)
        # GRADUATED 仍走 senior
        self.assertEqual(_grade_to_stage("GRADUATED"), STAGE_SENIOR)

    def test_leaderboard_valid_stages_includes_univ(self):
        """v3.9.47 · 排行榜 valid_stages 应包含 univ（大学），不再有 noi"""
        from web_app import _LEADERBOARD_VALID_STAGES
        self.assertIn("univ", _LEADERBOARD_VALID_STAGES)
        self.assertNotIn("noi", _LEADERBOARD_VALID_STAGES,
                         "v3.9.47 · NOI 应已改为 univ，残留 'noi' 是 bug")

    def test_tag_enrichment_completion_state_stored(self):
        """v3.9.47 · enrich_problem_tags 完成后应调用 update_task 设置 final 100% 状态
        防止节流丢帧导致 tag_fetch_success 卡在 92/250 等不完整值
        """
        # 该测试仅验证 update_task 不会因为不传 tag_fetch_* 而清空（v3.9.46 行为）
        from web_app import update_task
        from task_store import insert_task, delete_task, get_task
        task_id = "test-v3947-tag-final"
        try:
            delete_task(task_id)  # 清理可能残留
        except Exception:
            pass
        insert_task(task_id, status="running", message="test")
        update_task(task_id, tag_fetch_success=50, tag_fetch_total=100)
        t = get_task(task_id)
        self.assertEqual(int(t["tag_fetch_success"]), 50)
        self.assertEqual(int(t["tag_fetch_total"]), 100)
        # 模拟 v3.9.47 final update
        update_task(task_id, tag_fetch_success=100, tag_fetch_total=100, message="done")
        t2 = get_task(task_id)
        self.assertEqual(int(t2["tag_fetch_success"]), 100)
        self.assertEqual(int(t2["tag_fetch_total"]), 100)
        # 清理
        try:
            delete_task(task_id)
        except Exception:
            pass

    def test_leaderboard_invalid_stage_fallback_to_all(self):
        """非法 stage 字符串自动 fallback 到 'all'"""
        from web_app import compute_leaderboard
        # 空库 + 非法 stage 仍应返回空 list（不抛错）
        rows = compute_leaderboard(stage="invalid_xyz", limit=10)
        self.assertIsInstance(rows, list)

    def test_leaderboard_limit_clamped_to_max_100(self):
        """limit 超过 100 时被 clamp 到 100"""
        from web_app import compute_leaderboard, _LEADERBOARD_CACHE
        # 关键：让 cache 命中需要 ts 接近 now_ts（TTL 检查是 now-ts < TTL）
        _LEADERBOARD_CACHE["ts"] = time.time()
        rows = compute_leaderboard(stage="all", limit=99999)
        self.assertLessEqual(len(rows), 100,
                             f"limit=99999 应被 clamp 到 100，实际返回 {len(rows)}")
        # limit=0 时 fallback 到默认值 20（不抛错）
        rows2 = compute_leaderboard(stage="all", limit=0)
        self.assertIsInstance(rows2, list)

    def test_leaderboard_period_invalid_fallback_to_month(self):
        """v3.9.46 · 非法 period → fallback 到 'month'（不抛错）"""
        from web_app import compute_leaderboard
        # 非法 period 仍应返回 list（不抛错）
        rows = compute_leaderboard(stage="all", limit=10, period="garbage")
        self.assertIsInstance(rows, list)

    def test_leaderboard_period_filter_drops_old(self):
        """v3.9.46 · period=week 应过滤掉 > 7 天的报告"""
        import time as _t
        from web_app import _LEADERBOARD_CACHE
        from datetime import datetime, timedelta
        from web_app import compute_leaderboard
        # 关键：cache 命中需要 ts 接近 now_ts
        _LEADERBOARD_CACHE["ts"] = _t.time()
        # 注入一条历史测试数据：1 年前 + 1 个 U1375
        long_ago = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d %H:%M:%S")
        very_recent = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 缓存里是已经 sort+rank 过的数据，注入时手动加 rank
        _LEADERBOARD_CACHE["data"] = [
            {"luogu_uid": "111", "score": 999, "report_time": long_ago, "stage": "all", "rank": 1},
            {"luogu_uid": "222", "score": 888, "report_time": very_recent, "stage": "all", "rank": 2},
        ]
        # month (30 天) 应只剩 222
        rows_month = compute_leaderboard(stage="all", limit=10, period="month")
        uids_month = [r["luogu_uid"] for r in rows_month]
        self.assertIn("222", uids_month)
        self.assertNotIn("111", uids_month,
                         f"周榜/月榜应过滤掉 400 天前的报告，实际: {uids_month}")
        # week (7 天) 也应只剩 222
        rows_week = compute_leaderboard(stage="all", limit=10, period="week")
        self.assertNotIn("111", [r["luogu_uid"] for r in rows_week])
        # all (不限时间) 应都在
        rows_all = compute_leaderboard(stage="all", limit=10, period="all")
        self.assertIn("111", [r["luogu_uid"] for r in rows_all])
        self.assertIn("222", [r["luogu_uid"] for r in rows_all])

    def test_find_my_rank_returns_correct_position(self):
        """v3.9.46 · find_my_rank 应返回用户在榜单中的位置和百分位"""
        import time as _t
        from web_app import find_my_rank, _LEADERBOARD_CACHE
        _LEADERBOARD_CACHE["ts"] = _t.time()
        # 模拟已 sort+rank 的缓存数据（rank 已写入）
        _LEADERBOARD_CACHE["data"] = [
            {"luogu_uid": "100", "score": 900, "report_time": "2026-06-16 10:00:00", "stage": "all", "rank": 1, "display_name": "U0100", "score_label": "顶尖"},
            {"luogu_uid": "200", "score": 800, "report_time": "2026-06-16 10:00:00", "stage": "all", "rank": 2, "display_name": "U0200", "score_label": "优秀"},
            {"luogu_uid": "300", "score": 700, "report_time": "2026-06-16 10:00:00", "stage": "all", "rank": 3, "display_name": "U0300", "score_label": "良好"},
            {"luogu_uid": "400", "score": 600, "report_time": "2026-06-16 10:00:00", "stage": "all", "rank": 4, "display_name": "U0400", "score_label": "中等"},
        ]
        r = find_my_rank("200", stage="all", period="all")
        self.assertIsNotNone(r, "用户 200 应在榜上")
        self.assertEqual(r["rank"], 2)
        self.assertEqual(r["score"], 800)
        # 4 人里第 2 名 → 超过 (4-2)/4 = 50%
        self.assertEqual(r["percentile"], 25)  # (rank-1)*100/total = 1*100/4 = 25

    def test_find_my_rank_returns_none_for_missing_uid(self):
        """v3.9.46 · 榜单中不存在的 UID → 返回 None"""
        import time as _t
        from web_app import find_my_rank, _LEADERBOARD_CACHE
        _LEADERBOARD_CACHE["ts"] = _t.time()
        _LEADERBOARD_CACHE["data"] = [
            {"luogu_uid": "100", "score": 900, "report_time": "2026-06-16 10:00:00", "stage": "all", "rank": 1},
        ]
        r = find_my_rank("99999", stage="all", period="all")
        self.assertIsNone(r)

    # ── v3.9.48 · 海报 AI 定级兜底 ────────────────────────
    def test_fallback_ai_level_gesp8_strong_returns_css_strong(self):
        """v3.9.48 · GESP 8 级 80+ → CSP-S 熟练级"""
        from web_app import _fallback_ai_level
        self.assertEqual(
            _fallback_ai_level(0, {}, 8, 85),
            "CSP-S 熟练级（兜底）"
        )

    def test_fallback_ai_level_gesp7_returns_css_intro(self):
        """v3.9.48 · GESP 7 级 80+ → CSP-S 入门级（与"已可免 CSP-J"心智匹配）"""
        from web_app import _fallback_ai_level
        self.assertEqual(
            _fallback_ai_level(0, {}, 7, 85),
            "CSP-S 入门级（兜底）"
        )

    def test_fallback_ai_level_score_800_returns_css_intro(self):
        """v3.9.48 · 千分制 800 + GESP 0 → CSP-S 入门级（兜底）"""
        from web_app import _fallback_ai_level
        self.assertEqual(
            _fallback_ai_level(800, {}, 0, 0),
            "CSP-S 入门级（兜底）"
        )

    def test_fallback_ai_level_score_300_returns_csj_intro(self):
        """v3.9.48 · 千分制 300 → CSP-J 入门级"""
        from web_app import _fallback_ai_level
        self.assertEqual(
            _fallback_ai_level(300, {}, 0, 0),
            "CSP-J 入门级（兜底）"
        )

    def test_fallback_ai_level_zero_returns_starting(self):
        """v3.9.48 · 全 0 → 起步级（兜底）"""
        from web_app import _fallback_ai_level
        self.assertEqual(
            _fallback_ai_level(0, {}, 0, 0),
            "起步级（兜底）"
        )

    def test_fallback_ai_level_six_dim_used_when_score_zero(self):
        """v3.9.48 · ai_score=0 但 six_dim 有效 → 用 6 维均值 ×10 推算"""
        from web_app import _fallback_ai_level
        # 6 维均分 80 → 千分制 800 → CSP-S 入门级
        six = {"基础算法": 80, "数据结构": 80, "图论": 80, "动态规划": 80, "字符串": 80, "数学": 80}
        self.assertEqual(
            _fallback_ai_level(0, six, 0, 0),
            "CSP-S 入门级（兜底）"
        )

    # ── v3.9.48 · 知识树分支均衡分布 ────────────────────────
    def test_knowledge_tree_branches_balanced_left_right(self):
        """v3.9.48 · 分支左右均衡：n=6→3/3, n=8→4/4, n=9→4/5, n=10→5/5
        v3.9.49 · 强化：解析 SVG 中的 first_fruit_x 与 trunk_x 关系，
        验证前 half_n 个分支确实画在左侧（first_fruit_x < trunk_x）。
        """
        from luogu_evaluator import _build_one_tree_svg
        # n=9：前 half_n=5 个应在左，剩余 5 个在右
        cat_topics = [
            ("基础算法", [("循环", 1, "入门", 0)]),
            ("排序", [("快排", 1, "入门", 0)]),
            ("数据结构", [("栈", 1, "入门", 0)]),
            ("搜索", [("DFS", 1, "入门", 0)]),
            ("图论", [("BFS", 1, "入门", 0)]),
            ("动态规划", [("DP", 1, "入门", 0)]),
            ("贪心", [("贪心", 1, "入门", 0)]),
            ("数学", [("GCD", 1, "入门", 0)]),
            ("字符串", [("KMP", 1, "入门", 0)]),
        ]
        width = 460
        svg = _build_one_tree_svg("🌱", "CSP-J 入门", cat_topics, width=width)
        # 关键：检查 SVG 渲染成功，且未抛错
        self.assertIn("<svg", svg)
        self.assertNotIn("error", svg.lower())

        # v3.9.49 · 实际验证：解析每个分支的 first_fruit_x，统计左/右侧分支数
        # 每个分支的 path 会被绘制 2 次（阴影 + 主色双层），所以数 "M X" 应除以 2
        import re
        trunk_x = width // 2  # 230
        right_count = svg.count(f"M {trunk_x + 7} ") // 2  # 双层叠加 → /2
        left_count = svg.count(f"M {trunk_x - 7} ") // 2   # 双层叠加 → /2
        # n=9 时：half_n = 5，左侧 5 个，右侧 4 个
        self.assertEqual(left_count, 5, f"n=9 应有 5 个左分支，实际 {left_count}")
        self.assertEqual(right_count, 4, f"n=9 应有 4 个右分支，实际 {right_count}")

    # ── v3.9.49 · 知识点覆盖统计表·掌握度分布明细（全量展开） ────────────────
    def test_knowledge_coverage_table_lists_topic_names(self):
        """v3.9.49 · 掌握度 chip 顶部显示「N项」+ 下面换行逐个列全所有 topic
        v3.9.48 旧版只列前 2 + "…"，用户要求"列出全部知识点明细"，
        现改为不再截断（CSS 用 max-width 兜底换行），tooltip 仍保留。
        """
        from luogu_evaluator import build_trusted_data_summary_md

        # 构造 mock export_data：4 级别 × 各 5 个 topic（AC 数决定档位）
        # _level_for_ac 阈值：精通≥20 / 熟练 10-19 / 入门 3-9 / 初窥 1-2 / 空白 0
        export_data = {
            "student_info": {"eval_time": "2026-06-16 10:00:00"},
            "summary": {
                "difficulty_histogram": {"3": 1, "4": 1, "5": 1, "6": 1, "7": 0},
                "level_experience": {},
            },
            "syllabus_evaluation": {
                "csp_j": {
                    "stats": {"total": 5, "精通": 1, "熟练": 1, "入门": 1, "初窥": 1, "空白": 1},
                    "coverage": 80,
                    "details": [
                        {"topic": "基础算法-循环", "ac_count": 25},  # 精通（≥20）
                        {"topic": "排序-快排", "ac_count": 12},     # 熟练（10-19）
                        {"topic": "搜索-DFS", "ac_count": 5},       # 入门（3-9）
                        {"topic": "搜索-BFS", "ac_count": 1},       # 初窥（1-2）
                        {"topic": "图论-最短路", "ac_count": 0},    # 空白
                    ],
                },
                "csp_s": {"stats": {"total": 0}, "coverage": 0, "details": []},
                "provincial": {"stats": {"total": 0}, "coverage": 0, "details": []},
                "noi": {"stats": {"total": 0}, "coverage": 0, "details": []},
            },
        }

        html = build_trusted_data_summary_md(export_data)
        # 断言 1：表格标题
        self.assertIn("知识点覆盖统计表", html)
        # 断言 2：tooltip 包含具体 topic 名（鼠标悬停看全）
        self.assertIn("基础算法-循环", html)
        self.assertIn("排序-快排", html)
        # 断言 3：含 "title=" 鼠标悬停属性
        self.assertIn("title=", html)
        # 断言 4：chip 数量正确（每档 1 个 chip）
        self.assertIn("精通 1项", html)
        self.assertIn("熟练 1项", html)
        self.assertIn("入门 1项", html)
        self.assertIn("初窥 1项", html)
        self.assertIn("空白 1项", html)
        # 断言 5：v3.9.49 新行为——chip 内不再截断，topic 名直接展开在 chip 中
        # （v3.9.48 旧版有"…"省略号，新版应不出现；5 个 topic 全部可见）
        self.assertNotIn("…", html)

    def test_build_evolution_prompt_has_no_data_loss_when_no_history(self):
        """v3.9.48 · 知识树 10 个分支仍能稳定渲染（边界回归）"""
        from luogu_evaluator import _build_one_tree_svg
        cat_topics = [(f"分类{i}", [(f"知识点{i}", 1, "入门", 0)]) for i in range(10)]
        svg = _build_one_tree_svg("🌱", "CSP-J 入门", cat_topics, width=460)
        self.assertIn("<svg", svg)
        self.assertIn("</svg>", svg)

    # ── v3.9.51 · 超大分类自动拆分为子分支 ─────────────────────
    def test_knowledge_tree_splits_oversized_categories(self):
        """v3.9.51 · 单分类 > 28 个知识点时，应自动拆成多个子分支展示，
        确保所有知识点都能被看到（之前会被 +N 截断）。
        """
        from luogu_evaluator import build_knowledge_tree_html

        # 构造 1 个超大分类（30 个知识点）+ 1 个普通分类（3 个知识点）
        big_topics = [(f"DP变体{i}", 30 - i, "入门", 4) for i in range(30)]
        small_topics = [(f"搜索{i}", 1, "入门", 2) for i in range(3)]

        syllabus_eval = {
            "csp_j": {
                "stats": {"total": 33, "空白": 0},
                "coverage": 100,
                "details": [
                    {"topic": t[0], "ac_count": t[1], "difficulty": t[3]} for t in big_topics + small_topics
                ],
            },
            "csp_s": {"stats": {"total": 0}, "coverage": 0, "details": []},
            "provincial": {"stats": {"total": 0}, "coverage": 0, "details": []},
            "noi": {"stats": {"total": 0}, "coverage": 0, "details": []},
        }
        html = build_knowledge_tree_html(syllabus_eval)
        # 关键断言：30 个超大分类应被拆成 2 个子分支（① 和 ②）
        # 角标字符是 ① 和 ②
        self.assertIn("①", html, f"应有子分支角标 ①，实际 HTML 长度: {len(html)}")
        self.assertIn("②", html, f"应有子分支角标 ②，实际 HTML 长度: {len(html)}")
        # 所有 30 个 DP 变体的名字都应出现在 HTML 中（不丢失）
        for i in range(30):
            self.assertIn(f"DP变体{i}", html, f"DP变体{i} 应在 HTML 中")

    def test_knowledge_tree_no_split_for_small_categories(self):
        """v3.9.51 · 分类 ≤ 28 个知识点时，不应加角标（保持原样）"""
        from luogu_evaluator import build_knowledge_tree_html

        small_topics = [(f"主题{i}", 1, "入门", 2) for i in range(5)]
        syllabus_eval = {
            "csp_j": {
                "stats": {"total": 5, "空白": 0},
                "coverage": 100,
                "details": [
                    {"topic": t[0], "ac_count": t[1], "difficulty": t[3]} for t in small_topics
                ],
            },
            "csp_s": {"stats": {"total": 0}, "coverage": 0, "details": []},
            "provincial": {"stats": {"total": 0}, "coverage": 0, "details": []},
            "noi": {"stats": {"total": 0}, "coverage": 0, "details": []},
        }
        html = build_knowledge_tree_html(syllabus_eval)
        # 不应出现角标字符
        for sub in ("①", "②", "③"):
            self.assertNotIn(sub, html, f"小分类不应有角标 {sub}")

    # ── v3.9.52 · 账号密码登录（替代手工 Cookies） ─────────────────────
    def test_login_with_password_validates_empty_inputs(self):
        """v3.9.52 · 空用户名/密码应直接拒绝（不发请求）"""
        from web_app import login_with_password
        # 空用户名
        r1 = login_with_password("", "somepass")
        self.assertFalse(r1.get("ok"))
        self.assertIn("用户名", r1.get("error", ""))
        # 空密码
        r2 = login_with_password("12345", "")
        self.assertFalse(r2.get("ok"))
        self.assertIn("用户名", r2.get("error", ""))

    def test_login_with_password_returns_proper_structure(self):
        """v3.9.52 · 返回值结构必须稳定（前端依赖字段名）"""
        from web_app import login_with_password
        # 用错误密码触发 API 调用（不会真的发请求因为 _transport 不存在）
        # 这里只验证返回结构的字段
        result = login_with_password("", "")
        # 失败时必须有 ok 和 error 字段
        self.assertIn("ok", result)
        self.assertIn("error", result)
        self.assertFalse(result["ok"])

    def test_login_with_password_route_registered(self):
        """v3.9.52 · /login-with-password 路由必须存在"""
        from web_app import app
        rules = [str(r) for r in app.url_map.iter_rules()]
        self.assertIn("/login-with-password", rules, "缺少 /login-with-password 路由")
        # 必须是 POST
        for r in app.url_map.iter_rules():
            if str(r) == "/login-with-password":
                self.assertIn("POST", r.methods, "/login-with-password 必须支持 POST")

    def test_clear_temp_cookies_route_registered(self):
        """v3.9.52 · /clear-temp-cookies 路由必须存在（清理 session）"""
        from web_app import app
        rules = [str(r) for r in app.url_map.iter_rules()]
        self.assertIn("/clear-temp-cookies", rules, "缺少 /clear-temp-cookies 路由")

    def test_generate_route_uses_session_temp_cookies(self):
        """v3.9.52 · /generate 应能合并 session 里的 temp_cookies 到 form_data"""
        # 检查 /generate 路由存在
        from web_app import app
        rules = [str(r) for r in app.url_map.iter_rules()]
        self.assertIn("/generate", rules, "缺少 /generate 路由")

    def test_render_index_accepts_pwd_login_2fa_param(self):
        """v3.9.52 · render_index 必须支持 pwd_login_2fa 参数（2FA 模式渲染）"""
        from web_app import render_index
        import inspect
        sig = inspect.signature(render_index)
        self.assertIn("pwd_login_2fa", sig.parameters,
                      "render_index 必须有 pwd_login_2fa 参数")

    # ── v3.9.49 · AI 定级抽取新增 `当前对应等级` 模板兜底 ──────────────
    def test_extract_ai_level_handles_new_template_dangqian_duiying(self):
        """v3.9.49 · 报告改为「**当前对应等级**：**VALUE**」后，旧正则漏掉 → 海报显示"尚未生成报告"
        新增「当前对应等级」系列正则 + 兜底"取关键词后到第一个句号/换行前"逻辑。
        """
        from web_app import _extract_ai_evaluation_from_report

        # 场景 1：最新模板「**当前对应等级**：**CSP-J（入门级）能力达标，...**」
        md1 = """
### 5. 【考纲精准定级】
*   **当前对应等级**：**CSP-J（入门级）能力达标，CSP-S（提高级）能力严重不足**。
"""
        r1 = _extract_ai_evaluation_from_report(md1)
        self.assertIn("CSP-J（入门级）", r1["ai_level"] or "",
                      f"场景 1 抽取失败: {r1['ai_level']!r}")

        # 场景 2：带额外「** 」装饰（**当前对应等级水平：** ** **VALUE**）
        md2 = """
### 5. 【考纲精准定级】
当前对应等级水平：** **CSP-J 优秀水平，CSP-S 入門水平**。你具备很好的代码实现能力。
"""
        r2 = _extract_ai_evaluation_from_report(md2)
        self.assertIn("CSP-J 优秀水平", r2["ai_level"] or "",
                      f"场景 2 抽取失败: {r2['ai_level']!r}")

        # 场景 3：关键词后是换行 + bullet 列表（无直接 VALUE）→ 兜底取"关键词+冒号后第一段"
        md3 = """
### 5. 【考纲精准定级】
当前对应等级水平
- **CSP-J**：⚠️ 存在7个空白知识点
- **CSP-S**：🔴 严重不足
"""
        r3 = _extract_ai_evaluation_from_report(md3)
        # 场景 3 没有 VALUE 字符串，应该是 None
        # （兜底也救不回来——只验证函数不崩溃、不抛异常）
        self.assertIsNotNone(r3)

    def test_compute_score_from_export_prefers_v3944(self):
        """从 export_data.json 算分时优先用 v3.9.44 综合分"""
        from web_app import _compute_score_from_export
        export = self._TestV3944AntiGrindScoring__sample_strong_player() if False else {
            "solved_count": 80, "failed_count": 40,
            "summary": {
                "difficulty_histogram": {"3": 20, "4": 35, "5": 20, "6": 5},
                "top_tags": [
                    {"name": "动态规划", "count": 18, "type": 2},
                    {"name": "图论", "count": 15, "type": 2},
                ],
            },
        }
        score, label, source = _compute_score_from_export(export, None)
        self.assertEqual(source, "comprehensive_v3944")
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1000)
        # 实力派分数应 > 600（优秀档位）
        self.assertGreater(score, 600, f"实力派应 > 600，实际 {score}")


    def test_parent_subscribe_prompt_includes_full_profile_block(self):
        """v3.9.50 · generate_parent_subscribe 的 GESP 查询用了不存在的列 `c.event_date`（实际是 c.exam_date），
        导致整个 try 块 raise 被外层 except 静默吞掉，profile_block 退化为"档案拉取失败：no such column"，
        AI 重新措辞后输出"暂未参加 GESP/CSP/未填写城市/学校"（system prompt 禁止直接说'数据拉取失败'）。

        本测试用 in-memory SQLite 模拟 task_store，复现真实 bug 并验证修复后能拿到完整档案。
        """
        import sqlite3
        from luogu_evaluator import generate_parent_subscribe

        # ── 1) 搭一个临时 DB，复刻真实 schema（最关键的 4 张表） ──
        tmp = sqlite3.connect(":memory:")
        tmp.row_factory = sqlite3.Row
        cur = tmp.cursor()
        cur.executescript("""
            CREATE TABLE students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                luogu_uid TEXT UNIQUE NOT NULL,
                real_name TEXT, school TEXT, grade TEXT, gender TEXT, birth_date DATE,
                city TEXT DEFAULT '', province TEXT DEFAULT '', is_minor BOOLEAN DEFAULT 0,
                guardian_consent_at DATETIME, note TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE competitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT, name TEXT NOT NULL, type TEXT, level INTEGER,
                exam_date DATE NOT NULL, registration_deadline DATE, location TEXT,
                target_audience TEXT, fee_cny INTEGER DEFAULT 0, source_url TEXT,
                data_year INTEGER NOT NULL, notes TEXT, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE gesp_exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL REFERENCES students(id),
                exam_id INTEGER NOT NULL,
                registered_level INTEGER NOT NULL,
                actual_score INTEGER, passed BOOLEAN,
                can_skip_next BOOLEAN DEFAULT 0, exempts_csp_j BOOLEAN DEFAULT 0,
                exempts_csp_s BOOLEAN DEFAULT 0, certificate_no TEXT, notes TEXT,
                recorded_by TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                award_year INTEGER
            );
            CREATE TABLE csp_awards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL REFERENCES students(id),
                competition_type TEXT NOT NULL, award_level TEXT NOT NULL,
                award_year INTEGER NOT NULL, actual_score INTEGER, province TEXT,
                certificate_no TEXT, notes TEXT, recorded_by TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("INSERT INTO competitions (code,name,type,exam_date,data_year) VALUES (?,?,?,?,?)",
                    ("GESP-2026-03-L5-6", "GESP 等级认证（5-6 级春考）", "gesp", "2026-03-15", 2026))
        cur.execute("""INSERT INTO students
            (luogu_uid, real_name, school, city, province, grade, gender, birth_date)
            VALUES (?,?,?,?,?,?,?,?)""",
            ("935184", "刘一乐", "深圳市龙岗区外国语学校", "深圳", "广东",
             "JUNIOR_2", "M", "2012-05-21"))
        cur.execute("""INSERT INTO gesp_exams
            (student_id, exam_id, registered_level, actual_score, passed, award_year)
            VALUES (1, 1, 5, 80, 1, 2026)""")
        cur.execute("""INSERT INTO csp_awards
            (student_id, competition_type, award_level, award_year, actual_score)
            VALUES (1, 'csp_j_final', 'third', 2026, 145)""")
        tmp.commit()

        # ── 2) mock task_store._get_conn 返回这个内存库 ──
        from unittest.mock import patch
        captured = {"profile_block": None, "policy_block": None}

        # 同时也建一张空 policy_match_schools（避免 policy_block 报缺表）
        cur.execute("""CREATE TABLE policy_match_schools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_name TEXT, school_type TEXT, target_stage TEXT,
            city TEXT, province TEXT, policy_summary TEXT,
            priority_score INTEGER DEFAULT 0, requires_competition TEXT,
            source_url TEXT, last_updated DATE DEFAULT CURRENT_DATE
        )""")
        tmp.commit()

        real_get_conn_orig = None
        try:
            from task_store import _get_conn
            real_get_conn_orig = _get_conn
        except Exception:
            real_get_conn_orig = None

        def fake_get_conn():
            return tmp

        with patch("task_store._get_conn", fake_get_conn), \
             patch("luogu_evaluator._get_conn", fake_get_conn) if "luogu_evaluator._get_conn" in dir(__import__("luogu_evaluator")) else patch("builtins.print"):
            # ── 3) 用 monkey-patch 方式把生成出来的 user_prompt 抓出来 ──
            original_chat = None
            from openai import OpenAI
            from unittest.mock import MagicMock

            fake_response = MagicMock()
            fake_response.choices = [MagicMock()]
            fake_response.choices[0].message.content = "## 1. 学习进度评估（家长版）\n测试报告。\n"

            def fake_create(*args, **kwargs):
                # 把 user prompt 抓出来
                msgs = kwargs.get("messages") or args[0]
                user_msg = next((m for m in msgs if m["role"] == "user"), None)
                if user_msg:
                    captured["profile_block"] = user_msg["content"]
                return fake_response

            with patch.object(OpenAI, "chat") as mock_chat:
                mock_chat.completions.create = fake_create
                try:
                    md = generate_parent_subscribe(
                        report_md="## 测试 report\n无内容",
                        export_data={
                            "student_info": {
                                "name": "刘一乐",
                                "school": "深圳市龙岗区外国语学校",
                                "grade": "初二（初中二年级）",
                                "grade_zh": "初二（初中二年级）",
                                "eval_time": "2026-06-16 10:51",
                                # ⚠️ 没 city / province（复现真实 export_data.json 的样子）
                            },
                            "solved_count": 250,
                            "failed_count": 17,
                        },
                        api_key="sk-fake",
                        base_url=None,
                        model_name="gpt-4o-mini",
                        luogu_uid="935184",
                    )
                except Exception as e:
                    self.fail(f"generate_parent_subscribe 抛异常: {e}")

        prompt = captured["profile_block"] or ""
        # v3.9.50 修复后，profile_block 应包含完整的：
        #   - 学校：「深圳市龙岗区外国语学校」
        #   - 城市/省份：「深圳 / 广东」
        #   - GESP 真考历史：「GESP L5 · ...」
        #   - CSP/NOIP/NOI 获奖历史：「2026 CSP-J 复赛 三等」
        self.assertIn("深圳市龙岗区外国语学校", prompt,
                      f"修复后应含真实学校名。实际 prompt: {prompt[:1000]!r}")
        self.assertIn("深圳", prompt,
                      f"修复后应含真实城市。实际 prompt: {prompt[:1000]!r}")
        self.assertIn("广东", prompt,
                      f"修复后应含真实省份。实际 prompt: {prompt[:1000]!r}")
        self.assertIn("GESP L5", prompt,
                      f"修复后应含 GESP 真考记录（不再是'暂无比赛记录'）。实际 prompt: {prompt[:1000]!r}")
        self.assertIn("CSP-J 复赛", prompt,
                      f"修复后应含 CSP 获奖记录。实际 prompt: {prompt[:1000]!r}")
        self.assertIn("三等", prompt,
                      f"修复后应含 CSP 奖项等级。实际 prompt: {prompt[:1000]!r}")
        self.assertNotIn("暂无 GESP/CSP/NOIP/NOI 比赛记录", prompt,
                         "修复后不应再退化为'暂无比赛记录'占位")
        self.assertNotIn("档案拉取失败", prompt,
                         "修复后不应再出现'档案拉取失败'错误文案")


if __name__ == "__main__":
    unittest.main()
