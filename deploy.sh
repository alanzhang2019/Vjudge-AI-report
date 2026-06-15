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
# v3.9.43: deploy.ps1 上传的是 luogu-ai-report-pkg.{tar.gz,zip}（不是 deploy-pkg.*），
# 兼容老名字 + 新名字
ZIP_PATH="${PROJECT_DIR}/luogu-ai-report-pkg.tar.gz"
# 向后兼容：找老的 zip / 老的命名
[[ ! -f "$ZIP_PATH" ]] && [[ -f "${PROJECT_DIR}/deploy-pkg.tar.gz" ]] && ZIP_PATH="${PROJECT_DIR}/deploy-pkg.tar.gz"
[[ ! -f "$ZIP_PATH" ]] && [[ -f "${PROJECT_DIR}/luogu-ai-report-pkg.zip" ]] && ZIP_PATH="${PROJECT_DIR}/luogu-ai-report-pkg.zip"
[[ ! -f "$ZIP_PATH" ]] && [[ -f "${PROJECT_DIR}/deploy-pkg.zip" ]] && ZIP_PATH="${PROJECT_DIR}/deploy-pkg.zip"
echo "[v3.9.43] ZIP_PATH=$ZIP_PATH"
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
  shift || true   # v3.9.41 fix: $#=0 时 shift 返回 1，set -e 会让脚本静默退出
done

# ---------- 工具函数 ----------
log()      { echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $*"; }
ok()       { echo -e "${GREEN}✓${NC} $*"; }
warn()     { echo -e "${YELLOW}⚠${NC} $*"; }
err()      { echo -e "${RED}✗${NC} $*" >&2; }

need_root() {
  # v3.9.43: 服务器上 ubuntu 用户在 docker 组里，能直接跑 docker compose（不需要 sudo），
  # 原先严格检查 EUID=0 会让 ubuntu 部署全部失败。改为：root 直接通过；
  # docker 组用户警告后通过；其他用户拒绝。
  if [[ $EUID -eq 0 ]]; then
    return 0
  fi
  if id -nG "$USER" 2>/dev/null | tr ' ' '\n' | grep -qx 'docker' \
     || groups 2>/dev/null | tr ' ' '\n' | grep -qx 'docker'; then
    warn "EUID=$EUID（非 root），但用户 $USER 在 docker 组里，docker compose 可以直接跑"
    return 0
  fi
  err "请用 root 或 sudo 运行（首次需要写 /var/lib/docker），或把当前用户加入 docker 组"
  exit 1
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
  command -v tar >/dev/null || { warn "装 tar..."; apt-get install -y tar >/dev/null; }
  rm -rf .git
  # v3.9.42 兼容 zip 和 tar.gz：自动识别
  case "$ZIP_PATH" in
    *.tar.gz|*.tgz)
      tar -xzf "$ZIP_PATH" -C "$PROJECT_DIR"
      ;;
    *.zip)
      command -v unzip >/dev/null || { warn "装 unzip..."; apt-get install -y unzip >/dev/null; }
      unzip -oq "$ZIP_PATH" -d "$PROJECT_DIR"
      ;;
    *)
      err "未知压缩格式: $ZIP_PATH（需要 .zip / .tar.gz / .tgz）"
      exit 1
      ;;
  esac
  # 处理嵌套目录
  if [[ -d "$PROJECT_DIR/luogu-AI-report" ]]; then
    shopt -s dotglob
    mv "$PROJECT_DIR/luogu-AI-report/"* "$PROJECT_DIR/"
    rmdir "$PROJECT_DIR/luogu-AI-report"
  fi

  log "4/6 清理不进镜像的垃圾（reports 保留！那是 bind-mount 用户数据）"
  # v3.9.43：明确只清构建产物，避开所有用户数据（reports/ tasks.db 命名卷 / source_cache 命名卷）。
  # 原来 `rm -rf .git .source_cache __pycache__ tasks.db* *.pdf .dbg` 这行虽然 glob 不递归、
  # 不会误伤 bind mount，但语义上很危险：
  #   1) tasks.db* 写出来像个通用 sqlite 模式，未来如果有人误把 tasks.db 写到项目根目录就清空了
  #   2) *.pdf 同样，未来如果 REPORTS_DIR 改成不 bind mount，会被这一行误删历史报告
  # 因此拆开成 3 类：
  #   - 项目根的 git 元数据（不是 .gitignore 里那种，是真的 .git 目录——docker build 不会带，但 deploy 安全起见再清一次）
  #   - 项目根的源码缓存（Dockerfile 应当 .dockerignore 它，但保险起见）
  #   - 全目录 __pycache__（必须递归，否则 .pyc 会污染下一轮镜像）
  #   - 全目录 .dbg 调试文件（递归）
  # **不**碰：*.pdf / *.db / *.sqlite（这些是用户数据，可能落在项目根或者任何子目录）
  rm -rf "$PROJECT_DIR/.git" "$PROJECT_DIR/.source_cache" "$PROJECT_DIR/.dbg"
  find "$PROJECT_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
  find "$PROJECT_DIR" -name "*.dbg" -type f -delete 2>/dev/null
  # 约定的临时导出目录（如果存在则清空，不删目录本身，保留权限）
  if [[ -d "$PROJECT_DIR/exports" ]]; then
    find "$PROJECT_DIR/exports" -mindepth 1 -delete 2>/dev/null
  fi
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
