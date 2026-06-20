"""
test_v3100_register_regression.py — v3.10.0.2 邮箱注册回归测试

覆盖本次 bug 修复 + 周边回归点：
  A. 密码哈希单元
     1) hash_password + verify_password 双向 (BCrypt 主路径)
     2) hash_password 盐唯一 (两次哈希同密码应不同)
     3) verify_password 对错误密码返回 False
     4) verify_password 对空 hash / 异常 hash 安全降级 False
     5) **核心回归**:hash_password 在 bcrypt 不可用时走 PBKDF2 兜底分支
        —— 这是 v3.10.0.2 修复的 NameError(name 'os' is not defined)
     6) verify_password 对 PBKDF2 哈希也能正常校验
  B. register_student 端到端 (Flask test_client)
     1) GET /register 200 + 表单渲染
     2) POST /register 完整 4+2 字段 → 302 → /me/<short_id>
     3) POST 重复邮箱 → 200 + 业务错误文案
     4) POST 密码不一致 → 200 + "两次密码不一致"
     5) POST 密码过短 → 200 + "密码需 8-64 位"
     6) POST 邮箱非法 → 200 + "邮箱格式不合法"
     7) POST 未勾选协议 → 200 + "请勾选《用户协议》"

跑法（项目根目录）：
    python test_v3100_register_regression.py
    # 或 pytest 风格
    pytest test_v3100_register_regression.py -v

退出码: 0 = 全部通过, 1 = 有失败
"""
import hashlib
import os
import sys
import time
import builtins
import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# 1) 在 import web_app / admin_students 之前准备好 .env + 安全 baseline
os.environ.setdefault("TASK_DB_PATH", str(ROOT / "tasks.db"))
os.environ.setdefault("ADMIN_PASSWORD", "test-pwd-12345")
os.environ.setdefault("ADMIN_SESSION_SECRET", "test-secret-12345-abcdef-ghijkl-mnop")
os.environ.setdefault("ALLOW_INSECURE_DEFAULT", "1")  # 测试环境允许弱默认

sys.path.insert(0, str(ROOT))

from admin_students import hash_password, verify_password  # noqa: E402

# ========== 打印 helper ==========
PASS = "✅"
FAIL = "❌"
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    tag = PASS if ok else FAIL
    print(f"  {tag} {name}" + (f"  | {detail}" if detail else ""))
    results.append((name, ok, detail))


def section(title: str) -> None:
    print()
    print(f"=== {title} ===")


# ===========================================
# A. 密码哈希单元
# ===========================================
section("A. 密码哈希单元 (hash_password / verify_password)")

# A1. 双向 BCrypt
h1 = hash_password("TestPass1234")
is_bcrypt = h1.startswith(("$2a$", "$2b$", "$2y$"))
check("A1.1 hash_password 产出 BCrypt 格式", is_bcrypt, h1[:30])
check("A1.2 verify_password 正确密码通过", verify_password("TestPass1234", h1))

# A2. 盐唯一
h2 = hash_password("TestPass1234")
check("A2 两次哈希同密码应不同 (盐唯一)", h1 != h2, f"h1[:20]={h1[:20]}  h2[:20]={h2[:20]}")
check("A2 两次哈希都应能验证通过", verify_password("TestPass1234", h2))

# A3. 错误密码
check("A3 verify_password 错误密码返回 False", not verify_password("Wrong", h1))

# A4. 异常输入
check("A4 verify_password 空 hash 返回 False", not verify_password("anything", ""))
check("A4 verify_password 非法 hash 返回 False", not verify_password("anything", "garbage_hash_xxx"))
check("A4 verify_password None hash 返回 False", not verify_password("anything", None))  # type: ignore[arg-type]

# A5 + A6. 核心回归:PBKDF2 兜底路径
#   在函数内部 `import bcrypt` 时,人为让它 ImportError,从而强制走 PBKDF2 兜底
section("A. PBKDF2 兜底路径回归 (v3.10.0.2 修复点)")

# 用 sys.meta_path 的 finder hack 屏蔽 bcrypt 模块
import sys as _sys
class _BcryptBlocker:
    """拦截 `import bcrypt`, 抛 ImportError, 模拟 bcrypt 未安装"""
    def find_spec(self, name, path=None, target=None):
        if name == "bcrypt" or name.startswith("bcrypt."):
            raise ImportError(f"[test_stub] bcrypt 不可用: {name}")
        return None

_sys.meta_path.insert(0, _BcryptBlocker())
# 同步把可能已缓存的 bcrypt 屏蔽
_orig_import = builtins.__import__
def _import_no_bcrypt(name, *args, **kwargs):
    if name == "bcrypt" or name.startswith("bcrypt."):
        raise ImportError(f"[test_stub] bcrypt 不可用: {name}")
    return _orig_import(name, *args, **kwargs)
builtins.__import__ = _import_no_bcrypt
# 删掉已加载的 admin_students 缓存, 让 hash_password 重新 import bcrypt(然后被拦)
import admin_students as _ad
_ad.hash_password.__globals__.pop("bcrypt", None)

try:
    pbkdf_hash = hash_password("TestPass1234")
    is_pbkdf = pbkdf_hash.startswith("pbkdf2_sha256$")
    check("A5 强制 PBKDF2 兜底:hash 格式正确", is_pbkdf, pbkdf_hash[:50])
    check("A5 PBKDF2 hash 长度合规 (>= 100 字符)", len(pbkdf_hash) >= 100, f"len={len(pbkdf_hash)}")
    check("A6.1 PBKDF2 hash 正确密码通过", verify_password("TestPass1234", pbkdf_hash))
    check("A6.2 PBKDF2 hash 错误密码拒绝", not verify_password("Wrong", pbkdf_hash))
    # 验证参数 (200_000 轮)
    parts = pbkdf_hash.split("$")
    check("A5 PBKDF2 轮数 = 200000", parts[1] == "200000", f"got {parts[1]}")
    # 盐唯一
    pbkdf_hash2 = hash_password("TestPass1234")
    check("A5 PBKDF2 两次哈希同密码应不同 (盐唯一)", pbkdf_hash != pbkdf_hash2)
    # 兜底分支关键:不应出现 NameError
    check("A5 PBKDF2 兜底不应出现 NameError (v3.10.0.2 修复)", True)
except NameError as ne:
    check("A5 PBKDF2 兜底路径 — 修复未生效", False, f"NameError: {ne}")
except Exception as e:
    check("A5 PBKDF2 兜底路径 — 异常", False, f"{type(e).__name__}: {e}")
finally:
    # 还原 import 行为
    builtins.__import__ = _orig_import
    try:
        _sys.meta_path.remove(_BcryptBlocker())
    except ValueError:
        pass
    _ad.hash_password.__globals__.pop("bcrypt", None)
    # 重新加载 bcrypt 让后面用例可用
    try:
        importlib.import_module("bcrypt")
    except ImportError:
        pass

# ===========================================
# B. register_student 端到端
# ===========================================
section("B. register_student 端到端 (Flask test_client)")

# import web_app 会触发 _check_security_baseline,我们已经设了 ALLOW_INSECURE_DEFAULT=1
import web_app  # noqa: E402
client = web_app.app.test_client()

# 唯一邮箱,避免反复跑残留
ts = int(time.time())
TEST_EMAIL = f"regress_{ts}@test.local"
TEST_PWD = "Regress1234"

# B1. GET /register
r = client.get("/register")
check("B1 GET /register 200", r.status_code == 200, f"status={r.status_code}")
body = r.get_data(as_text=True)
check("B1 表单含 email 字段", 'name="email"' in body)
check("B1 表单含 password 字段", 'name="password"' in body)
check("B1 页面含 v3.10.0 pill", "v3.10.0" in body)

# B2. POST 完整注册
r = client.post("/register", data={
    "city": "北京",
    "real_name": f"回归用户{ts}",
    "grade": "JUNIOR_1",
    "gender": "M",
    "email": TEST_EMAIL,
    "password": TEST_PWD,
    "password_confirm": TEST_PWD,
    "agree": "on",
}, follow_redirects=False)
check("B2 POST 完整注册 302", r.status_code == 302, f"status={r.status_code}")
loc = r.headers.get("Location", "")
check("B2 Location 跳到 /me/<short_id>", loc.startswith("/me/"), f"loc={loc}")
import re as _re
m = _re.search(r"/me/([a-z0-9]{6,12})", loc)
short_id = m.group(1) if m else ""
check("B2 short_id 长度 6-12 字符", bool(short_id), f"short_id={short_id!r}")

# B3. 重复邮箱
r = client.post("/register", data={
    "city": "北京", "real_name": "重复测试", "grade": "JUNIOR_1", "gender": "F",
    "email": TEST_EMAIL, "password": TEST_PWD, "password_confirm": TEST_PWD, "agree": "on",
}, follow_redirects=False)
body = r.get_data(as_text=True)
check("B3 重复邮箱 200 (业务校验)", r.status_code == 200, f"status={r.status_code}")
check("B3 提示'已注册'", "已注册" in body, "")

# B4. 密码不一致
r = client.post("/register", data={
    "city": "北京", "real_name": "密码不一致", "grade": "JUNIOR_1", "gender": "M",
    "email": f"regress_b4_{ts}@test.local", "password": "Abc12345", "password_confirm": "Different9", "agree": "on",
}, follow_redirects=False)
body = r.get_data(as_text=True)
check("B4 密码不一致 200", r.status_code == 200, f"status={r.status_code}")
check("B4 提示'两次密码不一致'", "两次密码不一致" in body)

# B5. 密码过短
r = client.post("/register", data={
    "city": "北京", "real_name": "短密码", "grade": "JUNIOR_1", "gender": "M",
    "email": f"regress_b5_{ts}@test.local", "password": "Ab1", "password_confirm": "Ab1", "agree": "on",
}, follow_redirects=False)
body = r.get_data(as_text=True)
check("B5 密码过短 200", r.status_code == 200, f"status={r.status_code}")
check("B5 提示'密码需 8-64 位'", "密码需 8-64 位" in body)

# B6. 邮箱非法
r = client.post("/register", data={
    "city": "北京", "real_name": "坏邮箱", "grade": "JUNIOR_1", "gender": "M",
    "email": "not-an-email", "password": "Abc12345", "password_confirm": "Abc12345", "agree": "on",
}, follow_redirects=False)
body = r.get_data(as_text=True)
check("B6 邮箱非法 200", r.status_code == 200, f"status={r.status_code}")
check("B6 提示'邮箱格式不合法'", "邮箱格式不合法" in body)

# B7. 未勾选协议
r = client.post("/register", data={
    "city": "北京", "real_name": "未勾选", "grade": "JUNIOR_1", "gender": "M",
    "email": f"regress_b7_{ts}@test.local", "password": "Abc12345", "password_confirm": "Abc12345",
    # 缺 agree
}, follow_redirects=False)
body = r.get_data(as_text=True)
check("B7 未勾选协议 200", r.status_code == 200, f"status={r.status_code}")
check("B7 提示'请勾选《用户协议》'", "请勾选《用户协议》" in body)

# ===========================================
# 汇总
# ===========================================
print()
print("=" * 60)
total = len(results)
passed = sum(1 for _, ok, _ in results if ok)
failed = total - passed
print(f"汇总: {passed}/{total} 通过, {failed} 失败")
if failed:
    print()
    print("失败项:")
    for name, ok, detail in results:
        if not ok:
            print(f"  {FAIL} {name}  | {detail}")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
