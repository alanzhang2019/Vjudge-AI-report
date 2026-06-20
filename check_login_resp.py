"""v3.9.52 · 验证密码登录响应内容"""
import re
import sys
html = open('/tmp/login_resp.html').read()
# Find validation_result block
m = re.search(r'<div class="mt-2 rounded-md p-2 text-sm[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
if m:
    block = m.group(1)
    # Get title and message
    title = re.search(r'<p class="font-semibold">([^<]+)</p>', block)
    msg = re.search(r'<p>([^<]+)</p>', block)
    if title:
        print(f"Title: {title.group(1).strip()}")
    if msg:
        print(f"Message: {msg.group(1).strip()}")
else:
    # Look for any error/success block
    for line in html.split('\n'):
        if '登录' in line or '失败' in line or '成功' in line:
            stripped = line.strip()[:200]
            if stripped:
                print(f"  {stripped}")
