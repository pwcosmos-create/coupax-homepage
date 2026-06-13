#!/bin/bash
# coupax 월배당 ETF 일일 동기화 cron — search-etf 중단으로 등록하지 않음
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
bash "$SCRIPT_DIR/uninstall_monthly_etf_cron.sh"
echo ""
echo "search-etf.com API 호출 중단 정책: cron 미등록."
echo "CSV 병합만 필요하면 수동: python scripts/sync_daily_monthly_etfs.py"
