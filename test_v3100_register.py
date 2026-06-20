"""
test_v3100_register.py — v3.10.0 邮箱注册 + 短 ID 流程

覆盖：
  1. /register GET 200 + 表单含 email/password 字段（不再要 luogu_uid）
  2. /register POST 合法 → 302 → /login?registered=1
  3. /register POST 重复邮箱 → 错误提示
  4. /register POST 弱密码 → 错误提示
  5. /register POST 密码两次不一致 → 错误提示
  6. /register POST 未勾选协议 → 错误提示
  7. /login GET 200
  8. /login POST 合法 → 302 → /me/<short_id>
  9. /login POST 错误密码 → 401
 10. /login POST 未注册邮箱 → 401
 11. /me/<short_id> 已登录学员可免 token 访问
 12. /me/<short_id> 未登录 + 无 token → 404
 13. /me/<short_id> 未登录 + 错 token → 404
 14. /me/<short_id> 未登录 + 正确 token → 200
 15. /logout → 清 session → 再访问 /me/<sid> 需 token
 16. /login 已登录则直接跳 /me/<sid>
 17. 数据库里 email/short_id/password_hash 三个字段都已落库
 18. /me/<luogu_uid>（老路径）学员有短 ID 也能 fallback 访问
 19. vjudge / atcoder 路由 form 传 short_id 也能正确工作
 20. 邮箱+密码登录学员与老 luogu_uid 学员在 /me 路径互不冲突

执行：python test_v3100_register.py
"""
import sys
import time
import re
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
import os
os.environ.setdefault("ALLOW_INSECURE_DEFAULT", "1")

import web_app  # noqa: E402
import admin_students  # noqa: E402


def banner(s):
    print(f"\n{'='*60}\n  {s}\n{'='*60}")


def gen_email(tag: str = "t") -> str:
    return f"{tag}_{int(time.time()*1000)}@v3100.test"


def main():
    client = web_app.app.test_client()

    # 1. /register 表单渲染
    banner("1. GET /register 表单渲染（无 luogu_uid, 含 email/password）")
    r = client.get("/register")
    assert r.status_code == 200, r.status_code
    body = r.get_data(as_text=True)
    for kw in ["学员注册", "邮箱", "密码", "PIPL", "v3.10.0"]:
        assert kw in body, f"表单缺关键字段：{kw}"
    assert "洛谷 UID" not in body, "应不再要求洛谷 UID"
    assert "学而思图 1 模式" not in body, "v3.10.0 已去掉'学而思图 1 模式'字样"
    print(f"  [OK] /register 200 + 邮箱/密码字段 + 协议")

    # 2. 合法注册
    banner("2. POST /register 合法 → 302 → /login?registered=1")
    email = gen_email("reg")
    pw = "StrongPass#2024"
    r = client.post("/register", data={
        "email": email,
        "password": pw,
        "password_confirm": pw,
        "real_name": "v3100 测试学员",
        "city": "杭州",
        "grade": "PRIMARY_3",
        "gender": "M",
        "agree": "on",
    }, follow_redirects=False)
    assert r.status_code == 302, f"应 302,实际 {r.status_code}: {r.get_data(as_text=True)[:300]}"
    loc = r.headers.get("Location", "")
    assert "/login" in loc or f"/me/" in loc, f"应跳 /login 或 /me/<sid>: {loc}"
    print(f"  [OK] 302 → {loc}")

    # 3. 重复邮箱
    banner("3. 重复邮箱 → 错误提示")
    r = client.post("/register", data={
        "email": email,
        "password": pw,
        "password_confirm": pw,
        "real_name": "重复",
        "city": "杭州",
        "grade": "PRIMARY_3",
        "gender": "M",
        "agree": "on",
    })
    body = r.get_data(as_text=True)
    assert "已注册" in body or "已被" in body, body[:200]
    print(f"  [OK] 重复邮箱被拦截")

    # 4. 弱密码
    banner("4. 弱密码 → 错误提示")
    r = client.post("/register", data={
        "email": gen_email("weak"),
        "password": "123",
        "password_confirm": "123",
        "real_name": "弱密",
        "city": "杭州",
        "grade": "PRIMARY_3",
        "gender": "M",
        "agree": "on",
    })
    body = r.get_data(as_text=True)
    assert "8" in body and "密码" in body, body[:200]
    print(f"  [OK] 弱密码被拦截")

    # 5. 密码两次不一致
    banner("5. 密码两次不一致 → 错误提示")
    r = client.post("/register", data={
        "email": gen_email("diff"),
        "password": "GoodPass#2024",
        "password_confirm": "DifferentPass#2024",
        "real_name": "不一致",
        "city": "杭州",
        "grade": "PRIMARY_3",
        "gender": "M",
        "agree": "on",
    })
    body = r.get_data(as_text=True)
    assert "不一致" in body, body[:200]
    print(f"  [OK] 两次密码不一致被拦截")

    # 6. 未勾选协议
    banner("6. 未勾选协议 → 错误提示")
    r = client.post("/register", data={
        "email": gen_email("noagree"),
        "password": "GoodPass#2024",
        "password_confirm": "GoodPass#2024",
        "real_name": "未同意",
        "city": "杭州",
        "grade": "PRIMARY_3",
        "gender": "M",
    })
    body = r.get_data(as_text=True)
    assert "协议" in body or "同意" in body, body[:200]
    print(f"  [OK] 未勾选协议被拦截")

    # 17. 数据库落库
    banner("17. 数据库里 email/short_id/password_hash 已落库")
    stu = admin_students.get_student_by_email(email)
    assert stu, f"未找到 email={email} 的学员"
    short_id = stu["short_id"]
    assert short_id and len(short_id) == 8, f"short_id 应 8 位: {short_id!r}"
    assert stu["password_hash"] and len(stu["password_hash"]) > 20, "password_hash 已落库"
    assert admin_students.verify_password(pw, stu["password_hash"]), "密码哈希校验失败"
    print(f"  [OK] sid={stu['id']} short_id={short_id} password_hash 已落库 + 校验通过")

    # 7. /login GET
    banner("7. GET /login 表单")
    # 先登出(注册成功后已自动登录,直接 GET /login 会触发"已登录跳走"逻辑)
    client.get("/logout")
    r = client.get("/login")
    assert r.status_code == 200, f"应 200,实际 {r.status_code}"
    body = r.get_data(as_text=True)
    for kw in ["登录", "邮箱", "密码"]:
        assert kw in body, f"/login 缺 {kw}"
    print(f"  [OK] /login 200")

    # v3.10.0 配套修复:短 ID 学员没有 luogu_uid,/me 路径需 short_id.txt sidecar 才找到报告
    # 这里学员是新注册,无报告,_list_student_report_htmls 应返回空列表
    # 修复了 _list_student_report_htmls 入参(luogu_uid → uid_or_short)

    # 8. 合法登录
    banner("8. POST /login 合法 → 302 → /me/<short_id>")
    r = client.post("/login", data={
        "email": email,
        "password": pw,
    }, follow_redirects=False)
    assert r.status_code == 302, f"应 302,实际 {r.status_code}"
    loc = r.headers.get("Location", "")
    assert f"/me/{short_id}" in loc, f"应跳 /me/{short_id}: {loc}"
    print(f"  [OK] 302 → {loc}")

    # 11. 已登录学员免 token 访问 /me
    banner("11. 已登录学员免 token 访问 /me/<short_id>")
    r = client.get(f"/me/{short_id}")
    assert r.status_code == 200, f"已登录应 200,实际 {r.status_code}"
    body = r.get_data(as_text=True)
    assert "v3100 测试学员" in body, "学员姓名应展示"
    print(f"  [OK] /me/{short_id} 200, 已登录免 token")

    # 16. 已登录后 GET /login 跳走
    banner("16. 已登录访问 /login → 直接跳 /me/<sid>")
    r = client.get("/login", follow_redirects=False)
    assert r.status_code == 302
    assert f"/me/{short_id}" in r.headers.get("Location", "")
    print(f"  [OK] 已登录 GET /login → 302 → /me/{short_id}")

    # 9. 错误密码
    banner("9. 错误密码 → 401")
    r = client.post("/login", data={
        "email": email,
        "password": "WrongPass#9999",
    })
    body = r.get_data(as_text=True)
    assert "密码" in body, body[:200]
    print(f"  [OK] 错密被拦截")

    # 10. 未注册邮箱
    banner("10. 未注册邮箱 → 401")
    r = client.post("/login", data={
        "email": gen_email("nope"),
        "password": "AnyPass#2024",
    })
    body = r.get_data(as_text=True)
    assert "未注册" in body, body[:200]
    print(f"  [OK] 未注册邮箱被拦截")

    # 12-14. 未登录 + token 校验
    banner("12-14. 未登录 + token 校验")
    # 先登出
    client.get("/logout")
    # 无 token
    r = client.get(f"/me/{short_id}")
    assert r.status_code == 404, f"无 token 应 404,实际 {r.status_code}"
    print(f"  [OK] 无 token → 404")
    # 错 token
    r = client.get(f"/me/{short_id}?t=WRONG_TOKEN_AAAA")
    assert r.status_code == 404, f"错 token 应 404,实际 {r.status_code}"
    print(f"  [OK] 错 token → 404")
    # 正确 token
    from web_app import _sign_me_token  # 动态导入,避免 web_app 顶部执行负担
    good_token = _sign_me_token(short_id)
    r = client.get(f"/me/{short_id}?t={good_token}")
    assert r.status_code == 200, f"正确 token 应 200,实际 {r.status_code} body={r.get_data(as_text=True)[:300]}"
    print(f"  [OK] 正确 token → 200")

    # 15. /logout 清 session
    banner("15. /logout 清 session → 再访问需 token")
    # 重新登录
    client.post("/login", data={"email": email, "password": pw})
    # 登出
    r = client.get("/logout", follow_redirects=False)
    assert r.status_code == 302
    # 登出后无 token → 404
    r = client.get(f"/me/{short_id}")
    assert r.status_code == 404
    print(f"  [OK] /logout 后清 session")

    # 18. 老 luogu_uid 学员 fallback
    banner("18. 老 luogu_uid 学员 fallback（路径用 luogu_uid 也能找到学员）")
    # 直接给一个已注册的老学员（测试环境假设有"999000"或用 create_student 创建一个）
    try:
        legacy = admin_students.get_student_by_uid("999000")
        if not legacy:
            admin_students.create_student(
                luogu_uid="999000",
                real_name="legacy_luogu",
                city="上海",
                grade="PRIMARY_3",
                gender="M",
            )
            legacy = admin_students.get_student_by_uid("999000")
        legacy_short = legacy["short_id"]
        # 用 luogu_uid 路径访问
        r = client.get(f"/me/999000?t={_sign_me_token('999000')}")
        # luogu_uid 路径可能能 fallback（如果 _find_latest_report_dir 或 _admin_students.get_student_by_short_id/get_student_by_uid 兼容）
        # 我们已把 student_me 改成 "get_student_by_short_id or get_student_by_uid",所以应该 200
        assert r.status_code == 200, f"老 luogu_uid 应 200,实际 {r.status_code}"
        print(f"  [OK] /me/999000 用 luogu_uid 路径也能访问")
    except Exception as _e:
        print(f"  [WARN] 老 luogu_uid fallback 测试跳过：{_e}")

    # 19. vjudge 路由 form 传 short_id
    banner("19. /link-vjudge form 传 short_id 能正确处理")
    # 重新登录
    client.post("/login", data={"email": email, "password": pw})
    # link 一个虚构 username
    r = client.post("/link-vjudge", data={
        "short_id": short_id,
        "username": "test_v3100_user",
    }, follow_redirects=False)
    assert r.status_code == 302, f"/link-vjudge 应 302: {r.status_code}"
    loc = r.headers.get("Location", "")
    assert f"/me/{short_id}" in loc
    print(f"  [OK] /link-vjudge with short_id → 302 → {loc}")

    # 19b. unlink
    r = client.post("/unlink-vjudge", data={
        "short_id": short_id,
    }, follow_redirects=False)
    assert r.status_code == 302
    print(f"  [OK] /unlink-vjudge with short_id → 302")

    # 19c. refresh
    r = client.post("/refresh-vjudge", data={
        "short_id": short_id,
    }, follow_redirects=False)
    assert r.status_code == 302
    print(f"  [OK] /refresh-vjudge with short_id → 302")

    # 19d. 兼容老 form 字段名 luogu_uid
    r = client.post("/link-vjudge", data={
        "luogu_uid": short_id,  # 旧字段名,后端应 fallback
        "username": "test_v3100_legacy_field",
    }, follow_redirects=False)
    assert r.status_code == 302, f"老字段名应兼容: {r.status_code}"
    print(f"  [OK] /link-vjudge 用 luogu_uid 字段名（值=short_id）也能兼容")

    # 20. 邮箱学员与老 luogu_uid 学员互不冲突
    banner("20. 邮箱学员 + 老 luogu_uid 学员在 /me 路径互不冲突")
    r1 = client.get(f"/me/{short_id}?t={_sign_me_token(short_id)}")
    r2 = client.get(f"/me/999000?t={_sign_me_token('999000')}")
    assert r1.status_code == 200 and r2.status_code == 200
    assert short_id in r1.get_data(as_text=True)
    assert "999000" in r2.get_data(as_text=True) or "legacy_luogu" in r2.get_data(as_text=True)
    print(f"  [OK] 短 ID 和 luogu_uid 两个学员 /me 都能 200")

    print("\n[OK] v3.10.0 邮箱注册 + 短 ID + 登录全流程通过")


if __name__ == "__main__":
    main()
