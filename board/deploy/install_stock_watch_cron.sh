#!/bin/bash
# 주식 시황 스냅샷 — 30분마다 (worker 와 병행 백업)
set -euo pipefail
BOARD="${BOARD_ROOT:-/home/ubuntu/coupax-homepage/board}"
PY="${BOARD}/.venv/bin/python"
[ -x "$PY" ] || PY="python3"
LOG_DIR="/home/ubuntu/coupax-homepage/logs"
mkdir -p "$LOG_DIR"
LINE="*/30 * * * * cd $BOARD && PYTHONPATH=scripts $PY scripts/agent_office_stock_watch.py sync && PYTHONPATH=scripts $PY scripts/sync_stock_wiki.py >> $LOG_DIR/stock_watch.log 2>&1"
UNI="0 6 * * 1 cd $BOARD && PYTHONPATH=scripts $PY scripts/stock_kr_universe.py refresh >> $LOG_DIR/stock_universe.log 2>&1"
( crontab -l 2>/dev/null | grep -v "agent_office_stock_watch.py" | grep -v "stock_kr_universe.py" || true
  echo "$LINE"
  echo "$UNI"
) | crontab -
echo "installed: $LINE"
echo "installed: $UNI"
