#!/bin/bash
echo "=== 1) 排行榜 JSON（看 display_name 格式）==="
curl -s 'http://127.0.0.1:5000/api/leaderboard?stage=all&limit=8' | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    if isinstance(d, dict) and 'data' in d:
        d = d['data']
    for e in d[:8]:
        print(f'  #{e.get(\"rank\")} {e.get(\"display_name\")} - {e.get(\"grade\")} · {e.get(\"province\")} · {e.get(\"school\")} · {e.get(\"score\")}/1000')
except Exception as ex:
    print('parse error:', ex)
"

echo ""
echo "=== 2) 首页 HTML（看 leaderboard Top 3 + 已脱敏 badge 文字）==="
curl -s http://127.0.0.1:5000/ | grep -oE '(童|张|王|李|刘|陈|杨|赵|周|吴|徐|孙|胡|朱|高|林|何|郭|马|罗|梁|宋|郑|谢|韩|唐|冯|于|董|萧|程|曹|袁|邓|许|傅|沈|曾|彭|吕|苏|卢|蒋|蔡|贾|丁|魏|薛|叶|阎|余|潘|杜|戴|夏|钟|汪|田|任|姜|范|方|石|姚|谭|廖|邹|熊|金|陆|郝|孔|白|崔|康|毛|邱|秦|江|史|顾|侯|邵|孟|龙|万|段|雷|钱|汤|尹|黎|易|常|武|乔|贺|赖|龚|文)·U[0-9]+' | sort -u | head -20

echo ""
echo "=== 3) 知识树 SVG（左/右交替验证）==="
# 拿一份最新的学员报告 HTML 验证知识树
LATEST_DIR=$(ls -td /home/ubuntu/luogu-ai-report/reports/*/ | head -1)
echo "  latest dir: $LATEST_DIR"
if [ -d "$LATEST_DIR" ]; then
    HTML_FILE=$(find "$LATEST_DIR" -name 'parent_subscribe.html' -o -name 'report.html' -o -name 'index.html' 2>/dev/null | head -1)
    if [ -n "$HTML_FILE" ]; then
        echo "  html: $HTML_FILE"
        # 找第一个 SVG viewBox 和分类 chip 的 x 坐标
        grep -oE '<rect x="[0-9.]+" y="[0-9.]+" width="[0-9.]+" height="16"' "$HTML_FILE" 2>/dev/null | head -10
    fi
fi
echo ""
echo "=== 4) 验证最大子目录 (大齐 1752947) ==="
if [ -d "/home/ubuntu/luogu-ai-report/reports" ]; then
    ls -d /home/ubuntu/luogu-ai-report/reports/*/ 2>/dev/null | xargs -I{} basename {} | head -10
fi
