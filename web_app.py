import os
import json
import uuid
import threading
import time
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, send_from_directory

os.environ.setdefault("LUOGU_REPORT_AUTO_FONT_DOWNLOAD", "1")

# ========== 本地默认 API 配置（请在这里填写） ==========
DEFAULT_API_KEY = os.environ.get("OPENAI_API_KEY", "")                       # 例如: "sk-xxxxxxxx"
DEFAULT_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")                      # 例如: "https://api.openai.com/v1"
DEFAULT_MODEL_NAME = os.environ.get("OPENAI_MODEL_NAME", "gpt-4o-mini")              # 例如: "gpt-4o"
# ======================================================

import pyLuogu
from examples.export_for_ai import (
    DETAIL_FETCH_SAMPLE_LIMIT_FAILED,
    DETAIL_FETCH_SAMPLE_LIMIT_PASSED,
    _build_tag_maps,
    _summarize,
    _pick_record_for_problem,
)
from pyLuogu.errors import AuthenticationError, ForbiddenError, RequestError
from luogu_evaluator import (
    generate_ai_report,
    generate_chart_images,
    build_html_and_pdf,
    DEFAULT_REPORT_MD,
    DEFAULT_REPORT_HTML,
    DEFAULT_REPORT_PDF,
    DEFAULT_ASSETS_DIR,
    split_practice_problems,
    fetch_behavior_analysis,
    repair_behavior_analysis_from_items,
    summarize_detail_fetch_stats,
    enrich_problem_tags,
)
from behavior_analyzer import (
    compute_six_dimension_scores,
    format_behavior_summary,
)
from syllabus_matcher import (
    evaluate_all_topics,
    format_syllabus_report,
    get_weak_topics,
    get_strong_topics,
)
from task_store import (
    insert_task,
    update_task,
    get_task,
    list_tasks,
    get_stats,
)

app = Flask(__name__)

# 任务状态锁（数据库操作线程安全）
TASKS_LOCK = threading.Lock()


def describe_generation_error(exc: Exception, stage: str) -> str:
    stage_prefix = f"[阶段: {stage}] "
    if isinstance(exc, ValueError):
        return stage_prefix + str(exc)
    if isinstance(exc, AuthenticationError):
        if stage == "预检提交记录权限" or stage == "抓取提交记录与代码":
            return stage_prefix + "Cookies 无效或已失效，无法读取提交记录，请重新获取同一会话下的 __client_id、_uid 和 C3VK。"
        if stage == "预检做题记录权限" or stage == "获取标签与练习数据":
            return stage_prefix + "Cookies 无效或已失效，无法读取练习数据，请重新获取 __client_id、_uid 和 C3VK。"
        if stage == "获取标签与练习数据":
            return stage_prefix + "Cookies 无效或已失效，无法读取练习数据，请重新获取 __client_id、_uid 和 C3VK。"
        return stage_prefix + "Cookies 无效或已失效，请重新登录洛谷并更新 Cookies。"
    if isinstance(exc, ForbiddenError):
        return stage_prefix + f"访问被拒绝：{exc}"
    if isinstance(exc, RequestError):
        return stage_prefix + str(exc)
    return stage_prefix + str(exc)

INDEX_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>洛谷 AI 测评报告生成器</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .app-body{background:#f3f4f6;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:16px;font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,"Noto Sans","PingFang SC","Microsoft YaHei",sans-serif;}
        .app-card{background:#fff;border-radius:16px;box-shadow:0 10px 25px rgba(0,0,0,.08);padding:32px;width:100%;max-width:560px;}
        .app-title{font-size:24px;font-weight:800;color:#1e3a8a;margin:0 0 6px;}
        .app-subtitle{color:#6b7280;margin:0 0 10px;font-size:14px;}
        .app-muted{color:#9ca3af;font-size:12px;margin:0 0 18px;}
        .app-box{border-radius:10px;padding:12px 12px;border:1px solid #e5e7eb;}
        .app-box-yellow{background:#fffbeb;border-color:#fde68a;color:#92400e;}
        .app-box-blue{background:#eff6ff;border-color:#bfdbfe;color:#1d4ed8;}
        .app-box-green{background:#ecfdf5;border-color:#a7f3d0;color:#065f46;}
        .app-box-red{background:#fef2f2;border-color:#fecaca;color:#991b1b;}
        .app-label{display:block;font-size:13px;font-weight:700;color:#374151;}
        .app-input{margin-top:6px;display:block;width:100%;border-radius:10px;border:1px solid #d1d5db;padding:10px 12px;box-shadow:0 1px 2px rgba(0,0,0,.04);}
        .app-input:focus{outline:none;border-color:#3b82f6;box-shadow:0 0 0 3px rgba(59,130,246,.2);}
        .app-btn{display:inline-flex;align-items:center;justify-content:center;width:100%;border-radius:10px;padding:10px 14px;font-weight:800;transition:all .15s ease;}
        .app-btn-primary{background:#2563eb;color:#fff;}
        .app-btn-primary:hover{background:#1d4ed8;}
        .app-btn-secondary{background:#fff;color:#1d4ed8;border:1px solid #93c5fd;}
        .app-btn-secondary:hover{background:#eff6ff;}
        .app-btn:disabled{opacity:.5;cursor:not-allowed;}
        .app-row{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
        .app-space{margin-bottom:14px;}
        .app-small{font-size:12px;opacity:.9;}
    </style>
</head>
<body class="app-body bg-gray-100 min-h-screen flex items-center justify-center p-4">
    <div class="app-card bg-white rounded-xl shadow-lg p-8 w-full max-w-lg">
        <h1 class="app-title text-2xl font-bold text-blue-900 mb-2">洛谷 AI 测评报告生成器</h1>
        <p class="app-subtitle text-gray-500 mb-2">输入洛谷 Cookies 与 OpenAI 配置，在线生成测评报告</p>
        <div class="app-muted text-xs text-gray-400 mb-6 flex items-center justify-between gap-2">
            <div>
                QQ交流群：<span id="qqGroup" class="text-blue-700 font-semibold select-all">610931699</span>
                <span class="text-gray-400">（复制即可）</span>
            </div>
            <button id="copyQqBtn" type="button" class="px-3 py-1 rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50">复制</button>
        </div>
        {% if validation_result %}
        <div class="app-box rounded-md p-3 mb-4 text-sm {% if validation_result.ok %}app-box-green bg-green-50 border border-green-200 text-green-800{% else %}app-box-red bg-red-50 border border-red-200 text-red-800{% endif %}">
            <p class="font-semibold mb-1">{{ validation_result.title }}</p>
            <p>{{ validation_result.message }}</p>
        </div>
        {% endif %}
        <div class="app-box app-box-yellow bg-yellow-50 border border-yellow-200 rounded-md p-3 mb-4 text-sm text-yellow-800">
            <p class="font-semibold mb-1">如何获取洛谷 Cookies：</p>
            <ol class="list-decimal list-inside space-y-1 text-xs text-yellow-700">
                <li>打开 <code>https://www.luogu.com.cn</code> 并登录</li>
                <li>按 <kbd class="px-1 bg-yellow-100 rounded">F12</kbd> → <kbd class="px-1 bg-yellow-100 rounded">Application(应用)</kbd> → <kbd class="px-1 bg-yellow-100 rounded">Storage → Cookies</kbd> → <code>https://www.luogu.com.cn</code></li>
                <li>复制以下三个参数的 Name/Value 填入下方：</li>
            </ol>
        </div>
        <form action="/generate" method="post" class="space-y-4">
            <div>
                <label class="app-label block text-sm font-medium text-gray-700">__client_id</label>
                <input type="text" name="client_id" value="{{ form_values.client_id }}" required class="app-input mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2">
            </div>
            <div>
                <label class="app-label block text-sm font-medium text-gray-700">_uid</label>
                <input type="text" name="uid" value="{{ form_values.uid }}" required class="app-input mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2">
            </div>
            <div>
                <label class="app-label block text-sm font-medium text-gray-700">C3VK</label>
                <input type="text" name="c3vk" value="{{ form_values.c3vk }}" required class="app-input mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2">
            </div>
            <div class="app-box app-box-blue bg-blue-50 border border-blue-200 rounded-md p-3">
                <div class="flex items-start justify-between gap-3">
                    <div>
                        <p class="font-semibold mb-1">先校验 Cookies（推荐）</p>
                        <p class="text-xs text-blue-700">填写完上面三个参数后点一次，立刻检查 me / practice / record/list 是否可用。</p>
                    </div>
                </div>
                <div class="mt-3">
                    <button id="validateBtn" type="submit" formaction="/validate-cookies" class="app-btn app-btn-secondary w-full bg-white text-blue-700 font-semibold py-2 px-4 rounded-md border border-blue-300 hover:bg-blue-50 transition">校验 Cookies</button>
                </div>
                <p id="validateHint" class="app-small text-xs text-blue-700 mt-2">请先填写 __client_id、_uid、C3VK 后再校验。</p>
            </div>
            <div>
                <label class="app-label block text-sm font-medium text-gray-700">OpenAI API Key（留空使用服务端默认）</label>
                <input type="password" name="api_key" class="app-input mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2">
            </div>
            <div>
                <label class="app-label block text-sm font-medium text-gray-700">API Base URL（留空使用服务端默认）</label>
                <input type="text" name="base_url" value="{{ form_values.base_url }}" class="app-input mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2">
            </div>
            <div>
                <label class="app-label block text-sm font-medium text-gray-700">模型名称（留空使用服务端默认）</label>
                <input type="text" name="model_name" value="{{ form_values.model_name }}" class="app-input mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2">
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="app-label block text-sm font-medium text-gray-700">姓名</label>
                    <input type="text" name="student_name" value="{{ form_values.student_name }}" class="app-input mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2">
                </div>
                <div>
                    <label class="app-label block text-sm font-medium text-gray-700">学校</label>
                    <input type="text" name="school" value="{{ form_values.school }}" class="app-input mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2">
                </div>
            </div>
            <div>
                <label class="app-label block text-sm font-medium text-gray-700">年级</label>
                <input type="text" name="grade" value="{{ form_values.grade }}" class="app-input mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2">
            </div>
            <input type="hidden" name="max_passed" value="{{ form_values.max_passed }}">
            <input type="hidden" name="max_failed" value="{{ form_values.max_failed }}">
            <button id="generateBtn" type="submit" class="app-btn app-btn-primary w-full bg-blue-600 text-white font-semibold py-2 px-4 rounded-md hover:bg-blue-700 transition">生成报告</button>
        </form>
    </div>
    <script>
        (function () {
            function v(id) { var el = document.querySelector('input[name="' + id + '"]'); return el ? (el.value || '').trim() : ''; }
            var btn = document.getElementById('validateBtn');
            var hint = document.getElementById('validateHint');
            function refresh() {
                var ok = !!v('client_id') && !!v('uid') && !!v('c3vk');
                if (btn) btn.disabled = !ok;
                if (hint) hint.textContent = ok ? '已填写三个参数，建议先点一次校验。' : '请先填写 __client_id、_uid、C3VK 后再校验。';
            }
            ['client_id','uid','c3vk'].forEach(function (name) {
                var el = document.querySelector('input[name="' + name + '"]');
                if (el) el.addEventListener('input', refresh);
            });
            refresh();
        })();
        (function () {
            var btn = document.getElementById('copyQqBtn');
            var textEl = document.getElementById('qqGroup');
            if (!btn || !textEl) return;
            btn.addEventListener('click', async function () {
                var value = (textEl.textContent || '').trim();
                try {
                    if (navigator.clipboard && navigator.clipboard.writeText) {
                        await navigator.clipboard.writeText(value);
                    } else {
                        var ta = document.createElement('textarea');
                        ta.value = value;
                        ta.style.position = 'fixed';
                        ta.style.top = '-1000px';
                        document.body.appendChild(ta);
                        ta.focus();
                        ta.select();
                        document.execCommand('copy');
                        document.body.removeChild(ta);
                    }
                    btn.textContent = '已复制';
                    setTimeout(function () { btn.textContent = '复制'; }, 1200);
                } catch (e) {
                    btn.textContent = '复制失败';
                    setTimeout(function () { btn.textContent = '复制'; }, 1200);
                }
            });
        })();
    </script>
</body>
</html>
"""


def build_cookie_dict(form: dict) -> dict[str, str]:
    client_id = str(form.get("client_id", "")).strip()
    uid = str(form.get("uid", "")).strip()
    c3vk = str(form.get("c3vk", "")).strip()
    missing = []
    if not client_id:
        missing.append("__client_id")
    if not uid:
        missing.append("_uid")
    if not c3vk:
        missing.append("C3VK")
    if missing:
        raise ValueError(f"Cookies 参数为必填项，请完整填写：{', '.join(missing)}")
    return {
        "__client_id": client_id,
        "_uid": uid,
        "C3VK": c3vk,
    }


def build_form_values(form: dict | None = None) -> dict[str, str]:
    src = form or {}
    return {
        "client_id": str(src.get("client_id", "")),
        "uid": str(src.get("uid", "")),
        "c3vk": str(src.get("c3vk", "")),
        "base_url": str(src.get("base_url", "")),
        "model_name": str(src.get("model_name", "")),
        "student_name": str(src.get("student_name", "未知选手")),
        "school": str(src.get("school", "未知学校")),
        "grade": str(src.get("grade", "未知年级")),
        "max_passed": str(src.get("max_passed", "5000")),
        "max_failed": str(src.get("max_failed", "1000")),
    }


def render_index(form: dict | None = None, validation_result: dict | None = None):
    return render_template_string(
        INDEX_HTML,
        form_values=build_form_values(form),
        validation_result=validation_result,
    )


def validate_cookies(form: dict) -> dict[str, object]:
    current_stage = "构造 Cookies"
    luogu = None
    try:
        cookies = pyLuogu.LuoguCookies(build_cookie_dict(form))
        current_stage = "预检用户信息"
        luogu = pyLuogu.luoguAPI(cookies=cookies)
        me = luogu.me()
        uid = int(me.uid)

        current_stage = "预检做题记录权限"
        practice = luogu.get_user_practice(uid)
        solved, failed = split_practice_problems(practice)

        current_stage = "预检提交记录权限"
        record_list = luogu.get_record_list(page=1, uid=uid, user=str(uid))
        record_count = len(getattr(record_list, "records", []) or [])
        return {
            "ok": True,
            "title": "Cookies 校验通过",
            "message": (
                f"已通过 me()、practice 和 record/list 预检。"
                f"用户 ID: {uid}，已通过 {len(solved)} 题，未通过 {len(failed)} 题，"
                f"最近一页提交记录 {record_count} 条。"
            ),
        }
    except Exception as exc:
        return {
            "ok": False,
            "title": "Cookies 校验失败",
            "message": describe_generation_error(exc, current_stage),
        }
    finally:
        if luogu is not None:
            luogu.close()


def run_generation(task_id: str, form: dict):
    current_stage = "初始化"
    try:
        with TASKS_LOCK:
            update_task(task_id, status="running", message="正在连接洛谷 API...")

        current_stage = "构造 Cookies"
        cookies = pyLuogu.LuoguCookies(build_cookie_dict(form))

        api_key = form.get("api_key", "").strip() or DEFAULT_API_KEY or os.environ.get("OPENAI_API_KEY", "")
        base_url = form.get("base_url", "").strip() or DEFAULT_BASE_URL or os.environ.get("OPENAI_BASE_URL", "") or None
        model_name = form.get("model_name", "").strip() or DEFAULT_MODEL_NAME or os.environ.get("OPENAI_MODEL_NAME", "") or "gpt-4o"
        max_passed = int(form.get("max_passed", 10))
        max_failed = int(form.get("max_failed", 5))
        student_name = form.get("student_name", "未知选手").strip()
        school = form.get("school", "未知学校").strip()
        grade = form.get("grade", "未知年级").strip()

        # 文件夹命名：编号+学生姓名
        safe_name = "".join(c for c in student_name if c.isalnum() or c in "_-").strip() or "unknown"
        folder_name = f"{task_id[:8]}_{safe_name}"
        out_dir = Path("reports") / folder_name
        out_dir.mkdir(parents=True, exist_ok=True)
        assets_dir = out_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        md_path = out_dir / "report.md"
        html_path = out_dir / "report.html"
        pdf_path = out_dir / "report.pdf"

        current_stage = "连接洛谷 API / me()"
        luogu = pyLuogu.luoguAPI(cookies=cookies)
        me = luogu.me()
        uid = int(me.uid)

        with TASKS_LOCK:
            update_task(task_id, message=f"已连接，用户 ID: {uid}，正在拉取做题记录...")

        current_stage = "获取标签与练习数据"
        tag_by_id, type_by_id = _build_tag_maps(luogu)
        practice = luogu.get_user_practice(uid)

        current_stage = "预检提交记录权限"
        luogu.get_record_list(page=1, uid=uid, user=str(uid))

        all_passed, all_failed = split_practice_problems(practice)
        with TASKS_LOCK:
            update_task(task_id, message="正在补全题目标签数据...")
        current_stage = "补全题目标签"
        enrich_problem_tags(luogu, all_passed)

        all_passed.sort(key=lambda p: (p.difficulty if p.difficulty is not None else 10, p.pid), reverse=True)
        all_failed.sort(key=lambda p: (p.difficulty if p.difficulty is not None else 10, p.pid), reverse=True)
        passed_problems = all_passed[:max_passed]
        failed_problems = all_failed[:max_failed]

        with TASKS_LOCK:
            update_task(task_id, message="正在拉取提交记录与代码...")

        current_stage = "抓取提交记录与代码"
        source_code_total = int(len(passed_problems) + len(failed_problems))
        source_code_success = 0
        processed = 0
        last_progress_update = 0.0

        def _is_source_code_present(record_obj: object) -> bool:
            if isinstance(record_obj, dict):
                code = record_obj.get("sourceCode")
                return bool(code)
            return False

        def _maybe_update_progress(force: bool = False) -> None:
            nonlocal last_progress_update
            now = time.time()
            if (not force) and (now - last_progress_update) < 2.0 and (processed % 10 != 0):
                return
            last_progress_update = now
            msg = (
                f"正在拉取提交记录与代码（源码优先，速度较慢）... "
                f"已获取源码 {source_code_success}/{source_code_total}，进度 {processed}/{source_code_total}"
            )
            with TASKS_LOCK:
                update_task(
                    task_id,
                    message=msg,
                    stage=current_stage,
                    source_code_success=source_code_success,
                    source_code_total=source_code_total,
                )

        detail_fetch_state: dict[str, object] = {}
        passed_items = []
        with TASKS_LOCK:
            update_task(
                task_id,
                message="正在拉取提交记录与代码（源码优先，速度较慢）...",
                stage=current_stage,
                source_code_success=0,
                source_code_total=source_code_total,
            )
        for idx, problem in enumerate(passed_problems):
            try:
                record = _pick_record_for_problem(
                    luogu=luogu,
                    uid=uid,
                    pid=problem.pid,
                    max_records_to_try=5,
                    require_source_code=True,
                    detail_fetch_state=detail_fetch_state,
                )
            except Exception as e:
                record = {"error": str(e)}
            passed_items.append({"problem": problem.to_json(), "record": record})
            processed += 1
            if _is_source_code_present(record):
                source_code_success += 1
            _maybe_update_progress()

        failed_items = []
        for idx, problem in enumerate(failed_problems):
            try:
                record = _pick_record_for_problem(
                    luogu=luogu,
                    uid=uid,
                    pid=problem.pid,
                    max_records_to_try=5,
                    require_source_code=True,
                    detail_fetch_state=detail_fetch_state,
                )
            except Exception as e:
                record = {"error": str(e)}
            failed_items.append({"problem": problem.to_json(), "record": record})
            processed += 1
            if _is_source_code_present(record):
                source_code_success += 1
            _maybe_update_progress()

        _maybe_update_progress(force=True)
        detail_fetch_stats = summarize_detail_fetch_stats(passed_items, failed_items, detail_fetch_state)
        total_items = int(detail_fetch_stats.get("total_items") or 0)
        source_code_success = int(detail_fetch_stats.get("source_code_success") or 0)
        if total_items > 0 and source_code_success < total_items:
            raise RuntimeError(
                f"源码抓取未完成：成功 {source_code_success}/{total_items}。"
                f"已放慢抓取速度并提高重试，仍有缺失。"
                f"请重新获取同一会话下的 __client_id、_uid、C3VK 后重试；"
                f"必要时降低题量（max_passed/max_failed）以提高稳定性。"
            )

        summary = _summarize(all_passed, tag_by_id=tag_by_id)

        # ========== 新增：提交行为深度分析 ==========
        with TASKS_LOCK:
            update_task(task_id, message="正在进行提交行为深度分析...")

        current_stage = "提交行为分析"
        behavior_data = fetch_behavior_analysis(luogu, uid, passed_items + failed_items)
        behavior_data = repair_behavior_analysis_from_items(
            {
                "passed_items": passed_items,
                "failed_items": failed_items,
                "behavior_analysis": behavior_data,
            }
        )
        detail_fetch_stats = summarize_detail_fetch_stats(passed_items, failed_items, detail_fetch_state)

        # ========== 新增：大纲知识点对标 ==========
        with TASKS_LOCK:
            update_task(task_id, message="正在进行大纲知识点对标分析...")

        current_stage = "大纲知识点对标"
        syllabus_evaluation = evaluate_all_topics(summary.get("top_algorithm_tags", []) or summary.get("top_tags", []))
        six_dim_scores = compute_six_dimension_scores(
            {"solved_count": len(all_passed), "summary": summary},
            behavior_data if "error" not in behavior_data else {}
        )

        export_data = {
            "student_info": {
                "name": student_name,
                "school": school,
                "grade": grade,
                "eval_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            },
            "solved_count": len(all_passed),
            "failed_count": len(all_failed),
            "summary": summary,
            "passed_items": passed_items,
            "failed_items": failed_items,
            "detail_fetch_stats": detail_fetch_stats,
            "behavior_analysis": behavior_data,
            "syllabus_evaluation": syllabus_evaluation,
            "six_dimension_scores": six_dim_scores,
        }

        # 保存 export_data.json 供后台管理页面读取
        export_json_path = out_dir / "export_data.json"
        with open(export_json_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        with TASKS_LOCK:
            update_task(task_id, message=f"正在调用 {model_name} 生成 AI 报告，请耐心等待...")

        current_stage = "生成 AI 报告"
        report_md = generate_ai_report(export_data, api_key, base_url, model_name)

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(report_md)

        current_stage = "生成图表与 HTML/PDF"
        chart_paths = generate_chart_images(export_data, str(assets_dir))
        build_html_and_pdf(report_md, export_data, str(html_path), str(pdf_path), chart_paths)

        eval_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        with TASKS_LOCK:
            update_task(
                task_id,
                status="done",
                message="报告生成完成",
                html=f"/reports/{folder_name}/report.html",
                pdf=f"/reports/{folder_name}/report.pdf",
                md=f"/reports/{folder_name}/report.md",
                student_name=student_name,
                school=school,
                grade=grade,
                solved_count=len(all_passed),
                failed_count=len(all_failed),
                eval_time=eval_time,
            )
    except Exception as e:
        with TASKS_LOCK:
            update_task(task_id, status="error", message=describe_generation_error(e, current_stage))


@app.route("/")
def index():
    return render_index()


@app.route("/validate-cookies", methods=["POST"])
def validate_cookies_page():
    form = request.form.to_dict()
    return render_index(form=form, validation_result=validate_cookies(form))


@app.route("/generate", methods=["POST"])
def generate():
    task_id = str(uuid.uuid4())
    with TASKS_LOCK:
        insert_task(task_id, status="queued", message="排队中...")
    thread = threading.Thread(target=run_generation, args=(task_id, request.form.to_dict()))
    thread.start()
    return redirect(url_for("status_page", task_id=task_id))


STATUS_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>报告生成状态</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <meta http-equiv="refresh" content="3">
</head>
<body class="bg-gray-100 min-h-screen flex items-center justify-center p-4">
    <div class="bg-white rounded-xl shadow-lg p-8 w-full max-w-lg text-center">
        <h1 class="text-2xl font-bold text-blue-900 mb-4">报告生成状态</h1>
        <div class="mb-4">
            <span class="inline-block px-3 py-1 rounded-full text-sm font-semibold
                {% if status == 'done' %}bg-green-100 text-green-800{% elif status == 'error' %}bg-red-100 text-red-800{% else %}bg-blue-100 text-blue-800{% endif %}">
                {{ status }}
            </span>
        </div>
        {% if source_code_total and source_code_total|int > 0 %}
        <div class="mb-4 text-left">
            <div class="flex items-center justify-between text-sm text-gray-600 mb-1">
                <span>源码获取进度</span>
                <span class="font-semibold text-gray-800">{{ source_code_success }}/{{ source_code_total }}</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                <div class="bg-blue-600 h-3" style="width: {{ (100 * (source_code_success|int) / (source_code_total|int)) if (source_code_total|int) > 0 else 0 }}%;"></div>
            </div>
        </div>
        {% endif %}
        <p class="text-gray-700 mb-6">{{ message }}</p>
        {% if status == 'done' %}
        <div class="space-y-3">
            <a href="{{ html }}" target="_blank" class="block w-full bg-blue-600 text-white font-semibold py-2 px-4 rounded-md hover:bg-blue-700 transition">查看 HTML 报告</a>
            <a href="{{ pdf }}" target="_blank" class="block w-full bg-gray-700 text-white font-semibold py-2 px-4 rounded-md hover:bg-gray-800 transition">下载 PDF 报告</a>
            <a href="{{ md }}" target="_blank" class="block w-full bg-gray-200 text-gray-800 font-semibold py-2 px-4 rounded-md hover:bg-gray-300 transition">查看 Markdown 原文</a>
        </div>
        {% elif status == 'error' %}
        <a href="/" class="block w-full bg-blue-600 text-white font-semibold py-2 px-4 rounded-md hover:bg-blue-700 transition mt-4">返回重试</a>
        {% else %}
        <p class="text-sm text-gray-400">页面每 3 秒自动刷新...</p>
        {% endif %}
    </div>
</body>
</html>
"""


@app.route("/status/<task_id>")
def status_page(task_id):
    task = get_task(task_id) or {"status": "unknown", "message": "任务不存在"}
    return render_template_string(
        STATUS_HTML,
        status=task.get("status", "unknown"),
        message=task.get("message", ""),
        source_code_success=int(task.get("source_code_success", 0) or 0),
        source_code_total=int(task.get("source_code_total", 0) or 0),
        html=task.get("html", ""),
        pdf=task.get("pdf", ""),
        md=task.get("md", ""),
    )


@app.route("/reports/<path:filename>")
def serve_report(filename):
    return send_from_directory("reports", filename)


# ========== 后台管理页面 ==========
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>后台管理 - 洛谷 AI 测评报告</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <meta http-equiv="refresh" content="10">
</head>
<body class="bg-gray-100 min-h-screen p-6">
    <div class="max-w-6xl mx-auto">
        <div class="flex items-center justify-between mb-6">
            <h1 class="text-3xl font-bold text-blue-900">后台管理</h1>
            <a href="/" class="text-blue-600 hover:underline">返回首页</a>
        </div>

        <!-- 统计卡片 -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div class="bg-white rounded-xl shadow p-4">
                <p class="text-sm text-gray-500">总生成次数</p>
                <p class="text-2xl font-bold text-blue-700">{{ total_tasks }}</p>
            </div>
            <div class="bg-white rounded-xl shadow p-4">
                <p class="text-sm text-gray-500">今日生成</p>
                <p class="text-2xl font-bold text-green-700">{{ today_tasks }}</p>
            </div>
            <div class="bg-white rounded-xl shadow p-4">
                <p class="text-sm text-gray-500">进行中</p>
                <p class="text-2xl font-bold text-yellow-600">{{ running_tasks }}</p>
            </div>
            <div class="bg-white rounded-xl shadow p-4">
                <p class="text-sm text-gray-500">失败次数</p>
                <p class="text-2xl font-bold text-red-600">{{ error_tasks }}</p>
            </div>
        </div>

        <!-- 历史任务列表 -->
        <div class="bg-white rounded-xl shadow overflow-hidden">
            <div class="px-6 py-4 border-b border-gray-200">
                <h2 class="text-lg font-semibold text-gray-800">历史任务列表</h2>
            </div>
            <div class="overflow-x-auto">
                <table class="min-w-full text-sm text-left">
                    <thead class="bg-gray-50 text-gray-600 font-medium">
                        <tr>
                            <th class="px-6 py-3">任务 ID</th>
                            <th class="px-6 py-3">姓名</th>
                            <th class="px-6 py-3">学校</th>
                            <th class="px-6 py-3">年级</th>
                            <th class="px-6 py-3">通过题数</th>
                            <th class="px-6 py-3">失败题数</th>
                            <th class="px-6 py-3">状态</th>
                            <th class="px-6 py-3">时间</th>
                            <th class="px-6 py-3">操作</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        {% for task in tasks %}
                        <tr class="hover:bg-gray-50">
                            <td class="px-6 py-3 font-mono text-xs text-gray-500">{{ task.id[:8] }}...</td>
                            <td class="px-6 py-3 font-medium text-gray-900">{{ task.name }}</td>
                            <td class="px-6 py-3 text-gray-600">{{ task.school }}</td>
                            <td class="px-6 py-3 text-gray-600">{{ task.grade }}</td>
                            <td class="px-6 py-3 text-green-700 font-semibold">{{ task.solved }}</td>
                            <td class="px-6 py-3 text-red-600 font-semibold">{{ task.failed }}</td>
                            <td class="px-6 py-3">
                                {% if task.status == 'done' %}
                                    <span class="px-2 py-1 rounded-full text-xs bg-green-100 text-green-800">完成</span>
                                {% elif task.status == 'error' %}
                                    <span class="px-2 py-1 rounded-full text-xs bg-red-100 text-red-800">失败</span>
                                {% elif task.status == 'running' %}
                                    <span class="px-2 py-1 rounded-full text-xs bg-yellow-100 text-yellow-800">进行中</span>
                                {% else %}
                                    <span class="px-2 py-1 rounded-full text-xs bg-gray-100 text-gray-800">{{ task.status }}</span>
                                {% endif %}
                            </td>
                            <td class="px-6 py-3 text-gray-500 text-xs">{{ task.time }}</td>
                            <td class="px-6 py-3 space-x-2">
                                {% if task.html %}
                                <a href="{{ task.html }}" target="_blank" class="text-blue-600 hover:underline text-xs">HTML</a>
                                {% endif %}
                                {% if task.pdf %}
                                <a href="{{ task.pdf }}" target="_blank" class="text-blue-600 hover:underline text-xs">PDF</a>
                                {% endif %}
                                {% if task.md %}
                                <a href="{{ task.md }}" target="_blank" class="text-blue-600 hover:underline text-xs">MD</a>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
"""


@app.route("/admin")
def admin_page():
    stats = get_stats()
    db_tasks = list_tasks()

    task_list = []
    for row in db_tasks:
        task_list.append({
            "id": row.get("task_id", ""),
            "name": row.get("student_name", "未知"),
            "school": row.get("school", "未知"),
            "grade": row.get("grade", "未知"),
            "solved": row.get("solved_count", "-"),
            "failed": row.get("failed_count", "-"),
            "status": row.get("status", "unknown"),
            "time": row.get("eval_time") or row.get("created_at", "-"),
            "html": row.get("html", ""),
            "pdf": row.get("pdf", ""),
            "md": row.get("md", ""),
        })

    return render_template_string(
        ADMIN_HTML,
        total_tasks=stats["total"],
        today_tasks=stats["today"],
        running_tasks=stats["running"],
        error_tasks=stats["error"],
        tasks=task_list,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
