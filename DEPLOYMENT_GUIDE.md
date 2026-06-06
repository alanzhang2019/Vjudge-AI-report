# luogu-AI-report 部署指南

> **从零到生产**的完整手册 —— 涵盖首次部署、日常运维、多服务器、故障排查、安全清单。

---

## 目录

1. [概述](#1-概述)
2. [架构总览](#2-架构总览)
3. [前提条件](#3-前提条件)
4. [首次部署](#4-首次部署)
5. [日常运维](#5-日常运维)
6. [多服务器部署](#6-多服务器部署)
7. [故障排查](#7-故障排查)
8. [安全清单](#8-安全清单)
9. [维护计划](#9-维护计划)
10. [附录](#10-附录)
11. [域名 + HTTPS 生产部署](#11-域名--https-生产部署)
12. [备份清单与急救命令](#12-备份清单与急救命令)
13. [容器级急救命令](#13-容器级急救命令)
14. [联系 / 反馈](#14-联系--反馈)

---

## 1. 概述

luogu-AI-report 是一个基于 Flask 的 Web 应用，提供：

- 洛谷做题数据采集与统计
- AI 驱动的测评报告生成（Markdown / HTML / PDF）
- 考纲匹配（GESP / NOI）
- 六维能力评分
- 任务管理与历史记录

**技术栈**：
- Python 3.11 + Flask
- Playwright (Chromium) + Matplotlib (图表)
- SQLite (任务持久化)
- Docker 容器化部署
- Nginx（生产推荐反代）

---

## 2. 架构总览

```
┌────────────────────────────────────────────────────────────┐
│  浏览器 (前端用户)                                          │
│  └─► http://SERVER_IP:5000/                                │
└──────────────────────┬─────────────────────────────────────┘
                       │ HTTP
                       ▼
┌────────────────────────────────────────────────────────────┐
│  Docker Container: luogu-ai-report-luogu-coach             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Flask web_app.py (端口 5000)                        │  │
│  │  ├─ /                首页                             │  │
│  │  ├─ /admin/login     管理员登录                       │  │
│  │  ├─ /generate        生成报告                         │  │
│  │  ├─ /status/<id>     任务状态                         │  │
│  │  └─ /api/*           JSON API                         │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  核心模块                                              │  │
│  │  ├─ luogu_evaluator.py    AI 报告生成                 │  │
│  │  ├─ task_store.py         SQLite 任务持久化          │  │
│  │  ├─ behavior_analyzer.py  能力评分                    │  │
│  │  ├─ syllabus_matcher.py   考纲匹配                    │  │
│  │  └─ code_analyzer.py      代码分析                    │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  外部依赖                                              │  │
│  │  ├─ Playwright + Chromium (PDF 导出)                  │  │
│  │  ├─ Matplotlib (图表生成)                             │  │
│  │  └─ Noto CJK 字体 (中文字体)                          │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────┬──────────────────────────┬──────────────────────┘
           │                          │
           ▼                          ▼
┌──────────────────┐         ┌──────────────────┐
│ 命名卷           │         │ 宿主机绑定        │
│ ├─ tasks-data    │         │ ./reports/        │
│ │  └─ tasks.db   │         │  └─ 生成的报告    │
│ └─ source-cache  │         │                   │
│    └─ AI/题目缓存 │         │                   │
└──────────────────┘         └──────────────────┘
           │
           ▼
   ┌──────────────────┐
   │ 外部服务          │
   │ ├─ 洛谷 API       │
   │ └─ OpenAI 兼容 LLM│
   └──────────────────┘
```

---

## 3. 前提条件

### 3.1 服务器最低配置

| 项 | 最低 | 推荐 |
|---|---|---|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB（Playwright 吃内存） |
| 磁盘 | 60 GB | 100 GB |
| 系统 | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| Docker | 24.0+ | 最新 |
| 公网 | 静态 IP | 域名 + SSL |

### 3.2 客户端工具

- **Windows 10/11 1809+**（自带 ssh / scp）
- 或 **macOS / Linux**（自带）

### 3.3 必须的账号/资源

- [ ] 洛谷账号（拿 cookies 用）
- [ ] OpenAI 兼容平台账号（DeepSeek / Moonshot / OpenAI 等）+ **新生成**的 API Key
- [ ] 服务器 root 访问权限
- [ ] 服务器防火墙可放行 5000 端口

---

## 4. 首次部署

### 4.1 客户端准备

#### 4.1.1 克隆项目

```powershell
# Windows PowerShell
cd C:\Users\zpy20\Desktop\项目\luoguAI

# 二选一
# A) 克隆 GitHub 上游（可能不是最新）
git clone https://github.com/alanzhang2019/luogu-AI-report.git

# B) 用本地已有的项目目录
cd luogu-AI-report
```

#### 4.1.2 验证关键文件

```powershell
ls deploy.ps1 deploy.sh Dockerfile docker-compose.yml .env.example
# 应该看到 5 个文件
```

#### 4.1.3 配 SSH 免密登录（强烈推荐）

```powershell
# 生成本地 SSH 密钥（已有就跳过）
ssh-keygen -t ed25519

# 把公钥推送到服务器
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh ubuntu@SERVER_IP "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

之后所有 `ssh` / `scp` / `.\deploy.ps1` 都不用再输密码。

### 4.2 服务器一次性初始化

SSH 进服务器（用 root 或有 sudo 的用户）：

```bash
# === A. 创建/确认 ubuntu 用户 ===
id ubuntu || adduser ubuntu
usermod -aG sudo,docker ubuntu

# === B. 装 unzip（deploy.sh 需要） ===
apt-get update
apt-get install -y unzip

# === C. 防火墙放行 5000 ===
ufw allow 5000/tcp 2>/dev/null || iptables -A INPUT -p tcp --dport 5000 -j ACCEPT

# === D. 创建项目目录 ===
mkdir -p /home/ubuntu/luogu-ai-report
chown -R ubuntu:ubuntu /home/ubuntu/luogu-ai-report
```

### 4.3 传 .env（带真值的那份）

```powershell
# 客户端
scp .env ubuntu@SERVER_IP:/home/ubuntu/luogu-ai-report/
```

或**手动创建**（最干净）：

```bash
# 服务器
sudo -u ubuntu -H bash -c '
cd /home/ubuntu/luogu-ai-report
cp .env.example .env
vim .env
# 必改 3 项：
#   OPENAI_API_KEY=sk-你的新生成的key
#   ADMIN_PASSWORD=一串强密码（建议 16+ 字符，含大小写数字符号）
#   ADMIN_SESSION_SECRET=$(openssl rand -hex 32 生成)
chmod 600 .env
'
```

### 4.4 跑一键部署

```powershell
# 客户端
cd C:\Users\zpy20\Desktop\项目\luoguAI\luogu-AI-report
.\deploy.ps1 -Server ubuntu@SERVER_IP
```

脚本会自动：

1. 排除 `.git / .env / 缓存 / PDF` 打包
2. scp 上传到服务器
3. SSH 调用 `./deploy.sh --from-zip`
4. 服务器解包 → 清理 → 重建镜像 → 启动容器

### 4.5 验证

```powershell
# 看状态
.\deploy.ps1 -Server ubuntu@SERVER_IP -Status
```

期望输出：
```
=== 容器状态 ===
NAMES                              STATUS
luogu-ai-report-luogu-coach       Up X minutes (healthy)

=== 健康检查 ===
✓  http://127.0.0.1:5000/ 可访问
```

### 4.6 浏览器首次访问

```
http://SERVER_IP:5000/
```

1. 强刷 `Ctrl+Shift+R`
2. 登录：`admin` / `.env` 里的 `ADMIN_PASSWORD`
3. 进**系统设置**立即改密码
4. 填洛谷 cookies（DevTools → Application → Cookies → 复制 `__client_id` 和 `_uid`）
5. 测试一个学生 UID 跑首份报告

---

## 5. 日常运维

### 5.1 命令速查

| 任务 | 客户端命令 | 服务器命令 |
|---|---|---|
| 看状态 | `.\deploy.ps1 -Status` | `./deploy.sh --status` |
| 跟日志 | `.\deploy.ps1 -Logs` | `./deploy.sh --logs` |
| 改 .env 后重启 | `.\deploy.ps1 -Restart` | `./deploy.sh --restart` |
| 重置密码 | `.\deploy.ps1 -ResetPassword` | `./deploy.sh --reset-password` |
| 完整部署 | `.\deploy.ps1` | `./deploy.sh --from-zip` |
| 回滚 | `.\deploy.ps1 -Rollback` | `./deploy.sh --rollback` |
| 看健康 | `curl http://SERVER:5000/` | 同上 |

### 5.2 改代码后的标准工作流

```powershell
# 1) 本地改代码
# 2) 测试（可选）
python -c "import ast; ast.parse(open('web_app.py').read())"

# 3) 提交
cd C:\Users\zpy20\Desktop\项目\luoguAI\luogu-AI-report
git add -A
git commit -m "feat: xxx"
git push origin main    # 如果配了私有 remote

# 4) 一行部署
.\deploy.ps1
```

### 5.3 改 .env 后的正确做法

```bash
# 服务器上
vim .env
# 改完保存

# 关键：必须 down + up -d，restart 不会重读 env_file
./deploy.sh --restart
```

### 5.4 容器内调试

```bash
# 进容器交互 shell
docker exec -it luogu-ai-report-luogu-coach bash

# 看环境变量
docker exec luogu-ai-report-luogu-coach env | grep -E "OPENAI|ADMIN"

# 跑任意 Python 命令
docker exec luogu-ai-report-luogu-coach python -c "from task_store import DB_PATH; print(DB_PATH)"

# 看容器磁盘
docker exec luogu-ai-report-luogu-coach du -sh /app/data /app/.source_cache
```

### 5.5 备份策略

```bash
# 手动备份报告
tar czf ~/backup-reports-$(date +%Y%m%d).tar.gz -C /home/ubuntu/luogu-ai-report reports

# 自动备份（crontab）
crontab -e
# 加：每周日凌晨 3 点
0 3 * * 0  tar czf /home/ubuntu/backups/reports-$(date +\%Y\%m\%d).tar.gz -C /home/ubuntu/luogu-ai-report reports && find /home/ubuntu/backups -name "reports-*.tar.gz" -mtime +30 -delete
```

### 5.6 清理维护

```bash
# 清旧镜像
docker image prune -a -f

# 清卷（**危险**：会删所有任务历史和缓存）
docker volume prune

# 看磁盘占用
docker system df

# 清空源缓存（会触发重新拉取）
docker exec luogu-ai-report-luogu-coach rm -rf /app/.source_cache/*
```

---

## 6. 多服务器部署

### 6.1 跨服务器差异

| 项 | 是否每台独立 |
|---|---|
| `.env`（含 API Key） | ✅ 每台独立 |
| 洛谷 cookies | ✅ 每台独立（或共享） |
| `deploy.sh / ps1` | ❌ 第一次 deploy 时自动传 |
| 业务代码 | ❌ 每次 deploy 自动同步 |
| 任务库 / 报告 | ❌ 每台独立（命名卷隔离） |

### 6.2 新增第二台服务器

```powershell
# 客户端
.\deploy.ps1 -Server ubuntu@server2.example.com
```

服务器侧只需要：

```bash
# 1) 加 ubuntu 用户到 docker 组（如果还没）
sudo usermod -aG docker ubuntu
newgrp docker

# 2) 传 .env（**真值必须重新生成 API key**）
#    或者从 server1 拷过来（接受风险）
scp ubuntu@server1:/home/ubuntu/luogu-ai-report/.env /home/ubuntu/luogu-ai-report/
chmod 600 /home/ubuntu/luogu-ai-report/.env
sed -i "s|^ADMIN_SESSION_SECRET=.*|ADMIN_SESSION_SECRET=$(openssl rand -hex 32)|" /home/ubuntu/luogu-ai-report/.env
```

### 6.3 批量部署脚本

创建 `servers.txt`：
```
ubuntu@server1.example.com
ubuntu@server2.example.com
ubuntu@server3.example.com
```

```powershell
# 客户端 PowerShell
Get-Content servers.txt | ForEach-Object {
    Write-Host "=== $_ ===" -ForegroundColor Cyan
    .\deploy.ps1 -Server $_ -SkipBuild
}
```

`-SkipBuild` 复用上次打包的 zip，省时间。

### 6.4 负载均衡（高级）

多台服务器前置一层 Nginx：

```nginx
upstream luogu {
    server server1:5000;
    server server2:5000;
    server server3:5000;
}

server {
    listen 443 ssl;
    server_name report.example.com;

    ssl_certificate     /etc/letsencrypt/live/report.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/report.example.com/privkey.pem;

    client_max_body_size 100M;   # 允许上传大文件

    location / {
        proxy_pass http://luogu;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 600s;  # 报告生成可能要几分钟
    }
}
```

⚠️ 多实例时，**任务历史不共享**。如需共享需用共享数据库（PostgreSQL/MySQL 替代 SQLite）。

---

## 7. 故障排查

### 7.1 部署阶段常见问题

#### 7.1.1 `docker compose: command not found`

**原因**：服务器装的是老版 docker。

```bash
# 安装新版
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu
```

#### 7.1.2 容器启动后立即退出

```bash
docker compose logs --tail=50
```

| 日志特征 | 根因 | 修法 |
|---|---|---|
| `sqlite3.OperationalError` | 命名卷挂载失败 | 检查 `volumes:` 配置 + `TASK_DB_PATH` 环境变量 |
| `ImportError: cannot import name X` | 部署包不完整 | 用 `.\deploy.ps1 -SkipBuild:$false` 重新打包 |
| `ModuleNotFoundError: No module named 'X'` | `requirements.txt` 漏包 | 加上重新构建 |
| `Permission denied: '/app/...'` | 目录权限错 | `chown -R 1000:1000 /path/to/dir`（用容器内用户 UID） |

#### 7.1.3 healthcheck 一直失败

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
# 看到 (health: starting) 或 (unhealthy) 持续
```

**检查**：
1. 路由是否真存在：`docker exec CONT grep "@app.route" /app/web_app.py`
2. 改 `docker-compose.yml` 的 `healthcheck.test` 指向真路由
3. 临时改成 `curl -fsS http://127.0.0.1:5000/` 试

#### 7.1.4 scp Permission denied

**原因**：目标目录归属错。

```bash
# 服务器
sudo chown -R ubuntu:ubuntu /home/ubuntu/luogu-ai-report/
```

或用 `sudo` 跑 scp（不推荐，要传密码）：

```powershell
scp .\file ubuntu@SERVER:/home/ubuntu/luogu-ai-report/  # 先传到家
ssh ubuntu@SERVER "sudo mv ~/file /home/ubuntu/luogu-ai-report/"
```

### 7.2 运行时常见问题

#### 7.2.1 改了 .env 不生效

**根因**：`docker compose restart` 不重读 `env_file`。

**修法**：

```bash
docker compose down && docker compose up -d
```

#### 7.2.2 admin 密码错误

```bash
# 服务器上重置
./deploy.sh --reset-password
# 输出新密码
```

#### 7.2.3 报告生成卡住 / 超时

```bash
# 看实时日志
./deploy.sh --logs

# 看资源占用
docker stats luogu-ai-report-luogu-coach
```

**可能原因**：
- 洛谷接口慢 → 正常，等几分钟
- LLM 慢 → 取决于模型
- 内存不够 → OOM Killer 会杀进程，看 `dmesg | grep -i oom`

#### 7.2.4 中文字体显示方块

```bash
# 容器内装字体
docker exec -u root luogu-ai-report-luogu-coach \
  apt-get install -y fonts-noto-cjk fonts-wqy-zenhei
docker compose restart
```

或在 Dockerfile 加：
```dockerfile
RUN apt-get install -y fonts-noto-cjk fonts-wqy-zenhei
```

#### 7.2.5 PDF 生成失败

```bash
# 验证 Playwright 装好了
docker exec luogu-ai-report-luogu-coach python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    print('chromium OK')
    b.close()
"
```

如果报错，**重新构建镜像**：
```bash
docker compose build --no-cache
docker compose up -d
```

### 7.3 网络问题

#### 7.3.1 1Panel 网页终端粘贴乱码

**修法**：用 **1Panel 文件管理器** 替代终端粘贴。

#### 7.3.2 bash `!` 解析问题

**现象**：`bash: !X: event not found`

**修法**：用**单引号**包字符串：
```bash
NEW_PW='Luogu@Admin#2026Tx9k'   # 单引号避免 ! 解析
```

#### 7.3.3 多行代码粘贴被截断

**修法**：用 base64 单行传输：
```bash
# 客户端编码
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((Get-Content file -Raw))) > file.b64

# 服务器解码
base64 -d file.b64 > file
```

### 7.4 紧急回滚

```bash
# 1) 看历史
ls -lt /home/ubuntu/ | head
# 找最近一次备份目录 luogu-ai-report.bak.YYYYMMDD_HHMMSS

# 2) 一键回滚
./deploy.sh --rollback
```

或手动：

```bash
docker compose down
mv /home/ubuntu/luogu-ai-report /home/ubuntu/luogu-ai-report.broken
mv /home/ubuntu/luogu-ai-report.bak.YYYYMMDD_HHMMSS /home/ubuntu/luogu-ai-report
cd /home/ubuntu/luogu-ai-report
docker compose up -d --build
```

---

## 8. 安全清单

### 8.1 上线前必做

- [ ] **撤销+重发** GitHub 上游泄露的 API Key
- [ ] 改 `ADMIN_PASSWORD` 为强密码（16+ 字符）
- [ ] 改 `ADMIN_SESSION_SECRET` 为 `openssl rand -hex 32` 输出
- [ ] `.env` 文件权限 600（`chmod 600 .env`）
- [ ] 服务器开启防火墙（ufw / iptables / 安全组）
- [ ] 如果公网暴露，**必须**前置 Nginx + SSL（HTTPS）

### 8.2 推荐配置

- [ ] 配置 fail2ban 防 SSH 爆破：`apt install -y fail2ban`
- [ ] 定期 apt 升级：`unattended-upgrades`
- [ ] Docker 镜像定期重建（拉安全补丁）
- [ ] 备份到异地（OSS / S3）

### 8.3 危险操作警告

| 操作 | 风险 |
|---|---|
| `docker volume prune` | **会删除所有任务历史** |
| `rm -rf /var/lib/docker/volumes/luogu-ai-report_*` | **会删除所有数据** |
| 把 5000 端口直接公网开放 | **可能被扫** |
| 把 `.env` 推到 git | **凭据泄露**（项目已 .gitignore） |
| 共享 `ADMIN_PASSWORD` | **会被人进入管理后台** |

---

## 9. 维护计划

### 9.1 每日（自动）

- crontab 备份报告
- 1Panel 自动安全更新

### 9.2 每周（手动）

- [ ] 看一次日志确认无异常
- [ ] 清理旧 Docker 镜像
- [ ] 验证报告生成正常

### 9.3 每月

- [ ] 拉上游更新：`git pull upstream main && python sync_upstream.py`
- [ ] 重建镜像（拉新基础镜像）
- [ ] 备份验证（恢复演练）

### 9.4 每次大版本

- [ ] 完整部署一次 `.\deploy.ps1`
- [ ] 验证所有功能
- [ ] 写更新日志

---

## 10. 附录

### 10.1 关键文件清单

```
luogu-AI-report/
├── Dockerfile                # 镜像构建
├── docker-compose.yml        # 容器编排
├── requirements.txt          # 依赖
├── .env.example              # 配置模板（脱敏）
├── .env                      # 真值（不上 git）
├── .dockerignore             # 构建排除
├── .gitignore
├── deploy.sh                 # 服务器端部署脚本
├── deploy.ps1                # 客户端部署脚本
├── sync_upstream.py          # 上游同步工具
├── DEPLOYMENT_GUIDE.md       # ← 本文件
├── DEPLOY_QUICKREF.md        # 速查卡
├── web_app.py                # Flask 入口
├── task_store.py             # 任务持久化
├── behavior_analyzer.py      # 能力评分
├── syllabus_matcher.py       # 考纲匹配
├── code_analyzer.py          # 代码分析
├── env_loader.py             # .env 加载
├── luogu_evaluator.py        # AI 报告核心
├── examples/export_for_ai.py
├── pyLuogu/                  # 洛谷 API
├── report_template.html      # HTML 模板
├── GESP考纲.pdf.txt
├── NOI大纲.pdf.txt
└── report_public.pdf         # 示例报告
```

### 10.2 关键路径

| 用途 | 路径 |
|---|---|
| 项目根 | `/home/ubuntu/luogu-ai-report/` |
| `.env` | `/home/ubuntu/luogu-ai-report/.env` |
| 报告 | `/home/ubuntu/luogu-ai-report/reports/` |
| 任务库（卷） | `/var/lib/docker/volumes/luogu-ai-report_tasks-data/_data/tasks.db` |
| 缓存（卷） | `/var/lib/docker/volumes/luogu-ai-report_source-cache/_data/` |
| 备份 | `/home/ubuntu/luogu-ai-report.bak.YYYYMMDD_HHMMSS/` |
| 部署 zip | `/home/ubuntu/luogu-ai-report/deploy-pkg.zip`（自动删除） |

### 10.3 环境变量清单

| 变量 | 必填 | 说明 |
|---|---|---|
| `OPENAI_API_KEY` | ✅ | API 密钥 |
| `OPENAI_BASE_URL` | ✅ | API base URL |
| `OPENAI_MODEL_NAME` | ✅ | 模型名 |
| `OPENAI_ADMIN_KEY` | ❌ | 可选，备用 key |
| `ADMIN_USERNAME` | ✅ | 管理员用户名 |
| `ADMIN_PASSWORD` | ✅ | 管理员密码 |
| `ADMIN_SESSION_SECRET` | ✅ | session 加密 key |
| `TASK_DB_PATH` | ✅ | SQLite 路径（容器内 `/app/data/tasks.db`） |
| `LUOGU_REPORT_AUTO_FONT_DOWNLOAD` | ❌ | 自动下载字体 |

### 10.4 推荐环境变量（生产环境）

```bash
# 容器启动时额外加
FLASK_ENV=production         # 关闭 debug
PYTHONUNBUFFERED=1           # 日志不缓存
TZ=Asia/Shanghai             # 时区
```

### 10.5 升级上游

```powershell
# 客户端
cd C:\Users\zpy20\Desktop\项目\luoguAI\luogu-AI-report
git pull upstream main
python sync_upstream.py      # 自动同步 7 个核心文件
git add -A
git commit -m "sync upstream"
git push origin main
.\deploy.ps1
```

---

## 11. 域名 + HTTPS 生产部署

把 `oi.aijiangti.cn` 域名 + Let's Encrypt 证书接到 webapp 前端，**隐藏服务器 IP**。

### 11.1 完整架构

```
                    ┌─────────────────────────────────────┐
                    │   1Panel OpenResty (Docker 容器)    │
                    │   监听 80/443                        │
                    └────────────────┬────────────────────┘
                                     │
        ┌────────────────────────────┴─────────────────────┐
        │                                                  │
   Host 头 = oi.aijiangti.cn                       其他（IP 直访）
        │                                                  │
        ▼                                                  ▼
   HTTPS 反代                                       (没人监听，已关 5000 公网)
        │
        ▼
   127.0.0.1:5000  (luogu-ai-report webapp)
```

### 11.2 DNS 解析

去域名注册商后台（阿里云/腾讯云/Cloudflare）：

| 字段 | 值 |
|---|---|
| 主机记录 | `oi` |
| 记录类型 | `A` |
| 记录值 | 服务器公网 IP（如 `43.163.26.115`） |
| TTL | 600 |

验证：

```bash
dig oi.aijiangti.cn +short
# 期望：43.163.26.115
```

### 11.3 安装 OpenResty

1Panel → **应用商店** → 搜 **OpenResty** → 安装：

| 字段 | 值 |
|---|---|
| 名称 | `openresty` |
| HTTP 端口 | 80 |
| HTTPS 端口 | 443 |
| 网站目录 | `/opt/1panel/www` |

**前提**：80 端口必须空闲。如被占用（如 nofx 占了 80），改其 `.env` 文件端口后重启。

### 11.4 申请 Let's Encrypt 证书

```bash
# 1) 装 certbot
apt-get install -y certbot

# 2) 停 OpenResty 释放 80 端口
OPENRESTY=$(docker ps --format "{{.Names}}" | grep -i openresty | head -1)
docker stop "$OPENRESTY"

# 3) 强切 ASCII locale（避免非 ASCII 报错）
export LANG=C LC_ALL=C

# 4) 申请证书
certbot certonly --standalone \
    -d oi.aijiangti.cn \
    --email your@email.com \
    --agree-tos \
    --no-eff-email

# 5) 启 OpenResty
docker start "$OPENRESTY"
```

成功输出：

```
Certificate is saved at: /etc/letsencrypt/live/oi.aijiangti.cn/fullchain.pem
Key is saved at:         /etc/letsencrypt/live/oi.aijiangti.cn/privkey.pem
```

### 11.5 1Panel 创建反代网站

1Panel → **网站** → **创建网站**：

| 字段 | 值 |
|---|---|
| 类型 | **反向代理** |
| 主域名 | `oi.aijiangti.cn` |
| 代理地址 | `127.0.0.1:5000` |
| 备注 | luogu-ai-report |

### 11.6 把证书放到 1Panel 期望的路径

**不能用符号链接**（certbot 用的相对路径 `../../archive/...` 跨过 bind mount 边界会失效）。**用真实文件 + 续期 hook**：

```bash
# 1) 在 1Panel 管理的 SSL 目录放真实证书文件
SSL_DIR=/opt/1panel/www/sites/oi.aijiangti.cn/ssl
mkdir -p "$SSL_DIR"
cp /etc/letsencrypt/archive/oi.aijiangti.cn/fullchain1.pem "$SSL_DIR/fullchain.pem"
cp /etc/letsencrypt/archive/oi.aijiangti.cn/privkey1.pem   "$SSL_DIR/privkey.pem"

# 2) 写 certbot 续期 hook（自动同步）
cat > /etc/letsencrypt/renewal-hooks/deploy/sync-to-1panel.sh << 'HOOK'
#!/bin/bash
DOMAIN=oi.aijiangti.cn
DEST=/opt/1panel/www/sites/$DOMAIN/ssl
mkdir -p "$DEST"
FULLCHAIN=$(ls -1 /etc/letsencrypt/archive/$DOMAIN/fullchain*.pem | sort -V | tail -1)
PRIVKEY=$(ls -1 /etc/letsencrypt/archive/$DOMAIN/privkey*.pem | sort -V | tail -1)
cp -f "$FULLCHAIN" "$DEST/fullchain.pem"
cp -f "$PRIVKEY"   "$DEST/privkey.pem"
OPENRESTY=$(docker ps --format "{{.Names}}" | grep -i openresty | head -1)
[ -n "$OPENRESTY" ] && docker exec "$OPENRESTY" openresty -s reload
echo "$(date) synced $DOMAIN certs and reloaded $OPENRESTY" >> /var/log/certbot-sync.log
HOOK
chmod +x /etc/letsencrypt/renewal-hooks/deploy/sync-to-1panel.sh
```

### 11.7 反代超时（防 504）

1Panel → 网站 → `oi.aijiangti.cn` → **反向代理** → **配置**，在 `location /` 加：

```nginx
proxy_connect_timeout 600s;
proxy_send_timeout    600s;
proxy_read_timeout    600s;
client_max_body_size  100M;
```

### 11.8 强制 HTTPS

1Panel → 网站 → `oi.aijiangti.cn` → **设置** → 勾选 **HTTPS 强制跳转**

或者在 1Panel 配置文件里加（80 server 块）：

```nginx
if ($scheme = http) {
    return 301 https://$host$request_uri;
}
```

### 11.9 验证

```bash
# 证书
echo | openssl s_client -connect oi.aijiangti.cn:443 -servername oi.aijiangti.cn 2>/dev/null \
    | openssl x509 -noout -subject -issuer
# 期望：subject=CN = oi.aijiangti.cn
#       issuer=O = Let's Encrypt, CN = R10 (或 R11, YR1)

# HTTPS
curl -I https://oi.aijiangti.cn
# 期望：HTTP/2 200
```

浏览器 `Ctrl+Shift+R` 强刷 → 期望 🔒 绿锁。

### 11.10 踩过的坑

| 症状 | 原因 | 解决 |
|---|---|---|
| 1Panel 网站菜单提示"未检测到 OpenResty" | 没装 | 应用商店装 |
| "端口 80 已被占用" | nofx 占了 80 | 改 nofx `.env` 里 `NOFX_BACKEND_PORT=8080` |
| 浏览器"Not secure"但 Certificate valid | 1Panel 用自签证书 | 申请 Let's Encrypt + 装到正确路径 |
| `cannot load certificate` 配 softlink | certbot 软链相对路径跨 mount 失败 | 用真实文件，不用软链 |
| 两个 `ssl_certificate` 冲突 | 1Panel 自动 80+443 合并 + 手动 443 重复 | 删手动块，保留 1Panel 自动块 |
| `openresty -s reload` 报错但 curl 仍正常 | reload 失败但 OpenResty 在用老配置 | 改对配置后 reload |
| acme.sh "non-ASCII characters" | LANG=en_US.UTF-8 | `export LANG=C LC_ALL=C` |

### 11.11 隐藏服务器 IP（可选加固）

如果域名在 **Cloudflare** 解析：

1. Cloudflare → DNS → `oi` → 代理状态改成 **🟠 Proxied**
2. Cloudflare 自带 SSL + CDN + DDoS 防护
3. 服务器真实 IP 不再公开
4. Cloudflare 边缘节点用 Cloudflare Origin 自签证书和源站通信

防火墙可只放行 Cloudflare IP 段（这是终极加固）。

---

## 12. 备份清单与急救命令

### 12.1 必须备份的文件

| 类别 | 路径 | 说明 |
|---|---|---|
| **配置** | `/home/ubuntu/luogu-ai-report/.env` | API Key、管理员密码 |
| **配置** | `/opt/nofx/.env` | Coinglass API Key |
| **SSL** | `/etc/letsencrypt/` | 整个目录（含 live/archive/renewal） |
| **SSL** | `/opt/1panel/www/sites/oi.aijiangti.cn/ssl/` | 1Panel 实际用的证书 |
| **1Panel 配置** | `/opt/1panel/www/conf.d/` | OpenResty 网站配置 |
| **Hook** | `/etc/letsencrypt/renewal-hooks/deploy/` | 续期脚本 |
| **数据库** | `luogu-ai-report_tasks-data` 命名卷 | 任务历史（容器外是路径 /var/lib/docker/volumes/...） |
| **报告** | `luogu-ai-report_reports` 命名卷 | 生成的 PDF/HTML |
| **nofx 数据** | `/opt/nofx/config.db` | nofx 配置库 |
| **nofx 日志** | `/opt/nofx/decision_logs/` | 决策日志 |

### 12.2 备份脚本

```bash
#!/bin/bash
# /usr/local/bin/backup-luogu.sh
BACKUP=/backup/$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP"

# .env
cp /home/ubuntu/luogu-ai-report/.env "$BACKUP/luogu-env"

# SSL
tar -czf "$BACKUP/ssl.tar.gz" /etc/letsencrypt/

# 1Panel 网站配置
tar -czf "$BACKUP/openresty-config.tar.gz" /opt/1panel/www/

# 1Panel 证书
tar -czf "$BACKUP/1panel-ssl.tar.gz" /opt/1panel/www/sites/

# 续期 hook
cp -r /etc/letsencrypt/renewal-hooks "$BACKUP/renewal-hooks"

# 数据库卷
docker run --rm \
    -v luogu-ai-report_tasks-data:/data \
    -v "$BACKUP":/backup \
    alpine tar -czf /backup/tasks-data.tar.gz -C /data .

# 报告卷
docker run --rm \
    -v luogu-ai-report_reports:/data \
    -v "$BACKUP":/backup \
    alpine tar -czf /backup/reports.tar.gz -C /data .

# nofx
cp /opt/nofx/.env "$BACKUP/nofx-env"
cp /opt/nofx/config.db "$BACKUP/nofx-config.db"

# 清理 30 天前
find /backup -maxdepth 1 -type d -mtime +30 -exec rm -rf {} \;

echo "✅ 备份完成: $BACKUP"
```

加到 crontab：每天凌晨 3 点跑。

```bash
# /etc/cron.d/backup
0 3 * * * root /usr/local/bin/backup-luogu.sh
```

### 12.3 急救命令速查

```bash
# ===== 容器状态 =====
cd /home/ubuntu/luogu-ai-report
./deploy.sh --status

# ===== 实时日志 =====
./deploy.sh --logs               # webapp
docker logs 1Panel-openresty-uOBw --tail 50  # 反代

# ===== 重启 =====
./deploy.sh --restart            # 重启 webapp
docker restart 1Panel-openresty-uOBw  # 重启反代

# ===== 改 .env 后必须 down+up =====
cd /home/ubuntu/luogu-ai-report
docker compose down && docker compose up -d

# ===== 手动重载 OpenResty =====
docker exec $(docker ps --format "{{.Names}}" | grep -i openresty | head -1) openresty -s reload

# ===== 手动续期证书 =====
export LANG=C LC_ALL=C
certbot renew --force-renewal

# ===== 看证书状态 =====
echo | openssl s_client -connect oi.aijiangti.cn:443 -servername oi.aijiangti.cn 2>/dev/null \
    | openssl x509 -noout -subject -issuer -dates

# ===== 改管理员密码 =====
./deploy.sh --reset-password

# ===== 看 80 端口谁占用 =====
sudo ss -tlnp | grep ':80 '

# ===== 看 5000 端口谁占用 =====
sudo ss -tlnp | grep ':5000 '

# ===== 进入 webapp 容器调试 =====
docker exec -it luogu-ai-report-luogu-coach /bin/bash

# ===== 紧急回滚 =====
./deploy.sh --rollback

# ===== 看磁盘 =====
df -h
du -sh /var/lib/docker/volumes/luogu-ai-report*

# ===== 看报告数量 =====
ls -la /home/ubuntu/luogu-ai-report/reports/ 2>/dev/null
```

### 12.4 证书快到期

| 检查命令 | 输出 |
|---|---|
| `certbot certificates` | 列出所有证书及过期时间 |
| `ls -la /var/log/letsencrypt/` | 看续期日志 |
| `cat /var/log/certbot-sync.log` | 看 hook 续期日志 |

如果 30 天内没自动续期成功：

```bash
# 手动跑续期
export LANG=C LC_ALL=C
certbot renew --force-renewal

# 看 hook 是否执行
ls -lt /opt/1panel/www/sites/oi.aijiangti.cn/ssl/

# 看 hook 日志
tail -20 /var/log/certbot-sync.log
```

### 12.5 网站挂了 5 分钟排查流程

1. **看容器**：`./deploy.sh --status` → 是否 Up + healthy？
2. **看日志**：`./deploy.sh --logs` → 有什么 error？
3. **看端口**：`curl -I http://127.0.0.1:5000/` → 5000 通吗？
4. **看反代**：`curl -I http://127.0.0.1/` → 80 通吗？
5. **看反代容器**：`docker logs 1Panel-openresty-uOBw --tail 50`
6. **看证书**：`echo | openssl s_client -connect oi.aijiangti.cn:443 ...`
7. **看磁盘**：`df -h`（满 100% 会挂）
8. **看内存**：`free -h`

按这个顺序 8 步能定位 95% 的问题。

---

## 写在最后

部署这套系统踩了很多坑（Docker 权限、数据库持久化、SQLite 锁、1Panel 反代、Let's Encrypt 各种雷、OpenResty 配置冲突），都记录在这份文档里了。

**遇到新问题**先看：

1. 故障排查（第 7 章）
2. 域名 + HTTPS（第 11 章）
3. 急救命令（第 12.3 节）

**搞不定**先看 `./deploy.sh --status`，80% 的问题一眼能看出来。

Happy deploying! 🚀

---

## 13. 容器级急救命令（补充）

```bash
# 容器卡死，重启
docker compose restart

# 容器起不来，重建
docker compose up -d --build --force-recreate

# 完全重置（危险）
docker compose down -v
docker compose up -d --build

# 清理所有无用资源
docker system prune -a --volumes

# 看容器 CPU/内存实时
docker stats

# 看具体进程
docker exec luogu-ai-report-luogu-coach ps aux

# 看网络
docker network inspect luogu-ai-report_luogu-network
```

## 14. 联系 / 反馈

- 项目仓库：[github.com/alanzhang2019/luogu-AI-report](https://github.com/alanzhang2019/luogu-AI-report)
- 洛谷：[luogu.com.cn](https://www.luogu.com.cn)
- 问题反馈：项目 Issues

---

## 版本

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0 | 2026-06-06 | 首次编写，整合从部署到运维的全套流程 |
| 1.1 | 2026-06-07 | + 第 11 章域名 + HTTPS 部署（DNS、OpenResty、Let's Encrypt、certbot 自动续期）<br/>+ 第 12 章备份清单与急救命令（备份脚本、证书检查、5 分钟排查流程）<br/>+ 第 13 章容器级急救命令<br/>+ Cloudflare 隐藏 IP 加固方案 |
