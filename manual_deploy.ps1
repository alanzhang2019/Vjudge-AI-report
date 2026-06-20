# v3.9.48 manual deploy wrapper (ASCII only to avoid PowerShell ISE encoding bug)
$ErrorActionPreference = "Stop"

# Set console to UTF-8 to handle Chinese paths correctly
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$Server = "ubuntu@43.163.26.115"
$RemoteDir = "/home/ubuntu/luogu-ai-report"
$ProjectRoot = (Get-Location).Path
$ZipPath = "C:\Users\zpy20\Desktop\luogu-ai-report-pkg.zip"

Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ZipPath = $ZipPath"
Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ProjectRoot = $ProjectRoot"

# 1. clean old zip
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }

# 2. stage (use C:\TEMP to avoid Chinese path encoding issues)
$staging = "C:\TEMP\luogu-staging-$(Get-Random)"
New-Item -ItemType Directory -Path $staging -Force | Out-Null

$excludeDirs = @('.git', '.source_cache', 'reports', '__pycache__', '.dbg', 'node_modules', '.idea', '.vscode')
$excludeFiles = @('.env', 'tasks.db', 'luogu-ai-report-pkg.zip', 'deploy-pkg.zip', 'cookies.json')

$robocopyArgs = @(
    "`"$ProjectRoot`"",
    "`"$staging`"",
    "/MIR", "/NJH", "/NJS", "/NC", "/NDL", "/NFL", "/NP"
)
foreach ($d in $excludeDirs) { $robocopyArgs += "/XD"; $robocopyArgs += "`"$d`"" }
foreach ($f in $excludeFiles) { $robocopyArgs += "/XF"; $robocopyArgs += "`"$f`"" }

& robocopy @robocopyArgs | Out-Null
# robocopy exit codes 0-7 = success, 8+ = error
if ($LASTEXITCODE -ge 8) {
    Write-Host "robocopy exit code: $LASTEXITCODE"
    & robocopy @robocopyArgs
    exit 1
}

Get-ChildItem -Path $staging -Recurse -Include *.pdf -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $staging -Recurse -Include *.pyc -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

$PkgPath = [System.IO.Path]::ChangeExtension($ZipPath, '.tar.gz')
$oldLocation = Get-Location
Set-Location $staging
& tar -czf $PkgPath -- *
Set-Location $oldLocation
Remove-Item -Recurse -Force $staging

$size = [math]::Round((Get-Item $PkgPath).Length / 1MB, 2)
Write-Host "[$(Get-Date -Format 'HH:mm:ss')] packaged: $PkgPath ($size MB)" -ForegroundColor Green

# 3. scp
Write-Host "[$(Get-Date -Format 'HH:mm:ss')] scp to $Server ..."
& scp $PkgPath "${Server}:${RemoteDir}/luogu-ai-report-pkg.tar.gz"
if ($LASTEXITCODE -ne 0) { Write-Host "scp failed"; exit 1 }

# 4. remote deploy
Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ssh deploy.sh --from-zip ..."
& ssh $Server "cd $RemoteDir; bash deploy.sh --from-zip luogu-ai-report-pkg.tar.gz"
if ($LASTEXITCODE -ne 0) { Write-Host "remote deploy failed"; exit 1 }

Write-Host "[$(Get-Date -Format 'HH:mm:ss')] deploy OK" -ForegroundColor Green
