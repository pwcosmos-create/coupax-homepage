#!/usr/bin/env bash
# 명리 위원회 — 학습 카드 검증 (5분마다, 1회 4장, 부하 최소)
set -euo pipefail
BOARD="${BOARD:-/home/ubuntu/coupax-homepage/board}"
PY="${PY:-$BOARD/.venv/bin/python}"
LOG="${LOG:-/home/ubuntu/coupax-homepage/logs/saju_card_council.log}"
PER_TICK="${SAJU_COUNCIL_PER_TICK:-4}"
FAST="${SAJU_COUNCIL_FAST:-1}"
mkdir -p "$(dirname "$LOG")"
LINE="*/5 * * * * cd $BOARD && SAJU_COUNCIL_PER_TICK=$PER_TICK SAJU_COUNCIL_FAST=$FAST $PY scripts/agent_office_saju_card_council.py tick-cycle >> $LOG 2>&1"
( crontab -l 2>/dev/null | grep -v 'agent_office_saju_card_council.py' || true; echo "$LINE" ) | crontab -
echo "installed: $LINE"
echo "  SAJU_COUNCIL_PER_TICK=$PER_TICK (every 5 min, light load)"
