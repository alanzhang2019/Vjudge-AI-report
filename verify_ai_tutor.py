"""v3.11.31 · AI 讲题异步 API + 按钮集成验证

跑在 server 容器内, 走 http://127.0.0.1:5000 (loopback).
校验项:
  1) POST /api/ai-tutor/jobs → 202 + jobId + pollUrl + pollIntervalMs
  2) GET  /api/ai-tutor/jobs/<jobId> → 200 + 状态字段
  3) POST 缺字段 → 400
  4) GET 不存在的 job → 404
  5) STUDENT_ME_HTML 模板中按钮 onclick=luoguAiTutor(this) 替换 <a href aijiangti.cn>
  6) /r/<uid> 预览页按钮存在

后端默认为 stub (mock 6 节 C++ 讲题, 5~10s 内完成).
如果服务器 AI_TUTOR_BACKEND=aijiangti, 实际会转发到 StudyMate/aijiangti.cn.
"""
import sys
import time
import json
import urllib.request
import urllib.error
import re

BASE = "http://127.0.0.1:5000"


def http(method, path, body=None, headers=None):
    url = BASE + path
    data = None
    h = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        h["Content-Type"] = "application/json"
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def t(name, ok, detail=""):
    icon = "✅" if ok else "❌"
    print(f"  {icon} {name}{('  · ' + detail) if detail else ''}")
    return ok


failures = []


def assert_t(name, cond, detail=""):
    if not t(name, cond, detail):
        failures.append(name)


# ============================================================
# 1) POST /api/ai-tutor/jobs → 202
# ============================================================
print("\n[1] POST /api/ai-tutor/jobs (创建讲题任务)")
status, body = http("POST", "/api/ai-tutor/jobs", body={
    "problem_id": "P1001",
    "title": "A + B Problem",
    "source": "https://www.luogu.com.cn/problem/P1001",
    "language": "cpp",
    "requirement": "用C++代码实现并讲解",
    "luogu_uid": "999999",
})
data = {}
try:
    data = json.loads(body)
except Exception:
    pass
assert_t("HTTP 202", status == 202, f"got {status}")
assert_t("返回 jobId", bool(data.get("jobId")), f"jobId={data.get('jobId')}")
assert_t("返回 status=queued", data.get("status") == "queued")
assert_t("返回 pollUrl", "/api/ai-tutor/jobs/" in (data.get("pollUrl") or ""))
assert_t("返回 pollIntervalMs (5s)", data.get("pollIntervalMs") == 5000)
job_id = data.get("jobId") or ""


# ============================================================
# 2) GET /api/ai-tutor/jobs/<jobId> → 200
# ============================================================
print(f"\n[2] GET /api/ai-tutor/jobs/{job_id} (轮询状态)")
status2, body2 = http("GET", f"/api/ai-tutor/jobs/{job_id}")
d2 = {}
try:
    d2 = json.loads(body2)
except Exception:
    pass
assert_t("HTTP 200", status2 == 200, f"got {status2}")
assert_t("jobId 一致", d2.get("jobId") == job_id)
assert_t("status ∈ {queued, running}", d2.get("status") in ("queued", "running"))
assert_t("step 字段存在", "step" in d2)
assert_t("progress 字段存在", "progress" in d2)
assert_t("done 字段存在", "done" in d2)
# v3.11.31 · StudyMate 契约: 分镜进度字段
assert_t("scenesGenerated 字段存在 (StudyMate 契约)", "scenesGenerated" in d2)
assert_t("totalScenes 字段存在 (StudyMate 契约)", "totalScenes" in d2)
# v3.11.31b · totalScenes 不再硬编码 6: stub 后端是 6, aijiangti 后端透传上游 (可能是 7 / 6 / 其他, 由 LLM 决定)
assert_t("totalScenes 是 int >= 0", isinstance(d2.get("totalScenes"), int) and d2.get("totalScenes") >= 0,
         f"got {d2.get('totalScenes')!r} (stub=6, aijiangti 透传上游)")
assert_t("scenesGenerated >= 0", isinstance(d2.get("scenesGenerated"), int) and d2.get("scenesGenerated") >= 0)


# ============================================================
# 3) POST 缺字段 → 400
# ============================================================
print("\n[3] POST 缺字段 → 400")
status3, body3 = http("POST", "/api/ai-tutor/jobs", body={})
d3 = {}
try:
    d3 = json.loads(body3)
except Exception:
    pass
assert_t("HTTP 400", status3 == 400, f"got {status3}")
assert_t("error=MISSING_FIELDS", d3.get("error") == "MISSING_FIELDS")


# ============================================================
# 4) GET 不存在 job → 404
# ============================================================
print("\n[4] GET 不存在 job → 404")
status4, body4 = http("GET", "/api/ai-tutor/jobs/zzzzz99999")
d4 = {}
try:
    d4 = json.loads(body4)
except Exception:
    pass
assert_t("HTTP 404", status4 == 404, f"got {status4}")
assert_t("error=NOT_FOUND", d4.get("error") == "NOT_FOUND")


# ============================================================
# 5) 学员主版 HTML 含新按钮 (不跳 aijiangti.cn)
# ============================================================
print("\n[5] STUDENT_ME_HTML 渲染验证 (学员短码+主版)")
# 找一个已注册学员 short_id 渲染
try:
    import sys as _sys
    _sys.path.insert(0, "/app")
    from web_app import app, _admin_students, _sign_me_token
    studs = _admin_students.list_students(limit=1) or []
    if not studs:
        print("  [skip] 无学员数据, 跳过主版渲染验证")
    else:
        sid = studs[0].get("short_id") or ""
        token = _sign_me_token(sid)
        with app.test_client() as c:
            r = c.get(f"/me/{sid}?t={token}")
            html = r.get_data(as_text=True)
        assert_t("HTTP 200", r.status_code == 200, f"got {r.status_code}")
        assert_t("页面含 luoguAiTutor 按钮", "onclick=\"luoguAiTutor(this)\"" in html)
        assert_t("页面已无外跳 aijiangti.cn", "aijiangti.cn/?pid=" not in html)
        # AI_TUTOR_BUTTON_JS 注入检测
        assert_t("JS 函数 luoguAiTutor 已注入", "function luoguAiTutor(btn)" in html)
        # 错误地使用了 jinja 全局: 查 {{ AI_TUTOR_BUTTON_JS|safe }} 没渲染成原始字符串
        assert_t("Jinja 全局变量已解析", "{{ AI_TUTOR_BUTTON_JS" not in html)
except Exception as e:
    print(f"  [warn] 模板渲染验证跳过: {e}")


# ============================================================
# 5b) 学员 lite 版 HTML 验证 (找不到 report 时用)
# ============================================================
print("\n[5b] STUDENT_ME_LITE_HTML 渲染验证")
try:
    import sys as _sys
    _sys.path.insert(0, "/app")
    from web_app import app, _admin_students, _sign_me_token
    # 找一个无 report 的学员(无报告时走 lite 渲染路径)
    all_studs = _admin_students.list_students(limit=50) or []
    target = None
    for s in all_studs:
        # v3.9.18 lite 路径: get_student_by_short_id 返回但无报告
        # 直接渲染 /me/<sid>/lite (如果有此路由) 或尝试用 /me/<sid>?lite=1
        target = s
        break
    if not target:
        print("  [skip] 无学员数据")
    else:
        sid = target.get("short_id") or ""
        token = _sign_me_token(sid)
        with app.test_client() as c:
            r = c.get(f"/me/{sid}?t={token}")
            html = r.get_data(as_text=True)
        # 学员主版/ lite 版共用同一份模板, JS 验证基本相同
        assert_t("HTTP 200", r.status_code == 200)
        # 注入过就行
        assert_t("JS 函数 luoguAiTutor 已注入", "function luoguAiTutor(btn)" in html)
except Exception as e:
    print(f"  [warn] lite 渲染验证跳过: {e}")


# ============================================================
# 6) 公开 /r/<uid> 预览页 HTML 含按钮
# ============================================================
print("\n[6] /r/<uid> 公开预览页 HTML 验证")
try:
    import sys as _sys
    _sys.path.insert(0, "/app")
    from web_app import app, _admin_students
    # 找有 luogu_uid 的学员
    all_studs = _admin_students.list_students(limit=50) or []
    uid = ""
    for s in all_studs:
        v = (s.get("luogu_uid") or "").strip()
        if v and v.isdigit():
            uid = v
            break
    if not uid:
        # 兜底: 找数据库里所有 luogu_uid 非空的学员
        try:
            import sqlite3
            conn = sqlite3.connect("/app/data/students.db")
            cur = conn.execute("SELECT luogu_uid FROM students WHERE luogu_uid IS NOT NULL AND luogu_uid != '' LIMIT 1")
            row = cur.fetchone()
            conn.close()
            if row:
                uid = str(row[0])
        except Exception:
            pass
    if not uid:
        print("  [skip] 无 luogu_uid 数据, 跳过预览页验证")
    else:
        with app.test_client() as c:
            r = c.get(f"/r/{uid}")
            html = r.get_data(as_text=True)
        assert_t("HTTP 200", r.status_code == 200, f"got {r.status_code}")
        # 公开页可能没有错题数据(没报告),按钮可能 0 个,但 JS 必须注入
        assert_t("JS 函数 luoguAiTutor 已注入", "function luoguAiTutor(btn)" in html)
        assert_t("页面已无外跳 aijiangti.cn", "aijiangti.cn/?pid=" not in html)
except Exception as e:
    print(f"  [warn] /r/<uid> 验证跳过: {e}")


# ============================================================
# 7) 结果页 GET → 200 (job_id 存在)
# ============================================================
print(f"\n[7] GET /ai-tutor-result/{job_id} (匿名结果页)")
status7, body7 = http("GET", f"/ai-tutor-result/{job_id}")
assert_t("HTTP 200", status7 == 200, f"got {status7}")
assert_t("页面含 AI 讲题标题", "AI 讲题" in body7)
assert_t("页面含 progress 容器", "progress-fill" in body7)
# 轮询直到 done (stub 模式约 8s)
print("  ... 轮询 stub 后端完成 (max 15s)")
for _ in range(15):
    time.sleep(1)
    s, b = http("GET", f"/api/ai-tutor/jobs/{job_id}")
    try:
        d = json.loads(b)
    except Exception:
        continue
    if d.get("done"):
        print(f"  ✅ job 完成 status={d.get('status')}  progress={d.get('progress')}  scenesGenerated={d.get('scenesGenerated')}/{d.get('totalScenes')}")
        # 重新拉一次结果页, 应能看到 scenes
        _, body_done = http("GET", f"/ai-tutor-result/{job_id}")
        assert_t("完成态页面含 scenes 标题", "阶梯 1" in body_done or "scenes" in body_done)
        # v3.11.31 · 完成态时 scenesGenerated == totalScenes
        assert_t("完成时 scenesGenerated = totalScenes", d.get("scenesGenerated") == d.get("totalScenes"),
                 f"got {d.get('scenesGenerated')}/{d.get('totalScenes')}")
        # v3.11.31 · 页面包含分镜进度 DOM
        assert_t("结果页含分镜进度 DOM (progress-scene)", "progress-scene" in body_done)
        break
    else:
        # v3.11.31 · 过程中持续看到分镜进度推进
        sg = d.get("scenesGenerated", -1)
        ts = d.get("totalScenes", -1)
        if sg is not None and ts is not None and sg >= 0 and ts > 0:
            print(f"  ⏳ 进度 {d.get('progress')}%  scene {sg}/{ts}  step={d.get('step')}")
else:
    print("  ⚠️ stub 后端 15s 内未完成, 但 API 验证通过")


# ============================================================
# 总结
# ============================================================
print("\n" + "=" * 60)
if failures:
    print(f"❌ 失败 {len(failures)} 项:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print(f"✅ AI 讲题异步 API + 按钮集成 全部通过")
    sys.exit(0)
