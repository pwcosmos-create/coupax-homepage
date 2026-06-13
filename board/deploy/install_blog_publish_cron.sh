#!/usr/bin/env bash
# 블로그 순차 발행 — 하루 1건, 랜덤 시각 (plan 00:20 + tick 5분마다)
set -euo pipefail
BOARD="${BOARD_DIR:-/home/ubuntu/coupax-homepage/board}"
PY="${BOARD}/.venv/bin/python"
DRAFT_LINE="15 0 * * * cd ${BOARD} && BLOG_RESEARCH_DRAFT_ENABLED=1 ${PY} scripts/blog_research_draft.py ensure >> logs/blog_publish.log 2>&1"
PLAN_LINE="20 0 * * * cd ${BOARD} && BLOG_SCHEDULED_PUBLISH_ENABLED=1 ${PY} scripts/blog_publish_scheduler.py plan >> logs/blog_publish.log 2>&1"
TICK_LINE="*/5 * * * * cd ${BOARD} && BLOG_SCHEDULED_PUBLISH_ENABLED=1 ${PY} scripts/blog_publish_scheduler.py tick >> logs/blog_publish.log 2>&1"

mkdir -p "${BOARD}/logs"
( crontab -l 2>/dev/null | grep -v "blog_publish_scheduler.py" | grep -v "blog_research_draft.py" || true
  echo "${DRAFT_LINE}"
  echo "${PLAN_LINE}"
  echo "${TICK_LINE}"
) | crontab -
echo "Installed blog publish scheduler:"
echo "${PLAN_LINE}"
echo "${TICK_LINE}"
