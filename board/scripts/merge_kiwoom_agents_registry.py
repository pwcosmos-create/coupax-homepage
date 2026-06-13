"""agent_registry.json 에 차수거래(kiwoom-chasu) 에이전트가 없으면 추가."""
from __future__ import annotations

import json
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
REG = BOARD / "data" / "agent_registry.json"

KIWOM_IDS = (
    "kiwoom_reader",
    "kiwoom_risk",
    "kiwoom_structurer",
    "kiwoom_order",
    "kiwoom_account",
    "kiwoom_privacy",
    "kiwoom_curator",
    "kiwoom_rl",
    "kiwoom_error_fix",
    "kiwoom_monitor",
    "kiwoom_catalog",
)


def main() -> int:
    reg = json.loads(REG.read_text(encoding="utf-8"))
    ids = {a.get("id") for a in reg.get("agents") or [] if isinstance(a, dict)}
    seed_path = BOARD / "data" / "kiwoom_agents_seed.json"
    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    kiwoom = [a for a in seed.get("agents") or [] if isinstance(a, dict) and a.get("id") in KIWOM_IDS]
    if not kiwoom:
        print("no kiwoom seed agents in registry — update local agent_registry.json first")
        return 1
    added = 0
    for a in kiwoom:
        if a.get("id") not in ids:
            reg.setdefault("agents", []).append(dict(a))
            added += 1
            ids.add(a.get("id"))
    for a in reg.get("agents") or []:
        if isinstance(a, dict) and a.get("id") in KIWOM_IDS:
            a["division"] = "kiwoom-chasu"
    REG.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"added={added} kiwoom_total={sum(1 for a in reg.get('agents') or [] if a.get('id') in KIWOM_IDS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
