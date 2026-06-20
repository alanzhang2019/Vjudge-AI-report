"""
v3.9.74 · VJudge 路由 e2e 测试
不依赖网络,只测路由层 + 数据库交互
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 重定向 DB
_TMP_DIR = tempfile.mkdtemp(prefix="vj_routes_")
os.environ["TASK_DB_PATH"] = os.path.join(_TMP_DIR, "tasks.db")

import task_store
task_store.DB_PATH = Path(os.environ["TASK_DB_PATH"])
task_store.init_db()
task_store.init_vjudge_tables()

import web_app
app = web_app.app
app.config["TESTING"] = True


class VjudgeRoutesE2E(unittest.TestCase):

    def setUp(self):
        # 清残留(按 FK 顺序)
        conn = task_store._get_conn()
        try:
            for tbl in ("student_vjudge_fetch_tasks", "student_vjudge_oj_stats",
                        "student_vjudge_solved", "student_vjudge_data",
                        # AtCoder 也要清,因为 students 表是共用的
                        "atcoder_fetch_tasks", "student_atcoder_recent_subs",
                        "student_atcoder_ac_problems", "student_atcoder_data",
                        "student_cookies", "student_competitions",
                        "gesp_exams", "csp_awards", "student_goals",
                        "camp_progress", "weekly_reports", "tasks"):
                try:
                    conn.execute(f"DELETE FROM {tbl}")
                except Exception:
                    pass
            conn.execute("DELETE FROM activation_codes")
            conn.execute("DELETE FROM students")
            conn.execute("""
                INSERT INTO students (id, luogu_uid, real_name, school, grade)
                VALUES (1, '123456', 'Alice', 'TestSchool', 'G6'),
                       (2, '654321', 'Bob', 'TestSchool', 'G5')
            """)
            conn.commit()
        finally:
            conn.close()
        self.client = app.test_client()

    def test_link_vjudge_happy_path(self):
        resp = self.client.post("/link-vjudge", data={
            "luogu_uid": "123456", "username": "alice_2024"
        }, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        loc = resp.headers.get("Location", "")
        self.assertIn("/me/123456", loc)
        self.assertIn("vjudge_linked=1", loc)

    def test_link_vjudge_missing_params(self):
        resp = self.client.post("/link-vjudge", data={
            "luogu_uid": "123456"
            # username 缺失
        }, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("vjudge_error=missing_params", resp.headers.get("Location", ""))

    def test_link_vjudge_invalid_format(self):
        from urllib.parse import unquote
        resp = self.client.post("/link-vjudge", data={
            "luogu_uid": "123456", "username": "ab"  # 太短
        }, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        loc = resp.headers.get("Location", "")
        self.assertIn("vjudge_error=", loc)
        decoded = unquote(loc)
        self.assertIn("格式不合法", decoded)

    def test_link_vjudge_already_bound(self):
        # Alice 绑了 alice_2024
        self.client.post("/link-vjudge", data={
            "luogu_uid": "123456", "username": "alice_2024"
        })
        # Bob 尝试绑同一个 username
        from urllib.parse import unquote
        resp = self.client.post("/link-vjudge", data={
            "luogu_uid": "654321", "username": "alice_2024"
        }, follow_redirects=False)
        loc = unquote(resp.headers.get("Location", ""))
        self.assertIn("已被其他学员绑定", loc)

    def test_refresh_vjudge_creates_task(self):
        # 先绑
        self.client.post("/link-vjudge", data={"luogu_uid": "123456", "username": "alice_2024"})

        resp = self.client.post("/refresh-vjudge", data={"luogu_uid": "123456"},
                                follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("vjudge_refreshing=1", resp.headers.get("Location", ""))

        # 任务应该入队
        tasks = task_store._get_conn().execute(
            "SELECT * FROM student_vjudge_fetch_tasks WHERE status='pending'"
        ).fetchall()
        self.assertGreaterEqual(len(tasks), 1)

    def test_refresh_vjudge_throttled_in_1h(self):
        self.client.post("/link-vjudge", data={"luogu_uid": "123456", "username": "alice_2024"})

        # 第一次
        self.client.post("/refresh-vjudge", data={"luogu_uid": "123456"})
        # 第二次(1h 内)应该被节流
        resp = self.client.post("/refresh-vjudge", data={"luogu_uid": "123456"},
                                follow_redirects=False)
        loc = resp.headers.get("Location", "")
        self.assertIn("already_pending", loc)

    def test_unlink_vjudge(self):
        self.client.post("/link-vjudge", data={"luogu_uid": "123456", "username": "alice_2024"})
        task_store.vjudge_persist_data(1, "alice_2024", {
            "nick": "x", "total_submissions": 100, "total_ac": 30,
            "solved_count": 5, "solved_list": [],
        })
        resp = self.client.post("/unlink-vjudge", data={"luogu_uid": "123456"},
                                follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("vjudge_unlinked=1", resp.headers.get("Location", ""))

        # 验证 students.username 已清
        s = task_store._get_conn().execute(
            "SELECT vjudge_username FROM students WHERE id=1"
        ).fetchone()
        self.assertEqual(s["vjudge_username"], "")

    def test_api_vjudge_unlinked(self):
        resp = self.client.get("/api/vjudge/123456.json")
        self.assertEqual(resp.status_code, 200)
        import json
        data = json.loads(resp.data)
        self.assertFalse(data.get("linked"))
        self.assertEqual(data.get("link_status"), "unlinked")

    def test_api_vjudge_after_link(self):
        self.client.post("/link-vjudge", data={"luogu_uid": "123456", "username": "alice_2024"})
        resp = self.client.get("/api/vjudge/123456.json")
        self.assertEqual(resp.status_code, 200)
        import json
        data = json.loads(resp.data)
        # 刚绑,没数据 → pending
        self.assertTrue(data.get("linked"))
        self.assertEqual(data.get("link_status"), "pending")
        self.assertEqual(data.get("username"), "alice_2024")

    def test_api_vjudge_after_persist(self):
        self.client.post("/link-vjudge", data={"luogu_uid": "123456", "username": "alice_2024"})
        task_store.vjudge_persist_data(1, "alice_2024", {
            "nick": "Alice 2024",
            "total_submissions": 500, "total_ac": 430, "total_wa": 50,
            "total_tle": 10, "total_re": 5, "total_ce": 5,
            "ac_rate": 0.86, "solved_count": 200,
            "solved_list": [
                {"oj": "Codeforces", "problem_id": "1234A", "title": "Equalize",
                 "ac_time": "2024-06-01T10:00:00"},
            ],
            "oj_stats": {"Codeforces": 100, "AtCoder": 80, "Luogu": 20},
        })
        resp = self.client.get("/api/vjudge/123456.json")
        import json
        data = json.loads(resp.data)
        self.assertEqual(data["link_status"], "ok")
        self.assertEqual(data["nick"], "Alice 2024")
        self.assertEqual(data["solved_count"], 200)
        self.assertEqual(data["total_ac"], 430)
        self.assertEqual(len(data["recent_solved"]), 1)
        self.assertEqual(len(data["oj_stats"]), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
