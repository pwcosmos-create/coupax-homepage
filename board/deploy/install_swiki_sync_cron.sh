#!/usr/bin/env bash
# pwcosmos-swiki ↔ 젬마 지식 양방향 동기화 (15분마다)
set -euo pipefail
BOARD="${BOARD_DIR:-/home/ubuntu/coupax-homepage/board}"
PY="${BOARD}/.venv/bin/python"
CRON_LINE="*/15 * * * * cd ${BOARD} && SWIKI_SYNC_ENABLED=1 ${PY} scripts/agent_office_swiki_sync.py sync >> logs/swiki_sync.log 2>&1"

mkdir -p "${BOARD}/logs"
( crontab -l 2>/dev/null | grep -v "agent_office_swiki_sync.py" || true
  echo "${CRON_LINE}"
) | crontab -
echo "Installed:"
echo "${CRON_LINE}"
