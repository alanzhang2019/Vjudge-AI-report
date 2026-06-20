"""部署前验证：直接查生产 tasks.db，确认大齐（1752947）的修复效果
不导入 web_app（避免副作用），只复刻 status_page 的 SQL 逻辑。
"""
import os
import sys
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "tasks.db"
print(f"DB: {DB}  ({DB.stat().st_size} bytes)" if DB.exists() else f"DB missing: {DB}")
if not DB.exists():
    sys.exit(1)

conn = sqlite3.connect(str(DB))
conn.row_factory = sqlite3.Row

print()
print("=" * 70)
print("查询 1：UID 1752947（大齐）是否存在 + 兑换码绑定情况")
print("=" * 70)
stu = conn.execute(
    "SELECT id, luogu_uid, real_name, gesp_highest_passed, gesp_latest_score "
    "FROM students WHERE luogu_uid = ?",
    ("1752947",),
).fetchone()
if stu:
    print(f"  ✅ 找到大齐: id={stu['id']}, name={stu['real_name']}, "
          f"gesp_level={stu['gesp_highest_passed']}, gesp_score={stu['gesp_latest_score']}")
    stu_id = stu["id"]
else:
    print(f"  ❌ UID 1752947 不在 students 表中")
    stu_id = None

print()
print("=" * 70)
print("查询 2：activation_codes 中大齐相关的记录")
print("=" * 70)
if stu_id:
    rows = conn.execute(
        "SELECT id, code, sku, redeemed_at, expires_at, created_by "
        "FROM activation_codes WHERE student_id = ? "
        "ORDER BY id",
        (stu_id,),
    ).fetchall()
    for r in rows:
        print(f"  id={r['id']:>3}  {r['code']:18s}  sku={r['sku']:14s}  "
              f"redeemed={r['redeemed_at']}  expires={r['expires_at']}  by={r['created_by']}")
else:
    print("  无")

print()
print("=" * 70)
print("查询 3：复刻 _is_parent_subscribed(1752947) 的 SQL")
print("=" * 70)
row = conn.execute(
    "SELECT COUNT(*) AS n FROM activation_codes ac "
    "JOIN students s ON s.id = ac.student_id "
    "WHERE ac.sku IN ('parent_sub', 'parent_invite') "
    "  AND s.luogu_uid = ? "
    "  AND ac.redeemed_at IS NOT NULL "
    "  AND (ac.expires_at IS NULL OR ac.expires_at > datetime('now'))",
    ("1752947",),
).fetchone()
n = dict(row).get("n", 0)
print(f"  计数 n = {n}  →  {'✅ _is_parent_subscribed=True（门控短路）' if n > 0 else '❌ False（门控仍生效）'}")

print()
print("=" * 70)
print("查询 4：对比新用户（uid=9999999，不应存在）")
print("=" * 70)
row2 = conn.execute(
    "SELECT COUNT(*) AS n FROM activation_codes ac "
    "JOIN students s ON s.id = ac.student_id "
    "WHERE ac.sku IN ('parent_sub', 'parent_invite') "
    "  AND s.luogu_uid = ? "
    "  AND ac.redeemed_at IS NOT NULL "
    "  AND (ac.expires_at IS NULL OR ac.expires_at > datetime('now'))",
    ("9999999",),
).fetchone()
n2 = dict(row2).get("n", 0)
print(f"  计数 n = {n2}  →  {'❌ 对照组被错误激活' if n2 > 0 else '✅ 对照组未被激活'}")

print()
print("=" * 70)
print("查询 5：UPPER() 归一化 SQL 行为（大小写容错）")
print("=" * 70)
codes_to_test = [
    "PINV-B3EWHLDP",   # 标准大写
    "pinv-b3ewhldp",   # 全小写
    "PInv-B3ewHLDP",   # 混合
    "  PINV-B3EWHLDP  ",  # 带前后空格（应 strip）
]
for c in codes_to_test:
    normalized = c.strip().upper()
    row = conn.execute(
        "SELECT id, redeemed_at FROM activation_codes "
        "WHERE UPPER(code) = ? AND sku = 'parent_invite' LIMIT 1",
        (normalized,),
    ).fetchone()
    if row:
        print(f"  '{c}' → 匹配 id={row[0]}, redeemed={row[1]}")
    else:
        print(f"  '{c}' → 未匹配（检查码是否真实存在）")

conn.close()
