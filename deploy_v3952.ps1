# v3.9.52 - 简化的手动部署脚本（避免 tar 错误）
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$Server = "ubuntu@43.163.26.115"
$RemoteDir = "/home/ubuntu/luogu-ai-report"
$ProjectRoot = (Get-Location).Path
$TarPath = "C:\TEMP\luogu-pkg.tar.gz"

Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Step 1/5: clean old pkg"
if (Test-Path $TarPath) { Remove-Item $TarPath -Force -ErrorAction SilentlyContinue }

Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Step 2/5: stage files to C:\TEMP"
$staging = "C:\TEMP\luogu-staging-$(Get-Random)"
New-Item -ItemType Directory -Path $staging -Force | Out-Null

$excludeDirs = @('.git', '.source_cache', 'reports', '__pycache__', '.dbg', 'node_modules', '.idea', '.vscode', 'static')
$excludeFiles = @('.env', 'tasks.db', 'luogu-ai-report-pkg.zip', 'luogu-ai-report-pkg.tar.gz', 'deploy-pkg.zip', 'cookies.json')

$robocopyArgs = @(
    "`"$ProjectRoot`"",
    "`"$staging`"",
    "/MIR", "/NJH", "/NJS", "/NC", "/NDL", "/NFL", "/NP"
)
foreach ($d in $excludeDirs) { $robocopyArgs += "/XD"; $robocopyArgs += "`"$d`"" }
foreach ($f in $excludeFiles) { $robocopyArgs += "/XF"; $robocopyArgs += "`"$f`"" }

& robocopy @robocopyArgs | Out-Null
if ($LASTEXITCODE -ge 8) { Write-Host "robocopy failed: $LASTEXITCODE"; exit 1 }

# Clean up
Get-ChildItem -Path $staging -Recurse -Include *.pdf,*.pyc -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Step 3/5: create tar.gz (use 7z if available, else use Python)"

# Method 1: 7z if available
$7zPath = (Get-Command 7z -ErrorAction SilentlyContinue).Source
if ($7zPath) {
    Write-Host "  using 7z"
    $stagingAbs = (Resolve-Path $staging).Path
    & $7zPath a -ttar -so "$stagingAbs\*" 2>&1 | & $7zPath a -tgzip -si "$TarPath" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Host "  7z failed, falling back to tar"; }
}

# Method 2: tar with explicit file enumeration (avoid glob issues)
if (-not (Test-Path $TarPath) -or (Get-Item $TarPath).Length -lt 100000) {
    Write-Host "  using tar with -T file list"
    $fileList = Join-Path $staging "files.txt"
    # Use cmd.exe dir for reliable file enumeration
    cmd /c "dir /b /s /a-d `"$staging`"" | ForEach-Object {
        $f = $_.Trim()
        if ($f) {
            # Make path relative to staging
            $rel = $f -replace [regex]::Escape($staging + "\"), ""
            $rel = $rel -replace "\\", "/"
            "$rel"
        }
    } | Out-File -FilePath $fileList -Encoding ASCII

    $lineCount = (Get-Content $fileList | Measure-Object -Line).Lines
    Write-Host "  file count: $lineCount"

    $stagingAbs = (Resolve-Path $staging).Path
    Push-Location $stagingAbs
    try {
        # Use tar with --force-local to avoid C:\ path issues
        $env:TAR_OPTIONS = "--force-local"
        cmd /c "tar -czf `"$TarPath`" --force-local -T `"$fileList`" 2>&1"
    } finally {
        Pop-Location
    }
    Remove-Item $fileList -Force -ErrorAction SilentlyContinue
}

if (-not (Test-Path $TarPath)) { Write-Host "tar creation failed"; exit 1 }
$size = [math]::Round((Get-Item $TarPath).Length / 1MB, 2)
Write-Host "  pkg: $TarPath ($size MB)" -ForegroundColor Green

Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Step 4/5: scp to server"
& scp $TarPath "${Server}:${RemoteDir}/luogu-ai-report-pkg.tar.gz"
if ($LASTEXITCODE -ne 0) { Write-Host "scp failed"; exit 1 }

Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Step 5/5: remote deploy"
& ssh $Server "cd $RemoteDir; bash deploy.sh --from-zip luogu-ai-report-pkg.tar.gz"
if ($LASTEXITCODE -ne 0) { Write-Host "remote deploy failed"; exit 1 }

# Cleanup
Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $TarPath -Force -ErrorAction SilentlyContinue

Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ✓ deploy OK" -ForegroundColor Green
