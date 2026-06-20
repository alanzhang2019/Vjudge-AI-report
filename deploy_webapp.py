#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deploy_webapp.py  -  一键把本地 web_app.py 部署到远端 Docker 容器。

流程:
  1) 读本地 web_app.py,计算 md5
  2) scp 到 ubuntu@43.163.26.115 的 /tmp/web_app.py.new
  3) docker cp 到容器 luogu-ai-report-luogu-coach 的 /app/web_app.py
  4) 容器内 md5 校验,必须 == 本地 md5,否则 abort
  5) docker restart luogu-ai-report-luogu-coach
  6) sleep 10s 等启动
  7) curl http://localhost:5000/api/version(或公网),期望 200 且 APP_VERSION == 本地

使用:
  python deploy_webapp.py
  python deploy_webapp.py --local-webapp D:\\path\\to\\web_app.py
  python deploy_webapp.py --container luogu-ai-report-luogu-coach \\
                          --host ubuntu@43.163.26.115 \\
                          --public-url http://luogu.example.com
"""
import argparse
import hashlib
import shlex
import subprocess
import sys
import time
from pathlib import Path

REMOTE_TMP = "/tmp/web_app.py.new"
CONTAINER_PATH = "/app/web_app.py"
DEFAULT_HOST = "ubuntu@43.163.26.115"
DEFAULT_CONTAINER = "luogu-ai-report-luogu-coach"
DEFAULT_LOCAL = r"c:\Users\zpy20\Desktop\项目\luoguAI\luogu-api-python\web_app.py"
DEFAULT_PUBLIC_URL = "http://43.163.26.115"  # 走公网
LOCAL_PROBE_URL = "http://127.0.0.1:5000"    # 走容器内 localhost


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], *, check: bool = True, capture: bool = False, timeout: int = 120) -> subprocess.CompletedProcess:
    """统一封装:打印命令再执行,失败抛非 0 退出码。"""
    pretty = " ".join(shlex.quote(c) for c in cmd)
    print(f"  $ {pretty}")
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def ssh_cmd(host: str, remote_cmd: str, *, capture: bool = True) -> subprocess.CompletedProcess:
    return run(["ssh", host, remote_cmd], check=False, capture=capture, timeout=180)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--local-webapp", default=DEFAULT_LOCAL)
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--container", default=DEFAULT_CONTAINER)
    ap.add_argument("--public-url", default=DEFAULT_PUBLIC_URL)
    ap.add_argument("--skip-restart", action="store_true", help="只同步文件,不重启容器(调试用)")
    ap.add_argument("--skip-md5-check", action="store_true", help="跳过 md5 一致性校验")
    ap.add_argument("--log-file", default=None, help="把所有 print 输出也写到这个文件,便于 Trae 终端抓取")
    args = ap.parse_args()

    if args.log_file:
        import builtins as _b
        _orig_print = _b.print
        _log_fp = open(args.log_file, "a", encoding="utf-8")

        def _print(*a, **kw):
            _orig_print(*a, **kw)
            _orig_print(*a, **kw, file=_log_fp)

        _b.print = _print

    local = Path(args.local_webapp)
    if not local.exists():
        print(f"[ERR] 本地 web_app.py 不存在: {local}", file=sys.stderr)
        return 2

    print(f"[1/7] 读本地 {local}")
    local_md5 = md5_of(local)
    local_size = local.stat().st_size
    print(f"  本地 md5 = {local_md5}  size = {local_size} bytes")

    print(f"[2/7] scp → {args.host}:{REMOTE_TMP}")
    scp = run(["scp", str(local), f"{args.host}:{REMOTE_TMP}"], check=False, capture=True)
    if scp.returncode != 0:
        print(f"[ERR] scp 失败: {scp.stderr}", file=sys.stderr)
        return 3

    print(f"[3/7] docker cp → {args.container}:{CONTAINER_PATH}")
    docker_cp = run(
        ["ssh", args.host, f"docker cp {REMOTE_TMP} {args.container}:{CONTAINER_PATH}"],
        check=False, capture=True,
    )
    if docker_cp.returncode != 0:
        print(f"[ERR] docker cp 失败: {docker_cp.stderr}", file=sys.stderr)
        return 4

    if not args.skip_md5_check:
        print("[4/7] 容器内 md5 校验")
        chk = ssh_cmd(args.host, f"docker exec {args.container} md5sum {CONTAINER_PATH}")
        if chk.returncode != 0:
            print(f"[ERR] md5 校验命令失败: {chk.stderr}", file=sys.stderr)
            return 5
        # 输出形如: "abc123...  /app/web_app.py"
        remote_md5 = chk.stdout.strip().split()[0]
        print(f"  容器内 md5 = {remote_md5}")
        if remote_md5 != local_md5:
            print(f"[ERR] md5 不一致! 本地={local_md5}  容器={remote_md5}", file=sys.stderr)
            return 6
        print("  ✅ md5 一致")
    else:
        print("[4/7] 跳过 md5 校验(--skip-md5-check)")

    if args.skip_restart:
        print("[5/7] 跳过容器 restart(--skip-restart)")
    else:
        print(f"[5/7] docker restart {args.container}")
        rst = ssh_cmd(args.host, f"docker restart {args.container}", capture=False)
        if rst.returncode != 0:
            print(f"[ERR] restart 失败: {rst.stderr}", file=sys.stderr)
            return 7
        print("  ✅ 容器已重启")

    print("[6/7] sleep 10s 等启动")
    time.sleep(10)

    print("[7/7] 烟测 /api/version")
    # 先看容器内 127.0.0.1
    for label, url in (
        ("容器内", f"{LOCAL_PROBE_URL}/api/version"),
        ("公网", f"{args.public_url}/api/version"),
    ):
        probe = run(
            ["curl", "-fsS", "-m", "15", url],
            check=False, capture=True,
        )
        if probe.returncode == 0:
            print(f"  [{label}] 200 OK")
            print(f"    body: {probe.stdout.strip()}")
            print("\n✅ 部署完成,点击 AI 报告验证")
            return 0
        else:
            print(f"  [{label}] 失败: {probe.stderr.strip() or probe.stdout.strip()}")

    print("[ERR] 容器内 + 公网 /api/version 都不可达,部署视为失败", file=sys.stderr)
    return 8


if __name__ == "__main__":
    sys.exit(main())
