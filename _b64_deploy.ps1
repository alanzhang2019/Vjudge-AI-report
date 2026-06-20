$ErrorActionPreference = "Continue"
$LocalFile = "web_app.py"
$LogFile   = "_b64_deploy.log"
$B64Path   = "_b64.txt"
$Remote    = "ubuntu@43.163.26.115"
$Container = "luogu-ai-report-luogu-coach"
$RemoteTmp = "/tmp/_web_app_b64.py"

"" | Out-File $LogFile -Encoding utf8
Add-Content $LogFile "===== DEPLOY START ====="

Add-Content $LogFile "STEP1: local read + base64"
if (-not (Test-Path $LocalFile)) { Add-Content $LogFile "ERR: local file missing"; exit 1 }
$bytes = [System.IO.File]::ReadAllBytes($LocalFile)
$localMd5 = (Get-FileHash $LocalFile -Algorithm MD5).Hash
Add-Content $LogFile ("localSize: " + $bytes.Length)
Add-Content $LogFile ("localMd5:  " + $localMd5)
$b64 = [Convert]::ToBase64String($bytes)
[System.IO.File]::WriteAllText($B64Path, $b64, [System.Text.Encoding]::ASCII)
Add-Content $LogFile ("b64Length: " + $b64.Length)

Add-Content $LogFile "STEP2: ssh base64 decode to remote"
$b64Content = Get-Content $B64Path -Raw
$step2 = $b64Content | & ssh -o StrictHostKeyChecking=no $Remote "base64 -d > $RemoteTmp" 2>&1
$ec2 = $LASTEXITCODE
Add-Content $LogFile ("ssh2-out: " + $step2)
Add-Content $LogFile ("ssh2-exit: " + $ec2)
if ($ec2 -ne 0) { Add-Content $LogFile "ERR: Step 2 failed"; exit 1 }

Add-Content $LogFile "STEP3: verify remote file"
$step3 = & ssh -o StrictHostKeyChecking=no $Remote "ls -la $RemoteTmp; md5sum $RemoteTmp" 2>&1
Add-Content $LogFile ("ssh3-out: " + $step3)
if ($LASTEXITCODE -ne 0) { Add-Content $LogFile "ERR: Step 3 failed"; exit 1 }

Add-Content $LogFile "STEP4: docker cp + verify"
$cmd4 = "docker cp $RemoteTmp ${Container}:/app/web_app.py; " +
        "if [ `$? -eq 0 ]; then " +
        "docker exec -i $Container md5sum /app/web_app.py; " +
        "docker exec -i $Container grep -c DEPLOY-CHECK /app/web_app.py; " +
        "fi"
$step4 = & ssh -o StrictHostKeyChecking=no $Remote $cmd4 2>&1
Add-Content $LogFile ("ssh4-out: " + $step4)
if ($LASTEXITCODE -ne 0) { Add-Content $LogFile "ERR: Step 4 failed"; exit 1 }

Add-Content $LogFile "STEP5: py_compile + restart"
$cmd5 = "docker exec -i $Container python3 -m py_compile /app/web_app.py; " +
        "if [ `$? -eq 0 ]; then docker restart $Container; fi"
$step5 = & ssh -o StrictHostKeyChecking=no $Remote $cmd5 2>&1
Add-Content $LogFile ("ssh5-out: " + $step5)
if ($LASTEXITCODE -ne 0) { Add-Content $LogFile "ERR: Step 5 failed"; exit 1 }

Add-Content $LogFile "STEP6: wait 10s"
Start-Sleep -Seconds 10

Add-Content $LogFile "STEP7: final verify"
$step7 = & ssh -o StrictHostKeyChecking=no $Remote "docker exec -i $Container grep -c DEPLOY-CHECK /app/web_app.py" 2>&1
Add-Content $LogFile ("ssh7-out: " + $step7)

Add-Content $LogFile "STEP8: /api/version"
try {
    $resp = Invoke-WebRequest -Uri "http://43.163.26.115/api/version" -UseBasicParsing -TimeoutSec 15
    Add-Content $LogFile ("STATUS: " + $resp.StatusCode)
    Add-Content $LogFile ("BODY: " + $resp.Content)
} catch {
    Add-Content $LogFile ("ERR: " + $_.Exception.Message)
}

Add-Content $LogFile "===== DEPLOY END ====="
Write-Host ("DONE - log: " + $LogFile)
