import os
import json
import uuid
import threading
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, send_from_directory

# ========== 本地默认 API 配置（请在这里填写） ==========
DEFAULT_API_KEY = "sk-e00a5f2b299d599e65668a9b9008e3913ff577e1f8fc0bc1a050157279d27079"                       # 例如: "sk-xxxxxxxx"
DEFAULT_BASE_URL = "https://api.qnaigc.com/v1"                      # 例如: "https://api.openai.com/v1"
DEFAULT_MODEL_NAME = "deepseek/deepseek-v4-pro"              # 例如: "gpt-4o"
# ======================================================

import pyLuogu
from examples.export_for_ai import _build_tag_maps, _summarize, _pick_record_for_problem
from luogu_evaluator import (
    generate_ai_report,
    generate_chart_images,
    build_html_and_pdf,
    DEFAULT_REPORT_MD,
    DEFAULT_REPORT_HTML,
    DEFAULT_REPORT_PDF,
    DEFAULT_ASSETS_DIR,
)
from behavior_analyzer import (
    analyze_submission_behavior,
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

INDEX_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>洛谷 AI 测评报告生成器</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 min-h-screen flex items-center justify-center p-4">
    <div class="bg-white rounded-xl shadow-lg p-8 w-full max-w-lg">
        <h1 class="text-2xl font-bold text-blue-900 mb-2">洛谷 AI 测评报告生成器</h1>
        <p class="text-gray-500 mb-2">输入洛谷 Cookies 与 OpenAI 配置，在线生成测评报告</p>
        <p class="text-xs text-gray-400 mb-6">QQ交流群：<a href="https://qm.qq.com/q/610931699" target="_blank" class="text-blue-600 hover:underline">610931699</a></p>
        <div class="bg-yellow-50 border border-yellow-200 rounded-md p-3 mb-4 text-sm text-yellow-800">
            <p class="font-semibold mb-1">如何获取洛谷 Cookies：</p>
            <ol class="list-decimal list-inside space-y-1 text-xs text-yellow-700">
                <li>打开 <code>https://www.luogu.com.cn</code> 并登录</li>
                <li>按 <kbd class="px-1 bg-yellow-100 rounded">F12</kbd> → <kbd class="px-1 bg-yellow-100 rounded">Application(应用)</kbd> → <kbd class="px-1 bg-yellow-100 rounded">Storage → Cookies</kbd> → <code>https://www.luogu.com.cn</code></li>
                <li>复制以下三个参数的 Name/Value 填入下方：</li>
            </ol>
        </div>
        <form action="/generate" method="post" class="space-y-4">
            <div>
                <label class="block text-sm font-medium text-gray-700">__client_id</label>
                <input type="text" name="client_id" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700">_uid</label>
                <input type="text" name="uid" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700">C3VK（如有）</label>
                <input type="text" name="c3vk" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700">OpenAI API Key（留空使用服务端默认）</label>
                <input type="password" name="api_key" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700">API Base URL（留空使用服务端默认）</label>
                <input type="text" name="base_url" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2">
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700">模型名称（留空使用服务端默认）</label>
                <input type="text" name="model_name" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2">
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700">姓名</label>
                    <input type="text" name="student_name" value="未知选手" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2">
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700">学校</label>
                    <input type="text" name="school" value="未知学校" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2">
                </div>
            </div>
            <div>
                <label class="block text-sm font-medium text-gray-700">年级</label>
                <input type="text" name="grade" value="未知年级" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2">
            </div>
            <input type="hidden" name="max_passed" value="5000">
            <input type="hidden" name="max_failed" value="1000">
            <button type="submit" class="w-full bg-blue-600 text-white font-semibold py-2 px-4 rounded-md hover:bg-blue-700 transition">生成报告</button>
        </form>
    </div>
</body>
</html>
"""


def run_generation(task_id: str, form: dict):
    try:
        with TASKS_LOCK:
            update_task(task_id, status="running", message="正在连接洛谷 API...")

        cookie_dict = {
            "__client_id": form["client_id"].strip(),
            "_uid": form["uid"].strip(),
        }
        c3vk = form.get("c3vk", "").strip()
        if c3vk:
            cookie_dict["C3VK"] = c3vk
        cookies = pyLuogu.LuoguCookies(cookie_dict)

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

        luogu = pyLuogu.luoguAPI(cookies=cookies)
        me = luogu.me()
        uid = int(me.uid)

        with TASKS_LOCK:
            update_task(task_id, message=f"已连接，用户 ID: {uid}，正在拉取做题记录...")

        tag_by_id, type_by_id = _build_tag_maps(luogu)
        practice = luogu.get_user_practice(uid)

        all_passed = []
        if isinstance(practice.data, dict):
            items = practice.data.get("passed")
            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    pid = item.get("pid")
                    if pid:
                        all_passed.append(pyLuogu.ProblemSummary({
                            "pid": str(pid),
                            "title": item.get("title") or item.get("name") or "",
                            "difficulty": item.get("difficulty"),
                            "type": item.get("type"),
                        }))

        all_failed = []
        if isinstance(practice.data, dict):
            items = practice.data.get("failed")
            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    pid = item.get("pid")
                    if pid:
                        all_failed.append(pyLuogu.ProblemSummary({
                            "pid": str(pid),
                            "title": item.get("title") or item.get("name") or "",
                            "difficulty": item.get("difficulty"),
                            "type": item.get("type"),
                        }))

        all_passed.sort(key=lambda p: (p.difficulty if p.difficulty is not None else 10, p.pid), reverse=True)
        all_failed.sort(key=lambda p: (p.difficulty if p.difficulty is not None else 10, p.pid), reverse=True)
        passed_problems = all_passed[:max_passed]
        failed_problems = all_failed[:max_failed]

        with TASKS_LOCK:
            update_task(task_id, message="正在拉取提交记录与代码...")

        passed_items = []
        for problem in passed_problems:
            try:
                record = _pick_record_for_problem(luogu=luogu, uid=uid, pid=problem.pid, max_records_to_try=2)
            except Exception as e:
                record = {"error": str(e)}
            passed_items.append({"problem": problem.to_json(), "record": record})

        failed_items = []
        for problem in failed_problems:
            try:
                record = _pick_record_for_problem(luogu=luogu, uid=uid, pid=problem.pid, max_records_to_try=2)
            except Exception as e:
                record = {"error": str(e)}
            failed_items.append({"problem": problem.to_json(), "record": record})

        summary = _summarize(all_passed + all_failed, tag_by_id=tag_by_id)

        # ========== 新增：提交行为深度分析 ==========
        with TASKS_LOCK:
            update_task(task_id, message="正在进行提交行为深度分析...")

        behavior_data = {"error": "未获取提交记录"}
        try:
            # 获取最近 500 条提交记录用于行为分析
            record_list = luogu.get_record_list(page=1, uid=uid, user=str(uid))
            raw_records = []
            if hasattr(record_list, 'records') and record_list.records:
                for rec in record_list.records[:500]:
                    raw_records.append(rec.to_json() if hasattr(rec, 'to_json') else rec)
            if raw_records:
                behavior_data = analyze_submission_behavior(raw_records)
        except Exception as e:
            behavior_data = {"error": str(e)}

        # ========== 新增：大纲知识点对标 ==========
        with TASKS_LOCK:
            update_task(task_id, message="正在进行大纲知识点对标分析...")

        syllabus_evaluation = evaluate_all_topics(summary.get("top_tags", []))
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

        report_md = generate_ai_report(export_data, api_key, base_url, model_name)

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(report_md)

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
            update_task(task_id, status="error", message=str(e))


@app.route("/")
def index():
    return render_template_string(INDEX_HTML)


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
