"""로컬/서버 agent_registry.json 에 사주 학습부 에이전트가 없으면 추가."""
from __future__ import annotations

import json
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
REG = BOARD / "data" / "agent_registry.json"

SAJU_IDS = (
    "saju_privacy",
    "saju_reader",
    "saju_structurer",
    "saju_scholar",
    "saju_curator",
    "saju_rl",
    "saju_error_fix",
    "saju_reinspector",
)


def main() -> int:
    reg = json.loads(REG.read_text(encoding="utf-8"))
    ids = {a.get("id") for a in reg.get("agents") or []}
    seed = json.loads(REG.read_text(encoding="utf-8"))
    saju = [a for a in seed.get("agents") or [] if a.get("id") in SAJU_IDS]
    added = 0
    for a in saju:
        if a.get("id") not in ids:
            reg.setdefault("agents", []).append(a)
            added += 1
    for a in reg.get("agents") or []:
        if isinstance(a, dict) and a.get("id") not in SAJU_IDS:
            a.setdefault("division", "finance")
    REG.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"added={added} total_agents={len(reg.get('agents') or [])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
