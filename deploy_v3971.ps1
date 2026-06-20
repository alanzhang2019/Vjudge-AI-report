# deploy_v3971.ps1 - v3.9.71 一键部署（基于 v3970 改）
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Server = "ubuntu@43.163.26.115"
$RemoteDir = "/home/ubuntu/luogu-ai-report"
$ProjectRoot = (Get-Location).Path
$StagingBase = Join-Path $env:USERPROFILE "_deploy_pkg_v3971"
$TarPath = Join-Path $env:USERPROFILE "luogu-pkg-v3971.tar.gz"

Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Step 1/5: clean old pkg" -ForegroundColor Cyan
if (Test-Path $TarPath) { Remove-Item $TarPath -Force -ErrorAction SilentlyContinue }
if (Test-Path $StagingBase) { Remove-Item $StagingBase -Recurse -Force -ErrorAction SilentlyContinue }
New-Item -ItemType Directory -Path $StagingBase -Force | Out-Null

Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Step 2/5: stage files to $StagingBase" -ForegroundColor Cyan
$staging = $StagingBase

$excludeDirs = @('.git', '.source_cache', 'reports', '__pycache__', '.dbg', 'node_modules', '.idea', '.vscode', 'static', 'luogu_report_assets', 'docs', 'assets')
$excludeFiles = @('.env', 'tasks.db', 'luogu-ai-report-pkg.zip', 'luogu-ai-report-pkg.tar.gz', 'deploy-pkg.zip', 'cookies.json', 'luogu-pkg-v*.tar.gz', 'luogu_killswitch.json', 'luogu_killswitch.json.tmp', '_*.log', '_*.txt', '_*.py', '_COMMIT_MSG.txt', '_deploy_pkg_v*', 'deploy_v*.ps1', '*.pdf', '*.zip', '*.png', '*.jpg', '*.jpeg', '*.gif', '*.swp', 'luogu_export.json', 'luogu_coach_report.html', 'luogu-ai-coach.zip', '*.db', '*.sqlite', '*.sqlite3', '*.pyc', '*.pptx', '*.docx', '*.xlsx', 'test_*.png', 'out.txt', 'sc.png', 'deploy-pkg', 'verify_deploy.sh', 'remote_check.sh', 'sample_*', 'check_login_resp.py', 'pw_login.py', 'manual_deploy.ps1')

$robocopyArgs = @(
    "`"$ProjectRoot`"",
    "`"$staging`"",
    "/MIR", "/NJH", "/NJS", "/NC", "/NDL", "/NFL", "/NP"
)
foreach ($d in $excludeDirs) { $robocopyArgs += "/XD"; $robocopyArgs += "`"$d`"" }
foreach ($f in $excludeFiles) { $robocopyArgs += "/XF"; $robocopyArgs += "`"$f`"" }

& robocopy @robocopyArgs | Out-Null
if ($LASTEXITCODE -ge 8) { Write-Error "robocopy 失败"; exit 1 }

# 额外清理大文件
Get-ChildItem -Path $staging -Recurse -Include *.pdf,*.pyc,*.log,*.tmp -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Step 3/5: tar.gz to $TarPath" -ForegroundColor Cyan
& tar -czf $TarPath -C $staging .
$size = [math]::Round((Get-Item $TarPath).Length / 1MB, 2)
Write-Host "  打包完成: $size MB" -ForegroundColor Green

Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Step 4/5: scp to $Server" -ForegroundColor Cyan
scp $TarPath "${Server}:${RemoteDir}/luogu-pkg-v3971.tar.gz"
if ($LASTEXITCODE -ne 0) { Write-Error "scp 失败"; exit 1 }

Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Step 5/5: deploy.sh --from-zip on server" -ForegroundColor Cyan
ssh $Server "cd $RemoteDir && chmod +x deploy.sh && ./deploy.sh --from-zip luogu-pkg-v3971.tar.gz"
if ($LASTEXITCODE -ne 0) { Write-Error "部署失败"; exit 1 }

Write-Host "`n[$(Get-Date -Format 'HH:mm:ss')] ✅ v3.9.71 部署完成" -ForegroundColor Green
