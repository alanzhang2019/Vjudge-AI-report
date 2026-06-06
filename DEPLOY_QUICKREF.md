# 一键部署说明

本项目提供两条**幂等可重入**的部署脚本：

## 🎯 客户端（Windows PowerShell）

[`deploy.ps1`](deploy.ps1) — 在本地运行，一行命令完成 **打包 → scp → 服务器部署**。

```powershell
# 完整部署（推荐：先看一遍）
.\deploy.ps1

# 其他模式
.\deploy.ps1 -Status         # 看服务状态
.\deploy.ps1 -Logs           # 跟踪日志
.\deploy.ps1 -Restart        # 改了 .env 后重启
.\deploy.ps1 -ResetPassword  # 重置 admin 密码
.\deploy.ps1 -Rollback       # 回滚到上一个备份
.\deploy.ps1 -OnlyZip        # 只打包，不上传
.\deploy.ps1 -Server user@1.2.3.4 -RemoteDir /path/to/app   # 自定义服务器
```

## 🐚 服务器端（Linux bash）

[`deploy.sh`](deploy.sh) — 部署在服务器上，可独立运行。

```bash
chmod +x deploy.sh

./deploy.sh                  # 自动检测（zip 优先，否则 git pull）
./deploy.sh --from-zip       # 从 deploy-pkg.zip 部署
./deploy.sh --from-zip /tmp/pkg.zip
./deploy.sh --pull           # 拉取 git 最新代码
./deploy.sh --status         # 看服务状态
./deploy.sh --logs           # 跟日志
./deploy.sh --restart        # 改了 .env 后重启（down + up -d）
./deploy.sh --reset-password # 重置 admin 密码
./deploy.sh --rollback       # 回滚到最近备份
./deploy.sh --help
```

## 📋 第一次完整部署

```powershell
# === Windows 客户端 ===
# 1) 推项目到 git 远程（一次性）
cd C:\Users\zpy20\Desktop\项目\luoguAI\luogu-AI-report
git init
git add .
git commit -m "initial: luogu-AI-report"
git remote add origin https://你的私有仓库地址.git
git push -u origin main

# 2) 把 deploy.sh 上传到服务器（一次性）
scp .\deploy.sh ubuntu@43.163.26.115:/home/ubuntu/luogu-ai-report/

# 3) 服务器侧初始化
ssh ubuntu@43.163.26.115
cd /home/ubuntu/luogu-ai-report
chmod +x deploy.sh
cp .env.example .env
vim .env                       # 必改 3 项：API_KEY / ADMIN_PASSWORD / SESSION_SECRET

# 4) 以后每次改代码，本地一条命令搞定
cd C:\Users\zpy20\Desktop\项目\luoguAI\luogu-AI-report
.\deploy.ps1                   # 自动打包+scp+服务器部署
```

## 🔁 增量更新工作流

```powershell
# 1) 本地改代码
# 2) commit + push
git add . && git commit -m "xxx" && git push

# 3) 一行部署
.\deploy.ps1
```

## ⚠️ 踩坑提醒（已全部内化到 deploy 脚本）

1. **改 .env 后**必须 `down + up -d`，`restart` 不会重读 env_file
2. **bash 里的 `!`** 用单引号包，密码字符串避免双引号
3. **多行 Python 代码** 千万别用 heredoc 粘贴到终端，用 base64
4. **bind mount 文件** 不存在时 SQLite 会失败，用命名卷
5. **healthcheck 路由** 必须是真实存在的路由
