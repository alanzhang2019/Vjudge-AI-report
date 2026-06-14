"""Test regex on multiple 6-dim table formats."""
import re

# Test 1: Old format (both key and score bold)
test1 = """| 能力块 | 评分 | 当前等级 | 数据证据 | 已经具备 |
|:---|:---:|:---|:---|:---|
| **基础算法** | **72** | 🟢精通 | 模拟、贪心 | 扎实 |
| **数据结构** | **85** | 🟢精通 | 线段树 | 标准 |
| **图论** | **60** | 🟡熟练 | 最短路 | 模板 |
| **动态规划** | **80** | 🟢精通 | DP | 多维 |
| **字符串** | **40** | 🟠基础 | KMP | 自动机 |
| **数学** | **55** | 🟡熟练 | 组合 | 基础 |"""

# Test 2: New format (only key bold, score not bold)
test2 = """| 能力块 | 评分 | 当前等级 | 数据证据 | 已经具备 |
|:---|:---:|:---|:---|:---|
| **基础算法** | 95 | 🟢精通 | 模拟、贪心 | 扎实 |
| **数据结构** | 95 | 🟢精通 | 线段树 | 标准 |
| **图论** | 95 | 🟢精通 | 最短路 | 模板 |
| **动态规划** | 95 | 🟢精通 | DP | 多维 |
| **字符串** | 95 | 🟡熟练 | KMP | 自动机 |
| **数学** | 95 | 🟡熟练 | 组合 | 基础 |"""

# Test 3: Plain text format
test3 = """| 能力块 | 评分 | 当前等级 | 数据证据 | 已经具备 |
|:---|:---:|:---|:---|:---|
| 基础算法 | 72 | 🟢精通 | 模拟、贪心 | 扎实 |
| 数据结构 | 85 | 🟢精通 | 线段树 | 标准 |
| 图论 | 60 | 🟡熟练 | 最短路 | 模板 |
| 动态规划 | 80 | 🟢精通 | DP | 多维 |
| 字符串 | 40 | 🟠基础 | KMP | 自动机 |
| 数学 | 55 | 🟡熟练 | 组合 | 基础 |"""

def extract(md):
    six_dim_keys = ["基础算法", "数据结构", "图论", "动态规划", "字符串", "数学"]
    out = {}
    for k in six_dim_keys:
        m = None
        # 格式 A
        m = re.search(rf"\*\*\s*{re.escape(k)}\s*\*\*\s*\|\s*\*\*\s*(\d+)\s*\*\*", md)
        if not m:
            # 格式 B
            m = re.search(
                rf"\*\*\s*{re.escape(k)}\s*\*\*\s*\|\s*\*?\s*(\d{{1,3}})\s*\|",
                md,
            )
        if not m:
            # 格式 C
            m = re.search(
                rf"\|\s*{re.escape(k)}\s*\|\s*(\d{{1,3}})\s*\|",
                md,
            )
        if m:
            try:
                v = int(m.group(1))
                if 0 <= v <= 100:
                    out[k] = v
            except Exception:
                pass
    return out

print("Test 1 (old format, both bold):", extract(test1))
print("Test 2 (new format, only key bold):", extract(test2))
print("Test 3 (plain format):", extract(test3))

assert extract(test1) == {"基础算法": 72, "数据结构": 85, "图论": 60, "动态规划": 80, "字符串": 40, "数学": 55}, "Test 1 failed"
assert extract(test2) == {"基础算法": 95, "数据结构": 95, "图论": 95, "动态规划": 95, "字符串": 95, "数学": 95}, "Test 2 failed"
assert extract(test3) == {"基础算法": 72, "数据结构": 85, "图论": 60, "动态规划": 80, "字符串": 40, "数学": 55}, "Test 3 failed"
print("\nAll tests passed!")
