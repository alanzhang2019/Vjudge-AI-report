"""v3.10.0 邮箱注册修复验证脚本（落盘到 .verify_v3100_register/）

用法（在项目根目录的 PowerShell 里跑）：
    python .verify_v3100_register.py

跑完后会生成这些文件，每个我都用 Read 工具读：
  - 000_health.txt           oi.aijiangti.cn/api/version 的 JSON 输出
  - 010_register_get.html    GET /register 完整 HTML（200 应有表单，500 就是诊断页）
  - 020_register_post.html   POST /register 完整 HTML（302 跳走 = 成功 / 200 = 校验错 / 500 = 服务端异常）
  - 030_register_post_extracted.txt  关键字段（状态码 / 标题 / 红色错误 / Location header）
  - 040_create_student_direct.txt     直接在本地调 admin_students.create_student() 的诊断
  - 050_hash_password_direct.txt      直接在本地调 admin_students.hash_password() 的诊断（验证 import os 修复）

判定：
  - 020 里看到 "⚠️ 注册失败：name 'os' is not defined" → 还有缓存，需重启容器
  - 020 里看到 302 + Location: /me/... → 修复成功
  - 020 里看到 500 + 标题 "Internal Server Error" → 还有别的 bug
  - 050 显示 "OK pbkdf2_sha256$200000$..." → 修好了
  - 050 显示 "NameError: name 'os' is not defined" → 修复没生效
"""
import os
import sys
import re
import json
import time
import traceback
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from pathlib import Path

OUT = Path(__file__).resolve().parent / ".verify_v3100_register"
OUT.mkdir(exist_ok=True)

BASE = "https://oi.aijiangti.cn"


def nowstamp() -> str:
    return datetime.now().strftime("%H%M%S")


def write(name: str, content: str) -> Path:
    p = OUT / name
    p.write_text(content, encoding="utf-8")
    return p


def fetch(url: str, *, data: bytes | None = None, method: str = "GET", headers: dict | None = None) -> tuple[int, dict, str]:
    """返回 (status, headers_dict, body_text)"""
    req = urllib.request.Request(
        url, data=data, method=method,
        headers=headers or {"User-Agent": "verify_v3100_register/1.0"},
    )
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **kw): return None
    opener = urllib.request.build_opener(NoRedirect)
    try:
        r = opener.open(req, timeout=30)
        return r.status, dict(r.headers), r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", errors="replace")


# 1) 健康检查
print("=" * 60)
print(f"[1/5] 容器健康检查 {BASE}/api/version")
print("=" * 60)
try:
    status, headers, body = fetch(f"{BASE}/api/version")
    write("000_health.txt", f"status={status}\nheaders={json.dumps(dict(headers), ensure_ascii=False, indent=2)}\nbody={body}\n")
    print(f"  status={status}  body[:200]={body[:200]!r}")
except Exception as e:
    write("000_health.txt", f"EXC: {e!r}\n{traceback.format_exc()}")
    print(f"  EXC: {e!r}")

# 2) GET /register（确认页面能渲染）
print("=" * 60)
print(f"[2/5] GET /register（拿表单）")
print("=" * 60)
try:
    status, headers, body = fetch(f"{BASE}/register")
    write("010_register_get.html", body)
    # 提取 <title> 和 v3.10.0 pill
    title = (re.search(r"<title>([^<]+)</title>", body) or [None, "?"])[1]
    has_pill = "v3.10.0" in body
    has_form = "<form" in body and 'name="email"' in body
    write("011_register_get_extracted.txt",
          f"status={status}\ntitle={title}\nhas_v3p10_pill={has_pill}\nhas_form={has_form}\n")
    print(f"  status={status}  title={title!r}  pill={has_pill}  form={has_form}")
except Exception as e:
    write("010_register_get.html", f"EXC: {e!r}\n{traceback.format_exc()}")
    print(f"  EXC: {e!r}")

# 3) POST /register（真实注册请求）
print("=" * 60)
print(f"[3/5] POST /register（真实注册）")
print("=" * 60)
ts = int(time.time())
payload = urllib.parse.urlencode({
    "city": "北京",
    "real_name": f"验证用户{ts}",
    "grade": "JUNIOR_1",
    "gender": "M",
    "email": f"verify_{ts}@test.local",
    "password": "VerifyPass1234",
    "password_confirm": "VerifyPass1234",
    "agree": "on",
}).encode("utf-8")
try:
    status, headers, body = fetch(
        f"{BASE}/register", data=payload, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    write("020_register_post.html", body)
    title = (re.search(r"<title>([^<]+)</title>", body) or [None, "?"])[1]
    # 红色错误框
    err_match = re.search(r"app-box app-box-red[^>]*>(.*?)</div>", body, re.DOTALL)
    err = re.sub(r"<[^>]+>", "", err_match.group(1)).strip() if err_match else ""
    location = headers.get("Location", "")
    extracted = (
        f"status={status}\n"
        f"title={title}\n"
        f"location={location}\n"
        f"red_error={err!r}\n"
    )
    write("030_register_post_extracted.txt", extracted)
    print(f"  status={status}  title={title!r}")
    print(f"  location={location!r}")
    print(f"  red_error={err!r}")
except Exception as e:
    write("020_register_post.html", f"EXC: {e!r}\n{traceback.format_exc()}")
    write("030_register_post_extracted.txt", f"EXC: {e!r}\n")
    print(f"  EXC: {e!r}")

# 4) 本地直接调 admin_students.create_student() —— 验证 import os 是否修好
print("=" * 60)
print(f"[4/5] 本地调 admin_students.create_student()（验证 import os 修复）")
print("=" * 60)
try:
    # 跟 web_app.py 一样设安全 baseline 才能 import
    os.environ.setdefault("ADMIN_PASSWORD", "verify-pwd-12345")
    os.environ.setdefault("ADMIN_SESSION_SECRET", "verify-secret-12345-abcdef-ghijkl-mnop")
    os.environ.setdefault("ALLOW_INSECURE_DEFAULT", "1")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from admin_students import create_student, hash_password
    pw_hash = hash_password("TestPass1234")
    out = f"hash_password OK: {pw_hash[:30]}...\n"
    sid = create_student(
        luogu_uid="",
        real_name=f"本地验证{ts}",
        grade="JUNIOR_1",
        city="北京",
        gender="M",
        registered_via="verify_local",
        email=f"local_{ts}@test.local",
        password_hash=pw_hash,
    )
    out += f"create_student OK: id={sid}\n"
    write("040_create_student_direct.txt", out)
    print(f"  {out.strip().replace(chr(10), ' | ')}")
except Exception as e:
    write("040_create_student_direct.txt", f"EXC: {e!r}\n{traceback.format_exc()}")
    print(f"  EXC: {e!r}")

# 5) 本地 hash_password 单独跑
print("=" * 60)
print(f"[5/5] 本地 hash_password 单元测试")
print("=" * 60)
try:
    from admin_students import hash_password, verify_password
    h = hash_password("TestPass1234")
    ok1 = verify_password("TestPass1234", h)
    ok2 = verify_password("Wrong", h)
    out = (
        f"hash 格式: {'BCrypt' if h.startswith('$2') else 'PBKDF2'}\n"
        f"hash 开头: {h[:35]}...\n"
        f"verify(正确): {ok1}\n"
        f"verify(错误): {ok2}\n"
    )
    write("050_hash_password_direct.txt", out)
    print(f"  {out.strip().replace(chr(10), ' | ')}")
except Exception as e:
    write("050_hash_password_direct.txt", f"EXC: {e!r}\n{traceback.format_exc()}")
    print(f"  EXC: {e!r}")

print("=" * 60)
print(f"完成,结果在 {OUT}/")
print(f"  把这 6 个文件路径告诉 IDE 助手,用 Read 工具读 030 / 040 / 050 即可判定修复是否生效")
print("=" * 60)
