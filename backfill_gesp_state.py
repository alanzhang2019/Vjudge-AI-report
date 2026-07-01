"""v3.11.21t · 一次性回填脚本: 重算所有有 gesp_exams 但 students 6 字段未更新的学员

背景: 历史上(2026-06-14 等)录入的 gesp_exams 记录, 当时 students 缓存字段
      gesp_highest_passed/gesp_latest_score/gesp_next_eligible_level 等没回填,
      导致个人中心 / 排行榜都按 0/None 显示.
      修复: 对所有 gesp_exams 存在但 students 6 字段仍为 0/None 的学员,
           重新调 _recompute_student_gesp_state 同步缓存字段.
"""
import sqlite3
import sys
sys.path.insert(0, "/app")
import admin_students

c = admin_students._get_conn()
try:
    sids = [r[0] for r in c.execute(
        """
        SELECT DISTINCT ge.student_id
        FROM gesp_exams ge
        JOIN students s ON s.id = ge.student_id
        WHERE ge.actual_score IS NOT NULL
          AND (s.gesp_highest_passed = 0 OR s.gesp_highest_passed IS NULL)
        ORDER BY ge.student_id
        """
    ).fetchall()]
    print(f"待回填学员数: {len(sids)}: {sids}")
    for sid in sids:
        before = c.execute(
            "SELECT gesp_highest_passed, gesp_latest_score, gesp_next_eligible_level "
            "FROM students WHERE id=?", (sid,)).fetchone()
        admin_students._recompute_student_gesp_state(c, sid)
        after = c.execute(
            "SELECT gesp_highest_passed, gesp_latest_score, gesp_next_eligible_level "
            "FROM students WHERE id=?", (sid,)).fetchone()
        print(f"sid={sid}: {before} -> {after}")
    c.commit()
    print(f"✅ 已回填 {len(sids)} 个学员")
finally:
    c.close()
