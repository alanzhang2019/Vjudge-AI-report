"""test_local_http.py - 本地 Flask 服务的 HTTP 冒烟测试 (v3.11.0)"""
import json
import io
import zipfile
import urllib.request
import urllib.error
from pathlib import Path

BASE = "http://127.0.0.1:5000"


def make_zip() -> bytes:
    manifest = {
        "schema_version": 1,
        "luogu_uid": "123456",
        "username": "test_user",
        "name": "本地测试同学",
        "generated_at_iso": "2026-06-28T12:00:00+08:00",
        "solved_count": 10,
        "failed_count": 2,
    }
    export_data = {
        "schema_version": 1,
        "student_info": {
            "name": "本地测试同学",
            "school": "测试中学",
            "grade": "高二",
            "luogu_uid": "123456",
            "eval_time": "2026-06-28 12:00:00",
        },
        "solved_count": 10,
        "failed_count": 2,
        "summary": {
            "avg_difficulty": 3.5,
            "top_tag": "动态规划",
            "difficulty_histogram": {"0": 2, "1": 3, "2": 2, "3": 2, "4": 1, "5": 0, "6": 0},
            "top_algorithm_tags": ["动态规划", "图论"],
        },
        "passed_items": [{"pid": "P1000", "title": "A+B", "difficulty": 1, "tags": []}],
        "failed_items": [{"pid": "P2000", "title": "某难题", "difficulty": 7, "tags": []}],
        "records": [],
        "detail_fetch_stats": {"total_items": 2, "source_code_success": 1},
        "behavior_analysis": {"submission_count": 30, "ac_rate": 0.7, "active_days": 10},
        "syllabus_evaluation": {},
        "six_dimension_scores": {},
        "tags": {"by_id": {}},
    }
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
        zf.writestr("export_data.json", json.dumps(export_data, ensure_ascii=False))
    return bio.getvalue()


def build_multipart(fields, file_field, file_name, file_bytes, file_ct="application/zip"):
    """用 Python 标准库构造 multipart/form-data"""
    boundary = "----TestBoundaryABC123"
    body = b""
    for k, v in fields.items():
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode()
        body += str(v).encode("utf-8")
        body += b"\r\n"
    body += f"--{boundary}\r\n".encode()
    body += f'Content-Disposition: form-data; name="{file_field}"; filename="{file_name}"\r\n'.encode()
    body += f"Content-Type: {file_ct}\r\n\r\n".encode()
    body += file_bytes
    body += b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    return body, boundary


def post_no_redirect(url, data, headers):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(url, data=data, method="POST", headers=headers)
    try:
        r = opener.open(req, timeout=15)
        return r.status, r.headers.get("Location"), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location"), e.read()


def main():
    print("=" * 60)
    print(" 本地 Flask 服务冒烟测试 (v3.11.0)")
    print("=" * 60)

    # 1) 首页
    r = urllib.request.urlopen(f"{BASE}/", timeout=5)
    body = r.read()
    print(f"[1] GET /                 -> {r.status}  {len(body)} bytes")
    assert r.status == 200
    assert b"v3.11.0" in body, "首页应展示 v3.11.0"
    assert b"/upload-zip" in body, "首页应包含 /upload-zip 入口链接"

    # 2) /upload-zip 页面
    r = urllib.request.urlopen(f"{BASE}/upload-zip", timeout=5)
    body = r.read()
    print(f"[2] GET /upload-zip       -> {r.status}  {len(body)} bytes")
    assert r.status == 200
    assert b"zip_file" in body, "upload-zip 页面应包含 zip_file 字段"

    # 3) /api/version
    r = urllib.request.urlopen(f"{BASE}/api/version", timeout=5)
    body = json.loads(r.read())
    print(f"[3] GET /api/version      -> {r.status}  version={body.get('version')}")
    assert body.get("version") == "v3.11.0", f"期望 v3.11.0, 实际 {body.get('version')}"

    # 4) POST /upload-zip 正常用例
    zip_bytes = make_zip()
    fields = {
        "api_key": "",
        "student_name": "本地测试同学",
        "school": "测试中学",
        "grade": "高二",
        "luogu_uid": "123456",
        "exam_type": "noi_csp",
        "report_type": "full",
    }
    body, boundary = build_multipart(fields, "zip_file", "test_bundle.zip", zip_bytes)
    status, loc, resp = post_no_redirect(
        f"{BASE}/upload-zip",
        body,
        {"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    print(f"[4] POST /upload-zip      -> {status}  Location={loc}")
    assert status in (302, 303, 307), f"期望重定向, 实际 {status}"
    assert loc and loc.startswith("/status/"), f"应跳到 /status/<id>, 实际 {loc}"
    task_id = loc.rsplit("/", 1)[-1]
    print(f"    task_id = {task_id}")

    # 5) 状态页
    r = urllib.request.urlopen(f"{BASE}/status/{task_id}", timeout=5)
    body = r.read()
    print(f"[5] GET /status/{task_id} -> {r.status}  {len(body)} bytes")
    assert r.status == 200
    # 状态页是 JS 异步拉任务状态,初始 HTML 不会包含 task_id 字符串
    # 但页面标题/资源应能加载
    assert len(body) > 500, f"状态页内容过短: {len(body)} bytes"

    # 6) 错误用例 1: 不是 ZIP
    fields2 = dict(fields)
    body, boundary = build_multipart(fields2, "zip_file", "bad.txt", b"hello world", file_ct="text/plain")
    status, loc, resp = post_no_redirect(
        f"{BASE}/upload-zip",
        body,
        {"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    print(f"[6] POST /upload-zip (.txt) -> {status}")
    assert status == 400, f"非 .zip 文件应返回 400, 实际 {status}"

    # 7) 错误用例 2: ZIP 字节损坏(扩展名是 .zip 但内容不是)
    # 预期: 前端通过扩展名/大小校验 → 创建任务 → 302 跳到 /status
    #       后台线程会在解析时 fail,status 页会显示错误
    fields3 = dict(fields)
    body, boundary = build_multipart(fields3, "zip_file", "bad.zip", b"not a zip content")
    status, loc, resp = post_no_redirect(
        f"{BASE}/upload-zip",
        body,
        {"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    print(f"[7] POST /upload-zip (坏ZIP) -> {status}  Location={loc}")
    assert status == 302, f"坏 ZIP 也应该创建任务, 实际 {status}"
    bad_task_id = loc.rsplit("/", 1)[-1]

    # 8) 错误用例 3: 空文件
    fields4 = dict(fields)
    body, boundary = build_multipart(fields4, "zip_file", "empty.zip", b"")
    status, loc, resp = post_no_redirect(
        f"{BASE}/upload-zip",
        body,
        {"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    print(f"[8] POST /upload-zip (空文件) -> {status}  (期望 400)")
    assert status == 400, f"空文件应返回 400, 实际 {status}"

    # 9) 等几秒, 让坏 ZIP 后台线程解析并写入错误状态
    import time
    time.sleep(2)
    r = urllib.request.urlopen(f"{BASE}/status/{bad_task_id}", timeout=5)
    bad_body = r.read()
    print(f"[9] GET /status/{bad_task_id} -> {r.status}  {len(bad_body)} bytes (等 2s)")
    assert r.status == 200

    print()
    print("=" * 60)
    print(" ✅ 9/9 HTTP 测试全部通过")
    print("=" * 60)


if __name__ == "__main__":
    main()
