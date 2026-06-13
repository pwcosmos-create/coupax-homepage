#!/usr/bin/env bash
# 종목 시리즈 추천 운영: env 보강 + 종합조사 초안 cron 제거 + 시리즈 cron 등록
set -euo pipefail
BOARD="${BOARD_DIR:-/home/ubuntu/coupax-homepage/board}"
ENV_FILE="${BOARD}/.env"
PY="${BOARD}/.venv/bin/python"
LOG_DIR="$(dirname "$BOARD")/logs"
mkdir -p "$LOG_DIR"

touch "$ENV_FILE"
set_env() {
  local key="$1" val="$2"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    echo "${key}=${val}" >> "$ENV_FILE"
  fi
}

set_env BLOG_STOCK_SERIES_ENABLED 1
set_env BLOG_STOCK_SERIES_PER_DAY 2
set_env BLOG_STOCK_SERIES_AGENT_RESEARCH 1
set_env BLOG_STOCK_SERIES_FORCE_AGENTS 1
set_env BLOG_RESEARCH_DRAFT_ENABLED 0

# 종합 조사 하루 1건 cron 제거 (종목 시리즈와 중복 방지)
( crontab -l 2>/dev/null | grep -v "blog_research_draft.py ensure" || true ) | crontab -

bash "${BOARD}/deploy/install_blog_stock_series_cron.sh"

echo "OK: BLOG_STOCK_SERIES_PER_DAY=2, BLOG_RESEARCH_DRAFT_ENABLED=0, cron installed"
