#!/bin/bash
# 사주 학습 카드 — 분당 10장 추가 + Gemini 2.5 해설 (각 5초 간격)
set -euo pipefail
BOARD="${BOARD_ROOT:-/home/ubuntu/coupax-homepage/board}"
PY="${BOARD}/.venv/bin/python"
[ -x "$PY" ] || PY="python3"
LOG_DIR="/home/ubuntu/coupax-homepage/logs"
mkdir -p "$LOG_DIR"
PER_MIN="${SAJU_CARDS_PER_MINUTE:-10}"
SLEEP="${SAJU_CARDS_SLEEP_SEC:-5}"
GEMINI_N="${SAJU_GEMINI_BATCH_PER_MIN:-10}"
GEMINI_SLEEP="${SAJU_GEMINI_BATCH_SLEEP:-5}"
ADD_LINE="* * * * * cd $BOARD && $PY scripts/saju_auto_add_cards.py --per-minute $PER_MIN --sleep $SLEEP >> $LOG_DIR/saju_auto_cards.log 2>&1"
GEMINI_LINE="* * * * * cd $BOARD && $PY scripts/saju_card_llm_compose.py batch --count $GEMINI_N --sleep $GEMINI_SLEEP >> $LOG_DIR/saju_gemini_compose.log 2>&1"
( crontab -l 2>/dev/null | grep -v "saju_auto_add_cards.py" | grep -v "saju_card_llm_compose.py batch" || true
  echo "$ADD_LINE"
  echo "$GEMINI_LINE"
) | crontab -
echo "installed add: $ADD_LINE"
echo "installed gemini: $GEMINI_LINE"
echo "  SAJU_CARDS_PER_MINUTE=$PER_MIN SAJU_GEMINI_BATCH_PER_MIN=$GEMINI_N"
