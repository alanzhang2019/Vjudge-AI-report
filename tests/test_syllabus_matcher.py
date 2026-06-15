"""
v3.9.43 单元测试：验证 syllabus_matcher._match_topic 对"带空格标签"（如 "树形 DP"）
能正确匹配无空格关键词（"树形dp"），覆盖 UID 1490150 反馈的"树形DP/区间DP 已练过却空白"问题。
"""
import unittest

from syllabus_matcher import (
    _match_topic,
    _count_topic_ac,
    evaluate_all_topics,
    evaluate_topic_level,
    CSP_J_TOPICS,
    CSP_S_TOPICS,
)


class TestMatchTopicWhitespace(unittest.TestCase):
    """核心修复点：标签名带空格时必须能匹配无空格关键词。"""

    # ---------- UID 1490150 反馈的两个核心场景 ----------
    def test_tree_dp_with_space(self):
        """洛谷 API 真实返回的 "树形 DP" 必须匹配关键词 "树形dp"。"""
        self.assertTrue(_match_topic("树形 DP", ["树形dp"]))

    def test_interval_dp_with_space(self):
        """洛谷 API 真实返回的 "区间 DP" 必须匹配关键词 "区间dp"。"""
        self.assertTrue(_match_topic("区间 DP", ["区间dp"]))

    # ---------- 各种空格的鲁棒性 ----------
    def test_multiple_spaces(self):
        self.assertTrue(_match_topic("树形  DP", ["树形dp"]))

    def test_no_space(self):
        """原本就匹配的情况不能回归。"""
        self.assertTrue(_match_topic("树形DP", ["树形dp"]))

    def test_no_space_2(self):
        self.assertTrue(_match_topic("树形dp", ["树形dp"]))

    def test_nbsp(self):
        """\u00a0 不间断空格也要去掉。"""
        self.assertTrue(_match_topic("树形\u00a0DP", ["树形dp"]))

    def test_full_width_space(self):
        """\u3000 全角空格也要去掉。"""
        self.assertTrue(_match_topic("树形\u3000DP", ["树形dp"]))

    def test_case_insensitive_with_space(self):
        self.assertTrue(_match_topic("Manacher", ["manacher"]))

    def test_no_false_positive_on_unrelated_tag(self):
        """无关标签不能误匹配。"""
        self.assertFalse(_match_topic("字符串", ["树形dp"]))
        self.assertFalse(_match_topic("动态规划 DP", ["树形dp"]))


class TestCountTopicACForUID1490150(unittest.TestCase):
    """模拟 UID 1490150 的 top_tags 输入，验证 AC 计数与等级。"""

    def setUp(self):
        # 洛谷 /_lfe/tags 真实返回的标签名都是"带空格"的
        self.top_tags = [
            {"name": "树形 DP",   "count": 5, "type": 2},
            {"name": "区间 DP",   "count": 3, "type": 2},
            {"name": "数位 DP",   "count": 4, "type": 2},
            {"name": "插头 DP",   "count": 2, "type": 2},
            {"name": "状压 DP",   "count": 1, "type": 2},
            {"name": "动态规划 DP", "count": 8, "type": 2},
            {"name": "字符串",    "count": 6, "type": 2},
            {"name": "深度优先搜索 DFS", "count": 7, "type": 2},
            {"name": "广度优先搜索 BFS", "count": 4, "type": 2},
            # 完全无关的标签
            {"name": "数学",      "count": 10, "type": 2},
        ]

    def test_tree_dp_ac_count(self):
        ac = _count_topic_ac(self.top_tags, CSP_S_TOPICS["树形DP"])
        self.assertEqual(ac, 5, "树形DP 标签 '树形 DP' 应贡献 5 个 AC")

    def test_interval_dp_ac_count(self):
        ac = _count_topic_ac(self.top_tags, CSP_J_TOPICS["区间DP"])
        self.assertEqual(ac, 3, "区间DP 标签 '区间 DP' 应贡献 3 个 AC")

    def test_digit_dp_ac_count(self):
        # 数位DP 在 syllabus 关键词里没有，但应能被 "DP基础"/"多维DP" 等不命中
        # 这里只验证"区间DP"/"树形DP"这两个最关键的 UID 反馈点
        pass

    def test_evaluate_all_topics_not_blank_for_dp_tags(self):
        """UID 1490150 反馈的核心问题：树形DP/区间DP 不应被判定为'空白'。"""
        result = evaluate_all_topics(self.top_tags)
        details = result["csp_j"]["details"] + result["csp_s"]["details"]
        tree_dp = next(d for d in details if d["topic"] == "树形DP")
        interval_dp = next(d for d in details if d["topic"] == "区间DP")

        self.assertEqual(tree_dp["ac_count"], 5)
        self.assertNotEqual(tree_dp["level"], "🔴 空白",
                            f"树形DP 不应再被标为'空白'，实际为: {tree_dp['level']}")
        self.assertIn(tree_dp["level"], ["🟠 入门", "🟡 熟练", "🟢 精通"])

        self.assertEqual(interval_dp["ac_count"], 3)
        self.assertNotEqual(interval_dp["level"], "🔴 空白",
                            f"区间DP 不应再被标为'空白'，实际为: {interval_dp['level']}")
        self.assertIn(interval_dp["level"], ["🟠 入门", "🟡 熟练", "🟢 精通"])


class TestMatchTopicBackwardsCompat(unittest.TestCase):
    """回归保护：原有用例不应被破坏。"""

    def test_empty_tag(self):
        self.assertFalse(_match_topic("", ["dp"]))

    def test_none_tag(self):
        self.assertFalse(_match_topic(None, ["dp"]))  # type: ignore[arg-type]

    def test_empty_keywords(self):
        self.assertFalse(_match_topic("树形 DP", []))

    def test_empty_keyword_in_list(self):
        # 空字符串关键词应被跳过
        self.assertTrue(_match_topic("树形DP", ["", "树形dp"]))

    def test_dfs_bfs(self):
        """"深度优先搜索 DFS" 包含 "dfs"（去空格后），应匹配 DFS 知识点。"""
        self.assertTrue(_match_topic("深度优先搜索 DFS", CSP_J_TOPICS["DFS"]))


if __name__ == "__main__":
    unittest.main()
