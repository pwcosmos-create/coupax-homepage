#!/bin/bash
# [사용 중단] board 전용 GEMINI 키는 board/.env 에만 둡니다.
# coupax_app 키를 복사하지 마세요 — deploy/set_board_gemini_key_only.sh 참고.
set -euo pipefail
echo "SKIP: board GEMINI_API_KEY is managed only in board/.env (not copied from coupax_app)."
echo "  To set: edit $BOARD/.env or run deploy/set_board_gemini_key_only.sh"
exit 0