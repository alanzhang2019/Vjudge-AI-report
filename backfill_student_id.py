"""v3.11.25 · 一次性 backfill: 把历史 task 的 student_id 补上 (按 luogu_uid 匹配)"""
import sqlite3

DB = "/app/data/tasks.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# 1) 看看有多少待补
n = conn.execute("""
    SELECT COUNT(*)
      FROM tasks t
 LEFT JOIN students s ON s.luogu_uid = t.luogu_uid
                       AND s.luogu_uid IS NOT NULL AND s.luogu_uid != ''
       AND t.luogu_uid IS NOT NULL AND t.luogu_uid != ''
     WHERE t.status = 'done'
       AND t.student_id IS NULL
       AND s.id IS NOT NULL
""").fetchone()[0]
print(f"待补 tasks (by luogu_uid match): {n}")

# 2) 真正 backfill
cur = conn.execute("""
    UPDATE tasks
       SET student_id = (
           SELECT s.id FROM students s
            WHERE s.luogu_uid = tasks.luogu_uid
              AND s.luogu_uid IS NOT NULL AND s.luogu_uid != ''
            LIMIT 1
       )
     WHERE status = 'done'
       AND luogu_uid IS NOT NULL AND luogu_uid != ''
       AND student_id IS NULL
""")
print(f"已更新行数: {cur.rowcount}")
conn.commit()
conn.close()
