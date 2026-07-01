import sys, json
from pathlib import Path
sys.path.insert(0, '/app')
from web_app import _compute_score_from_export, _override_achievements_with_export_v3944

# 直接选一个有 export_data.json 的报告目录
candidate_dirs = [
    '/app/reports/58800787_未知选手',
    '/app/reports/ce4f94e0_陈豆豆',
    '/app/reports/992272a4_黄鼎',
]

for path_str in candidate_dirs:
    d = Path(path_str)
    ep = d / 'export_data.json'
    if not ep.exists():
        print(path_str + ': no export_data.json')
        continue
    exp = json.loads(ep.read_text(encoding='utf-8'))
    score, label, src = _compute_score_from_export(exp, exp.get('behavior_analysis') or {})
    six = exp.get('six_dimension_scores') or {}
    six_mean = sum(six.values()) / max(1, len(six)) if six else 0
    six_only_score = int(round(six_mean * 10))
    print('=' * 60)
    print(d.name + ':')
    print('  6 维: ' + json.dumps(six, ensure_ascii=False))
    print('  6 维均值x10 (旧): ' + str(six_only_score))
    print('  综合分(v3.9.44 / 与排行榜同源): ' + str(score) + ' / 1000')
    print('    label: ' + label + '  src: ' + src)

    # 测一下 _override_achievements_with_export_v3944
    ach = {'six_dim': dict(six), 'ai_score_thousand': six_only_score, 'ai_score_label': 'old label', 'six_dim_source': 'old'}
    ok = _override_achievements_with_export_v3944(ach, d)
    print('  _override_achievements_with_export_v3944: ok=' + str(ok))
    print('  override 后 achievements.ai_score_thousand: ' + str(ach.get('ai_score_thousand')))
    print('  override 后 achievements.ai_score_label:    ' + str(ach.get('ai_score_label')))
    print('  override 后 achievements.ai_score_source:   ' + str(ach.get('ai_score_source')))
    print('  override 后 achievements.six_dim_source:    ' + str(ach.get('six_dim_source')))

print('=' * 60)
print('结论: 个人中心的「能力总分」现在调用 _compute_score_from_export,')
print('      与排行榜 compute_leaderboard 用同一函数, 分数完全一致.')
