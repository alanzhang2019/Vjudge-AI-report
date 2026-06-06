#!/usr/bin/env python3
"""
一键从 alanzhang2019/luogu-AI-report 上游拉取缺失/过时的文件到当前项目目录。
用法：python sync_upstream.py
"""
import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

REPO = "alanzhang2019/luogu-AI-report"
BRANCH = "main"
API = f"https://api.github.com/repos/{REPO}/contents"
RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"

ROOT = Path(__file__).resolve().parent

# 需要覆盖/新建的文件（相对项目根）
TARGETS = [
    "web_app.py",
    "task_store.py",
    "behavior_analyzer.py",
    "syllabus_matcher.py",
    "code_analyzer.py",
    "env_loader.py",
    "luogu_evaluator.py",
    "examples/export_for_ai.py",
    "report_template.html",
    ".env.example",
]

SKIP_DIRS = {".git", ".github", ".dbg", ".source_cache", "reports", "assets", "node_modules", "__pycache__", "tests"}


def list_repo(path: str = "") -> list[dict]:
    url = f"{API}/{path}" if path else API
    req = urllib.request.Request(url, headers={"User-Agent": "sync-script"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def download_file(sha: str, dest: Path) -> int:
    """通过 blobs API 拿 base64 编码的内容，解码后写盘。"""
    url = f"https://api.github.com/repos/{REPO}/git/blobs/{sha}"
    req = urllib.request.Request(url, headers={"User-Agent": "sync-script"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
    content_b64 = data.get("content", "")
    encoding = data.get("encoding", "")
    if encoding != "base64":
        raise RuntimeError(f"{dest}: unexpected encoding {encoding}")
    raw = base64.b64decode(content_b64)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)
    return len(raw)


def fetch_top_level() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for item in list_repo(""):
        if item["name"] in SKIP_DIRS:
            continue
        out[item["name"]] = item
    return out


def fetch_subdir(sub: str) -> list[dict]:
    out: list[dict] = []
    try:
        out = list_repo(sub)
    except Exception as e:
        print(f"  ! 跳过子目录 {sub}: {e}")
    return [x for x in out if x["name"] not in SKIP_DIRS]


def main() -> int:
    print(f"[sync] 仓库: {REPO}@{BRANCH}")
    print(f"[sync] 目标: {ROOT}")
    print()

    # 1) 单文件拉取
    top = fetch_top_level()
    for rel in TARGETS:
        name = rel.split("/", 1)[0]
        if name not in top:
            print(f"  - 跳过 {rel}（上游不存在）")
            continue
        item = top[name]
        if item["type"] != "file":
            # 比如 export_for_ai.py 在 examples 子目录
            sub, fname = rel.split("/", 1)
            sub_items = {x["name"]: x for x in fetch_subdir(sub)}
            if fname not in sub_items:
                print(f"  - 跳过 {rel}（上游子目录不存在）")
                continue
            item = sub_items[fname]
        dest = ROOT / rel
        try:
            size = download_file(item["sha"], dest)
            print(f"  + {rel}  ({size} bytes)")
        except Exception as e:
            print(f"  ! {rel} 下载失败: {e}")

    # 2) 字体目录 assets/fonts
    if "assets" in top and top["assets"]["type"] == "dir":
        print()
        print("[sync] 拉取 assets/fonts ...")
        fonts = fetch_subdir("assets/fonts")
        for f in fonts:
            if f["type"] != "file":
                continue
            dest = ROOT / "assets" / "fonts" / f["name"]
            try:
                size = download_file(f["sha"], dest)
                print(f"  + assets/fonts/{f['name']}  ({size} bytes)")
            except Exception as e:
                print(f"  ! assets/fonts/{f['name']} 失败: {e}")
    else:
        print()
        print("[sync] 上游无 assets/ 目录，跳过字体。")

    # 3) requirements.txt（如果存在）
    if "requirements.txt" in top:
        dest = ROOT / "requirements.txt"
        try:
            size = download_file(top["requirements.txt"]["sha"], dest)
            print(f"\n[sync] 覆盖 requirements.txt ({size} bytes)")
        except Exception as e:
            print(f"\n[sync] requirements.txt 失败: {e}")

    print()
    print("[sync] 完成。请检查变更后再重新构建 Docker 镜像。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
