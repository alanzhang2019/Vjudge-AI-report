# =============================================================================
#  restart_server.ps1
#  一键脚本：清 __pycache__ 缓存 → 停旧 Flask 进程 → 启动新 web 服务
#
#  用法：
#      powershell -ExecutionPolicy Bypass -File .\restart_server.ps1
#      或双击运行（需先解除执行策略）
# =============================================================================

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "==[1/4] 清理 __pycache__ ..." -ForegroundColor Cyan
Get-ChildItem -Path $ProjectRoot -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    ForEach-Object {
        Write-Host "    rm $($_.FullName)"
        Remove-Item -Recurse -Force $_.FullName
    }
# 兜底：项目根下的 .pyc
Get-ChildItem -Path $ProjectRoot -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue |
    Remove-Item -Force

Write-Host "`n==[2/4] 停止占用 5000 端口的旧 Flask 进程 ..." -ForegroundColor Cyan
$listeners = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
if ($listeners) {
    $oldPids = $listeners | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($p in $oldPids) {
        $proc = Get-Process -Id $p -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "    stop pid=$p  ($($proc.ProcessName), start=$($proc.StartTime))"
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Seconds 1
} else {
    Write-Host "    端口 5000 无监听，跳过"
}

# 兜底：把所有跑 web_app.py 的 python 进程也停掉（按命令行匹配）
Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*web_app.py*" } |
    ForEach-Object {
        $p = $_.ProcessId
        Write-Host "    stop pid=$p  (cmdline matched web_app.py)"
        Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
    }
Start-Sleep -Seconds 1

Write-Host "`n==[3/4] 启动 web 服务 (python -B web_app.py) ..." -ForegroundColor Cyan
$logDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$logFile = Join-Path $logDir ("web_app_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))

# -B 禁用 .pyc 写入，从源头避免再被旧字节码缓存坑到
$args = @("-B", "web_app.py")
$proc = Start-Process -FilePath "python" -ArgumentList $args `
                     -WorkingDirectory $ProjectRoot `
                     -RedirectStandardOutput $logFile `
                     -RedirectStandardError  ($logFile -replace '\.log$', '.err.log') `
                     -WindowStyle Hidden -PassThru
Write-Host "    started pid=$($proc.Id), log=$logFile"

Write-Host "`n==[4/4] 等待端口 5000 监听 ..." -ForegroundColor Cyan
$ok = $false
for ($i = 1; $i -le 30; $i++) {
    Start-Sleep -Seconds 1
    $test = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
    if ($test) {
        $ok = $true
        Write-Host "    [$i s] port 5000 listening (pid=$($test.OwningProcess))" -ForegroundColor Green
        break
    }
    Write-Host "    [$i s] waiting ..."
}
if (-not $ok) {
    Write-Host "    30 秒内端口未就绪，请查看日志: $logFile" -ForegroundColor Red
    exit 1
}

Write-Host "`n✅ 重启完成，访问 http://127.0.0.1:5000" -ForegroundColor Green
Write-Host "   实时日志: Get-Content '$logFile' -Wait" -ForegroundColor Gray
