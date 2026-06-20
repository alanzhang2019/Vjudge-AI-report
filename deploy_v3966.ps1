# v3.9.66 - 部署脚本 (use Python for tar)
# 变更点：GESP 报告注入 8 级知识地图（不再注入 NOI 4 级树）
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Server = "ubuntu@43.163.26.115"
$RemoteDir = "/home/ubuntu/luogu-ai-report"
$ProjectRoot = (Get-Location).Path
$TarPath = "C:\TEMP\luogu-pkg-v3966.tar.gz"

Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Step 1/6: clean old pkg"
if (Test-Path $TarPath) { Remove-Item $TarPath -Force -ErrorAction SilentlyContinue }

Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Step 2/6: stage files to C:\TEMP"
$staging = "C:\TEMP\luogu-staging-$(Get-Random)"
if (Test-Path $staging) { Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue }
New-Item -ItemType Directory -Path $staging -Force | Out-Null

$excludeDirs = @('.git', '.source_cache', 'reports', '__pycache__', '.dbg', 'node_modules', '.idea', '.vscode', 'static')
$excludeFiles = @('.env', 'tasks.db', 'luogu-ai-report-pkg.zip', 'luogu-ai-report-pkg.tar.gz', 'deploy-pkg.zip', 'cookies.json', 'luogu-pkg-v3966.tar.gz')

$robocopyArgs = @(
    "`"$ProjectRoot`"",
    "`"$staging`"",
    "/MIR", "/NJH", "/NJS", "/NC", "/NDL", "/NFL", "/NP"
)
foreach ($d in $excludeDirs) { $robocopyArgs += "/XD"; $robocopyArgs += "`"$d`"" }
foreach ($f in $excludeFiles) { $robocopyArgs += "/XF"; $robocopyArgs += "`"$f`"" }

& robocopy @robocopyArgs | Out-Null
if ($LASTEXITCODE -ge 8) { Write-Host "robocopy failed: $LASTEXITCODE"; exit 1 }

# 清理临时测试/调试文件
Get-ChildItem -Path $staging -Recurse -Include *.pdf,*.pyc -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $staging -Recurse -File -Filter "_smoke_v*.py" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $staging -Recurse -File -Filter "_debug*.py" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $staging -Recurse -File -Filter "_test_*.py" -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Step 3/6: create tar.gz via Python"
$pythonCmd = @"
import os, sys, tarfile
staging = r'$staging'
out = r'$TarPath'
with tarfile.open(out, 'w:gz') as tf:
    for root, dirs, files in os.walk(staging):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git')]
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, staging).replace(os.sep, '/')
            tf.add(full, arcname=rel)
print('OK', os.path.getsize(out), 'bytes')
"@
$pythonCmd | & python -
if ($LASTEXITCODE -ne 0) { Write-Host "python tar failed"; exit 1 }

if (-not (Test-Path $TarPath)) { Write-Host "tar creation failed"; exit 1 }
$size = [math]::Round((Get-Item $TarPath).Length / 1MB, 2)
Write-Host "  pkg: $TarPath ($size MB)" -ForegroundColor Green

Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Step 4/6: scp to server"
& scp $TarPath "${Server}:${RemoteDir}/luogu-ai-report-pkg.tar.gz"
if ($LASTEXITCODE -ne 0) { Write-Host "scp failed"; exit 1 }

Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Step 5/6: remote deploy"
& ssh $Server "cd $RemoteDir; bash deploy.sh --from-zip luogu-ai-report-pkg.tar.gz"
if ($LASTEXITCODE -ne 0) { Write-Host "remote deploy failed"; exit 1 }

Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Step 6/6: health check on server"
& ssh $Server "curl -s -o /dev/null -w 'health: %{http_code}\n' http://127.0.0.1:5000/health 2>&1 || echo 'no /health, try /'"

# Cleanup
Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $TarPath -Force -ErrorAction SilentlyContinue

Write-Host "[$(Get-Date -Format 'HH:mm:ss')] deploy v3.9.66 OK" -ForegroundColor Green
