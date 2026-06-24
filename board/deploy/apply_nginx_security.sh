#!/usr/bin/env bash
set -euo pipefail
CONF_SRC="${1:-/home/ubuntu/coupax-homepage/board/deploy/000-coupax.co.kr.nginx}"
CONF_DST="/etc/nginx/sites-available/coupax.co.kr"
sudo cp "$CONF_SRC" "$CONF_DST"
sudo nginx -t
sudo systemctl reload nginx
echo "OK: nginx reloaded"
