"""
test_vjudge_flow.py - v3.9.74 验证脚本
端到端测试 /link-vjudge → /refresh-vjudge → /unlink-vjudge 完整流程。
打线上 http://43.163.26.115:5000/，验证 VJudge 接入是否通畅。

用法:
    python test_vjudge_flow.py                          # 用默认 UID 跑
    python test_vjudge_flow.py --uid 1752947            # 指定学员 UID
    python test_vjudge_flow.py --uid 1752947 --dry-run  # 只跑不写入(只读探活)
"""

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from typing import Optional, Tuple

# ---------- 默认参数 ----------
DEFAULT_BASE = "https://oi.aijiangti.cn"   # v3.8 · 部署默认域名(docker-compose PUBLIC_BASE_URL)
DEFAULT_UID = "1752947"               # 部署服务器上已知存在的测试学员
DEFAULT_VJ_USER = "tourist"            # VJudge 上真实存在的高知名度账号(只读抓公开数据)

# ---------- 配色 ----------
class C:
    G = "\033[92m"; Y = "\033[93m"; R = "\033[91m"; B = "\033[94m"; X = "\033[0m"

def ok(msg):  print(f"  {C.G}✓{C.X} {msg}")
def fail(msg):print(f"  {C.R}✗{C.X} {msg}")
def info(msg): print(f"  {C.B}·{C.X} {msg}")
def warn(msg): print(f"  {C.Y}!{C.X} {msg}")
def step(msg): print(f"\n{C.B}▶{C.X} {msg}")

# ---------- HTTP 封装 ----------
def http(method: str, url: str, data: Optional[dict] = None,
         timeout: int = 15) -> Tuple[int, dict, str]:
    """返回 (status_code, headers, body)。不抛异常,失败用 (-1, {}, err) 表示。"""
    body_bytes = b""
    headers = {}
    if data is not None:
        body_bytes = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
    # 关掉 SSL 证书校验(自签证书场景),生产域名一般是可信 CA
    import ssl
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return e.code, dict(e.headers or {}), body
    except urllib.error.URLError as e:
        return -1, {}, f"URLError: {e.reason}"
    except Exception as e:
        return -1, {}, f"{type(e).__name__}: {e}"

def post_form(base, path, data, timeout=15):
    return http("POST", f"{base}{path}", data=data, timeout=timeout)

def get_json(base, path, timeout=15):
    return http("GET", f"{base}{path}", timeout=timeout)

# ---------- 验证函数 ----------
def check_version(base: str) -> bool:
    step("Step 0 · 健康检查 /api/version")
    code, _, body = get_json(base, "/api/version", timeout=10)
    if code != 200:
        fail(f"无法访问 {base}/api/version, code={code}")
        return False
    try:
        j = json.loads(body)
        info(f"version   = {j.get('version')}")
        info(f"build     = {j.get('build')}")
        info(f"git       = {j.get('git')}")
        if not j.get("version", "").startswith("v3.9.74"):
            warn(f"当前部署不是 v3.9.74(可能未升级)")
        ok("/api/version 200")
        return True
    except Exception as e:
        fail(f"返回非 JSON: {body[:200]}")
        return False

def check_link_valid(base: str, uid: str, username: str) -> bool:
    step(f"Step 1 · POST /link-vjudge  (uid={uid}, user={username})")
    code, hdr, body = post_form(base, "/link-vjudge", {"luogu_uid": uid, "username": username})
    if code != 302:
        fail(f"期望 302,实际 {code}, body={body[:200]}")
        return False
    loc = hdr.get("Location", "") or hdr.get("location", "")
    info(f"Location = {loc}")
    if "vjudge_linked=1" in loc or "vjudge_error" in loc:
        if "vjudge_error" in loc:
            fail(f"绑定失败: {urllib.parse.unquote(loc)}")
            return False
        ok("绑定成功,跳转 vjudge_linked=1")
        return True
    fail(f"跳转 URL 异常: {loc}")
    return False

def check_link_validation_errors(base: str) -> bool:
    step("Step 2 · POST /link-vjudge 边界用例")
    all_pass = True
    cases = [
        ({"luogu_uid": "1752947", "username": ""},    "missing_params", "空 username"),
        ({"luogu_uid": "1752947", "username": "ab"},   "format",         "username 长度 < 3"),
        ({"luogu_uid": "1752947", "username": "中文名"}, "format",        "username 含中文"),
        ({"luogu_uid": "",        "username": "alice"}, "missing_params", "空 luogu_uid"),
    ]
    for data, expect_kw, desc in cases:
        code, hdr, body = post_form(base, "/link-vjudge", data)
        loc = hdr.get("Location", "") or hdr.get("location", "")
        if code == 302 and expect_kw in loc:
            ok(f"{desc} → 302 {loc[:60]}")
        else:
            fail(f"{desc} → code={code} loc={loc[:80]}")
            all_pass = False
    return all_pass

def check_api_unlinked_then_linked(base: str, uid: str, username: str) -> bool:
    step(f"Step 3 · GET /api/vjudge/{uid}.json 状态轮询")
    # 绑完后再读一次,应该是 linked=true,link_status=pending/ok
    code, _, body = get_json(base, f"/api/vjudge/{uid}.json")
    if code != 200:
        fail(f"读 API 失败,code={code}")
        return False
    try:
        j = json.loads(body)
    except Exception:
        fail(f"返回非 JSON: {body[:200]}")
        return False
    info(f"linked       = {j.get('linked')}")
    info(f"link_status  = {j.get('link_status')}")
    info(f"username     = {j.get('username')}")
    info(f"fetch_status = {j.get('fetch_status')}")
    if j.get("linked") and j.get("username") == username:
        ok(f"API 状态正确(linked=true, user={username})")
        return True
    fail(f"API 状态异常: {j}")
    return False

def check_refresh(base: str, uid: str) -> bool:
    step(f"Step 4 · POST /refresh-vjudge  (uid={uid})")
    code, hdr, body = post_form(base, "/refresh-vjudge", {"luogu_uid": uid})
    loc = hdr.get("Location", "") or hdr.get("location", "")
    if code == 302 and ("vjudge_refreshing=1" in loc or "vjudge_error" in loc):
        if "vjudge_error=already_pending" in loc:
            warn("1h 内已有 pending 任务,跳过(节流逻辑正常)")
            return True
        if "vjudge_refreshing=1" in loc:
            ok("已入队,跳转 vjudge_refreshing=1")
            return True
    fail(f"刷新异常: code={code} loc={loc[:100]}")
    return False

def check_poll_pending_to_ok(base: str, uid: str, max_wait: int = 90) -> bool:
    step(f"Step 5 · 轮询 fetch_status (uid={uid}, 最长等 {max_wait}s)")
    deadline = time.time() + max_wait
    seen = set()
    while time.time() < deadline:
        code, _, body = get_json(base, f"/api/vjudge/{uid}.json")
        if code == 200:
            try:
                j = json.loads(body)
            except Exception:
                j = {}
            st = j.get("fetch_status") or j.get("link_status") or "?"
            if st not in seen:
                info(f"fetch_status = {st}")
                seen.add(st)
            if st == "ok":
                ok(f"抓取完成,AC={j.get('total_ac', 0)}, solved={j.get('solved_count', 0)}")
                return True
            if st == "failed":
                warn(f"抓取失败: {j.get('fetch_error', '?')}")
                return False
        time.sleep(3)
    warn(f"超时 {max_wait}s 未到 ok,最后状态={st}")
    return False

def check_unlink(base: str, uid: str) -> bool:
    step(f"Step 6 · POST /unlink-vjudge  (uid={uid})")
    code, hdr, body = post_form(base, "/unlink-vjudge", {"luogu_uid": uid})
    loc = hdr.get("Location", "") or hdr.get("location", "")
    if code == 302 and "vjudge_unlinked=1" in loc:
        ok("解绑成功,跳转 vjudge_unlinked=1")
    else:
        fail(f"解绑异常: code={code} loc={loc[:100]}")
        return False
    # 再读 API 确认 unlinked
    code, _, body = get_json(base, f"/api/vjudge/{uid}.json")
    if code == 200:
        try:
            j = json.loads(body)
            info(f"unlinked 后 API: {j}")
            if j.get("linked") is False and j.get("link_status") == "unlinked":
                ok("API 状态: linked=false link_status=unlinked ✓")
                return True
        except Exception:
            pass
    fail(f"解绑后 API 状态异常: {body[:200]}")
    return False

# ---------- 主流程 ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE, help="线上 base URL")
    ap.add_argument("--uid",  default=DEFAULT_UID,  help="测试学员 luogu_uid")
    ap.add_argument("--user", default=DEFAULT_VJ_USER, help="VJudge username")
    ap.add_argument("--dry-run", action="store_true", help="只打健康检查,不写入")
    ap.add_argument("--skip-poll", action="store_true", help="跳过抓取轮询(节省时间)")
    ap.add_argument("--wait", type=int, default=90, help="轮询超时秒数")
    args = ap.parse_args()

    print(f"{C.B}== VJudge 接入验证 =={C.X}")
    print(f"  base = {args.base}")
    print(f"  uid  = {args.uid}")
    print(f"  user = {args.user}")
    if args.dry_run:
        warn("--dry-run: 只做健康检查")
    if not check_version(args.base):
        return 2

    if args.dry_run:
        return 0

    results = {}
    results["link_valid"]   = check_link_valid(args.base, args.uid, args.user)
    results["validation"]   = check_link_validation_errors(args.base)
    results["api_linked"]   = check_api_unlinked_then_linked(args.base, args.uid, args.user)
    results["refresh"]      = check_refresh(args.base, args.uid)
    if not args.skip_poll:
        results["poll_ok"]  = check_poll_pending_to_ok(args.base, args.uid, args.wait)
    else:
        warn("跳过抓取轮询(--skip-poll)")
        results["poll_ok"]  = None
    results["unlink"]       = check_unlink(args.base, args.uid)

    # ----- 总结 -----
    print(f"\n{C.B}== 汇总 =={C.X}")
    width = max(len(k) for k in results)
    fails = 0
    for k, v in results.items():
        if v is True:
            print(f"  {C.G}PASS{C.X}  {k.ljust(width)}")
        elif v is False:
            print(f"  {C.R}FAIL{C.X}  {k.ljust(width)}")
            fails += 1
        else:
            print(f"  {C.Y}SKIP{C.X}  {k.ljust(width)}")
    if fails == 0:
        print(f"\n{C.G}全部通过 ✓{C.X}")
        return 0
    else:
        print(f"\n{C.R}{fails} 项失败 ✗{C.X}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
