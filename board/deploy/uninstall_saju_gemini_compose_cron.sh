#!/usr/bin/env bash
# PASS 카드 Gemini polish cron 제거 (API 비용 절감)
set -euo pipefail
( crontab -l 2>/dev/null | grep -v 'saju_card_llm_compose.py batch' || true ) | crontab -
echo "Removed saju_card_llm_compose.py batch from crontab."
echo "Also set SAJU_COMPOSE_LLM=0 in board/.env"
