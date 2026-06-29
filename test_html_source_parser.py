"""test_html_source_parser.py - v3.11.0
html_source_parser 单元测试 (不依赖网络 / 不依赖 flask)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import html_source_parser as hsp
import problemset_index as pi


SAMPLE_FULL = """
<!DOCTYPE html>
<html>
<head>
  <title>张三 的个人中心 - 洛谷</title>
  <script id="__NEXT_DATA__" type="application/json">
{"props":{"pageProps":{"user":{"uid":123456,"name":"张三"},"practiceData":{"passed":[{"pid":"P1000","title":"超级玛丽游戏","difficulty":1,"tags":[1,2],"status":12},{"pid":"P1001","title":"A+B Problem","difficulty":1,"tags":[1],"status":12},{"pid":"P3811","title":"乘法逆元","difficulty":3,"tags":[5,7],"status":12}],"submitted":[{"pid":"P1002","title":"写文件","difficulty":2,"tags":[3],"status":4},{"pid":"P1003","title":"数组","difficulty":2,"tags":[3],"status":4},{"pid":"P3379","title":"LCA","difficulty":5,"tags":[6],"status":4}]}}}}
  </script>
</head>
<body><a href="/user/123456">主页</a></body>
</html>
"""

# 含 LaTeX + 转义换行
SAMPLE_LATEX = (
    '<script>{"props":{"pageProps":{"passed":[{"pid":"P1000","title":"X",'
    '"difficulty":1,"status":12,"hint":"$$a^2+b^2=c^2$$"}],'
    '"submitted":[{"pid":"P1001","title":"Y","difficulty":1,"status":4}]}}}\n</script>'
)

# 完全没 passed
SAMPLE_EMPTY = "<html><body>" + ("foo bar baz " * 20) + "</body></html>"


def t1_full():
    out = hsp.parse_html_source(SAMPLE_FULL)
    assert out["source"] == "html_source"
    assert out["user"]["uid"] == 123456
    assert out["user"]["name"] == "张三"
    assert len(out["passed_items"]) == 3, f"got {len(out['passed_items'])}"
    assert len(out["failed_items"]) == 3, f"got {len(out['failed_items'])}"
    assert out["stats"]["passed"] == 3
    assert out["stats"]["failed"] == 3
    assert out["stats"]["total"] == 6
    # 每条 item 字段齐
    p0 = out["passed_items"][0]
    assert p0["pid"] == "P1000"
    assert p0["title"] == "超级玛丽游戏"
    assert p0["difficulty"] == 1
    assert p0["difficulty_name"] == "入门"
    assert p0["status"] == "passed"
    # failed 数组 (status != 12)
    f0 = out["failed_items"][0]
    assert f0["status"] == "failed"
    # records = passed + failed
    assert len(out["records"]) == 6
    print("  [OK] t1_full: passed=3 failed=3 uid=123456 name=张三")


def t2_latex():
    out = hsp.parse_html_source(SAMPLE_LATEX)
    assert len(out["passed_items"]) == 1
    assert out["passed_items"][0]["pid"] == "P1000"
    assert len(out["failed_items"]) == 1
    assert out["failed_items"][0]["pid"] == "P1001"
    print("  [OK] t2_latex: LaTeX $$...$$ 占位 + 换行 都能 parse")


def t3_empty():
    try:
        hsp.parse_html_source(SAMPLE_EMPTY)
        assert False, "should have raised"
    except hsp.HtmlSourceParseError as e:
        assert "passed" in str(e)
        print(f"  [OK] t3_empty: 正确抛错 ({e})")


def t4_empty_string():
    for bad in ["", "   ", None, 123, "x" * 50]:  # 短于 80
        try:
            hsp.parse_html_source(bad)  # type: ignore
            assert False, f"should have raised for {bad!r}"
        except (hsp.HtmlSourceParseError, TypeError):
            pass
    print("  [OK] t4_empty_string: 空串/非 str/过短 都拒绝")


def t5_uid_hint():
    """URL 没 /user/X 时用 form 的 uid_hint 兜底"""
    src = '<script>{"passed":[{"pid":"P1000","title":"X","difficulty":1,"status":12}],"submitted":[]}</script>'
    out = hsp.parse_html_source(src, uid_hint=888, name_hint="兜底名")
    assert out["user"]["uid"] == 888
    assert out["user"]["name"] == "兜底名"
    print("  [OK] t5_uid_hint: form 的 uid/name 兜底")


def t6_difficulty_name():
    """difficulty_name 跟 problemset_index 的 get_difficulty_name 一致"""
    assert pi.get_difficulty_name(0) == "暂无评定"
    assert pi.get_difficulty_name(1) == "入门"
    assert pi.get_difficulty_name(2) == "普及−"
    assert pi.get_difficulty_name(3) == "普及/提高−"
    assert pi.get_difficulty_name(4) == "普及+/提高"
    assert pi.get_difficulty_name(5) == "提高+/省选−"
    assert pi.get_difficulty_name(6) == "省选/NOI−"
    assert pi.get_difficulty_name(7) == "NOI/NOI+/CTSC"
    assert pi.get_difficulty_name(None) == "暂无评定"
    assert pi.get_difficulty_name(99) == "暂无评定"
    assert pi.get_difficulty_name("foo") == "暂无评定"
    print("  [OK] t6_difficulty_name: 8 档 + 边界值全对")


def t7_enrich_export():
    """enrich_export_data 会补 difficulty_name"""
    pi.download_and_build(progress_cb=lambda s, d, t: None)
    export = {
        "passed_items": [{"pid": "P1000", "difficulty": 1, "difficulty_name": ""}],
        "failed_items": [{"pid": "P3811", "difficulty": 3, "difficulty_name": ""}],
        "records": [],
    }
    stats = pi.enrich_export_data(export)
    assert stats["passed"] >= 1, f"got {stats}"
    assert export["passed_items"][0].get("difficulty_name") == "入门"
    assert export["failed_items"][0].get("difficulty_name") == "普及/提高−"
    print(f"  [OK] t7_enrich_export: difficulty_name 已补 (stats={stats})")


def main():
    print("=" * 60)
    print(" html_source_parser + difficulty_name 单元测试 (v3.11.0)")
    print("=" * 60)

    print("\n--- t1 full sample ---")
    t1_full()

    print("\n--- t2 LaTeX + 换行 ---")
    t2_latex()

    print("\n--- t3 empty ---")
    t3_empty()

    print("\n--- t4 empty/short ---")
    t4_empty_string()

    print("\n--- t5 uid_hint 兜底 ---")
    t5_uid_hint()

    print("\n--- t6 difficulty_name 映射表 ---")
    t6_difficulty_name()

    print("\n--- t7 enrich_export_data 补 difficulty_name ---")
    t7_enrich_export()

    print("\n" + "=" * 60)
    print(" ALL PASS ✅")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
