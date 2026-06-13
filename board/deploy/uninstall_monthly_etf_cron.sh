#!/bin/bash
# search-etf 연동 일일 sync cron 제거
set -euo pipefail
( crontab -l 2>/dev/null | grep -v 'sync_daily_monthly_etfs' || true ) | crontab -
echo "Removed sync_daily_monthly_etfs from crontab (if present)."
crontab -l 2>/dev/null | grep -E 'sync_daily|monthly_etf' || echo "(no related cron lines)"
