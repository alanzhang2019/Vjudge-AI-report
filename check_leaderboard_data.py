"""v3.11.25 · 检查 students / tasks 关联情况"""
import sqlite3

DB = "/app/data/tasks.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

print("=== students count ===")
print(conn.execute("SELECT COUNT(*) FROM students").fetchone()[0])

print("\n=== students with province (last 20 by id) ===")
rows = conn.execute(
    "SELECT luogu_uid, real_name, school, grade, province, city, registered_via, created_at "
    "FROM students WHERE province IS NOT NULL AND province != '' "
    "ORDER BY id DESC LIMIT 20"
).fetchall()
for r in rows:
    print(dict(r))

print("\n=== students with luogu_uid (last 20 by id) ===")
rows = conn.execute(
    "SELECT luogu_uid, real_name, school, grade, province, registered_via "
    "FROM students WHERE luogu_uid IS NOT NULL AND luogu_uid != '' "
    "ORDER BY id DESC LIMIT 20"
).fetchall()
for r in rows:
    print(dict(r))

print("\n=== tasks count by status ===")
rows = conn.execute("SELECT status, COUNT(*) AS cnt FROM tasks GROUP BY status").fetchall()
for r in rows:
    print(dict(r))

print("\n=== tasks with student_id (last 20 done) ===")
rows = conn.execute(
    "SELECT task_id, luogu_uid, student_id, created_at, student_name, school, grade "
    "FROM tasks WHERE status = 'done' AND student_id IS NOT NULL "
    "ORDER BY created_at DESC LIMIT 20"
).fetchall()
for r in rows:
    print(dict(r))

print("\n=== tasks without student_id (last 20 done) ===")
rows = conn.execute(
    "SELECT task_id, luogu_uid, student_id, created_at, student_name, school, grade "
    "FROM tasks WHERE status = 'done' AND student_id IS NULL "
    "ORDER BY created_at DESC LIMIT 20"
).fetchall()
for r in rows:
    print(dict(r))

print("\n=== total done tasks ===")
print(conn.execute("SELECT COUNT(*) FROM tasks WHERE status='done'").fetchone()[0])

print("\n=== done tasks by student_id (top 10) ===")
rows = conn.execute(
    "SELECT student_id, COUNT(*) AS cnt FROM tasks "
    "WHERE status='done' AND student_id IS NOT NULL "
    "GROUP BY student_id ORDER BY cnt DESC LIMIT 10"
).fetchall()
for r in rows:
    print(dict(r))

print("\n=== 总 students (按 province 统计) ===")
rows = conn.execute(
    "SELECT province, COUNT(*) AS cnt FROM students "
    "WHERE province IS NOT NULL AND province != '' "
    "GROUP BY province ORDER BY cnt DESC LIMIT 20"
).fetchall()
for r in rows:
    print(dict(r))

print("\n=== 总 students (按 registered_via 统计) ===")
rows = conn.execute(
    "SELECT registered_via, COUNT(*) AS cnt FROM students GROUP BY registered_via"
).fetchall()
for r in rows:
    print(dict(r))

conn.close()
