#!/bin/bash
# 댓글 자동 답글 봇 cron 등록 (venv 파이썬·로그 디렉터리)
set -euo pipefail
# Oracle 기본: /home/opc/...  ubuntu 서버면 설치 시:
#   COMMENT_BOT_BOARD_DIR=/home/ubuntu/coupax-homepage/board bash deploy/install_comment_bot_cron.sh
BOARD="${COMMENT_BOT_BOARD_DIR:-/home/opc/coupax-homepage/board}"
LOGDIR="$BOARD/logs"
mkdir -p "$LOGDIR"
ENV_FILE="$BOARD/.env.comment_bot"
# 운영자: ENV 파일에 다음 예시로 설정할 것
#   export COMMENT_BOT_ENABLED=1
#   export COMMENT_BOT_PASSWORD='...'
#   export COMMENT_BOT_MIN_COMMENT_ID=123   # 최초 배포 시 현재 최대 댓글 id
# 선택: OPENAI_API_KEY, COMMENT_BOT_AUTHOR, COMMENT_BOT_POST_IDS 등
# shellcheck disable=SC2016
CRON_LINE="*/15 * * * * . $ENV_FILE 2>/dev/null; cd $BOARD && $BOARD/.venv/bin/python scripts/comment_reply_bot.py >> $LOGDIR/comment_reply_bot.log 2>&1"
( crontab -l 2>/dev/null | grep -v 'comment_reply_bot.py' || true
  echo "$CRON_LINE"
) | crontab -
echo "Installed (loads $ENV_FILE if present):"
crontab -l | grep comment_reply_bot || true
echo "If first time: create $ENV_FILE with COMMENT_BOT_ENABLED=1 and COMMENT_BOT_PASSWORD."
