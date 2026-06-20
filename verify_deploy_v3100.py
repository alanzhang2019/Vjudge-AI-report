"""v3.10.0 部署后验证脚本(直接走 SSH,不依赖 Trae 终端回显)

把远端 docker logs / sqlite / pip list 拉到本地 .verify/ 目录,
IDE 可以直接读这些文件确认状态。
"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime

REMOTE = "ubuntu@43.163.26.115"
CONTAINER = "luogu-ai-report-luogu-coach"
OUT = Path(__file__).parent / ".verify"
OUT.mkdir(exist_ok=True)


def ssh(cmd: str, label: str) -> None:
    full = f"ssh -o StrictHostKeyChecking=no {REMOTE} {cmd!r}"
    ts = datetime.now().strftime("%H%M%S")
    f = OUT / f"{ts}_{label}.txt"
    print(f"[{ts}] {label} ...", flush=True)
    try:
        r = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=60)
        f.write_text(
            f"=== CMD ===\n{full}\n\n"
            f"=== RC ===\n{r.returncode}\n\n"
            f"=== STDOUT ===\n{r.stdout}\n\n"
            f"=== STDERR ===\n{r.stderr}\n",
            encoding="utf-8",
        )
        print(f"  -> {f} (rc={r.returncode}, {len(r.stdout)} bytes)", flush=True)
    except Exception as e:
        f.write_text(f"=== EXC ===\n{e!r}\n", encoding="utf-8")
        print(f"  -> {f} (exc)", flush=True)


def curl_register() -> None:
    import urllib.request, urllib.parse
    ts = int(datetime.utcnow().timestamp())
    data = urllib.parse.urlencode({
        "city": "北京", "real_name": "调试用户", "grade": "JUNIOR_1", "gender": "M",
        "email": f"verify_{ts}@test.local",
        "password": "Aa123456!", "password_confirm": "Aa123456!", "agree": "on",
    }).encode("utf-8")
    url = "https://oi.aijiangti.cn/register"
    ts2 = datetime.now().strftime("%H%M%S")
    f = OUT / f"{ts2}_register_response.html"
    try:
        req = urllib.request.Request(url, data=data, method="POST",
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
        # 不跟随重定向
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **kw): return None
        opener2 = urllib.request.build_opener(NoRedirect)
        r = opener2.open(req, timeout=30)
        body = r.read().decode("utf-8", errors="replace")
        f.write_text(
            f"=== URL ===\n{url}\n\n"
            f"=== STATUS ===\n{r.status}\n\n"
            f"=== HEADERS ===\n{dict(r.headers)}\n\n"
            f"=== BODY (前 3000 字符) ===\n{body[:3000]}\n",
            encoding="utf-8",
        )
        print(f"  -> {f} (status={r.status})", flush=True)
        # 抓错误信息
        import re
        m = re.search(r'app-box app-box-red[^<]*<[^>]*>\s*([^<]+)', body)
        if m:
            print(f"  >> 错误: {m.group(1).strip()}", flush=True)
        m2 = re.search(r'<title>([^<]+)</title>', body)
        if m2:
            print(f"  >> 标题: {m2.group(1)}", flush=True)
    except urllib.error.HTTPError as e:
        f.write_text(
            f"=== HTTPError ===\nstatus={e.code}\nheaders={dict(e.headers)}\n"
            f"body (前 3000)=\n{e.read().decode('utf-8', errors='replace')[:3000]}\n",
            encoding="utf-8",
        )
        print(f"  -> {f} (http {e.code})", flush=True)
    except Exception as e:
        f.write_text(f"=== EXC ===\n{e!r}\n", encoding="utf-8")
        print(f"  -> {f} (exc)", flush=True)


print("=" * 60, flush=True)
print(f"目标: {REMOTE} / {CONTAINER}", flush=True)
print("=" * 60, flush=True)

# 1. 容器状态
ssh(f'"docker ps --filter name={CONTAINER} --format \'{{{{.Names}}}} {{{{.Status}}}} {{{{.Ports}}}}\'"', "docker_status")
# 2. 容器最近 200 行日志
ssh(f'"docker logs --tail 200 {CONTAINER} 2>&1"', "docker_logs")
# 3. 容器里 schema
ssh(f'"docker exec {CONTAINER} sqlite3 /app/tasks.db \'.schema students\'"', "schema_students")
# 4. 容器里 pip list grep bcrypt
ssh(f'"docker exec {CONTAINER} sh -c \'pip list 2>&1 | grep -iE \'bcrypt|flask|playwright|gunicorn\'',"pip_list")
# 5. 容器里 health
ssh(f'"docker exec {CONTAINER} sh -c \'curl -fsS http://127.0.0.1:5000/api/version 2>&1\'"', "api_version")
# 6. 容器里看文件 web_app.py 顶部 version
ssh(f'"docker exec {CONTAINER} grep -m 1 APP_VERSION /app/web_app.py"', "app_version_const")
# 7. /register GET 拿 form
ssh(f'"docker exec {CONTAINER} sh -c \'curl -fsS http://127.0.0.1:5000/register | head -c 2000\'"', "register_get_head")

# 8. 直接在容器里 POST /register 触发 500
ts = int(datetime.utcnow().timestamp())
body = f"city=%E5%8C%97%E4%BA%AC&real_name=%E8%B0%83%E8%AF%95%E7%94%A8%E6%88%B7&grade=JUNIOR_1&gender=M&email=docker_{ts}@test.local&password=Aa123456!&password_confirm=Aa123456!&agree=on"
ssh(f'"docker exec {CONTAINER} sh -c \'curl -i -X POST -d \\"{body}\\" http://127.0.0.1:5000/register 2>&1 | head -40\'"', "register_post_inside")

# 9. 容器日志再拉一次
ssh(f'"docker logs --tail 200 {CONTAINER} 2>&1 | tail -120"', "docker_logs_after")

# 10. 外网 curl 触发
curl_register()

# 11. 外网 curl 之后再看日志
ssh(f'"docker logs --tail 200 {CONTAINER} 2>&1 | tail -100"', "docker_logs_after_outside")

print("=" * 60, flush=True)
print("完成,结果在 .verify/ 目录", flush=True)
print("=" * 60, flush=True)
