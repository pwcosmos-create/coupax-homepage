#!/usr/bin/env bash
# 종목 시리즈: 장 마감 후 신규 글 1종목 + 기존 시리즈 글 댓글 갱신
set -euo pipefail
BOARD="${BOARD_DIR:-/home/ubuntu/coupax-homepage/board}"
PY="${BOARD}/.venv/bin/python"
LOG_DIR="${BOARD}/../logs"
mkdir -p "$LOG_DIR"
# 16:10 KST — 시세 sync 후 발행·댓글 (stock_watch 30분 cron과 맞춤)
LINE="10 16 * * 1-5 cd ${BOARD} && BLOG_STOCK_SERIES_ENABLED=1 PYTHONPATH=scripts ${PY} scripts/blog_stock_series.py tick >> ${LOG_DIR}/blog_stock_series.log 2>&1"
( crontab -l 2>/dev/null | grep -v "blog_stock_series.py" || true
  echo "$LINE"
) | crontab -
echo "installed: $LINE"
