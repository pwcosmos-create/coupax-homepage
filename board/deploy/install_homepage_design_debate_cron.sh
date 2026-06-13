#!/usr/bin/env bash
# 홈페이지 디자인 토론 주제 자동 생성 — 45분마다 (위원회 젬마 주기와 동일)
set -euo pipefail
BOARD="${BOARD_ROOT:-/home/ubuntu/coupax-homepage/board}"
PY="${BOARD}/.venv/bin/python"
CRON_TAG="coupax-homepage-design-debate-auto"
MAX="${HOMEPAGE_DESIGN_DEBATE_MAX_PER_RUN:-1}"
LINE="7,52 * * * * cd ${BOARD} && PYTHONPATH=scripts HOMEPAGE_DESIGN_DEBATE_AUTO=1 HOMEPAGE_DESIGN_DEBATE_MAX_PER_RUN=${MAX} ${PY} scripts/homepage_design_debate_generator.py run >> ${BOARD}/logs/homepage_design_debate.log 2>&1 # ${CRON_TAG}"
mkdir -p "${BOARD}/logs"
( crontab -l 2>/dev/null | grep -v "${CRON_TAG}" || true; echo "${LINE}" ) | crontab -
echo "installed: ${CRON_TAG} (max ${MAX} topic/run)"
