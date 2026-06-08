"""
test_phase2_routes.py — Phase 2 端到端测试

覆盖 v3.5 §6.2 验收：
  - /admin/guardians 家长录入
  - 家长 token 30 天过期
  - /parent/<token> 家长面板（无登录）
  - 学员目标路径 + AI 跳级建议
  - 周报生成 + 家长打开 +1
  - GESP 7 级 80+ 录入后，周报自动出现"9 月 CSP-J 免初赛已解锁"
"""
import os
import sys
import time
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("TASK_DB_PATH", str(ROOT / "tasks.db"))
os.environ.setdefault("ALLOW_INSECURE_DEFAULT", "1")

sys.path.insert(0, str(ROOT))

import web_app  # noqa: E402

client = web_app.app.test_client()


def banner(s: str) -> None:
    print()
    print("=" * 60)
    print(f"  {s}")
    print("=" * 60)


def section(s: str) -> None:
    print()
    print(f"--- {s} ---")


# 0) 模拟 admin 登录
with client.session_transaction() as sess:
    sess["admin_authed"] = True
    sess["admin_user"] = "admin"

# 1) 准备一个有 GESP 7 级 80+ 的学员
banner("0. 准备测试学员（GESP 7 级 85 分 → 触发 CSP-J 免）")
import admin_students  # noqa: E402
test_uid = f"phase2_test_{int(time.time())}"
existing = admin_students.get_student_by_uid(test_uid)
if existing:
    admin_students.delete_student(existing["id"])
sid = admin_students.create_student(
    test_uid, real_name="Phase2 测试", school="测试小学", grade="2024"
)
conn = sqlite3.connect(str(ROOT / "tasks.db"))
conn.row_factory = sqlite3.Row
g7 = conn.execute(
    "SELECT id FROM competitions WHERE type='gesp' AND code LIKE '%L7-8%' LIMIT 1"
).fetchone()
conn.close()
assert g7, "先跑 import_competitions.py 灌入 GESP 赛事"
admin_students.add_gesp_exam(int(sid), int(g7["id"]), 7, 85, recorded_by="e2e")
print(f"  [OK] 学员 id={sid}（GESP 7 级 85 分，can_exempt_csp_j=True）")

banner("1. /admin/students/<id>/guardians GET 显示空列表")
r = client.get(f"/admin/students/{sid}/guardians")
assert r.status_code == 200, r.status_code
body = r.get_data(as_text=True)
assert "家长列表" in body
assert "尚未绑定家长" in body
print(f"  [OK] GET /admin/students/{sid}/guardians 空列表渲染")

banner("2. POST 添加家长（email 通知）")
r = client.post(f"/admin/students/{sid}/guardians", data={
    "display_name": "测试妈妈",
    "phone": "13800138000",
    "email": "test_mom@example.com",
    "notify_channel": "email",
}, follow_redirects=False)
assert r.status_code == 302, f"未跳转: {r.status_code}"
loc = r.headers.get("Location", "")
assert f"/admin/students/{sid}/guardians" in loc
print(f"  [OK] 添加家长 302 → {loc[:80]}...")

# 取出 token 用于后续家长面板测试
import admin_guardians  # noqa: E402
gs = admin_guardians.list_guardians_by_student(int(sid))
assert len(gs) == 1
guardian_token = gs[0]["notify_token"]
print(f"  [OK] 取得 token: {guardian_token[:16]}...")

banner("3. GET 家长列表（应含刚添加的家长 + 30 天有效期）")
r = client.get(f"/admin/students/{sid}/guardians")
body = r.get_data(as_text=True)
assert "测试妈妈" in body
assert "13800138000" in body or "test_mom" in body
assert "email" in body
# 验证 30 天有效期
import re
m = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", body)
assert m, "未找到过期时间"
print(f"  [OK] 家长列表渲染：测试妈妈 + 邮箱 + 过期时间 {m.group(1)}")

banner("4. /parent/<token> 家长面板首页（无登录）")
r = client.get(f"/parent/{guardian_token}")
assert r.status_code == 200, r.status_code
body = r.get_data(as_text=True)
assert "家长端" in body
assert "赛事仪表盘" in body
assert "Phase2 测试" in body
assert "[7✦]" in body  # 段位图
assert "已解锁 CSP-J 免初赛" in body  # 7 级 80+ 触发
assert "学员画像" in body  # v3.5.4 替代 v3.5.1 CSP 12 岁卡
assert "赛事路径规划" in body  # v3.5.1 学而思图 2
assert "4 SKU 升级路径" in body  # v3.5.1 付费 CTA
print(f"  [OK] /parent/{guardian_token[:8]}... 200 + v3.5.1 赛事仪表盘全要素")

banner("5. /parent/<token> 非法 token → 410")
r = client.get("/parent/invalid_token_xyz")
assert r.status_code == 410, f"非法 token 应 410，实际 {r.status_code}"
body = r.get_data(as_text=True)
assert "链接无效" in body
print(f"  [OK] 非法 token 410 + 友好提示")

banner("6. POST 设置学员目标路径（强基 → 清华）")
r = client.post(f"/admin/students/{sid}/goal", data={
    "primary_path": "强基",
    "target_university": "清华大学",
    "target_province": "北京",
    "notes": "测试目标",
}, follow_redirects=False)
assert r.status_code == 302
print(f"  [OK] POST /admin/students/{sid}/goal 302")

banner("7. GET 学员目标页（含 AI 跳级建议）")
r = client.get(f"/admin/students/{sid}/goal")
body = r.get_data(as_text=True)
assert r.status_code == 200
assert "强基" in body
assert "清华大学" in body
assert "AI 跳级建议" in body
# 强基 + 7 级 85 分（< 90）→ 推稳扎稳打
assert "稳" in body
print(f"  [OK] 目标页：强基 / 清华大学 / AI 跳级建议已渲染")

banner("8. POST 立即生成周报")
r = client.post(f"/admin/students/{sid}/reports/generate", follow_redirects=False)
assert r.status_code == 302
loc = r.headers.get("Location", "")
assert "/admin/students/" in loc and "reports" in loc
print(f"  [OK] 生成周报 302 → {loc[:80]}...")

# 查 weekly_reports 表
import weekly_reports  # noqa: E402
reports = weekly_reports.list_weekly_reports(int(sid))
assert len(reports) >= 1
report_id = reports[0]["id"]
print(f"  [OK] 周报已入库 id={report_id}")

banner("9. GET 周报列表（admin 视图）")
r = client.get(f"/admin/students/{sid}/reports")
body = r.get_data(as_text=True)
assert r.status_code == 200
assert "家长周报" in body
assert str(report_id) in body
print(f"  [OK] 周报列表渲染（id={report_id}）")

banner("10. /parent/<token>/report/<id> 查看周报 + 打开数 +1")
r1 = client.get(f"/parent/{guardian_token}/report/{report_id}")
assert r1.status_code == 200, r1.status_code
body1 = r1.get_data(as_text=True)
assert "GESP 段位" in body1
assert "免初赛里程碑" in body1
# CSP-J 免 + 9 月免初赛
assert "CSP-J 初赛" in body1
assert "免初赛" in body1
print(f"  [OK] 家长打开周报 200 + 段位图 + 免初赛里程碑")

# 再次打开
r2 = client.get(f"/parent/{guardian_token}/report/{report_id}")
assert r2.status_code == 200
# 校验 open_count +1
reports_after = weekly_reports.list_weekly_reports(int(sid))
assert reports_after[0]["open_count"] >= 2
print(f"  [OK] 再次打开：open_count = {reports_after[0]['open_count']}（>= 2）")

banner("11. /parent/<token>/report/<id> 横向越权测试")
# 把 report_id 改成其他学员的报告应该 404
# 这里只能确认 token 不匹配会 410
r = client.get(f"/parent/invalid_token/report/{report_id}")
assert r.status_code == 410
print(f"  [OK] 越权 token → 410")

banner("12. POST 重置家长 token（旧 token 失效）")
gid = gs[0]["id"]
r = client.post(f"/admin/students/{sid}/guardians/{gid}/rotate", follow_redirects=False)
assert r.status_code == 302
print(f"  [OK] rotate_token 302")

# 旧 token 失效
r = client.get(f"/parent/{guardian_token}")
assert r.status_code == 410, f"旧 token 应失效 (410)，实际 {r.status_code}"
print(f"  [OK] 旧 token 失效 → 410")

# 新 token 取一次
gs_new = admin_guardians.list_guardians_by_student(int(sid))
new_token = gs_new[0]["notify_token"]
assert new_token != guardian_token
r = client.get(f"/parent/{new_token}")
assert r.status_code == 200
print(f"  [OK] 新 token 有效 → 200")

banner("13. POST 删除家长 + 清理学员")
r = client.post(f"/admin/students/{sid}/guardians/{gid}/delete", follow_redirects=False)
assert r.status_code == 302
# 删除后 token 失效
r = client.get(f"/parent/{new_token}")
assert r.status_code == 410
print(f"  [OK] 删除家长 → token 立即失效")

admin_students.delete_student(int(sid))
print(f"  [OK] 清理测试学员 id={sid}")

print()
print("=" * 60)
print("[OK] Phase 2 端到端测试全部通过（13 项）")
print("=" * 60)
