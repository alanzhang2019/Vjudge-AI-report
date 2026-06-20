"""
v3.9.73 · AtCoder 路由 e2e 测试(Flask test client + 临时 DB)

覆盖:
  - POST /link-atcoder 正常绑 / 格式错 / UNIQUE 冲突 / UID 不存在 / 缺参
  - POST /refresh-atcoder 入队 / 1h 节流
  - GET /api/atcoder/<uid>.json linked=True/False
  - task_store.atcoder_link_handle / atcoder_persist_data / 重绑清旧
"""

import unittest
import tempfile
import os
from pathlib import Path

# ===== 在所有 import 之前,先重定向 DB(否则 web_app 已绑老 DB_PATH) =====
_TMP_DIR = tempfile.mkdtemp(prefix="atcoder_test_")
os.environ["TASK_DB_PATH"] = os.path.join(_TMP_DIR, "tasks.db")

# 让 tests/ 跑时能 import 根目录的模块
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import task_store
# 重置 module-level DB_PATH(必须重置;init_db 已经在 import 时跑了)
task_store.DB_PATH = Path(os.environ["TASK_DB_PATH"])
# 重新跑一次以确保表存在
task_store.init_db()
task_store.init_atcoder_tables()
# 清掉之前 import 期间可能产生的旧数据
conn = task_store._get_conn()
try:
    for tbl in ("atcoder_fetch_tasks", "student_atcoder_recent_subs",
                "student_atcoder_ac_problems", "student_atcoder_data",
                "student_cookies", "student_competitions",
                "gesp_exams", "csp_awards", "student_goals",
                "camp_progress", "weekly_reports", "tasks",
                "activation_codes"):
        try:
            conn.execute(f"DELETE FROM {tbl}")
        except Exception:
            pass
    conn.execute("DELETE FROM students")
    conn.commit()
finally:
    conn.close()

# 启动 worker(单例)
from atcoder_fetcher import start_atcoder_worker
start_atcoder_worker()

# 现在 import web_app(此时 task_store 已经是干净临时 DB)
import web_app
app = web_app.app
app.config["TESTING"] = True


# ===========================================================================
# 路由 e2e
# ===========================================================================

class AtcoderRoutesE2E(unittest.TestCase):

    def setUp(self):
        # v3.9.74 · 同步 VJudge 表(防止 worker 报 no such table)
        try:
            task_store.init_vjudge_tables()
        except Exception:
            pass
        # 每个测试前清状态(按依赖顺序清,绕开 FK 约束)
        conn = task_store._get_conn()
        try:
            # 1. 清所有引用 students.id 的子表
            for tbl in ("atcoder_fetch_tasks", "student_atcoder_recent_subs",
                        "student_atcoder_ac_problems", "student_atcoder_data",
                        # v3.9.74 · VJudge 4 表
                        "student_vjudge_fetch_tasks", "student_vjudge_oj_stats",
                        "student_vjudge_solved", "student_vjudge_data",
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

    # ----- 1. POST /link-atcoder -----

    def test_link_atcoder_happy_path(self):
        resp = self.client.post("/link-atcoder", data={
            "luogu_uid": "123456", "handle": "tourist"
        }, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        loc = resp.headers.get("Location", "")
        self.assertIn("/me/123456", loc)
        self.assertIn("atcoder_linked=1", loc)

    def test_link_atcoder_invalid_handle(self):
        resp = self.client.post("/link-atcoder", data={
            "luogu_uid": "654321", "handle": "alice-bob"  # 含连字符不合法
        }, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("invalid_format", resp.headers.get("Location", ""))

    def test_link_atcoder_luogu_uid_not_found(self):
        resp = self.client.post("/link-atcoder", data={
            "luogu_uid": "999999", "handle": "newbie"
        }, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("luogu_uid_not_found", resp.headers.get("Location", ""))

    def test_link_atcoder_missing_params(self):
        resp = self.client.post("/link-atcoder", data={}, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("missing_params", resp.headers.get("Location", ""))

    def test_link_atcoder_already_bound(self):
        # Alice 先绑
        self.client.post("/link-atcoder", data={
            "luogu_uid": "123456", "handle": "tourist"
        })
        # Bob 再绑同一个 handle
        resp = self.client.post("/link-atcoder", data={
            "luogu_uid": "654321", "handle": "tourist"
        }, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("already_bound", resp.headers.get("Location", ""))

    # ----- 2. POST /refresh-atcoder -----

    def test_refresh_atcoder_happy_path(self):
        # 先绑
        self.client.post("/link-atcoder", data={"luogu_uid": "123456", "handle": "alice"})
        resp = self.client.post("/refresh-atcoder", data={"luogu_uid": "123456"},
                                 follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/me/123456", resp.headers.get("Location", ""))

    def test_refresh_atcoder_throttled(self):
        from datetime import datetime, timedelta
        self.client.post("/link-atcoder", data={"luogu_uid": "123456", "handle": "alice"})
        # 写一个 30min 前的 last_fetched_at
        conn = task_store._get_conn()
        try:
            now = (datetime.now() - timedelta(minutes=30)).isoformat(timespec="seconds")
            conn.execute("""
                INSERT INTO student_atcoder_data (
                    student_id, handle, rating, link_status, last_fetched_at
                ) VALUES (1, 'alice', 1500, 'ok', ?)
            """, (now,))
            conn.commit()
        finally:
            conn.close()
        resp = self.client.post("/refresh-atcoder", data={"luogu_uid": "123456"},
                                 follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("atcoder_throttled=1", resp.headers.get("Location", ""))

    # ----- 3. GET /api/atcoder/<uid>.json -----

    def test_api_atcoder_linked(self):
        # 先绑
        self.client.post("/link-atcoder", data={"luogu_uid": "123456", "handle": "tourist"})
        resp = self.client.get("/api/atcoder/123456.json")
        self.assertEqual(resp.status_code, 200)
        import json
        data = json.loads(resp.data)
        self.assertTrue(data.get("linked"))
        self.assertEqual(data.get("handle"), "tourist")

    def test_api_atcoder_unlinked(self):
        resp = self.client.get("/api/atcoder/654321.json")
        self.assertEqual(resp.status_code, 200)
        import json
        data = json.loads(resp.data)
        self.assertEqual(data.get("link_status"), "unlinked")
        self.assertFalse(data.get("linked"))

    def test_api_atcoder_nonexistent_uid(self):
        resp = self.client.get("/api/atcoder/999999.json")
        self.assertEqual(resp.status_code, 200)
        import json
        data = json.loads(resp.data)
        self.assertEqual(data.get("link_status"), "unlinked")


# ===========================================================================
# task_store.atcoder_link_handle 单元(直接调函数,不依赖路由)
# ===========================================================================

class AtcoderLinkHandleUnit(unittest.TestCase):

    def setUp(self):
        # v3.9.74 · 同步 VJudge 表
        try:
            task_store.init_vjudge_tables()
        except Exception:
            pass
        conn = task_store._get_conn()
        try:
            for tbl in ("atcoder_fetch_tasks", "student_atcoder_recent_subs",
                        "student_atcoder_ac_problems", "student_atcoder_data",
                        "student_vjudge_fetch_tasks", "student_vjudge_oj_stats",
                        "student_vjudge_solved", "student_vjudge_data"):
                try:
                    conn.execute(f"DELETE FROM {tbl}")
                except Exception:
                    pass
            conn.execute("DELETE FROM students")
            conn.execute("INSERT INTO students (luogu_uid, real_name) VALUES ('111', 'u1')")
            conn.execute("INSERT INTO students (luogu_uid, real_name) VALUES ('222', 'u2')")
            conn.commit()
        finally:
            conn.close()

    def test_invalid_handle(self):
        for bad in ("ab", "alice-bob", "中", ""):
            r = task_store.atcoder_link_handle("111", bad)
            self.assertFalse(r["ok"], f"应该被拒: {bad!r}")
            self.assertEqual(r["code"], "invalid_format")

    def test_luogu_uid_not_found(self):
        r = task_store.atcoder_link_handle("99999", "tourist")
        self.assertFalse(r["ok"])
        self.assertEqual(r["code"], "luogu_uid_not_found")

    def test_happy_path_creates_task(self):
        r = task_store.atcoder_link_handle("111", "tourist")
        self.assertTrue(r["ok"])
        self.assertGreater(r["student_id"], 0)
        self.assertIn("task_id", r)
        conn = task_store._get_conn()
        try:
            s = conn.execute("SELECT atcoder_handle FROM students WHERE id=?",
                             (r["student_id"],)).fetchone()
            self.assertEqual(s["atcoder_handle"], "tourist")
            t = conn.execute("SELECT status, trigger FROM atcoder_fetch_tasks WHERE task_id=?",
                             (r["task_id"],)).fetchone()
            self.assertEqual(t["status"], "pending")
            self.assertEqual(t["trigger"], "user_link")
        finally:
            conn.close()

    def test_already_bound_conflict(self):
        task_store.atcoder_link_handle("111", "tourist")
        r2 = task_store.atcoder_link_handle("222", "tourist")
        self.assertFalse(r2["ok"])
        self.assertEqual(r2["code"], "already_bound")

    def test_relinking_clears_old_ac_problems(self):
        from task_store import atcoder_persist_data
        r1 = task_store.atcoder_link_handle("111", "tourist")
        student_id = r1["student_id"]
        # 模拟之前有数据
        atcoder_persist_data(student_id, "tourist", {
            "rating": 1500, "rank": "blue",
            "ac_problems": [{"contest_id": "a", "problem_id": "b"}],
        })
        # 改绑其他 handle
        r = task_store.atcoder_link_handle("111", "alice")
        self.assertTrue(r["ok"])
        conn = task_store._get_conn()
        try:
            p = conn.execute(
                "SELECT count(*) c FROM student_atcoder_ac_problems WHERE student_id=?",
                (student_id,)).fetchone()
            self.assertEqual(p["c"], 0, "改绑后旧 AC 列表应被清")
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
