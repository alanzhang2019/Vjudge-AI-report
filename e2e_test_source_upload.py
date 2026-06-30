"""e2e_test_source_upload.py - 端到端测试 /upload-source 是否还报 'no such column: html_path'
直接打公网 43.163.26.115:5000
"""
import json
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from http.cookiejar import CookieJar

BASE = "http://43.163.26.115:5000"

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


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def post_form(path, data):
    body = urllib.parse.urlencode(data, doseq=True).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    opener = urllib.request.build_opener(NoRedirect)
    try:
        resp = opener.open(req, timeout=30)
        return resp.status, resp.read().decode("utf-8", errors="replace"), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace"), dict(e.headers)


def get_status(task_id):
    """GET /status/<task_id>, 解析 HTML 里的 status/message/stage
    STATUS_HTML 模板用 {{ status }} / {{ message }} / {{ stage }} 直接渲染。
    用更鲁棒的正则: 找 "app-pill-done|app-pill-error|app-pill-running" 后的文案,
    以及 message / stage 字段。
    """
    try:
        with urllib.request.urlopen(f"{BASE}/status/{task_id}", timeout=10) as r:
            html = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None, f"HTTP error: {e}", ""
    import re
    # 1) status pill: <span class="app-pill ..."> ⏳进行中 / ✅完成 / ❌失败 </span>
    m_pill = re.search(r'app-pill[^"]*"[^>]*>\s*([^<]+?)\s*</span>', html, re.S)
    status = re.sub(r'\s+', ' ', m_pill.group(1)).strip() if m_pill else "?"
    # 2) 通用 message: <p class="text-gray-700 mb-6">{{ message }}</p>
    m_msg = re.search(r'text-gray-700[^>]*mb-6[^>]*>\s*([^<]+?)\s*</p>', html, re.S)
    if m_msg:
        msg = re.sub(r'\s+', ' ', m_msg.group(1)).strip()
    else:
        # 2b) 兜底: 找 vjudge_report error 卡的 text-rose-600
        m_err = re.search(r'text-rose-600[^>]*>\s*([^<]+?)\s*</p>', html, re.S)
        if m_err:
            msg = re.sub(r'\s+', ' ', m_err.group(1)).strip()
        else:
            msg = "(no message)"
    return status, msg, html


def main():
    print(f"=== 端到端: POST {BASE}/upload-source ===")
    print(f"[1/3] 提交 HTML 源码 ({len(SAMPLE_HTML)} bytes)")
    code, body, hdrs = post_form("/upload-source", {
        "html_source": SAMPLE_HTML,
        "student_name": "张三",
        "school": "测试中学",
        "grade": "高一",
        "luogu_uid": "123456",
        "exam_type": "noi_csp",
    })
    print(f"  → HTTP {code}")
    if code == 302:
        loc = hdrs.get("Location", "")
        print(f"  Location: {loc}")
        m = loc.rstrip("/").rsplit("/", 1)
        if len(m) != 2:
            print("  [ERR] redirect 路径不对:", loc); return 1
        task_id = m[1]
    elif code in (200, 201) and "task_id" in body.lower():
        try:
            j = json.loads(body)
            task_id = j.get("task_id") or j.get("taskId")
        except Exception:
            task_id = None
        if not task_id:
            print(f"  [ERR] 没拿到 task_id: {body[:300]}")
            return 1
    else:
        print(f"  [ERR] 提交失败: {body[:300]}")
        return 1
    print(f"  task_id: {task_id}")

    print(f"\n[2/3] 轮询 status")
    last_msg = ""
    last_status = ""
    for i in range(50):
        time.sleep(5)
        status, msg, _ = get_status(task_id)
        if msg != last_msg or status != last_status:
            print(f"  t+{i*5:>3d}s status={status!r}  msg={msg!r}")
            last_msg, last_status = msg, status
        if "完成" in status or "失败" in status or "done" in (status or "").lower() or "error" in (status or "").lower():
            break
    else:
        print("  [TIMEOUT] 250s 内未结束")
        return 2

    print(f"\n[3/3] 检查是否含 'no such column: html_path'")
    full = f"{status} | {msg}"
    if "no such column" in full or "html_path" in full:
        print(f"  ❌ 仍然报: {full}")
        return 3
    if "完成" in status or "✅" in status:
        print(f"  ✅ 端到端通过: {full}")
        return 0
    print(f"  ❌ status={status!r} msg={msg!r}")
    return 4


if __name__ == "__main__":
    sys.exit(main())
