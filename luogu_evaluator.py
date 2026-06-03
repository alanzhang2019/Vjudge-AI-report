import os
import json
import argparse
import math
import re
import base64
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from rich.console import Console
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from openai import OpenAI
import pyLuogu
from examples.export_for_ai import _build_tag_maps, _summarize, _pick_record_for_problem

import markdown as md
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

console = Console()
DEFAULT_REPORT_MD = "luogu_coach_report.md"
DEFAULT_REPORT_HTML = "luogu_coach_report.html"
DEFAULT_REPORT_PDF = "luogu_coach_report.pdf"
DEFAULT_ASSETS_DIR = "luogu_report_assets"

DIAGNOSTIC_FRAMEWORK = """
【能力评估参考框架】（请对照此框架对用户进行诊断和分级建议）：
1. S级 - 计数与组合推导：赛时容易先写DFS/枚举，缺乏“统计对象集合”思维。需强化：组合数/容斥/DP/生成函数。
2. S级 - 图论建模与最短路变形：模板能写但建图边含义不稳，差分约束/分层图易卡。需强化：图的语义定义、最短路树。
3. A级 - 数据结构维护不变量：基础线段树能做，多标记易WA。需强化：节点信息明确数学定义、merge/pushdown的代数正确性。
4. A级 - DP 状态设计与优化：常规DP能写，维度多易爆复杂度。需强化：树形/区间/状压DP，单调队列优化。
5. A级 - 部分分升级能力：赛时能拿部分分，但不会倒推。需强化：从小n、小值域、树退化等子任务倒推正解。
6. B级 - 高级字符串结构：KMP/Hash有基础，自动机/SAM不稳定。需强化：节点代表的集合、Fail树/link的含义。
7. B级 - 计算几何：缺模板，少边界意识。需强化：向量/叉积、凸包、扫描线基础与eps处理。
8. B级 - 网络流/匹配：缺乏模式识别。需强化：建图谱系、最小割模型、费用流。
9. S级 - 复盘与错因沉淀：盲目改代码AC后就过。需强化：四段式复盘（赛时模型、错因、正解性质、代码不变量）。
"""


def find_chinese_font_path() -> str | None:
    candidates = [
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\msyh.ttf",
        r"C:\Windows\Fonts\msyhbd.ttf",
        r"C:\Windows\Fonts\simkai.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


def configure_matplotlib_font() -> str | None:
    font_path = find_chinese_font_path()
    if font_path:
        from matplotlib import font_manager

        font_name = font_manager.FontProperties(fname=font_path).get_name()
        plt.rcParams["font.sans-serif"] = [font_name]
    plt.rcParams["axes.unicode_minus"] = False
    return font_path


def register_pdf_font() -> str:
    font_path = find_chinese_font_path()
    if font_path:
        try:
            pdfmetrics.registerFont(TTFont("CoachChinese", font_path))
            return "CoachChinese"
        except Exception:
            pass
    return "Helvetica"


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def compute_ability_scores(export_data: dict) -> dict[str, int]:
    summary = export_data.get("summary", {}) or {}
    top_tags = summary.get("top_tags", []) or []
    difficulty_histogram = summary.get("difficulty_histogram", {}) or {}
    solved_count = int(export_data.get("solved_count", 0))
    failed_count = int(export_data.get("failed_count", 0))

    keyword_map = {
        "基础实现": [],
        "搜索 / DFS": ["dfs", "搜索", "回溯", "枚举", "树遍历"],
        "动态规划": ["dp", "背包", "区间", "树形", "状压"],
        "图论": ["图", "tarjan", "lca", "最短路", "并查集", "网络流", "匹配", "树"],
        "数据结构": ["线段树", "树状数组", "bit", "堆", "单调", "平衡树", "st表", "数据结构"],
        "字符串 / 数学": ["字符串", "kmp", "hash", "trie", "sam", "数论", "数学", "组合", "计数", "贪心", "构造", "证明"],
    }

    difficulty_total = 0
    weighted = 0
    for key, value in difficulty_histogram.items():
        if str(key).isdigit():
            difficulty_total += int(value)
            weighted += int(key) * int(value)
    avg_difficulty = weighted / difficulty_total if difficulty_total else 0

    scores: dict[str, int] = {}
    for ability, keywords in keyword_map.items():
        score = 35 + min(20, solved_count * 2) - min(12, failed_count * 2)
        if ability == "基础实现":
            score = 48 + min(28, solved_count * 2) + int(avg_difficulty * 4)
        for item in top_tags:
            tag_name = str(item.get("name") or "").lower()
            count = int(item.get("count", 0))
            if any(keyword in tag_name for keyword in keywords):
                score += min(18, count * 2)
        if ability in {"动态规划", "图论", "数据结构", "字符串 / 数学"}:
            score += int(avg_difficulty * 3)
        scores[ability] = max(20, min(95, int(score)))
    return scores


def generate_chart_images(export_data: dict, output_dir: str) -> dict[str, str]:
    ensure_dir(output_dir)
    configure_matplotlib_font()

    chart_paths: dict[str, str] = {}
    summary = export_data.get("summary", {}) or {}
    difficulty_histogram = summary.get("difficulty_histogram", {}) or {}
    top_tags = summary.get("top_tags", []) or []
    solved_count = int(export_data.get("solved_count", 0))
    failed_count = int(export_data.get("failed_count", 0))

    difficulty_meta = {
        0: ("暂无评定", "#9CA3AF"),
        1: ("入门", "#EF4444"),
        2: ("普及-", "#F97316"),
        3: ("普及/提高-", "#F59E0B"),
        4: ("普及+/提高", "#22C55E"),
        5: ("提高+/省选-", "#3B82F6"),
        6: ("省选/NOI-", "#A855F7"),
        7: ("NOI/NOI+/CTSC", "#111827"),
    }

    def _get_hist_count(key: int | str) -> int:
        if key in difficulty_histogram:
            return int(difficulty_histogram[key])
        skey = str(key)
        return int(difficulty_histogram.get(skey, 0))

    numeric_levels = []
    other_keys = []
    for k in difficulty_histogram.keys():
        ks = str(k)
        if ks.isdigit():
            numeric_levels.append(int(ks))
        else:
            other_keys.append(ks)

    numeric_levels = sorted(set(numeric_levels))
    other_keys = sorted(set(other_keys))

    if numeric_levels or other_keys:
        labels: list[str] = []
        values: list[int] = []
        colors: list[str] = []

        for level in numeric_levels:
            name, color = difficulty_meta.get(level, (str(level), "#4C78A8"))
            labels.append(name)
            values.append(_get_hist_count(level))
            colors.append(color)

        for k in other_keys:
            labels.append(k)
            values.append(_get_hist_count(k))
            colors.append("#4C78A8")

        fig, ax = plt.subplots(figsize=(7.6, 4.6))
        x = list(range(len(labels)))
        ax.bar(x, values, color=colors, edgecolor="#E5E7EB")
        ax.set_title("题目难度分布（按洛谷难度等级）")
        ax.set_xlabel("难度")
        ax.set_ylabel("题目数量")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=20, ha="right")
        for idx, value in enumerate(values):
            ax.text(idx, value + 0.1, str(value), ha="center", va="bottom", fontsize=9)
        fig.tight_layout()
        difficulty_path = os.path.join(output_dir, "difficulty_histogram.png")
        fig.savefig(difficulty_path, dpi=180, bbox_inches="tight")
        plt.close(fig)
        chart_paths["difficulty"] = difficulty_path

    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    counts = [solved_count, failed_count]
    labels = ["已通过", "未通过"]
    colors_list = ["#59A14F", "#E15759"]
    if sum(counts) == 0:
        counts = [1]
        labels = ["暂无数据"]
        colors_list = ["#BAB0AC"]
    ax.pie(counts, labels=labels, autopct="%1.0f%%", startangle=90, colors=colors_list)
    ax.set_title("通过 / 未通过占比")
    fig.tight_layout()
    status_path = os.path.join(output_dir, "status_ratio.png")
    fig.savefig(status_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    chart_paths["status"] = status_path

    selected_tags = top_tags[:8]
    if selected_tags:
        fig, ax = plt.subplots(figsize=(8, 4.8))
        tag_names = [str(item.get("name") or item.get("id")) for item in selected_tags][::-1]
        tag_counts = [int(item.get("count", 0)) for item in selected_tags][::-1]
        ax.barh(tag_names, tag_counts, color="#F28E2B")
        ax.set_title("高频标签 Top 8")
        ax.set_xlabel("出现次数")
        for idx, value in enumerate(tag_counts):
            ax.text(value + 0.1, idx, str(value), va="center", fontsize=9)
        fig.tight_layout()
        tags_path = os.path.join(output_dir, "top_tags.png")
        fig.savefig(tags_path, dpi=180, bbox_inches="tight")
        plt.close(fig)
        chart_paths["tags"] = tags_path

    ability_scores = compute_ability_scores(export_data)
    radar_labels = list(ability_scores.keys())
    radar_values = [ability_scores[key] for key in radar_labels]
    if radar_labels:
        angles = [n / float(len(radar_labels)) * 2 * math.pi for n in range(len(radar_labels))]
        angles += angles[:1]
        radar_plot_values = radar_values + radar_values[:1]
        fig = plt.figure(figsize=(6.6, 6.2))
        ax = plt.subplot(111, polar=True)
        ax.set_theta_offset(math.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_thetagrids([angle * 180 / math.pi for angle in angles[:-1]], radar_labels, fontsize=9)
        ax.set_ylim(0, 100)
        zone_colors = [
            (0, 40, "#FDECEC"),
            (40, 65, "#FFF3E0"),
            (65, 85, "#E8F4FF"),
            (85, 100, "#E7F6EC"),
        ]
        zone_angles = [n / 180.0 * math.pi for n in range(361)]
        for start, end, zone_color in zone_colors:
            ax.fill_between(zone_angles, start, end, color=zone_color, alpha=0.35)
        ax.plot(angles, radar_plot_values, color="#4C78A8", linewidth=2)
        ax.fill(angles, radar_plot_values, color="#4C78A8", alpha=0.25)
        ax.set_rgrids([20, 40, 60, 80, 100], angle=90, fontsize=8, color="#8A96A3")
        ax.set_title("能力雷达图", pad=18)
        radar_path = os.path.join(output_dir, "ability_radar.png")
        fig.savefig(radar_path, dpi=180, bbox_inches="tight")
        plt.close(fig)
        chart_paths["radar"] = radar_path
        
    # 生成性格画像雷达图
    behavior_data = export_data.get("behavior_analysis", {})
    personality_scores = behavior_data.get("personality_scores", {})
    if personality_scores:
        p_labels = list(personality_scores.keys())
        p_values = [personality_scores[k] for k in p_labels]
        angles = [n / float(len(p_labels)) * 2 * math.pi for n in range(len(p_labels))]
        angles += angles[:1]
        p_plot_values = p_values + p_values[:1]
        
        fig = plt.figure(figsize=(6.6, 6.2))
        ax = plt.subplot(111, polar=True)
        ax.set_theta_offset(math.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_thetagrids([angle * 180 / math.pi for angle in angles[:-1]], p_labels, fontsize=10)
        ax.set_ylim(0, 100)
        
        # 性格雷达图配色使用偏橙色/活力的色调
        zone_colors = [
            (0, 40, "#F3F4F6"),
            (40, 60, "#E5E7EB"),
            (60, 80, "#FEF3C7"),
            (80, 100, "#FEF08A"),
        ]
        zone_angles = [n / 180.0 * math.pi for n in range(361)]
        for start, end, zone_color in zone_colors:
            ax.fill_between(zone_angles, start, end, color=zone_color, alpha=0.35)
            
        ax.plot(angles, p_plot_values, color="#D97706", linewidth=2.5)
        ax.fill(angles, p_plot_values, color="#F59E0B", alpha=0.3)
        ax.set_rgrids([20, 40, 60, 80, 100], angle=90, fontsize=8, color="#9CA3AF")
        ax.set_title("性格特质雷达图", pad=18, fontsize=12, fontweight="bold", color="#92400E")
        
        p_radar_path = os.path.join(output_dir, "personality_radar.png")
        fig.savefig(p_radar_path, dpi=180, bbox_inches="tight")
        plt.close(fig)
        chart_paths["personality_radar"] = p_radar_path

    # 生成一发入魂率柱状图
    ac_submit_distribution = behavior_data.get("ac_submit_distribution", {})
    if ac_submit_distribution:
        def _dist_get(mapping: dict, key: int) -> int:
            if key in mapping:
                return int(mapping[key])
            return int(mapping.get(str(key), 0))

        # 将字符串键转换为整数排序
        keys = []
        for k in ac_submit_distribution.keys():
            try:
                keys.append(int(k))
            except ValueError:
                pass
        keys.sort()
        
        # 准备 x 和 y 轴数据，合并 >= 10 的部分
        labels = []
        values = []
        count_10_plus = 0
        total_ac = sum(ac_submit_distribution.values())
        
        for k in keys:
            if k >= 10:
                count_10_plus += _dist_get(ac_submit_distribution, k)
            else:
                labels.append(str(k))
                values.append(_dist_get(ac_submit_distribution, k))
                
        if count_10_plus > 0:
            labels.append("10+")
            values.append(count_10_plus)

        if labels:
            fig, ax = plt.subplots(figsize=(8, 4.5))
            # 设置颜色：第一发是深蓝色，其他是浅蓝色
            colors = ["#2563EB" if l == "1" else "#93C5FD" for l in labels]
            bars = ax.bar(labels, values, color=colors, edgecolor="none")
            ax.set_title("AC 所需提交次数分布（一发入魂率）", fontsize=12, fontweight="bold")
            ax.set_xlabel("AC 所需提交次数")
            ax.set_ylabel("题目数")
            
            # 在柱子上添加文字标签
            for bar, value in zip(bars, values):
                percentage = (value / total_ac * 100) if total_ac > 0 else 0
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                        f"{value}\n({percentage:.0f}%)",
                        ha="center", va="bottom", fontsize=8)
                        
            fig.tight_layout()
            ac_dist_path = os.path.join(output_dir, "ac_submit_distribution.png")
            fig.savefig(ac_dist_path, dpi=180, bbox_inches="tight")
            plt.close(fig)
            chart_paths["ac_submit_distribution"] = ac_dist_path

    return chart_paths


def build_html_and_pdf(report_md: str, export_data: dict, html_path: str, pdf_path: str, chart_paths: dict[str, str]) -> None:
    # 扩展 markdown，支持表格
    report_html = md.markdown(report_md, extensions=['tables', 'fenced_code'])
    report_html = re.sub(
        r"((?:⭐|☆){3,5})",
        lambda m: f'<span style="color:#f59e0b;font-size:1.05em;letter-spacing:1px;">{m.group(1)}</span>',
        report_html,
    )
    
    # 替换错题分页
    # 在 6. **【未通过题目专属题解（从暴力到正解）】** 后面的 h3 题目标题前插入分页符
    report_html = re.sub(r'(<h3>Problem)', r'<div class="page-break"></div>\1', report_html)

    # 动态为表格中的“当前等级”和“优先级”添加圆角徽章颜色样式
    # 使用正则匹配 td 标签里的特定文字，加上 span 标签
    badge_style_base = "display:inline-block;padding:2px 8px;border-radius:9999px;border:1px solid;font-size:12px;font-weight:700;line-height:1.2;white-space:nowrap;"
    badge_styles = {
        "green": badge_style_base + "background:#DCFCE7;color:#166534;border-color:#86EFAC;",
        "orange": badge_style_base + "background:#FFEDD5;color:#9A3412;border-color:#FDBA74;",
        "red": badge_style_base + "background:#FEE2E2;color:#991B1B;border-color:#FCA5A5;",
        "gray": badge_style_base + "background:#F3F4F6;color:#374151;border-color:#D1D5DB;",
    }
    risk_legend_html = '<p style="margin:0 0 12px 0;color:#6b7280;font-size:13px;">优先级说明：S（高/立即处理） · A（中/近期处理） · B（低/可后置）。</p>'
    risk_legend_inserted = False

    level_rules = [
        (re.compile(r"(短板|明显短板|偏弱|弱|无涉及|未涉及|缺失|不会|没涉及|没有涉及|基础弱)", re.I), "red"),
        (re.compile(r"(中等偏稳|有基础|基础稳|待强化|会但赛时成本高|需要加强|高级弱|易错|不熟)", re.I), "orange"),
        (re.compile(r"(稳|强项|覆盖充分|中上|优秀|熟练|稳定)", re.I), "green"),
    ]

    def _clean_cell_inner(inner: str) -> str:
        inner = re.sub(r"</?p[^>]*>", "", inner, flags=re.I)
        inner = re.sub(r"<[^>]+>", "", inner)
        return inner.strip()

    def _wrap_td_inner(td_html: str, display_text: str, style_key: str) -> str:
        m = re.match(r"<td(?P<attrs>[^>]*)>(?P<inner>.*)</td>", td_html, flags=re.S | re.I)
        if not m:
            return td_html
        attrs = m.group("attrs") or ""
        return f'<td{attrs}><span style="{badge_styles[style_key]}">{display_text}</span></td>'

    def _process_table(table_html: str) -> str:
        nonlocal risk_legend_inserted
        is_ability_table = bool(
            re.search(r"<th[^>]*>\s*能力块\s*</th>", table_html, flags=re.I)
            and re.search(r"<th[^>]*>\s*当前等级\s*</th>", table_html, flags=re.I)
        )
        is_risk_table = bool(
            re.search(r"<th[^>]*>\s*优先级\s*</th>", table_html, flags=re.I)
            and re.search(r"<th[^>]*>\s*风险项\s*</th>", table_html, flags=re.I)
        )
        if not (is_ability_table or is_risk_table):
            return table_html

        def _row_repl(m: re.Match) -> str:
            row = m.group(0)
            if "<th" in row:
                return row
            tds = re.findall(r"<td[^>]*>.*?</td>", row, flags=re.S | re.I)
            if not tds:
                return row

            if is_ability_table:
                col_idx = 1
                if len(tds) <= col_idx:
                    return row
                target_td = tds[col_idx]
                inner = re.sub(r"^<td[^>]*>|</td>$", "", target_td, flags=re.S | re.I)
                text = _clean_cell_inner(inner)
                if not text:
                    return row
                style_key = None
                for rule, key in level_rules:
                    if rule.search(text):
                        style_key = key
                        break
                if not style_key:
                    return row
                new_td = _wrap_td_inner(target_td, text, style_key)
                return row.replace(target_td, new_td, 1)

            col_idx = 0
            if len(tds) <= col_idx:
                return row
            target_td = tds[col_idx]
            inner = re.sub(r"^<td[^>]*>|</td>$", "", target_td, flags=re.S | re.I)
            text = _clean_cell_inner(inner)
            normalized = (text or "").strip().upper()
            mapping = {
                "S": ("S（高/立即处理）", "red"),
                "A": ("A（中/近期处理）", "orange"),
                "B": ("B（低/可后置）", "green"),
            }
            if normalized not in mapping:
                return row
            label, style_key = mapping[normalized]
            new_td = _wrap_td_inner(target_td, label, style_key)
            return row.replace(target_td, new_td, 1)

        processed = re.sub(r"<tr>.*?</tr>", _row_repl, table_html, flags=re.S | re.I)
        if is_risk_table and not risk_legend_inserted:
            risk_legend_inserted = True
            return processed + risk_legend_html
        return processed

    report_html = re.sub(r"<table[^>]*>.*?</table>", lambda m: _process_table(m.group(0)), report_html, flags=re.S | re.I)

    # 准备模板数据
    summary = export_data.get("summary", {}) or {}
    difficulty_histogram = summary.get("difficulty_histogram", {}) or {}
    total = 0
    weighted = 0
    for key, value in difficulty_histogram.items():
        if str(key).isdigit():
            total += int(value)
            weighted += int(key) * int(value)
    avg_difficulty = f"{(weighted / total):.1f}" if total else "0.0"
    
    top_tag = "暂无"
    top_tags = summary.get("top_tags", []) or []
    if top_tags:
        top_tag = str(top_tags[0].get("name") or top_tags[0].get("id"))

    # 渲染 HTML
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('report_template.html')
    
    def _chart_src(value: str) -> str:
        if not value:
            return ""
        if value.startswith("data:"):
            return value
        if value.startswith("file:///") or value.startswith("http://") or value.startswith("https://"):
            return value
        p = Path(value)
        if not p.exists():
            return value
        ext = p.suffix.lower()
        mime = "image/png"
        if ext in {".jpg", ".jpeg"}:
            mime = "image/jpeg"
        elif ext == ".webp":
            mime = "image/webp"
        data = base64.b64encode(p.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{data}"

    chart_srcs = {k: _chart_src(v) for k, v in chart_paths.items()}

    rendered_html = template.render(
        export_data=export_data,
        report_html=report_html,
        chart_paths=chart_srcs,
        avg_difficulty=avg_difficulty,
        top_tag=top_tag
    )

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(rendered_html)

    # 导出为 PDF
    console.print("[cyan]正在调用 Playwright 将 HTML 导出为高质量 PDF...[/cyan]")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            # 加上 file:// 协议访问本地 HTML
            file_url = f"file:///{os.path.abspath(html_path).replace(os.sep, '/')}"
            page.goto(file_url)
            page.wait_for_load_state("networkidle")
            page.pdf(
                path=pdf_path,
                format="A4",
                print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}
            )
            browser.close()
    except Exception as e:
        console.print(f"[red]PDF 导出失败（Playwright 错误），请确保已运行 `playwright install chromium`。\n错误详情：{e}[/red]")

def load_or_prompt_openai_config():
    key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    
    if not key:
        console.print(Panel("[yellow]OpenAI API Key not found.[/yellow]\nThis tool requires an OpenAI-compatible API key to evaluate your code and generate suggestions.\nIt supports any third-party platform that provides OpenAI-compatible endpoints (e.g., DeepSeek, Moonshot, SiliconFlow, etc.).", title="Configuration"))
        key = Prompt.ask("Please enter your API Key")
        os.environ["OPENAI_API_KEY"] = key.strip()
        
    if not base_url:
        base_url_input = Prompt.ask("Please enter the API Base URL (leave blank for default OpenAI: https://api.openai.com/v1)")
        if base_url_input.strip():
            os.environ["OPENAI_BASE_URL"] = base_url_input.strip()
            base_url = base_url_input.strip()
            
    # Also ask for model if base URL is provided since different platforms have different model names
    model_name = os.environ.get("OPENAI_MODEL_NAME")
    if not model_name:
        default_model = "gpt-4o" if not base_url else ""
        model_input = Prompt.ask(f"Please enter the model name to use (leave blank for default: {default_model})")
        if model_input.strip():
            os.environ["OPENAI_MODEL_NAME"] = model_input.strip()
        else:
            os.environ["OPENAI_MODEL_NAME"] = default_model
            
    return key, base_url, os.environ.get("OPENAI_MODEL_NAME")

def load_or_prompt_cookies():
    cookie_file = Path("cookies.json")
    if cookie_file.exists():
        try:
            return pyLuogu.LuoguCookies.from_file(str(cookie_file))
        except Exception as e:
            console.print(f"[red]Failed to load cookies.json: {e}[/red]")
            
    console.print(Panel("[yellow]Luogu Cookies not found.[/yellow]\nTo fetch your submissions, we need your Luogu cookies.", title="Configuration"))
    client_id = Prompt.ask("Enter your __client_id cookie value")
    uid = Prompt.ask("Enter your _uid cookie value")
    
    cookies = pyLuogu.LuoguCookies({
        "__client_id": client_id.strip(),
        "_uid": uid.strip()
    })
    
    with open("cookies.json", "w", encoding="utf-8") as f:
        json.dump(cookies.to_json(), f, indent=2)
        
    return cookies

def generate_ai_report(export_data: dict, api_key: str, base_url: str | None, model_name: str) -> str:
    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
        
    client = OpenAI(**client_kwargs)
    
    solved_count = export_data.get("solved_count", 0)
    failed_count = export_data.get("failed_count", 0)
    summary = export_data.get("summary", {})

    # 提取代码样本（通过的题）
    passed_samples = []
    for item in export_data.get("passed_items", []):
        record = item.get("record")
        if record and isinstance(record, dict) and record.get("sourceCode"):
            passed_samples.append(f"### Problem {item['problem']['pid']} - {item['problem']['title']} (Passed)\n```cpp\n{record['sourceCode'][:800]}\n```\n")
        if len(passed_samples) >= 3:
            break

    # 提取未通过/做错的题
    failed_samples = []
    for item in export_data.get("failed_items", []):
        record = item.get("record")
        pid = item['problem']['pid']
        title = item['problem']['title']
        code_str = ""
        if record and isinstance(record, dict) and record.get("sourceCode"):
            code_str = f"User's failed code snippet:\n```cpp\n{record['sourceCode'][:800]}\n```\n"
        failed_samples.append(f"### Problem {pid} - {title} (Attempted but NOT passed)\n{code_str}")
        if len(failed_samples) >= 5: # Limit failed examples
            break

    # 行为分析数据
    behavior_data = export_data.get("behavior_analysis", {})
    behavior_summary = ""
    if behavior_data and "error" not in behavior_data:
        from behavior_analyzer import format_behavior_summary
        behavior_summary = format_behavior_summary(behavior_data)
    else:
        behavior_summary = "**提交行为分析**: 未获取到提交记录数据。"

    # 代码风格静态分析
    from code_analyzer import analyze_code_style, format_code_analysis
    code_records = []
    for item in export_data.get("passed_items", []) + export_data.get("failed_items", []):
        if "record" in item and isinstance(item["record"], dict):
            code_records.append(item["record"])
    
    code_analysis_data = analyze_code_style(code_records)
    code_analysis_summary = format_code_analysis(code_analysis_data)

    # 大纲对标数据
    syllabus_eval = export_data.get("syllabus_evaluation", {})
    syllabus_summary = ""
    if syllabus_eval:
        from syllabus_matcher import format_syllabus_report
        syllabus_summary = format_syllabus_report(syllabus_eval)
    else:
        syllabus_summary = "**大纲知识点对标**: 未获取到评估数据。"

    # 六维评分
    six_dim = export_data.get("six_dimension_scores", {})
    six_dim_text = ""
    if six_dim:
        six_dim_text = "| 维度 | 评分 |\n|------|------|\n"
        for dim, score in six_dim.items():
            six_dim_text += f"| {dim} | {score} |\n"

    # Load syllabus contexts if available
    syllabus_context = ""
    syllabus_candidates = [
        "NOI大纲_Syllabus_Edition_2025.pdf.txt",
        "GESP考纲.pdf.txt",
        "noi大纲.pdf.txt",
    ]
    for syllabus_file in syllabus_candidates:
        syllabus_path = Path(syllabus_file)
        if syllabus_path.exists():
            content = syllabus_path.read_text(encoding="utf-8")
            syllabus_context += f"【{syllabus_file} 内容摘要】\n{content[:20000]}\n\n"
            break  # 优先使用最新版大纲

    import datetime
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    difficulty_guide = """
洛谷难度映射请严格使用以下标准名称，不要写“难度1/难度2”：
- 0: 暂无评定（灰色）
- 1: 入门（红色）
- 2: 普及-（橙色）
- 3: 普及/提高-（黄色）
- 4: 普及+/提高（绿色）
- 5: 提高+/省选-（蓝色）
- 6: 省选/NOI-（紫色）
- 7: NOI/NOI+/CTSC（黑色）
"""

    prompt = f"""
你是一位顶级的算法竞赛金牌教练。我导出了一位选手的近期洛谷做题记录（包括已通过和尝试但未通过的题目代码）。
请你根据我提供的【能力评估参考框架】以及【官方考纲】，对他进行深度的诊断，并针对他【未做完/做错的题目】给出极具启发性的题解。

**报告生成时间**：{current_time}

{DIAGNOSTIC_FRAMEWORK}

{difficulty_guide}

{syllabus_context}

### 选手的全局数据统计
- 本次导出中已通过题数: {solved_count}
- 本次导出中未通过/卡住题数: {failed_count}
- 难度分布直方图: {json.dumps(summary.get('difficulty_histogram'))}
- 偏好的算法标签: {json.dumps(summary.get('top_tags'))}

### 六维能力评分
{six_dim_text if six_dim_text else '未计算'}

### 提交行为深度分析
{behavior_summary}

### 大纲知识点对标
{syllabus_summary}

{code_analysis_summary}

### 选手最近通过的代码样本（用于评估代码习惯）
{''.join(passed_samples) if passed_samples else '暂无代码'}

### 选手未做完/尝试失败的题目（重点出题解部分）
{''.join(failed_samples) if failed_samples else '暂无未通过的题目'}

请你输出一份结构化的 Markdown 辅导报告，必须包含以下部分。在生成 Markdown 时，请务必使用以下视觉元素增强表现力：
 - 评分请使用黄色星级，如 ⭐⭐⭐⭐☆ (使用 ⭐ 和 ☆)
 - 难度或占比进度条请使用区块字符，如 ██████████ 16%
 - 等级前缀符号请使用 🟢精通 | 🟡熟练 | 🟠入门 | 🔵初窥 | 🔴空白
 - 各处点评或结论段落，请使用 `<p class="text-blue-700 font-semibold">解读：...</p>` 样式包装。
 - 整个报告尽可能以 Markdown 表格、区块等图表化、直观的形式呈现，少用长篇大论的文字。

 1. **【选手概览与性格画像】**：
    基于提交行为数据，提炼选手的性格画像（坚韧度、完美主义、冒险精神、自律性、调试耐心、作息规律）。用黄色星级（如 ⭐⭐⭐⭐☆）评分，并附上数据支撑和拟人化评价。如果数据不足以评估某一项，请标注“无法评估”并说明原因（如：作息规律无法评估是因为未能获取具体的提交时间点数据）。

 2. **【提交行为深度分析】**：
    基于提供的提交行为数据，以表格和重点解读的形式，深入分析用户的提交习惯。必须包含以下子模块：
    - **死磕题目 TOP (提交次数最多)**：列出提交次数最多的几道题，分析原因。
    - **一次 AC 率**：分析“一发入魂”和多次尝试的比例。
    - **其他显著行为特征**：如单日高强度刷题记录、长耗时题目等。
    (注意：此部分请用表格展示数据，并在表下附上 `<p class="text-blue-700 font-semibold">特征：...</p>`)

 3. **【难度分布与水平研判】**：
    分析选手的难度分布特征，判断其处于哪个阶段（入门/普及/提高/省选）。使用 HTML 彩色区块（如 `<span style="display:inline-block;width:100px;height:12px;background-color:#3b82f6;"></span>`）生成直观的横向进度条，不同难度使用不同颜色，不要再生成成长曲线。

 4. **【六维能力雷达表与诊断】（评分参考：85-100 优秀 | 65-84 良好 | 40-64 基础 | <40 薄弱）**：
      输出 Markdown 表格，评估选手在六大维度的状态：`| 能力块 | 评分 | 当前等级 | 数据证据 | 已经具备 |`
      六大维度：基础算法、数据结构、图论、动态规划、字符串、数学。当前等级请使用前缀符号（如 🟢精通）。

  5. **【考纲精准定级与知识点盲区】**（根据提供的 NOI大纲 2025版）：
     - **当前对应等级水平**：明确指出该选手目前处于 CSP-J / CSP-S / 省选 / NOI 哪个阶段。
     - **知识点强弱项**：严格对照考纲中的知识点名词，列出其掌握得最好的 3 个考点，以及最薄弱的 3 个考点（使用 🟢🟡🔴 标注）。
     - **训练盲区**：指出他在当前等级中"完全没有涉及/刷题数据中缺失"的必考知识点。
     - **分级汇总表**：输出 CSP-J / CSP-S / 省选级 / NOI级 的覆盖率统计表格。

  6. **【风险诊断与训练闭环表】**：
     输出 Markdown 表格：`| 优先级 | 风险项 | 触发场景 | 比赛症状 | 根因判断 | 训练专题 | 验收标准 |`
     - 行数至少 5 行，优先级使用 `S/A/B`。
     - 这个表必须是高度可执行的训练方案。

  7. **【代码质量与工程习惯深度分析】**：基于《源码静态风格分析》及代码样本，提供一份来自资深架构师视角的 Review。分析代码长度、宏定义习惯（如 `#define int long long`）、IO 优化、命名、STL 容器使用情况等。指出 2 个优点和 3 个必须改掉的坏习惯。

  8. **【定制训练题单（6个月路线图）】**：
     根据上述大纲盲区和薄弱项，定制一份分阶段的训练计划：
     - 第一阶段（Month 1-2）：巩固基础，补齐短板
     - 第二阶段（Month 3-4）：数据结构/算法突破
     - 第三阶段（Month 5-6）：提速与稳定
     每个阶段包含具体知识点 + 推荐题目（带洛谷题号）。

  9. **【核心建议（优先级排序）】**：
     列出 5-8 条核心建议，按优先级排序（🔴紧急 / 🟡重要 / 🟢建议）。例如：`🔴 紧急: 补加 ios::sync_with_stdio(false) 防止大数据 TLE`。

  10. **【未通过题目专属题解（从暴力到正解）】**：针对上面列出的"未做完/尝试失败的题目"，逐一出题解。
    - 绝不能直接给出最优解！
    - 必须严格遵循**"从暴力到正解的思考过程"**：
      a) **AI 题解摘要**：一句话点出这道题的核心思路或坑点。
      b) 暴力思路怎么想？（复杂度是多少，能拿多少部分分？）
      c) 瓶颈在哪里？（时间卡在哪，空间卡在哪？）
      d) 关键性质/不变量观察（Key Observation）。
      e) 最终正解的推导与核心代码结构。
      f) **推荐同类题**：推荐 1-2 道涉及相同考点或技巧的洛谷题目（标明题号和简要推荐理由）。
 """
    
    response = client.chat.completions.create(
        model=model_name, # 使用用户指定的模型
        messages=[
            {"role": "system", "content": "你是顶级算法竞赛教练，极其擅长引导学生通过“暴力-观察-优化”的过程推导正解，且熟悉各种算法训练框架。"},
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.choices[0].message.content

def extract_problems_from_practice(practice_data, key: str):
    problems = []
    if isinstance(practice_data, dict):
        items = practice_data.get(key)
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict): continue
                pid = item.get("pid")
                if pid:
                    problems.append(
                        pyLuogu.ProblemSummary({
                            "pid": str(pid),
                            "title": item.get("title") or item.get("name") or "",
                            "difficulty": item.get("difficulty"),
                            "type": item.get("type"),
                        })
                    )
    return problems

def main():
    parser = argparse.ArgumentParser(description="Luogu AI Evaluator - Coach Edition")
    parser.add_argument("--max-passed", type=int, default=10, help="Number of passed problems to fetch")
    parser.add_argument("--max-failed", type=int, default=5, help="Number of failed/unsolved problems to fetch")
    parser.add_argument("--report-md", default=DEFAULT_REPORT_MD, help="Markdown report output path")
    parser.add_argument("--report-pdf", default=DEFAULT_REPORT_PDF, help="PDF report output path")
    parser.add_argument("--assets-dir", default=DEFAULT_ASSETS_DIR, help="Directory for generated chart assets")
    args = parser.parse_args()
    
    console.print(Panel.fit("[bold cyan]Welcome to the Luogu AI Evaluator (Coach Edition)[/bold cyan]\n[dim]Incorporating Advanced Diagnostic Framework & Step-by-Step Editorials[/dim]"))
    
    # 收集学生信息
    console.print("\n[bold]为了生成更正式的报告，请填写测评基础信息（直接回车可跳过）：[/bold]")
    student_name = Prompt.ask("姓名", default="未知选手")
    school = Prompt.ask("学校", default="未知学校")
    grade = Prompt.ask("年级", default="未知年级")
    
    api_key, base_url, model_name = load_or_prompt_openai_config()
    cookies = load_or_prompt_cookies()
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        task = progress.add_task("[cyan]Connecting to Luogu API...", total=None)
        
        try:
            luogu = pyLuogu.luoguAPI(cookies=cookies)
            me = luogu.me()
            uid = int(me.uid)
            progress.update(task, description=f"[green]Connected as User ID: {uid}[/green]")
            
            tag_by_id, type_by_id = _build_tag_maps(luogu)
            practice = luogu.get_user_practice(uid)
            
            from behavior_analyzer import analyze_submission_behavior, compute_six_dimension_scores
            from syllabus_matcher import evaluate_all_topics
            
            # Fetch behavior data by fetching recent submissions
            try:
                progress.update(task, description="[cyan]Fetching recent submissions for behavior analysis...")
                raw_records = []
                for page in range(1, 26):
                    record_list = luogu.get_record_list(page=page, uid=uid, user=str(uid))
                    page_records = getattr(record_list, "records", None) or getattr(record_list, "data", None) or []
                    normalized_records = [
                        rec.to_json() if hasattr(rec, "to_json") else rec
                        for rec in page_records
                    ]
                    if not normalized_records:
                        break
                    raw_records.extend(normalized_records)
                    if len(normalized_records) < 20 or len(raw_records) >= 1000:
                        break
                behavior_analysis = analyze_submission_behavior(raw_records)
            except Exception as e:
                console.print(f"[yellow]Failed to fetch behavior analysis data: {e}[/yellow]")
                behavior_analysis = {"error": str(e)}
            
            # Fetch Passed
            all_passed_problems = extract_problems_from_practice(practice.data, "passed")
            all_passed_problems.sort(key=lambda p: (p.difficulty if p.difficulty is not None else 10, p.pid), reverse=True)
            passed_problems = all_passed_problems[:args.max_passed]
            
            # Fetch Failed (Attempted but not passed)
            all_failed_problems = extract_problems_from_practice(practice.data, "failed")
            all_failed_problems.sort(key=lambda p: (p.difficulty if p.difficulty is not None else 10, p.pid), reverse=True)
            failed_problems = all_failed_problems[:args.max_failed]
            
            progress.update(task, description=f"[cyan]Fetching submissions for {len(passed_problems)} passed and {len(failed_problems)} failed problems...")
            
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
                
            summary = _summarize(all_passed_problems + all_failed_problems, tag_by_id=tag_by_id)
            syllabus_evaluation = evaluate_all_topics(summary.get("top_tags", []))
            six_dim_scores = compute_six_dimension_scores(
                {"solved_count": len(all_passed_problems), "summary": summary},
                behavior_analysis if "error" not in behavior_analysis else {},
            )
            
            import datetime
            export_data = {
                "student_info": {
                    "name": student_name,
                    "school": school,
                    "grade": grade,
                    "eval_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                },
                "solved_count": len(all_passed_problems),
                "failed_count": len(all_failed_problems),
                "summary": summary,
                "passed_items": passed_items,
                "failed_items": failed_items,
                "behavior_analysis": behavior_analysis,
                "syllabus_evaluation": syllabus_evaluation,
                "six_dimension_scores": six_dim_scores,
            }
            
            progress.update(task, description=f"[cyan]Analyzing with {model_name} (Applying diagnostic framework & generating editorials)...")
            report_md = generate_ai_report(export_data, api_key, base_url, model_name)
            progress.update(task, description="[green]Analysis complete!")
            
        except Exception as e:
            console.print(f"[red]Error during execution: {e}[/red]")
            return

    console.print("\n")
    console.print(Panel(Markdown(report_md), title="[bold magenta]AI Evaluation & Coaching Report[/bold magenta]"))

    with open(args.report_md, "w", encoding="utf-8") as f:
        f.write(report_md)

    chart_paths = generate_chart_images(export_data, args.assets_dir)
    build_html_and_pdf(report_md, export_data, DEFAULT_REPORT_HTML, args.report_pdf, chart_paths)

    console.print(f"\n[green]Markdown 报告已保存到 {os.path.abspath(args.report_md)}[/green]")
    console.print(f"[green]HTML 报告已保存到 {os.path.abspath(DEFAULT_REPORT_HTML)}[/green]")
    console.print(f"[green]PDF 报告已保存到 {os.path.abspath(args.report_pdf)}[/green]")
    if chart_paths:
        console.print(f"[green]图表资源已保存到 {os.path.abspath(args.assets_dir)}[/green]")

if __name__ == "__main__":
    main()
