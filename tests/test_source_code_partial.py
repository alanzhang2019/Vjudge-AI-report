"""
v3.9.43 单元测试：验证"1 道题源码抓取失败"不再让整份报告 abort。

历史行为（UID 283224 反馈的 12 次连续失败）：
   哪怕只缺 1 道题源码（如 1142/1143 = 99.91%），也 raise RuntimeError，
   用户连续重试 12 次都失败。

新行为：
   1) 软警告（写日志 + 写 task.message）
   2) 报告继续生成（下游 summarize / behavior_analyzer / 知识树都能容忍）
   3) 失败 PID 被记录下来方便用户自查
"""
import unittest

import web_app


class TestSourceCodePartialSuccess(unittest.TestCase):
    """核心修复点：源码抓取 99.91% 成功率不再 abort 整个流程。"""

    def test_all_source_code_success_does_not_warn(self):
        """全部成功时，_build_partial_source_code_warning 应返回 None。"""
        result = web_app._build_partial_source_code_warning(
            source_code_success=10, total_items=10, missing_pids=[]
        )
        self.assertIsNone(result)

    def test_partial_source_code_returns_warning_message(self):
        """1 题缺失时，应返回带 PIDs 的警告消息。"""
        result = web_app._build_partial_source_code_warning(
            source_code_success=1142, total_items=1143, missing_pids=["P1234"]
        )
        self.assertIsNotNone(result)
        self.assertIn("1142/1143", result)
        self.assertIn("P1234", result)
        # 警告应当明确说明"继续生成"
        self.assertIn("继续生成", result)

    def test_multiple_missing_pids_truncated_to_10(self):
        """缺失很多时，PID 列表只显示前 10 个 + '等' 后缀。"""
        pids = [f"P{1000+i}" for i in range(20)]
        result = web_app._build_partial_source_code_warning(
            source_code_success=80, total_items=100, missing_pids=pids, cached_hits=0
        )
        self.assertIn("P1000", result)
        self.assertIn("P1009", result)
        self.assertNotIn("P1019", result)
        self.assertIn("等", result)

    def test_no_source_code_means_full_report_skipped_keeps_going(self):
        """极端：全部失败时（0/N），不应让函数崩溃。"""
        result = web_app._build_partial_source_code_warning(
            source_code_success=0, total_items=10, missing_pids=[f"P{i}" for i in range(10)]
        )
        self.assertIn("0/10", result)


if __name__ == "__main__":
    unittest.main()
