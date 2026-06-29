"""test_zip_bundle_loader.py - v3.11.0

zip_bundle_loader 单元测试:
  1) 构造一个最小的 schema v1 ZIP
  2) load_zip_bytes 解析, 校验各字段
  3) 错误用例:
     - schema_version 不匹配 → BundleLoadError
     - ZIP 损坏 → BundleLoadError
     - 空字节流 → BundleLoadError
     - export_data 不是 dict → BundleLoadError
     - 缺 manifest.json → BundleLoadError
  4) 写一份最小可用的 export_data 喂给 _generate_ai_report_artifacts 的依赖函数
     (用 _resolve_source_code_progress 做冒烟)

跑法:
  cd c:\\Users\\zpy20\\Desktop\\项目\\luoguAI\\Vjudge-AI-report
  python test_zip_bundle_loader.py
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import zipfile
from pathlib import Path


# 让脚本可以从仓库根目录导入 zip_bundle_loader
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _make_minimal_zip() -> bytes:
    """构造一个 schema_version=1 的最小 ZIP, 内容合理"""
    manifest = {
        "schema_version": 1,
        "luogu_uid": "123456",
        "username": "test_user",
        "name": "测试选手",
        "generated_at_iso": "2026-06-28T12:00:00+08:00",
        "solved_count": 50,
        "failed_count": 5,
    }
    export_data = {
        "schema_version": 1,
        "generated_at": 1751083200,
        "student_info": {
            "name": "测试选手",
            "school": "测试学校",
            "grade": "高一",
            "luogu_uid": "123456",
            "eval_time": "2026-06-28 12:00:00",
        },
        "solved_count": 50,
        "failed_count": 5,
        "summary": {
            "avg_difficulty": 4.2,
            "top_tag": "动态规划",
            "difficulty_histogram": {"0": 5, "1": 8, "2": 12, "3": 10, "4": 8, "5": 5, "6": 2},
            "top_algorithm_tags": ["动态规划", "图论", "数据结构"],
        },
        "passed_items": [
            {"pid": "P1000", "title": "超级玛丽游戏", "difficulty": 1, "tags": []},
            {"pid": "P1001", "title": "A+B Problem", "difficulty": 0, "tags": []},
        ],
        "failed_items": [
            {"pid": "P2000", "title": "某道难题", "difficulty": 7, "tags": []},
        ],
        "records": [],
        "detail_fetch_stats": {
            "total_items": 3,
            "source_code_success": 2,
        },
        "behavior_analysis": {
            "submission_count": 100,
            "ac_rate": 0.55,
            "active_days": 30,
        },
        "syllabus_evaluation": {},
        "six_dimension_scores": {},
        "tags": {"by_id": {}},
    }
    passed_item = {"pid": "P1000", "title": "超级玛丽游戏"}
    failed_item = {"pid": "P2000", "title": "某道难题"}

    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        zf.writestr("export_data.json", json.dumps(export_data, ensure_ascii=False, indent=2))
        zf.writestr("items/passed/P1000.json", json.dumps(passed_item, ensure_ascii=False))
        zf.writestr("items/failed/P2000.json", json.dumps(failed_item, ensure_ascii=False))
    return bio.getvalue()


def test_happy_path() -> None:
    from zip_bundle_loader import load_zip_bytes, ReportBundle, BundleLoadError

    print("▶ test_happy_path ...", end=" ")
    data = _make_minimal_zip()
    bundle = load_zip_bytes(data, "test.zip")
    assert isinstance(bundle, ReportBundle)
    assert bundle.schema_version == 1
    assert bundle.luogu_uid == "123456"
    assert bundle.username == "test_user"
    assert bundle.name == "测试选手"
    assert bundle.solved_count == 50
    assert bundle.failed_count == 5
    assert bundle.summary_line() == (
        "uid=123456 username=test_user name=测试选手 "
        "passed=50 failed=5 schema=v1"
    )
    assert len(bundle.passed_items) == 1
    assert len(bundle.failed_items) == 1
    assert bundle.passed_items[0]["pid"] == "P1000"
    assert bundle.failed_items[0]["pid"] == "P2000"
    assert isinstance(bundle.export_data, dict)
    assert bundle.export_data["student_info"]["name"] == "测试选手"
    assert bundle.export_data["solved_count"] == 50
    print("OK")


def test_wrong_schema() -> None:
    from zip_bundle_loader import load_zip_bytes, BundleLoadError

    print("▶ test_wrong_schema ...", end=" ")
    data = _make_minimal_zip()
    # 把 manifest 的 schema_version 改成 99
    import zipfile
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
        # 故意写个 schema_version=99 的 manifest
        bad_manifest = {"schema_version": 99, "luogu_uid": "x"}
        zf.writestr("manifest.json", json.dumps(bad_manifest))
        zf.writestr("export_data.json", json.dumps({"student_info": {}}))
    try:
        load_zip_bytes(bio.getvalue(), "bad.zip")
        raise AssertionError("应该抛 BundleLoadError")
    except BundleLoadError as e:
        assert "schema_version" in str(e), f"错误信息应提到 schema_version: {e}"
    print("OK")


def test_empty_bytes() -> None:
    from zip_bundle_loader import load_zip_bytes, BundleLoadError

    print("▶ test_empty_bytes ...", end=" ")
    try:
        load_zip_bytes(b"", "empty.zip")
        raise AssertionError("应该抛 BundleLoadError")
    except BundleLoadError as e:
        assert "空" in str(e), f"错误信息应提到空: {e}"
    print("OK")


def test_corrupted_zip() -> None:
    from zip_bundle_loader import load_zip_bytes, BundleLoadError

    print("▶ test_corrupted_zip ...", end=" ")
    try:
        load_zip_bytes(b"this is not a zip", "bad.zip")
        raise AssertionError("应该抛 BundleLoadError")
    except BundleLoadError as e:
        assert "ZIP" in str(e), f"错误信息应提到 ZIP: {e}"
    print("OK")


def test_missing_manifest() -> None:
    from zip_bundle_loader import load_zip_bytes, BundleLoadError

    print("▶ test_missing_manifest ...", end=" ")
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("export_data.json", json.dumps({"student_info": {}}))
    try:
        load_zip_bytes(bio.getvalue(), "no_manifest.zip")
        raise AssertionError("应该抛 BundleLoadError")
    except BundleLoadError as e:
        assert "manifest.json" in str(e), f"错误信息应提到 manifest.json: {e}"
    print("OK")


def test_export_data_not_dict() -> None:
    from zip_bundle_loader import load_zip_bytes, BundleLoadError

    print("▶ test_export_data_not_dict ...", end=" ")
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps({"schema_version": 1}))
        zf.writestr("export_data.json", json.dumps([1, 2, 3]))  # 故意写成 list
    try:
        load_zip_bytes(bio.getvalue(), "weird.zip")
        raise AssertionError("应该抛 BundleLoadError")
    except BundleLoadError as e:
        assert "dict" in str(e), f"错误信息应提到 dict: {e}"
    print("OK")


def test_load_from_disk() -> None:
    """load_zip() 从磁盘路径读"""
    from zip_bundle_loader import load_zip, BundleLoadError

    print("▶ test_load_from_disk ...", end=" ")
    data = _make_minimal_zip()
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
        f.write(data)
        tmp_path = Path(f.name)
    try:
        bundle = load_zip(tmp_path)
        assert bundle.schema_version == 1
        assert bundle.solved_count == 50
    finally:
        tmp_path.unlink(missing_ok=True)

    # 不存在的文件
    try:
        load_zip("nonexistent_zip_file_12345.zip")
        raise AssertionError("应该抛 BundleLoadError")
    except BundleLoadError as e:
        assert "不存在" in str(e)
    print("OK")


def test_integration_with_webapp_helpers() -> None:
    """冒烟: 模拟 run_zip_generation() 会用的辅助函数"""
    from zip_bundle_loader import load_zip_bytes

    print("▶ test_integration_with_webapp_helpers ...", end=" ")
    data = _make_minimal_zip()
    bundle = load_zip_bytes(data, "test.zip")

    # 模拟 run_zip_generation 里的字段提取
    export_data = bundle.export_data
    student_info = export_data.get("student_info") or {}
    student_name = student_info.get("name") or bundle.name or "未知选手"
    school = student_info.get("school") or "未知学校"
    grade = student_info.get("grade") or "未知年级"
    luogu_uid = bundle.luogu_uid or student_info.get("luogu_uid") or ""

    assert student_name == "测试选手"
    assert school == "测试学校"
    assert grade == "高一"
    assert luogu_uid == "123456"
    assert bundle.solved_count == 50
    assert bundle.failed_count == 5
    print("OK")


def main() -> int:
    print("=" * 60)
    print(" zip_bundle_loader 单元测试 (v3.11.0)")
    print("=" * 60)
    tests = [
        test_happy_path,
        test_wrong_schema,
        test_empty_bytes,
        test_corrupted_zip,
        test_missing_manifest,
        test_export_data_not_dict,
        test_load_from_disk,
        test_integration_with_webapp_helpers,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"FAIL: {t.__name__}: {e!r}")
    print("=" * 60)
    print(f" {passed}/{passed + failed} passed, {failed} failed")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
