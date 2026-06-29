"""test_source_http.py - HTTP 冒烟测试 /upload-source 入口 (v3.11.0)
先起 web_app.py:5000, 然后跑下面的步骤
"""
import json
import urllib.parse
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:5000"

# 模拟一份"用户粘贴的洛谷练习页源码"
SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>张三 的个人中心 - 洛谷</title>
  <script id="__NEXT_DATA__" type="application/json">
{"props":{"pageProps":{"user":{"uid":123456,"name":"张三"},"practiceData":{"passed":[{"pid":"P1000","title":"超级玛丽游戏","difficulty":1,"tags":[1,2],"status":12},{"pid":"P1001","title":"A+B Problem","difficulty":1,"tags":[1],"status":12},{"pid":"P3811","title":"乘法逆元","difficulty":3,"tags":[5,7],"status":12}],"submitted":[{"pid":"P1002","title":"写文件","difficulty":2,"tags":[3],"status":4},{"pid":"P3379","title":"LCA","difficulty":5,"tags":[6],"status":4}]}}}}
  </script>
</head>
<body><a href="/user/123456">主页</a></body>
</html>
"""


def _post_form(path: str, data: dict, *, timeout: int = 10, follow_redirects: bool = False):
    """POST application/x-www-form-urlencoded, 不 follow redirect"""
    body = urllib.parse.urlencode(data, doseq=True).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    opener = urllib.request.build_opener(NoRedirect)
    try:
        resp = opener.open(req, timeout=timeout)
        return resp.status, resp.read().decode("utf-8", errors="replace"), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace"), dict(e.headers)


def t1_get_form():
    """GET /upload-source 应返回 200 + 含 textarea 的 HTML"""
    r = urllib.request.urlopen(f"{BASE}/upload-source", timeout=5)
    html = r.read().decode("utf-8")
    assert r.status == 200, f"期望 200, 实际 {r.status}"
    assert "htmlSource" in html, "表单应含 #htmlSource textarea"
    assert "粘贴洛谷练习页源码" in html, "应含标题"
    assert "/upload-source" in html, "应含 action"
    print("  [OK] t1_get_form: GET /upload-source → 200, 含表单")


def t2_post_empty():
    """POST 粘空内容 → 400"""
    code, body, _ = _post_form("/upload-source", {"html_source": ""})
    assert code == 400, f"期望 400, 实际 {code}: {body[:200]}"
    j = json.loads(body)
    assert j.get("ok") is False
    assert "未粘贴" in j.get("message", "")
    print(f"  [OK] t2_post_empty: → {code} {j.get('message')!r}")


def t3_post_too_short():
    """POST 过短内容 (< 80 字符) → 400"""
    code, body, _ = _post_form("/upload-source", {"html_source": "x" * 50})
    assert code == 400, f"期望 400, 实际 {code}: {body[:200]}"
    j = json.loads(body)
    assert "过短" in j.get("message", "") or "短" in j.get("message", "")
    print(f"  [OK] t3_post_too_short: → {code} {j.get('message')!r}")


def t4_post_valid():
    """POST 完整源码 → 302 redirect 到 /status/<task_id>"""
    code, body, hdrs = _post_form(
        "/upload-source",
        {
            "html_source": SAMPLE_HTML,
            "student_name": "测试学员",
            "school": "测试学校",
            "grade": "高一",
            "luogu_uid": "123456",
            "exam_type": "noi_csp",
        },
    )
    assert code in (301, 302, 303, 307, 308), f"期望 30x 重定向, 实际 {code}: {body[:200]}"
    loc = hdrs.get("Location", "") or hdrs.get("location", "")
    assert "/status/" in loc, f"重定向应到 /status/, 实际 {loc!r}"
    task_id = loc.rsplit("/", 1)[-1]
    print(f"  [OK] t4_post_valid: → {code} {loc} (task_id={task_id[:8]}...)")
    return task_id


def t5_status_page(task_id: str):
    """GET /status/<task_id> → 200 + 含学员名"""
    r = urllib.request.urlopen(f"{BASE}/status/{task_id}", timeout=5)
    html = r.read().decode("utf-8")
    assert r.status == 200
    assert "测试学员" in html or "源码" in html or task_id[:8] in html
    print(f"  [OK] t5_status_page: /status/{task_id[:8]}... → 200")


def t6_index_has_source_link():
    """首页应含 /upload-source 链接"""
    r = urllib.request.urlopen(f"{BASE}/", timeout=5)
    html = r.read().decode("utf-8", errors="replace")
    assert "/upload-source" in html, "首页应含 /upload-source 入口"
    assert "粘贴" in html
    print("  [OK] t6_index_has_source_link: 首页含 /upload-source 入口")


def main():
    print("=" * 60)
    print(" /upload-source HTTP 冒烟测试 (v3.11.0)")
    print("=" * 60)

    print("\n--- t1 GET /upload-source ---")
    t1_get_form()

    print("\n--- t2 POST 空 ---")
    t2_post_empty()

    print("\n--- t3 POST 过短 ---")
    t3_post_too_short()

    print("\n--- t6 首页入口 ---")
    t6_index_has_source_link()

    print("\n--- t4 POST 完整源码 ---")
    task_id = t4_post_valid()

    print("\n--- t5 状态页 ---")
    t5_status_page(task_id)

    print("\n" + "=" * 60)
    print(" ALL PASS ✅")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
