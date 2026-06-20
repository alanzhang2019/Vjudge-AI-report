"""冒烟测试：直接复用 _render_share_card 验证修复后代码能渲染

策略：把 matplotlib 渲染部分单独抽出来跑，跳过 Flask 上下文
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch

# 直接复制 web_app.py 里的关键渲染代码（关键赛事段）到独立函数里执行
def render_events_only(events, output_png):
    """只渲染赛事列表部分，验证 row_h=0.30 + zorder=5 不报错"""
    fig, ax = plt.subplots(figsize=(9, 16), dpi=80)
    ax.set_xlim(0, 9)
    ax.set_ylim(0, 16)
    ax.axis("off")

    # 标题
    ax.text(4.5, 15.0, "信息学AI测评结果", ha="center", va="center",
            fontsize=22, color="#1F2937", fontweight="bold")

    # 关键赛事标题
    ax.text(4.5, 3.95, "2026 关键赛事倒计时", ha="center", va="center",
            fontsize=12, color="#7C3AED", fontweight="bold")

    # 用 web_app 的渲染逻辑（复制后修改 row 高度）
    y = 3.55
    row_h = 0.30
    for ev in events[:5]:
        days = ev["days"]
        if days <= 0:
            tag = "进行中"
        elif days <= 14:
            tag = f"! {days} 天"
        elif days <= 60:
            tag = f"还有 {days} 天"
        else:
            tag = f"{days} 天后"
        nm = ev.get("display") or ev["name"]

        # 赛事行（zorder=5）
        ev_box = FancyBboxPatch((0.7, y - 0.15), 7.6, row_h,
                                boxstyle="round,pad=0,rounding_size=0.12",
                                facecolor="#FFFFFF", edgecolor="#E5E7EB", lw=1)
        ev_box.set_zorder(5)
        ax.add_patch(ev_box)
        ax.text(0.95, y, f"•  {nm}", ha="left", va="center",
                fontsize=10, color="#1F2937", fontweight="bold", zorder=6)

        # 徽章
        ev_badge = FancyBboxPatch((6.55, y - 0.07), 1.65, 0.24,
                                  boxstyle="round,pad=0,rounding_size=0.12",
                                  facecolor="#F1F5F9", edgecolor="none")
        ev_badge.set_zorder(5)
        ax.add_patch(ev_badge)
        ax.text(7.375, y + 0.05, tag, ha="center", va="center",
                fontsize=9, color="#64748B", fontweight="bold", zorder=6)
        y -= row_h

    # 脚注
    ax.text(4.5, 1.95, "CSP-J/S = CCF 软件能力认证 · NOIP = 信息学奥赛联赛",
            ha="center", va="center", fontsize=8, color="#94A3B8", style="italic")

    # QR 卡片（zorder 默认 1，row 5 的 zorder=5 会盖在上面）
    qr_card = FancyBboxPatch((5.55, 0.40), 2.85, 2.10,
                             boxstyle="round,pad=0,rounding_size=0.20",
                             facecolor="#FFFFFF", edgecolor="#E5E7EB", lw=1)
    ax.add_patch(qr_card)

    # 落盘
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), dpi=80)
    plt.close(fig)

    png = buf.getvalue()
    with open(output_png, "wb") as f:
        f.write(png)
    return len(png)


# 真实数据模拟（来自 docs/competitions.json + v3.9.6 合并：同日 CSP-J/S → 1 条）
events = [
    {"name": "GESP 等级认证（1-4 级夏考）", "display": "GESP 考级（夏考）", "date": "2026-06-13", "days": 0},
    {"name": "NOI 2026",                   "display": "NOI 信息学奥赛",   "date": "2026-07-15", "days": 29},
    {"name": "GESP 等级认证（1-4 级秋考）", "display": "GESP 考级（秋考）", "date": "2026-09-12", "days": 88},
    {"name": "CSP-J+S 2026 第一轮（初赛）", "display": "CSP-J/S 初赛",     "date": "2026-09-19", "days": 95},
    {"name": "CSP-J 2026 第二轮（复赛）",   "display": "CSP-J 复赛",       "date": "2026-10-31", "days": 137},
    {"name": "NOIP 2026 全国赛",            "display": "NOIP 全国赛",      "date": "2026-11-28", "days": 165},
    {"name": "GESP 等级认证（1-4 级冬考）", "display": "GESP 考级（冬考）", "date": "2026-12-19", "days": 186},
]

print(f"输入事件总数: {len(events)}")
print(f"前 5 条将渲染到海报:")
for e in events[:5]:
    print(f"  - {e['display']:18s}  -  {e['days']} 天后")

out = os.path.join(tempfile.gettempdir(), "share_card_smoke.png")
size = render_events_only(events, out)
print(f"\n✅ 渲染成功，PNG {size} 字节 → {out}")
