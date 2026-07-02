# deploy_fix.ps1
$ErrorActionPreference = "Continue"
$LocalDir = (Get-Location).Path
$RemoteHost = "ubuntu@43.163.26.115"
$Container = "luogu-ai-report-luogu-coach"

Write-Host "LocalDir: $LocalDir"

$Files = @("web_app.py", "task_store.py", "ai_tutor_jobs.py")

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

Write-Host "--- restart ---"
& ssh -o StrictHostKeyChecking=no $RemoteHost "docker restart $Container"
Write-Host "--- wait 12s ---"
Start-Sleep -Seconds 12

Write-Host "--- verify (rate-limited popup text) ---"
& scp -o StrictHostKeyChecking=no -O (Join-Path $LocalDir "_verify_msg.py") "${RemoteHost}:/tmp/_verify_msg.py"
& ssh -o StrictHostKeyChecking=no $RemoteHost "docker cp /tmp/_verify_msg.py ${Container}:/app/_verify_msg.py && docker exec $Container python /app/_verify_msg.py"

Write-Host "--- version via wget 80 ---"
& ssh -o StrictHostKeyChecking=no $RemoteHost "docker exec $Container wget -q -O- http://127.0.0.1:5000/api/version 2>&1 || echo 'wget not available'"
Write-Host "DONE"
