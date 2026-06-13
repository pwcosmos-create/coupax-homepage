#!/usr/bin/env bash
# 홈페이지 디자인 카탈로그·토론 — 2시간마다
set -euo pipefail
BOARD="${BOARD_ROOT:-/home/ubuntu/coupax-homepage/board}"
PY="${BOARD}/.venv/bin/python"
CRON_TAG="coupax-homepage-design-catalog"
LINE="17 */2 * * * cd ${BOARD} && PYTHONPATH=scripts ${PY} scripts/homepage_design_catalog_maintain.py run >> ${BOARD}/logs/homepage_design_catalog.log 2>&1 # ${CRON_TAG}"
mkdir -p "${BOARD}/logs"
( crontab -l 2>/dev/null | grep -v "${CRON_TAG}" || true; echo "${LINE}" ) | crontab -
echo "installed: ${CRON_TAG}"
