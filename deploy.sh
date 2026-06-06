#!/usr/bin/env bash
# ============================================================================
# luogu-AI-report 一键部署脚本（服务器端）
# 用法：
#   ./deploy.sh                                    # 默认部署（构建+启动）
#   ./deploy.sh --pull                             # 拉取最新代码（git 模式）
#   ./deploy.sh --from-zip                         # 从 deploy-pkg.zip 部署
#   ./deploy.sh --from-zip /path/to/pkg.zip        # 指定 zip 路径
#   ./deploy.sh --rollback                         # 回滚到上一个版本
#   ./deploy.sh --status                           # 查看服务状态
#   ./deploy.sh --logs                             # 跟踪日志
#   ./deploy.sh --restart                          # 改 .env 后生效
#   ./deploy.sh --reset-password                   # 重置 admin 密码
#   ./deploy.sh --help                             # 帮助
# ============================================================================

set -euo pipefail

# ---------- 颜色 ----------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

# ---------- 默认值 ----------
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="luogu-ai-report-luogu-coach"
ZIP_PATH="${PROJECT_DIR}/deploy-pkg.zip"
BACKUP_PREFIX="luogu-ai-report.bak"
MODE="default"

# ---------- 帮助 ----------
usage() {
  sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

# ---------- 参数 ----------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --pull)         MODE="pull" ;;
    --from-zip)     MODE="zip"; shift; [[ $# -gt 0 && "$1" != --* ]] && ZIP_PATH="$1" ;;
    --rollback)     MODE="rollback" ;;
    --status)       MODE="status" ;;
    --logs)         MODE="logs" ;;
    --restart)      MODE="restart" ;;
    --reset-password) MODE="reset-password" ;;
    --help|-h)      usage ;;
    *)              echo -e "${RED}未知参数: $1${NC}"; usage ;;
  esac
  shift
done

# ---------- 工具函数 ----------
log()      { echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $*"; }
ok()       { echo -e "${GREEN}✓${NC} $*"; }
warn()     { echo -e "${YELLOW}⚠${NC} $*"; }
err()      { echo -e "${RED}✗${NC} $*" >&2; }

need_root() {
  if [[ $EUID -ne 0 ]]; then
    err "请用 root 或 sudo 运行（首次需要写 /var/lib/docker）"
    exit 1
  fi
}

# ---------- 子命令 ----------

cmd_status() {
  cd "$PROJECT_DIR"
  echo
  echo "=== 容器状态 ==="
  docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "NAMES|$APP_NAME" || echo "  (无)"
  echo
  echo "=== 镜像 ==="
  docker images luogu-ai-report/webapp --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" 2>/dev/null | head -10
  echo
  echo "=== 卷 ==="
  docker volume ls | grep luogu-ai-report || echo "  (无)"
  echo
  echo "=== .env 状态 ==="
  if [[ -f "$PROJECT_DIR/.env" ]]; then
    echo "  存在，行数：$(wc -l < "$PROJECT_DIR/.env")"
    grep -E "ADMIN_PASSWORD|OPENAI_API_KEY" "$PROJECT_DIR/.env" | sed 's/=.*/=***已设置***/' | sed 's/^/    /'
  else
    warn "  .env 不存在！需要创建：cp .env.example .env"
  fi
  echo
  echo "=== 健康检查 ==="
  if curl -fsS --max-time 5 http://127.0.0.1:5000/ >/dev/null 2>&1; then
    ok "  http://127.0.0.1:5000/ 可访问"
  else
    warn "  http://127.0.0.1:5000/ 不可访问"
  fi
}

cmd_logs() {
  cd "$PROJECT_DIR"
  docker compose logs -f --tail=200
}

cmd_restart() {
  cd "$PROJECT_DIR"
  log "改 .env 必须 down + up -d（restart 不会重读 env_file）"
  docker compose down
  docker compose up -d
  ok "已重启，10 秒后检查健康状态..."
  sleep 10
  cmd_status
}

cmd_reset_password() {
  cd "$PROJECT_DIR"
  if [[ ! -f .env ]]; then
    err ".env 不存在，请先 cp .env.example .env"
    exit 1
  fi
  # 用单引号避免 ! 解析
  NEW_PW='Luogu@Admin#2026Tx9k'
  sed -i "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=${NEW_PW}|" .env
  sed -i "s|^ADMIN_SESSION_SECRET=.*|ADMIN_SESSION_SECRET=$(openssl rand -hex 32)|" .env
  ok "新密码已写入：$NEW_PW"
  cmd_restart
}

# 从 zip 包部署
cmd_zip() {
  cd "$PROJECT_DIR"
  if [[ ! -f "$ZIP_PATH" ]]; then
    err "找不到 $ZIP_PATH"
    err "先把 zip 传到服务器：scp pkg.zip user@server:/home/ubuntu/luogu-ai-report/"
    exit 1
  fi

  log "1/6 停掉旧容器"
  docker compose down || true

  log "2/6 备份旧目录"
  if [[ -f docker-compose.yml ]] || [[ -f web_app.py ]]; then
    BACKUP_DIR="${PROJECT_DIR%/}/${BACKUP_PREFIX}.$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    # 备份关键文件
    cp docker-compose.yml Dockerfile requirements.txt .env.example "$BACKUP_DIR/" 2>/dev/null || true
    [[ -f .env ]] && cp .env "$BACKUP_DIR/.env.snapshot"
    [[ -f web_app.py ]] && cp web_app.py "$BACKUP_DIR/"
    ok "  备份到 $BACKUP_DIR"
  fi

  log "3/6 解压新包"
  command -v unzip >/dev/null || { warn "装 unzip..."; apt-get install -y unzip >/dev/null; }
  rm -rf .git
  unzip -oq "$ZIP_PATH" -d "$PROJECT_DIR"
  # 处理嵌套目录
  if [[ -d "$PROJECT_DIR/luogu-AI-report" ]]; then
    shopt -s dotglob
    mv "$PROJECT_DIR/luogu-AI-report/"* "$PROJECT_DIR/"
    rmdir "$PROJECT_DIR/luogu-AI-report"
  fi

  log "4/6 清理不进镜像的垃圾"
  rm -rf .git .source_cache reports __pycache__ tasks.db* *.pdf .dbg
  find "$PROJECT_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
  rm -f "$ZIP_PATH"

  log "5/6 检查 .env"
  if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
      cp .env.example .env
      warn "  .env 不存在，已用 .env.example 复制一份，请立即编辑："
      warn "  vim .env  必改：OPENAI_API_KEY / ADMIN_PASSWORD / ADMIN_SESSION_SECRET"
      err "未配置 .env，部署中止"
      exit 1
    else
      err "  .env 和 .env.example 都不存在！"
      exit 1
    fi
  else
    ok "  .env 已存在，保留"
  fi

  log "6/6 构建并启动"
  docker compose up -d --build

  ok "部署完成"
  sleep 8
  cmd_status
}

# git pull 部署
cmd_pull() {
  cd "$PROJECT_DIR"
  if [[ ! -d .git ]]; then
    err "当前不是 git 仓库，请用 --from-zip 方式部署"
    exit 1
  fi
  log "拉取最新代码"
  git pull --rebase --autostash
  log "停掉旧容器"
  docker compose down
  log "构建并启动"
  docker compose up -d --build
  ok "部署完成"
  sleep 8
  cmd_status
}

# 回滚
cmd_rollback() {
  cd "$PROJECT_DIR"
  # 找最近备份
  LATEST_BAK=$(ls -dt ${BACKUP_PREFIX}.* 2>/dev/null | head -1 || true)
  if [[ -z "$LATEST_BAK" ]]; then
    err "找不到备份目录（${BACKUP_PREFIX}.*）"
    exit 1
  fi
  warn "将回滚到：$LATEST_BAK"
  read -rp "确认？[y/N] " ans
  [[ "$ans" =~ ^[Yy]$ ]] || { echo "已取消"; exit 0; }
  docker compose down
  mv "$PROJECT_DIR" "${PROJECT_DIR}.broken.$(date +%H%M%S)"
  mv "$LATEST_BAK" "$PROJECT_DIR"
  cd "$PROJECT_DIR"
  docker compose up -d --build
  ok "回滚完成"
  sleep 8
  cmd_status
}

# ---------- 主流程 ----------

case "$MODE" in
  status)         cmd_status ;;
  logs)           cmd_logs ;;
  restart)        cmd_restart ;;
  reset-password) cmd_reset_password ;;
  pull)           need_root; cmd_pull ;;
  zip)            need_root; cmd_zip ;;
  rollback)       need_root; cmd_rollback ;;
  default)
    if [[ -f deploy-pkg.zip ]]; then
      need_root; cmd_zip
    elif [[ -d .git ]]; then
      need_root; cmd_pull
    else
      usage
    fi
    ;;
esac
