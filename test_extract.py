"""v3.9.32 · Test _extract_achievements_from_report on 李颖天 report.md"""
import re
import sys
sys.path.insert(0, '.')
from web_app import _extract_achievements_from_report

with open(r'C:\Users\zpy20\Desktop\项目\luoguAI\luogu-api-python\report_72dd5efa.md', encoding='utf-8') as f:
    md = f.read()
result = _extract_achievements_from_report(md)
print('six_dim:', result.get('six_dim'))
print('ai_score_thousand:', result.get('ai_score_thousand'))
print('ai_score_label:', result.get('ai_score_label'))
print('mistakes count:', len(result.get('mistakes') or []))
