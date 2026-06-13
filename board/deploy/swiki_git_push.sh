#!/bin/bash
set -euo pipefail
REPO="${1:-/home/ubuntu/coupax-homepage/board/data/pwcosmos-swiki}"
cd "$REPO"
git config user.email "${SWIKI_GIT_EMAIL:-office@coupax.co.kr}"
git config user.name "${SWIKI_GIT_NAME:-Coupax Agent Office}"
git add -A
if git diff --cached --quiet; then
  echo "nothing to commit"
else
  git commit -m "sync: dedupe orphans and consolidate coupax wiki"
fi
git pull --rebase origin main
git push origin main
echo "OK"
