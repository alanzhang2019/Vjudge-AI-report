#!/bin/bash
set +e

echo "=== A) Docker 容器信息 ==="
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" | head -10

echo
echo "=== B) 容器内 DB 路径（容器里的 tasks.db 真实位置）==="
docker exec luogu-ai-report-luogu-coach sh -c '
  echo "TASK_DB_PATH=$TASK_DB_PATH"
  echo "PWD=$PWD"
  ls -la /app/ 2>/dev/null | head -20
  echo "---"
  find / -name "tasks.db" 2>/dev/null | head -10
  echo "---"
  echo "DB size:"
  find / -name "tasks.db" 2>/dev/null -exec ls -la {} \;
'

echo
echo "=== C) 宿主机上的 tasks.db 备份/数据 ==="
ls -la /home/ubuntu/luogu-ai-report/data/ 2>&1
echo "---"
ls -la /home/ubuntu/luogu-ai-report/ 2>&1 | head -15
echo "---"
# 查看挂载点
docker inspect luogu-ai-report-luogu-coach --format '{{json .Mounts}}' 2>&1 | head -30

echo
echo "=== D) 容器内查 UID 1752947 ==="
docker exec luogu-ai-report-luogu-coach python3 -c "
import sqlite3, os
db = os.environ.get('TASK_DB_PATH', '/app/data/tasks.db')
print('DB =', db)
if not os.path.exists(db):
    # 尝试常见路径
    for p in ['/app/data/tasks.db', '/app/tasks.db', '/data/tasks.db', './tasks.db']:
        if os.path.exists(p):
            db = p
            print('FOUND:', db)
            break
conn = sqlite3.connect(db)
for r in conn.execute(\"SELECT id, luogu_uid, real_name, gesp_highest_passed, gesp_latest_score FROM students WHERE luogu_uid='1752947';\"):
    print(f'  students: id={r[0]} uid={r[1]} name={r[2]} gesp={r[3]}/{r[4]}')
print('---')
rows = conn.execute('''
    SELECT ac.id, ac.code, ac.sku, ac.redeemed_at, ac.expires_at, s.luogu_uid
    FROM activation_codes ac LEFT JOIN students s ON s.id = ac.student_id
    WHERE s.luogu_uid = '1752947'
    ORDER BY ac.id
''').fetchall()
for r in rows:
    print(f'  ac: id={r[0]} {r[1]:20s} sku={r[2]} redeemed={r[3]} expires={r[4]} uid={r[5]}')
print(f'  共 {len(rows)} 条 activation_codes')
"

echo
echo "=== E) 用 _is_parent_subscribed SQL 复刻检查 ==="
docker exec luogu-ai-report-luogu-coach python3 -c "
import sqlite3, os
db = os.environ.get('TASK_DB_PATH', '/app/data/tasks.db')
conn = sqlite3.connect(db)
row = conn.execute('''
    SELECT COUNT(*) AS n FROM activation_codes ac
    JOIN students s ON s.id = ac.student_id
    WHERE ac.sku IN ('parent_sub', 'parent_invite')
      AND s.luogu_uid = '1752947'
      AND ac.redeemed_at IS NOT NULL
      AND (ac.expires_at IS NULL OR ac.expires_at > datetime('now'))
''').fetchone()
print(f'  n = {row[0]}')
print('  ->', 'True: 短路门控' if row[0] > 0 else 'False: 用户需重输邀请码')
"
