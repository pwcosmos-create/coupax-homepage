#!/bin/bash
# board/.env 전용 Gemini 키 설정 (coupax_app 과 분리)
# 사용: GEMINI_API_KEY='...' bash deploy/set_board_gemini_key_only.sh
set -euo pipefail
BOARD="${BOARD:-/home/ubuntu/coupax-homepage/board}"
ENV="$BOARD/.env"
KEY="${GEMINI_API_KEY:-}"
if [ -z "$KEY" ]; then
  echo "FAIL: set GEMINI_API_KEY env var (board-only key)"
  exit 1
fi
touch "$ENV"
if grep -q '^GEMINI_API_KEY=' "$ENV"; then
  sed -i "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=$KEY|" "$ENV"
else
  printf '%s\n' "GEMINI_API_KEY=$KEY" >> "$ENV"
fi
# board 전용 — GOOGLE_API_KEY 는 board에서 Gemini fallback으로 쓰지 않음
grep -q '^GOOGLE_API_KEY=' "$ENV" && sed -i '/^GOOGLE_API_KEY=/d' "$ENV" || true
for v in SAJU_COMPOSE_LLM=1 SAJU_CARD_LLM_PROVIDER=gemini SAJU_CARD_LLM_ALLOW_OLLAMA_FALLBACK=0 SAJU_CARD_GEMINI_MODEL=gemini-2.5-flash SAJU_CARD_GEMINI_MAX_TOKENS=12000; do
  k="${v%%=*}"
  val="${v#*=}"
  if grep -q "^${k}=" "$ENV"; then
    sed -i "s|^${k}=.*|${k}=${val}|" "$ENV"
  else
    echo "${k}=${val}" >> "$ENV"
  fi
done
cd "$BOARD"
PY="${BOARD}/.venv/bin/python"
[ -x "$PY" ] || PY=python3
"$PY" scripts/saju_card_llm_compose.py status | head -1
echo "OK: board-only GEMINI_API_KEY in $ENV"
