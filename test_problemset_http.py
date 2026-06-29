"""test_problemset_http.py - HTTP 冒烟测试 problemset_index 接入"""
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:5000"


def main():
    print("=" * 60)
    print(" problemset_index HTTP 冒烟测试 (v3.11.0)")
    print("=" * 60)

    # 1) problemset 状态
    r = urllib.request.urlopen(f"{BASE}/api/problemset-status", timeout=5)
    status = json.loads(r.read())
    print()
    print("[1] GET /api/problemset-status")
    for k, v in status.items():
        vs = str(v)
        if len(vs) > 80:
            vs = vs[:80] + "..."
        print(f"  {k}: {vs}")
    assert status.get("ready") is True, "应有本地索引就绪 (刚才跑过 test)"
    assert status.get("problem_count") > 10000, f"题目数应 > 10000, 实际 {status.get('problem_count')}"

    # 2) 查 P1000 (HIT)
    r = urllib.request.urlopen(f"{BASE}/api/problemset/lookup/P1000", timeout=5)
    info = json.loads(r.read())
    print()
    print("[2] GET /api/problemset/lookup/P1000")
    for k, v in info.items():
        vs = str(v)
        if len(vs) > 80:
            vs = vs[:80] + "..."
        print(f"  {k}: {vs}")
    assert info.get("title") == "超级玛丽游戏"
    assert info.get("difficulty") == 1
    assert isinstance(info.get("tags"), list) and len(info["tags"]) > 0

    # 3) 查 P3811 (HIT, 模板题)
    r = urllib.request.urlopen(f"{BASE}/api/problemset/lookup/P3811", timeout=5)
    info = json.loads(r.read())
    print()
    print("[3] GET /api/problemset/lookup/P3811")
    print(f"  title: {info.get('title')!r}")
    print(f"  difficulty: {info.get('difficulty')}")
    print(f"  tags: {info.get('tags')}")
    assert info.get("title"), "应有 title"

    # 4) miss (404)
    try:
        r = urllib.request.urlopen(f"{BASE}/api/problemset/lookup/NONEXISTENT_999", timeout=5)
        print(f"\n[4] /lookup/NONEXISTENT_999 -> {r.status} (期望 404)")
        assert False, "miss 应返回 404"
    except urllib.error.HTTPError as e:
        print(f"\n[4] /lookup/NONEXISTENT_999 -> {e.code} (期望 404)")
        assert e.code == 404

    # 5) admin refresh (force=0, 不重下)
    req = urllib.request.Request(
        f"{BASE}/admin/refresh-problemset",
        data=b"force=0",
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    r = urllib.request.urlopen(req, timeout=5)
    print()
    print(f"[5] POST /admin/refresh-problemset (force=0) -> {r.status}")
    body = json.loads(r.read())
    print(f"  body: {body}")
    assert r.status == 202
    assert body.get("ok") is True

    # 6) 老的 API 不受影响
    r = urllib.request.urlopen(f"{BASE}/api/version", timeout=5)
    body = json.loads(r.read())
    print()
    print(f"[6] GET /api/version")
    print(f"  body: {body}")
    assert body.get("version") == "v3.11.0"

    # 7) ZIP 上传页面仍能访问(回归)
    r = urllib.request.urlopen(f"{BASE}/upload-zip", timeout=5)
    print()
    print(f"[7] GET /upload-zip -> {r.status}  {len(r.read())} bytes")
    assert r.status == 200

    # 8) 首页仍能访问(回归)
    r = urllib.request.urlopen(f"{BASE}/", timeout=5)
    body = r.read()
    print(f"[8] GET / -> {r.status}  {len(body)} bytes")
    assert r.status == 200
    assert b"v3.11.0" in body
    assert b"/upload-zip" in body

    print()
    print("=" * 60)
    print(" ✅ 8/8 HTTP 测试全部通过")
    print("=" * 60)


if __name__ == "__main__":
    main()
