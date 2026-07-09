# deploy_fix.ps1
# v3.11.31b · 一次部署 web_app.py + 全部依赖 .py, 重建容器 (让 .env 注入生效)
$ErrorActionPreference = "Continue"
$LocalDir = (Get-Location).Path
$RemoteHost = "ubuntu@43.163.26.115"
$Container = "luogu-ai-report-luogu-coach"
$ComposeDir = "/home/ubuntu/luogu-ai-report"

Write-Host "LocalDir: $LocalDir"

# v3.11.31c · web_app.py 的所有本地依赖, 一起 deploy 避免漏模块
# (注: docker compose build 时 Dockerfile 会 COPY host 当前目录进 image,
#  所以漏 deploy 某个 .py 会导致 image 含老版本, 跟容器/host 不一致)
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
    "admin_students.py",
    "elo_ranking.py"
)

foreach ($f in $Files) {
    if (-not (Test-Path (Join-Path $LocalDir $f))) {
        Write-Host "[skip] $f not found locally"
        continue
    }
    $Local = Join-Path $LocalDir $f
    # v3.11.31c · scp 必须到 host 项目目录 ($ComposeDir), 不是 /tmp
    # (因为 docker compose build --no-cache 会 COPY $ComposeDir 进 image,
    #  如果只 scp 到 /tmp 然后 docker cp, build 时还是用 host 旧版,
    #  启动后容器内文件被 image 覆盖 → 所有改动失效)
    $Remote = "$ComposeDir/$f"
    Write-Host "--- deploy $f to $Remote ---"
    & scp -o StrictHostKeyChecking=no -O "$Local" "${RemoteHost}:${Remote}"
}

Write-Host "--- rebuild image + container (让 .env + .py 改动都注入) ---"
# v3.11.31c · 必须先 docker compose build --no-cache, 否则 image 不会重建,
# 容器重启后会被 image 里的老 .py 覆盖 (Dockerfile COPY 时打进去的)
# v3.11.31b · 必须 docker compose up -d, 不能仅 docker restart
# (后者 env 已被冻结, .env 改动不会生效)
& ssh -o StrictHostKeyChecking=no $RemoteHost "docker stop $Container 2>&1; docker rm $Container 2>&1; cd $ComposeDir && docker compose build --no-cache 2>&1 | tail -10; docker compose up -d 2>&1"
Write-Host "--- wait 25s (build + start) ---"
Start-Sleep -Seconds 25

Write-Host "--- verify (rate-limited popup text) ---"
& scp -o StrictHostKeyChecking=no -O (Join-Path $LocalDir "_verify_msg.py") "${RemoteHost}:/tmp/_verify_msg.py"
& ssh -o StrictHostKeyChecking=no $RemoteHost "docker cp /tmp/_verify_msg.py ${Container}:/app/_verify_msg.py && docker exec $Container python /app/_verify_msg.py"

Write-Host "--- version via wget 80 ---"
& ssh -o StrictHostKeyChecking=no $RemoteHost "docker exec $Container wget -q -O- http://127.0.0.1:5000/api/version 2>&1 || echo 'wget not available'"
Write-Host "--- AI_TUTOR_BACKEND ---"
& ssh -o StrictHostKeyChecking=no $RemoteHost "docker exec $Container printenv AI_TUTOR_BACKEND"
Write-Host "DONE"
