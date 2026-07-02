# deploy_fix.ps1
# v3.11.31b · 一次部署 web_app.py + 全部依赖 .py, 重建容器 (让 .env 注入生效)
$ErrorActionPreference = "Continue"
$LocalDir = (Get-Location).Path
$RemoteHost = "ubuntu@43.163.26.115"
$Container = "luogu-ai-report-luogu-coach"
$ComposeDir = "/home/ubuntu/luogu-ai-report"

Write-Host "LocalDir: $LocalDir"

# v3.11.31b · web_app.py 的所有本地依赖, 一起 deploy 避免漏模块
$Files = @(
    "web_app.py",
    "task_store.py",
    "ai_tutor_jobs.py",
    "env_loader.py",
    "luogu_evaluator.py",
    "behavior_analyzer.py",
    "syllabus_matcher.py",
    "problemset_index.py",
    "html_source_parser.py",
)

foreach ($f in $Files) {
    if (-not (Test-Path (Join-Path $LocalDir $f))) {
        Write-Host "[skip] $f not found locally"
        continue
    }
    $Local = Join-Path $LocalDir $f
    $Remote = "/tmp/_DEPLOY_$f"
    Write-Host "--- deploy $f ---"
    & scp -o StrictHostKeyChecking=no -O "$Local" "${RemoteHost}:${Remote}"
    & ssh -o StrictHostKeyChecking=no $RemoteHost "docker cp $Remote ${Container}:/app/$f && rm $Remote"
}

Write-Host "--- rebuild container (让 .env 注入生效) ---"
# v3.11.31b · 必须 docker compose up -d, 不能仅 docker restart
# (后者 env 已被冻结, .env 改动不会生效)
& ssh -o StrictHostKeyChecking=no $RemoteHost "docker stop $Container 2>&1; docker rm $Container 2>&1; cd $ComposeDir && docker compose up -d 2>&1"
Write-Host "--- wait 18s ---"
Start-Sleep -Seconds 18

Write-Host "--- verify (rate-limited popup text) ---"
& scp -o StrictHostKeyChecking=no -O (Join-Path $LocalDir "_verify_msg.py") "${RemoteHost}:/tmp/_verify_msg.py"
& ssh -o StrictHostKeyChecking=no $RemoteHost "docker cp /tmp/_verify_msg.py ${Container}:/app/_verify_msg.py && docker exec $Container python /app/_verify_msg.py"

Write-Host "--- version via wget 80 ---"
& ssh -o StrictHostKeyChecking=no $RemoteHost "docker exec $Container wget -q -O- http://127.0.0.1:5000/api/version 2>&1 || echo 'wget not available'"
Write-Host "--- AI_TUTOR_BACKEND ---"
& ssh -o StrictHostKeyChecking=no $RemoteHost "docker exec $Container printenv AI_TUTOR_BACKEND"
Write-Host "DONE"
