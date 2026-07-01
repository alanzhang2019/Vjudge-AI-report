#!/bin/bash
set -e
TS=$(date +%s)
echo "--- backup ---"
sudo docker exec luogu-ai-report-luogu-coach cp /app/web_app.py /tmp/web_app_backup_${TS}.py
echo "  /tmp/web_app_backup_${TS}.py"

echo "--- copy new ---"
sudo docker cp /tmp/web_app.py luogu-ai-report-luogu-coach:/tmp/web_app_new.py
sudo docker exec luogu-ai-report-luogu-coach cp /tmp/web_app_new.py /app/web_app.py

echo "--- syntax check ---"
sudo docker exec luogu-ai-report-luogu-coach python <<'PY'
import py_compile
py_compile.compile('/app/web_app.py', doraise=True)
print('SYNTAX OK')
PY

echo "--- reload (HUP) ---"
sudo docker exec luogu-ai-report-luogu-coach sh -c "pkill -HUP -f gunicorn 2>/dev/null; pkill -HUP -f 'python.*web_app' 2>/dev/null; true"
sleep 2

echo "--- health ---"
curl -sk --max-time 5 http://localhost:5000/ -o /dev/null -w "HTTP %{http_code}\n"
