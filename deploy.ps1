# 部署脚本
$ErrorActionPreference = "Continue"
$LocalFile = "c:\Users\zpy20\Desktop\项目\luoguAI\luogu-api-python\web_app.py"
$LogFile = "c:\Users\zpy20\Desktop\项目\luoguAI\luogu-api-python\deploy.log"
$RemoteHost = "ubuntu@43.163.26.115"
$RemoteTmp = "/tmp/_DEPLOY_TEST.py"
$Container = "luogu-ai-report-luogu-coach"

"" | Out-File $LogFile
Add-Content $LogFile "===== 部署开始 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ====="

# Step 1: 本地 grep
$localCount = (Get-Content $LocalFile | Select-String "DEPLOY-CHECK").Count
Add-Content $LogFile "STEP1 本地 DEPLOY-CHECK 出现次数: $localCount"

# Step 2: SCP
Add-Content $LogFile "STEP2 开始 SCP..."
$scpResult = scp -o StrictHostKeyChecking=no -O $LocalFile "${RemoteHost}:${RemoteTmp}" 2>&1
Add-Content $LogFile "SCP 输出: $scpResult"
Add-Content $LogFile "SCP exit: $LASTEXITCODE"

# Step 3: 远程 md5
Add-Content $LogFile "STEP3 远程验证..."
$ssh3 = ssh -o StrictHostKeyChecking=no $RemoteHost "ls -la $RemoteTmp && md5sum $RemoteTmp" 2>&1
Add-Content $LogFile "REMOTE: $ssh3"
Add-Content $LogFile "ssh3 exit: $LASTEXITCODE"

# Step 4: docker cp
Add-Content $LogFile "STEP4 docker cp..."
$ssh4 = ssh -o StrictHostKeyChecking=no $RemoteHost "docker cp $RemoteTmp $Container`:/app/web_app.py && docker exec -i $Container md5sum /app/web_app.py && docker exec -i $Container grep -c 'DEPLOY-CHECK' /app/web_app.py" 2>&1
Add-Content $LogFile "DOCKER: $ssh4"
Add-Content $LogFile "ssh4 exit: $LASTEXITCODE"

# Step 5: restart
Add-Content $LogFile "STEP5 restart..."
$ssh5 = ssh -o StrictHostKeyChecking=no $RemoteHost "docker restart $Container" 2>&1
Add-Content $LogFile "RESTART: $ssh5"
Add-Content $LogFile "restart exit: $LASTEXITCODE"

# Step 6: sleep
Add-Content $LogFile "STEP6 等待 10s..."
Start-Sleep -Seconds 10

# Step 7: 验证 /api/version
Add-Content $LogFile "STEP7 测试 /api/version..."
try {
    $resp = Invoke-WebRequest -Uri "http://43.163.26.115/api/version" -UseBasicParsing -TimeoutSec 15
    Add-Content $LogFile "STATUS: $($resp.StatusCode)"
    Add-Content $LogFile "BODY: $($resp.Content)"
} catch {
    Add-Content $LogFile "ERR: $($_.Exception.Message)"
}

Add-Content $LogFile "===== 部署结束 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ====="
