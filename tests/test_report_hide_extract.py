import unittest
import textwrap
from web_app import _extract_ai_summary


SAMPLE_REPORT = """# 测试报告

## 一、基础信息
...

### （一）AI 核心解读

这位选手展现出扎实的基础算法功底，在动态规划和字符串处理方面表现尤为突出。建议在保持现有优势的同时，重点加强图论和数据结构相关题目的练习，特别是在复杂场景的应用方面。

## 二、详细分析
...
"""


class TestExtractAiSummary(unittest.TestCase):
    def test_empty_report(self):
        self.assertEqual(_extract_ai_summary(""), "")

    def test_extracts_core_interpretation(self):
        out = _extract_ai_summary(SAMPLE_REPORT)
        self.assertIn("基础算法", out)
        self.assertIn("动态规划", out)

    def test_truncates_to_200_chars(self):
        long = "### （一）AI 核心解读\n\n" + "测试" * 500 + "\n\n## 二、"
        out = _extract_ai_summary(long)
        # 截断后追加省略号「…」,故最大长度为 200 + 1 = 201
        self.assertLessEqual(len(out), 201)
        self.assertGreater(len(out), 0)
        self.assertTrue(out.endswith("…"))

    def test_returns_empty_when_section_missing(self):
        out = _extract_ai_summary("""# 报告

## 一、基础信息
选手是小学生。
""")
        self.assertEqual(out, "")

    def test_none_input(self):
        self.assertEqual(_extract_ai_summary(None), "")

    def test_multiple_sections_returns_first(self):
        md = textwrap.dedent("""\
            ### （一）AI 核心解读

            第一节内容，包含重要信息。

            ### （二）AI 核心解读

            第二节内容，不应被返回。
        """)
        out = _extract_ai_summary(md)
        self.assertIn("第一节", out)
        self.assertNotIn("第二节", out)

    def test_section_with_h4_subhead(self):
        md = textwrap.dedent("""\
            ### （一）AI 核心解读

            主体内容第一段。

            #### 子解读细节

            这里是 h4 子标题，不应终止 section。
            继续主体内容。
        """)
        out = _extract_ai_summary(md)
        self.assertIn("子解读细节", out)
        self.assertIn("继续主体内容", out)


from web_app import _extract_top_suggestions


SAMPLE_SUGGESTIONS = """# 报告

## 九、训练建议

- 优先补「动态规划」专项训练，建议每周 3 题
- 错题本：贪心/构造可专项突破
- GESP 7 级已具备，建议冲 8 级免 CSP-J 初赛
- 暂时不考虑

## 十、错题
"""


class TestExtractTopSuggestions(unittest.TestCase):
    def test_empty_report(self):
        self.assertEqual(_extract_top_suggestions(""), [])

    def test_extracts_three_bullets(self):
        out = _extract_top_suggestions(SAMPLE_SUGGESTIONS)
        self.assertEqual(len(out), 3)
        self.assertIn("动态规划", out[0])

    def test_truncates_to_three(self):
        md = "## 九、训练建议\n\n" + "\n".join(f"- 建议 {i}" for i in range(10)) + "\n\n## 十、"
        out = _extract_top_suggestions(md)
        self.assertEqual(len(out), 3)
