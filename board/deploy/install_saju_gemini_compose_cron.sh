#!/bin/bash
# PASS 카드 Gemini 2.5 해설 — 분당 N장
# llm_composed_at 이 있는 카드는 batch 가 건너뜀(저장본 재사용, API 재호출 없음)
set -euo pipefail
BOARD="${BOARD:-/home/ubuntu/coupax-homepage/board}"
PY="${PY:-$BOARD/.venv/bin/python}"
LOG="${LOG:-/home/ubuntu/coupax-homepage/logs/saju_gemini_compose.log}"
N="${SAJU_GEMINI_BATCH_PER_MIN:-10}"
SLEEP="${SAJU_GEMINI_BATCH_SLEEP:-5}"
mkdir -p "$(dirname "$LOG")"
LINE="* * * * * cd $BOARD && $PY scripts/saju_card_llm_compose.py batch --count $N --sleep $SLEEP >> $LOG 2>&1"
( crontab -l 2>/dev/null | grep -v 'saju_card_llm_compose.py batch' || true; echo "$LINE" ) | crontab -
echo "installed: $LINE"
