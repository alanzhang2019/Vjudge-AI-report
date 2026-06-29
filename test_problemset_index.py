"""test_problemset_index.py - 单元测试 + 真实下载/构建/查询 (v3.11.0)"""
import time
import problemset_index as pi


def cb_log(stage, done, total):
    if stage in ("download", "ready", "error"):
        print(f"  [progress] {stage}: {done} {'/' + str(total) if total >= 0 else ''}")
    elif done % 5000 < 200:
        print(f"  [progress] {stage}: {done}")


def main():
    print("=" * 60)
    print(" problemset_index 端到端测试 (v3.11.0)")
    print("=" * 60)

    # 0) 启动状态
    print()
    print("--- 0) 启动状态 (无缓存) ---")
    s = pi.get_status()
    for k, v in s.items():
        print(f"  {k}: {v}")

    # 1) 真实下载 + 构建(可能用 1-2 分钟)
    print()
    print("--- 1) 真实下载 + 构建索引 ---")
    t0 = time.time()
    ok = pi.download_and_build(progress_cb=cb_log, force_download=False)
    dt = time.time() - t0
    print(f"  [done] ok={ok}, {dt:.1f}s")

    if not ok:
        print("[FAIL] download_and_build 失败,无法继续")
        return 1

    # 2) 查询常用题
    print()
    print("--- 2) 常用题 spot check ---")
    for pid in ["P1000", "P1001", "P1042", "P3811", "CF1A", "AT_abc001_a", "B2031", "SP1", "U69096"]:
        info = pi.get(pid)
        if info:
            t = info.get("title", "")
            if len(t) > 30:
                t = t[:30] + "..."
            print(f"  {pid:18s} | diff={info.get('difficulty')} | tags={len(info.get('tags') or [])} | {t}")
        else:
            print(f"  {pid:18s} | <not found>")

    # 3) 批量查询
    print()
    print("--- 3) 批量查询 ---")
    batch = pi.get_many(["P1000", "P1001", "NONEXISTENT_999", "P1042"])
    print(f"  hit {len(batch)}/4 (NONEXISTENT_999 应 miss)")

    # 4) 补全 ProblemSummary-like 对象
    print()
    print("--- 4) enrich_problem (空 → 填充) ---")
    class FakeProblem:
        def __init__(self, pid):
            self.pid = pid
            self.title = ""
            self.difficulty = None
            self.tags = []
    p = FakeProblem("P1000")
    changed = pi.enrich_problem(p)
    print(f"  改动字段数: {changed}, title={p.title!r}, diff={p.difficulty}, tags_count={len(p.tags)}")
    assert p.title, "title 应被填充"

    # 5) 幂等: 第二次 enrich_problem 不应改动(因为字段已非空)
    changed2 = pi.enrich_problem(p)
    print(f"  第二次改动: {changed2} (期望 0)")
    assert changed2 == 0, "已填充字段不应被覆盖"

    # 6) miss 时的退化
    p_bad = FakeProblem("NONEXISTENT_999")
    changed_bad = pi.enrich_problem(p_bad)
    print(f"  miss pid 改动: {changed_bad} (期望 0)")
    assert changed_bad == 0

    # 7) 最终状态
    print()
    print("--- 7) 最终状态 ---")
    s = pi.get_status()
    for k, v in s.items():
        vs = str(v)
        if len(vs) > 80:
            vs = vs[:80] + "..."
        print(f"  {k}: {vs}")

    # 8) 重复调用 ensure_ready 应走内存缓存(不重复构建)
    print()
    print("--- 8) ensure_ready 二次调用(应直接命中内存) ---")
    t0 = time.time()
    ok = pi.ensure_ready()
    dt = (time.time() - t0) * 1000
    print(f"  ok={ok}, {dt:.1f}ms")
    assert ok and dt < 50, f"二次 ensure_ready 应 < 50ms, 实际 {dt:.1f}ms"

    print()
    print("=" * 60)
    print(" ✅ 全部通过")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
