#!/usr/bin/env bash
# 사주 학습부 8종 젬마 ON + 위원회 cron(FAST 옵션)
set -euo pipefail
BOARD="${BOARD:-/home/ubuntu/coupax-homepage/board}"
PY="${PY:-$BOARD/.venv/bin/python}"
FAST="${SAJU_COUNCIL_FAST:-0}"

cd "$BOARD"
"$PY" scripts/merge_saju_agents_registry.py

"$PY" - <<'PY'
import json
from pathlib import Path

reg = Path("data/agent_registry.json")
data = json.loads(reg.read_text(encoding="utf-8"))
saju_ids = {
    "saju_privacy",
    "saju_reader",
    "saju_structurer",
    "saju_scholar",
    "saju_curator",
    "saju_rl",
    "saju_error_fix",
    "saju_reinspector",
}
for a in data.get("agents") or []:
    if isinstance(a, dict) and a.get("id") in saju_ids:
        a["mode_on"] = True
        a["interval_minutes"] = 0
        a["interval_label"] = "항상"
        a.setdefault("division", "saju-learn")
reg.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("saju_learn_agents=ON count", sum(1 for a in data["agents"] if a.get("id") in saju_ids))
PY

ENV="$BOARD/.env"
touch "$ENV"
if grep -q '^SAJU_COUNCIL_FAST=' "$ENV"; then
  sed -i "s|^SAJU_COUNCIL_FAST=.*|SAJU_COUNCIL_FAST=$FAST|" "$ENV"
else
  echo "SAJU_COUNCIL_FAST=$FAST" >> "$ENV"
fi

bash "$BOARD/deploy/install_saju_card_council_cron.sh"
echo "SAJU_COUNCIL_FAST=$FAST in $ENV"
"$PY" scripts/agent_office_saju_card_council.py status
