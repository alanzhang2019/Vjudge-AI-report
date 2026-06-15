"""
v3.9.43 单元测试：验证 compute_ability_scores (luogu_evaluator) 和
compute_six_dimension_scores (behavior_analyzer) 不再把"树形 DP"/"线段树"/
"字典树"等数据结构和 DP 标签误算到"图论"能力头上。
"""
import unittest

from luogu_evaluator import compute_ability_scores
from behavior_analyzer import compute_six_dimension_scores


def _export_data_with_tags(tags):
    return {
        "solved_count": 10,
        "failed_count": 1,
        "summary": {
            "difficulty_histogram": {"3": 5, "4": 3, "5": 2},
            "top_algorithm_tags": [{"name": t, "count": 1} for t in tags],
        },
    }


# 已知"会误算到图论"的标签（修复前会命中裸关键词 "树"）
TREE_DS_DP_TAGS = [
    "树形 DP",         # → DP，不应进图论
    "线段树",          # → DS，不应进图论
    "树状数组",        # → DS，不应进图论
    "字典树",          # → DS，不应进图论
    "二叉树",          # → DS，不应进图论
    "平衡树 Splay",    # → DS，不应进图论
    "树链剖分",        # → DS，不应进图论
    "单调栈",          # → DS，不应进图论（修复前"栈"不命中，但"树"也不命中，安全）
    "树上启发式合并",  # → DS（也是图论技巧，但本实现归 DS，不应进图论）
    "树的最大独立集",  # → DP，不应进图论
]

# 应当被算到"图论"的标签
REAL_GRAPH_TAGS = [
    "图论",            # 命中 "图"
    "图的遍历",        # 命中 "图" + "图的遍历"
    "最短路",          # 命中 "最短路"
    "Dijkstra",       # 命中 "图"（包含 "图" 在 "Dijkstra"... 实际不包含，靠 "图" 之外？
                       #   "Dijkstra" 不含 "图"；测试会发现它**不**被图论命中——这是预期的）
    "网络流",          # 命中 "网络流"
    "并查集",          # 命中 "并查集"
    "Tarjan",         # 命中 "tarjan"
    "LCA",            # 命中 "lca"
    "最近公共祖先 LCA", # 命中 "lca"
    "二分图",          # 命中 "二分图"
    "拓扑排序",        # 命中 "拓扑"
    "基环树",          # 命中 "基环树"
]


class TestAbilityScoresTreeOvermatchFix(unittest.TestCase):
    """luogu_evaluator.compute_ability_scores：图论组不再被 "树" 关键词污染。"""

    def test_tree_dp_does_not_boost_graph(self):
        """只刷"树形 DP"标签时，图论分数不应被它拉高。"""
        data = _export_data_with_tags(TREE_DS_DP_TAGS)
        scores = compute_ability_scores(data)
        # baseline: 同样数量但全是无关标签
        baseline_data = _export_data_with_tags(["xxx", "yyy", "zzz"] * (len(TREE_DS_DP_TAGS) // 3 + 1))
        baseline_scores = compute_ability_scores(baseline_data)

        # 修复后：树系标签对图论分贡献应该和不相关标签一致
        self.assertEqual(
            scores["图论"], baseline_scores["图论"],
            f"图论分被树系标签污染: {scores['图论']} vs baseline {baseline_scores['图论']}",
        )

    def test_tree_dp_boosts_dp_not_graph(self):
        """"树形 DP" 应该让 DP 分高，不应该让图论分高。"""
        data_with_tree_dp = _export_data_with_tags(["树形 DP"] * 10)
        scores = compute_ability_scores(data_with_tree_dp)
        # DP 分应该拿到 +min(18, 10*2) = +18 的加成
        # 图论分应该和 baseline 一致
        baseline_data = _export_data_with_tags([])
        baseline_scores = compute_ability_scores(baseline_data)
        self.assertGreater(scores["动态规划"], baseline_scores["动态规划"])
        self.assertEqual(scores["图论"], baseline_scores["图论"])

    def test_segment_tree_boosts_ds_not_graph(self):
        """"线段树" 应该让 DS 分高，不应该让图论分高。"""
        data = _export_data_with_tags(["线段树"] * 10)
        scores = compute_ability_scores(data)
        baseline = compute_ability_scores(_export_data_with_tags([]))
        self.assertGreater(scores["数据结构"], baseline["数据结构"])
        self.assertEqual(scores["图论"], baseline["图论"])

    def test_real_graph_tags_still_match_graph(self):
        """真正的图论标签仍然应该算到图论。"""
        data = _export_data_with_tags(REAL_GRAPH_TAGS)
        scores = compute_ability_scores(data)
        baseline = compute_ability_scores(_export_data_with_tags([]))
        self.assertGreater(scores["图论"], baseline["图论"])

    def test_tree_graph_specific_keywords_picked_up(self):
        """新加的 "图遍历"/"树的遍历"/"基环树" 等图论专属关键词必须能命中。"""
        for tag in ["图遍历", "树的遍历", "树的直径", "树的重心", "基环树"]:
            data = _export_data_with_tags([tag] * 5)
            scores = compute_ability_scores(data)
            baseline = compute_ability_scores(_export_data_with_tags([]))
            self.assertGreater(
                scores["图论"], baseline["图论"],
                f"图论专属标签 '{tag}' 没能拉高图论分",
            )


class TestSixDimensionTreeOvermatchFix(unittest.TestCase):
    """behavior_analyzer.compute_six_dimension_scores：图论组同样修复。"""

    def test_tree_dp_does_not_boost_graph(self):
        data = {"summary": {
            "difficulty_histogram": {"3": 5},
            "top_algorithm_tags": [{"name": t, "count": 1} for t in TREE_DS_DP_TAGS],
        }, "solved_count": 10}
        scores = compute_six_dimension_scores(data, {})
        baseline = compute_six_dimension_scores(
            {"summary": {"difficulty_histogram": {"3": 5}, "top_algorithm_tags": []},
             "solved_count": 10},
            {},
        )
        self.assertEqual(
            scores["图论"], baseline["图论"],
            f"图论分被树系标签污染: {scores['图论']} vs baseline {baseline['图论']}",
        )

    def test_real_graph_tags_still_match_graph(self):
        data = {"summary": {
            "difficulty_histogram": {"4": 5},
            "top_algorithm_tags": [{"name": t, "count": 2} for t in REAL_GRAPH_TAGS],
        }, "solved_count": 10}
        scores = compute_six_dimension_scores(data, {})
        baseline = compute_six_dimension_scores(
            {"summary": {"difficulty_histogram": {"4": 5}, "top_algorithm_tags": []},
             "solved_count": 10},
            {},
        )
        self.assertGreater(scores["图论"], baseline["图论"])

    def test_tree_graph_specific_keywords_picked_up(self):
        for tag in ["图遍历", "树的遍历", "基环树"]:
            data = {"summary": {
                "difficulty_histogram": {"4": 3},
                "top_algorithm_tags": [{"name": tag, "count": 5}],
            }, "solved_count": 10}
            scores = compute_six_dimension_scores(data, {})
            baseline = compute_six_dimension_scores(
                {"summary": {"difficulty_histogram": {"4": 3}, "top_algorithm_tags": []},
                 "solved_count": 10},
                {},
            )
            self.assertGreater(
                scores["图论"], baseline["图论"],
                f"图论专属标签 '{tag}' 没能拉高图论分",
            )


if __name__ == "__main__":
    unittest.main()
