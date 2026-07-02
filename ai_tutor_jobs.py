"""
v3.11.31 · AI 讲题异步任务存储 + Worker

设计参照 StudyMate 仓库的 async job pattern:
  https://github.com/alanzhang2019/StudyMate/blob/main/app/api/generate-classroom/route.ts
  https://github.com/alanzhang2019/StudyMate/blob/main/app/api/generate-classroom/[jobId]/route.ts

  POST /api/generate-classroom  → 202 { jobId, status, step, message, pollUrl, pollIntervalMs }
  GET  /api/generate-classroom/<jobId> → 200 {
      jobId, status, step, progress, message, pollUrl, pollIntervalMs,
      scenesGenerated, totalScenes, result, error, done
  }

本模块的接口 (路径兼容 luoguAI 项目):
  - create_job(requirement, problem_id, source, language, title, luogu_uid, ...) -> job_id
  - get_job(job_id) -> { jobId, status, step, progress, message,
                          scenesGenerated, totalScenes, result, done, ... }
  - _worker_run(job_id, ...)  后台线程跑讲解

后端可配 (环境变量):
  AI_TUTOR_BACKEND = "openai"        # 走本项目现有的 LLM 配置
  AI_TUTOR_BACKEND = "aijiangti"     # POST 到 https://aijiangti.cn/api/...
  AI_TUTOR_BACKEND = "stub"          # 直接返回占位讲解 (默认, 待真实后端上线)

存储: 进程内 dict + 线程锁 (简化). 重启后清空 (job 短期任务, 不需要持久化).
"""

from __future__ import annotations
import os
import time
import uuid
import json
import logging
import threading
from typing import Any, Callable, Optional
from dataclasses import dataclass, field, asdict

log = logging.getLogger("ai_tutor_jobs")

# ----------------------------------------------------------------------------
# 后端选择
# ----------------------------------------------------------------------------
AI_TUTOR_BACKEND = (os.environ.get("AI_TUTOR_BACKEND") or "stub").strip().lower()
AI_TUTOR_POLL_INTERVAL_MS = int(os.environ.get("AI_TUTOR_POLL_INTERVAL_MS") or "5000")
# 兜底 URL: 真打 aijiangti.cn 的可配置入口 (默认指向 StudyMate 同形态的服务)
AI_TUTOR_FORWARD_URL = (
    os.environ.get("AI_TUTOR_FORWARD_URL") or "https://aijiangti.cn/api/generate-classroom"
).strip()

# ----------------------------------------------------------------------------
# 内存存储
# ----------------------------------------------------------------------------
_jobs: dict[str, "AiTutorJob"] = {}
_jobs_lock = threading.Lock()

JOB_TTL_SECONDS = 60 * 60 * 4  # 4 小时后清理 (讲解完通常 30~60s, 留 4h 缓冲)


@dataclass
class AiTutorJob:
    """单次 AI 讲题任务"""
    job_id: str
    status: str = "queued"  # queued | running | succeeded | failed
    step: str = "queued"
    progress: int = 0
    message: str = ""
    # 输入 (透传给 worker)
    requirement: str = ""
    problem_id: str = ""
    title: str = ""
    source: str = ""
    language: str = "cpp"
    extra: dict = field(default_factory=dict)
    # 输出
    result: Optional[dict] = None
    error: Optional[str] = None
    # v3.11.31 · StudyMate 契约: 分镜进度 (生成课件时的 scene-by-scene 进度)
    # scenesGenerated: 已经生成的分镜数
    # totalScenes:     总分镜数 (本项目固定 6 节: 题意 / 暴力 / 优化 / 正解 / 易错点 / 同类题)
    scenes_generated: int = 0
    total_scenes: int = 0
    # 时间
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    # 拥有者 (学员 luogu_uid) - 用于结果页路由
    luogu_uid: str = ""

    def touch(self) -> None:
        self.updated_at = time.time()

    def to_dict(self) -> dict:
        d = asdict(self)
        d["jobId"] = self.job_id  # v3.11.31 · 对齐 StudyMate 契约: 驼峰命名 jobId
        d["done"] = self.status in ("succeeded", "failed")
        # v3.11.31 · 对齐 StudyMate 契约: 驼峰命名 scenesGenerated / totalScenes
        d["scenesGenerated"] = int(self.scenes_generated or 0)
        d["totalScenes"] = int(self.total_scenes or 0)
        d["created_at"] = int(self.created_at)
        d["updated_at"] = int(self.updated_at)
        return d


def create_job(
    requirement: str,
    problem_id: str = "",
    title: str = "",
    source: str = "",
    language: str = "cpp",
    luogu_uid: str = "",
    extra: Optional[dict] = None,
) -> str:
    """v3.11.31 · 新建讲题 job, 立即返回 job_id, 后台线程跑."""
    job_id = uuid.uuid4().hex[:10]  # 与 StudyMate nanoid(10) 长度一致
    job = AiTutorJob(
        job_id=job_id,
        requirement=requirement or "",
        problem_id=problem_id or "",
        title=title or "",
        source=source or "",
        language=(language or "cpp").strip().lower(),
        luogu_uid=luogu_uid or "",
        extra=extra or {},
        message="任务已创建, 等待 AI 讲师接管...",
    )
    with _jobs_lock:
        _jobs[job_id] = job
    _start_worker(job_id)
    return job_id


def get_job(job_id: str) -> Optional[AiTutorJob]:
    """v3.11.31 · 查 job 状态 (StudyMate GET /api/generate-classroom/<jobId> 同形)."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        return None
    return job


def _set_status(job_id: str, status: str, step: str = "", progress: int = -1, message: str = "") -> None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job.status = status
        if step:
            job.step = step
        if progress >= 0:
            job.progress = progress
        if message:
            job.message = message
        job.touch()


def _set_result(job_id: str, result: dict) -> None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job.result = result
        job.status = "succeeded"
        job.step = "done"
        job.progress = 100
        job.message = result.get("summary") or "讲解已完成"
        job.touch()


def _set_error(job_id: str, error: str) -> None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job.error = error
        job.status = "failed"
        job.step = "failed"
        job.message = error
        job.touch()


def _set_scene_progress(job_id: str, scenes_generated: int, total_scenes: int) -> None:
    """v3.11.31 · 更新分镜进度 (StudyMate 契约字段 scenesGenerated / totalScenes).
    后台 worker 在每生成一个分镜后调用,前端可看到「scene 3/6」式进度.
    """
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job.scenes_generated = max(int(scenes_generated or 0), job.scenes_generated or 0)
        if total_scenes and total_scenes > 0:
            job.total_scenes = total_scenes
        job.touch()


def _cleanup_loop() -> None:
    """后台线程, 每 10 分钟清一次过期 job."""
    while True:
        try:
            time.sleep(600)
            now = time.time()
            with _jobs_lock:
                stale = [jid for jid, j in _jobs.items() if now - j.updated_at > JOB_TTL_SECONDS]
                for jid in stale:
                    _jobs.pop(jid, None)
            if stale:
                log.info(f"[ai_tutor] cleaned {len(stale)} stale jobs")
        except Exception as e:
            log.warning(f"[ai_tutor] cleanup loop error: {e}")


# ----------------------------------------------------------------------------
# Worker
# ----------------------------------------------------------------------------
_workers_started: bool = False
_workers_lock = threading.Lock()


def _start_worker(job_id: str) -> None:
    """启动 worker 线程处理单个 job. 使用 daemon=True, 进程退出时不强等."""
    global _workers_started
    with _workers_lock:
        if not _workers_started:
            _workers_started = True
            try:
                t = threading.Thread(target=_cleanup_loop, daemon=True, name="ai-tutor-cleanup")
                t.start()
            except Exception as e:
                log.warning(f"[ai_tutor] failed to start cleanup thread: {e}")
    t = threading.Thread(target=_worker_run, args=(job_id,), daemon=True, name=f"ai-tutor-{job_id[:6]}")
    t.start()


def _worker_run(job_id: str) -> None:
    """v3.11.31 · Worker 主入口. 根据 AI_TUTOR_BACKEND 选后端."""
    job = get_job(job_id)
    if job is None:
        return
    _set_status(job_id, "running", step="starting", progress=5, message="正在准备讲解上下文...")
    try:
        if AI_TUTOR_BACKEND == "aijiangti":
            _run_via_aijiangti(job_id, job)
        elif AI_TUTOR_BACKEND == "openai":
            _run_via_openai(job_id, job)
        else:
            # 默认 stub: 模拟 3 步进度后返回占位讲解
            _run_stub(job_id, job)
    except Exception as e:
        log.exception(f"[ai_tutor] worker crashed job={job_id}: {e}")
        _set_error(job_id, f"内部错误: {type(e).__name__}: {e}")


def _run_stub(job_id: str, job: AiTutorJob) -> None:
    """v3.11.31 · 占位 worker: 模拟 3 步进度 (3s+3s+3s) 后返回占位讲解.
    等待真实后端 (openai / aijiangti) 上线时, 改 AI_TUTOR_BACKEND 即可.
    v3.11.31 · 增加分镜进度 (scenesGenerated / totalScenes),对齐 StudyMate 契约.
    """
    log.info(f"[ai_tutor/stub] job={job_id} pid={job.problem_id} title={job.title[:40]}")

    # v3.11.31 · 分镜蓝图 (6 节: 题意 / 暴力 / 优化 / 正解 / 易错点 / 同类题)
    scene_titles = [
        "📌 题意速读",
        "🪜 阶梯 1 · 暴力思路 (O(n²))",
        "🪜 阶梯 2 · 优化思路 (O(n log n))",
        "✅ 阶梯 3 · 正解 (O(n) 或 O(n log n))",
        "🧪 易错点 / 边界",
        "🧠 同类题推荐",
    ]
    total = len(scene_titles)
    _set_scene_progress(job_id, 0, total)
    _set_status(job_id, "running", step="fetching_problem", progress=10, message="📥 正在读取题目上下文 (洛谷 / Codeforces / 校内 OJ)...")

    # 第 1 步: 拉取题目上下文
    time.sleep(2.0)
    _set_status(job_id, "running", step="analyzing_brute", progress=25, message="🔍 正在分析暴力解与边界, 提取典型错因...")

    # 第 2 步: 模拟分镜生成 (每节 ~0.5s, 共 3s)
    for i, title in enumerate(scene_titles, start=1):
        # v3.11.31 · 逐镜推 progress + scenesGenerated,前端可看到 scene 1/6 → 6/6
        pct = 25 + int(60 * i / total)  # 25 → 85
        _set_scene_progress(job_id, i, total)
        _set_status(
            job_id, "running", step=f"scene_{i}_of_{total}", progress=pct,
            message=f"✍️ 正在写「{title}」({i}/{total})...",
        )
        time.sleep(0.5)

    # 第 3 步: 整理排版
    _set_status(job_id, "running", step="polishing", progress=92, message="🎨 整理排版, 准备课件...")
    time.sleep(1.0)

    # 构造占位 result (6 节)
    result = {
        "summary": f"已为「{job.title or job.problem_id or '该题'}」生成 C++ 讲题 · v3.11.31 占位版",
        "language": job.language or "cpp",
        "problem_id": job.problem_id,
        "title": job.title,
        "source": job.source,
        "backend": AI_TUTOR_BACKEND,
        "scenes": [
            {
                "title": "📌 题意速读",
                "body": (job.requirement or f"本节为「{job.title}」一句话题意。")[:300]
                       or f"请先通读题目, 明确输入输出格式。题目源: {job.source or '—'}",
            },
            {
                "title": "🪜 阶梯 1 · 暴力思路 (O(n²))",
                "body": (
                    "**思路** · 直接枚举所有满足条件的子串 / 子序列 / 子集.\n\n"
                    "**复杂度** · O(n²) 或 O(2ⁿ), 100% TLE.\n\n"
                    "**C++ 模板**\n```cpp\nfor (int i = 0; i < n; ++i)\n  for (int j = i; j < n; ++j) {\n    // 检查 [i, j] 是否满足条件\n  }\n```\n\n"
                    "💡 这个版本用来拿部分分, 至少能对 1~2 个测试点."
                ),
            },
            {
                "title": "🪜 阶梯 2 · 优化思路 (O(n log n))",
                "body": (
                    "**关键观察** · 题目约束通常有「单调性」「前缀和」「滑动窗口」其中之一.\n\n"
                    "**思路** · 用前缀和 / 单调队列 / 二分把内层 O(n) 降到 O(log n).\n\n"
                    "**C++ 模板**\n```cpp\n// 前缀和 + 二分\nvector<long long> pre(n+1, 0);\nfor (int i = 0; i < n; ++i) pre[i+1] = pre[i] + a[i];\n\nauto ok = [&](int l, int r) {\n  return pre[r] - pre[l] >= k;  // 区间 [l, r) 和\n};\n```\n\n"
                    "💡 这个版本是大多数题能 AC 的版本."
                ),
            },
            {
                "title": "✅ 阶梯 3 · 正解 (O(n) 或 O(n log n))",
                "body": (
                    "**正解特征** · 通常基于「单调队列 / 线段树 / DS on tree / 莫队 / 主席树」.\n\n"
                    "**通用框架**\n```cpp\n// 1. 离线排序后用 set 维护\n// 2. 在线滑动窗口维护最值\n// 3. 树上问题: 重链剖分 / 长链剖分\n```\n\n"
                    "💡 看到「子数组 / 子序列最值」第一反应应该是 **单调队列**, 而不是堆.\n\n"
                    "💡 看到「区间第 k 大」第一反应应该是 **主席树 / 树套树**, 而不是 sort + 离散化."
                ),
            },
            {
                "title": "🧪 易错点 / 边界",
                "body": (
                    "1. **0-indexed vs 1-indexed** · 洛谷多数题目 1-indexed, 注意数组下标\n"
                    "2. **long long** · 求和 / 乘法结果可能 > 2³¹, 务必 long long\n"
                    "3. **mod 取负** · `(x % mod + mod) % mod`\n"
                    "4. **递归深度** · 树形 DP 时 `ios::sync_with_stdio(false)` + 适当 `cin.tie(nullptr)`\n"
                    "5. **vector 越界** · `v.size()` 是 size_t, 与 int 比较会触发 warning"
                ),
            },
            {
                "title": "🧠 同类题推荐",
                "body": (
                    "做对本题后, 建议按以下顺序刷:\n"
                    "1. 同算法标签下, 难度 +0.5 的题 (巩固)\n"
                    "2. 同算法标签下, 难度 +1.5 的题 (拔高)\n"
                    "3. 洛谷「推荐练习」自动生成的同源变式题"
                ),
            },
        ],
    }
    _set_scene_progress(job_id, total, total)  # v3.11.31 · 收尾: 6/6
    _set_result(job_id, result)


def _run_via_aijiangti(job_id: str, job: AiTutorJob) -> None:
    """v3.11.31 · 真打 aijiangti.cn 的 /api/generate-classroom (StudyMate 错题讲解 API).

    上游契约 (StudyMate):
      POST {url} { requirement, pdfContent?, ... } → 202 { jobId, pollUrl, ... }
      GET  {pollUrl} → { status, step, progress, scenesGenerated, totalScenes, result, done, error }

    v3.11.31b · 关键修复:
      - 上游只识别 `requirement` 字符串, C++ 题目 (problem_id/title/source) 必须转写到 requirement 里
      - 学员中文 requirement 放在最前 (StudyMate upstream 用 requirement.substring(0, 60) 做日志 snippet, 所以中文要求放在前 60 字符内)
      - 附上洛谷 / Codeforces 题号 + 标题 + 源 URL + 语言 (cpp) + C++ 算法竞赛上下文
      - 上游 result 字段可能叫 scenes / outline / classroom / content, 做兼容适配
      - 处理 rate limit (RPM 限流) / network 错误, 给出友好提示
    """
    import urllib.request as _ur
    import urllib.error as _ue
    import json as _json
    import socket as _socket
    ctx = None
    try:
        import ssl as _ssl
        ctx = _ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = _ssl.CERT_NONE
    except Exception:
        pass

    _set_status(job_id, "running", step="forwarding", progress=10, message="🌐 正在把 C++ 题目转发给 AI 讲题服务 (aijiangti.cn)...")

    # v3.11.31b · 把 C++ 题目信息转写到 requirement 字符串
    # 上游 StudyMate upstream 用 rawBody.requirement?.substring(0, 60) 做日志, 中文要求放最前
    req_chinese = (job.requirement or "请用 C++ 代码实现并讲解").strip()[:60]
    pid = (job.problem_id or "").strip()
    title = (job.title or "").strip()
    source = (job.source or "").strip()
    language = (job.language or "cpp").strip()
    # StudyMate 错题讲解上游对 C++ 洛谷题上下文: 拼成清晰的"题面"格式让 LLM 知道是什么题
    # 注意 requirement 字符串别太长 (避免某些上游有 length cap), 题面正文不抓 (交给 LLM 自助)
    parts = [req_chinese]
    if pid:
        parts.append(f"题号: {pid}")
    if title:
        parts.append(f"题目标题: {title}")
    if source:
        parts.append(f"题面链接: {source}")
    parts.append(f"目标语言: {language} (信奥 / NOI-CSP 算法竞赛)")
    parts.append("请按以下 6 步讲题: 1) 题意速读 2) 暴力思路 3) 优化思路 4) 正解 (含 C++ 代码模板) 5) 易错点/边界 6) 同类题推荐")
    requirement_text = "\n".join(parts)

    payload = {
        "requirement": requirement_text,
        # StudyMate 上游习惯字段: language / problemId 透传, 上游不一定用, 但加上无副作用
        "language": language,
        "problemId": pid,
        "title": title,
        "source": source,
    }
    body_bytes = _json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def _do_request(method, url, data=None, timeout=30):
        req = _ur.Request(url, data=data, method=method, headers={
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "luoguAI-Vjudge/1.0 (ai-tutor-bridge)",
        })
        return _ur.urlopen(req, timeout=timeout, context=ctx)

    try:
        resp = _do_request("POST", AI_TUTOR_FORWARD_URL, data=body_bytes, timeout=30)
        raw = resp.read().decode("utf-8", "replace")
    except _ue.HTTPError as e:
        # 上游 4xx/5xx 错误, 读 body
        try:
            err_body = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            err_body = ""
        _set_error(job_id, f"AI 讲题服务返回 HTTP {e.code}: {err_body[:200]}")
        return
    except (_ue.URLError, _socket.timeout, _socket.error) as e:
        _set_error(job_id, f"连接 AI 讲题服务失败: {e}")
        return
    except Exception as e:
        _set_error(job_id, f"转发讲解服务异常: {type(e).__name__}: {e}")
        return

    # 解析 POST 响应
    try:
        upstream = _json.loads(raw)
        # v3.11.31b · StudyMate 用 success=true 包裹, 也兼容裸 jobId
        if isinstance(upstream, dict) and upstream.get("success") is False:
            _set_error(job_id, f"AI 讲题服务拒绝: {upstream.get('error') or upstream.get('message') or raw[:200]}")
            return
    except Exception:
        _set_error(job_id, f"AI 讲题服务响应非 JSON: {raw[:200]}")
        return

    remote_job_id = upstream.get("jobId") or upstream.get("job_id")
    poll_url = upstream.get("pollUrl") or upstream.get("poll_url")
    if not remote_job_id or not poll_url:
        _set_error(job_id, f"AI 讲题服务响应缺 jobId/pollUrl: {raw[:200]}")
        return
    log.info(f"[ai_tutor/forward] job={job_id} → remote={remote_job_id} pid={pid}")

    # 轮询 remote
    deadline = time.time() + 60 * 10  # 最长等 10 分钟
    last_progress = 10
    while time.time() < deadline:
        time.sleep(AI_TUTOR_POLL_INTERVAL_MS / 1000.0)
        try:
            resp = _do_request("GET", poll_url, timeout=20)
            raw_poll = resp.read().decode("utf-8", "replace")
        except Exception as e:
            log.warning(f"[ai_tutor/forward] poll error: {e}")
            continue
        try:
            data = _json.loads(raw_poll)
        except Exception:
            continue
        step = data.get("step") or data.get("status") or "running"
        progress = int(data.get("progress") or last_progress)
        message = data.get("message") or ""
        # v3.11.31 · 透传 StudyMate 契约: 分镜进度 scenesGenerated / totalScenes
        sg = data.get("scenesGenerated") or data.get("scenes_generated")
        ts = data.get("totalScenes") or data.get("total_scenes")
        if sg is not None or ts is not None:
            _set_scene_progress(job_id, int(sg or 0), int(ts or 0))
        if progress > last_progress:
            last_progress = progress
        _set_status(job_id, "running", step=step, progress=progress, message=message)
        if data.get("done") or data.get("status") in ("succeeded", "failed"):
            if data.get("status") == "failed" or data.get("error"):
                err_msg = str(data.get("error") or data.get("message") or "讲解失败")
                # v3.11.31b · 友好化上游错误
                if "rate limit" in err_msg.lower() or "rpm" in err_msg.lower():
                    err_msg = "AI 讲师讲太快了, 触发了上游 RPM 限流. 请稍等 1-2 分钟再来, 或换一道题试试"
                _set_error(job_id, err_msg)
            else:
                sg2 = data.get("scenesGenerated") or data.get("scenes_generated")
                ts2 = data.get("totalScenes") or data.get("total_scenes")
                if sg2 is not None or ts2 is not None:
                    _set_scene_progress(job_id, int(sg2 or 0), int(ts2 or 0))
                # v3.11.31b · result 字段兼容 (上游可能叫 classroom / outline / content)
                result = data.get("result") or {}
                if not result:
                    # 上游把 scenes 直接放在顶层 (StudyMate 早期版本)
                    if data.get("scenes"):
                        result = {"scenes": data.get("scenes"), "summary": data.get("summary") or ""}
                    elif data.get("outline"):
                        result = {"scenes": data.get("outline"), "summary": data.get("summary") or ""}
                    elif data.get("classroom"):
                        result = {"scenes": data.get("classroom"), "summary": data.get("summary") or ""}
                if not result and isinstance(data, dict):
                    # 上游有时候整个 data 就是 result
                    if any(k in data for k in ("scenes", "outline", "classroom", "content", "html", "markdown")):
                        result = {k: data[k] for k in ("scenes", "outline", "classroom", "content", "html", "markdown", "summary") if k in data}
                if not result:
                    result = {"scenes": [], "summary": data.get("message") or "讲解已完成, 但上游未返回结构化结果", "raw": data}
                # 把 C++ 题目信息钉到 result 头部 (前端展示)
                if isinstance(result, dict):
                    result["problem_id"] = pid
                    result["title"] = result.get("title") or title
                    result["source"] = result.get("source") or source
                    result["language"] = result.get("language") or language
                    result["backend"] = "aijiangti"
                _set_result(job_id, result)
            return
    _set_error(job_id, "讲解超时 (10 分钟内上游未完成)")


def _run_via_openai(job_id: str, job: AiTutorJob) -> None:
    """v3.11.31 · 走本项目 OPENAI_API_KEY 生成 C++ 讲题.
    复用 web_app.py 的 _call_openai / _openai_client, 这里用最简形式.
    """
    import requests as _r
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_ADMIN_KEY") or ""
    api_base = (os.environ.get("OPENAI_API_BASE") or "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
    if not api_key.strip():
        _set_error(job_id, "OPENAI_API_KEY 未配置, 无法走 openai 后端")
        return
    _set_status(job_id, "running", step="calling_llm", progress=20, message="🧠 正在调用大模型生成 C++ 讲题...")
    prompt = (
        f"你是洛谷 C++ 讲题老师, 学员要求: {job.requirement or '讲解这道题'}\n\n"
        f"题目: {job.title or job.problem_id}\n"
        f"题号: {job.problem_id or '—'}\n"
        f"来源: {job.source or '—'}\n"
        f"语言: {job.language or 'cpp'}\n\n"
        f"请用 JSON 格式返回: {{'summary': str, 'scenes': [{{'title': str, 'body': str}} x 5]}}\n"
        f"scenes 必须包含: 题意速读 / 暴力思路 / 优化思路 / 正解 / 易错点 / 同类题推荐 这 6 节.\n"
        f"body 中 C++ 代码用 ```cpp ... ``` 包裹."
    )
    try:
        resp = _r.post(
            f"{api_base}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "你是洛谷 C++ 讲题老师, 输出 JSON."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.4,
            },
            timeout=120,
        )
    except Exception as e:
        _set_error(job_id, f"调用大模型失败: {e}")
        return
    if resp.status_code != 200:
        _set_error(job_id, f"大模型返回 {resp.status_code}: {resp.text[:200]}")
        return
    try:
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        # 提取 JSON 块
        if "```json" in content:
            content = content.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in content:
            content = content.split("```", 1)[1].split("```", 1)[0]
        parsed = json.loads(content.strip())
    except Exception as e:
        _set_error(job_id, f"大模型返回解析失败: {e}")
        return
    _set_result(job_id, parsed)
