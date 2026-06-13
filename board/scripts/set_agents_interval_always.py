"""모든 에이전트 작업 주기를 항상(0분 = cron마다)으로 설정."""
from __future__ import annotations

import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import agent_registry


def main() -> int:
    data = agent_registry.load_registry()
    for a in data.get("agents") or []:
        if isinstance(a, dict):
            a["interval_minutes"] = 0
            a["interval_label"] = "항상"
    agent_registry.save_registry(data)
    for a in data.get("agents") or []:
        print(f"{a.get('id')}: interval=항상 (cron 5분마다)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
