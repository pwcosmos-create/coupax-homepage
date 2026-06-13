#!/usr/bin/env python3
"""원키스US 오류·매매 시나리오 학습 카드 일괄 시드.

  python scripts/seed_workisus_error_cards.py --add
  python scripts/seed_workisus_error_cards.py --sync
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_workisus_learn as learn  # noqa: E402
import workisus_agent_card_compose as wac  # noqa: E402
from workisus_atr_cards import all_atr_specs  # noqa: E402
from workisus_error_cards import all_error_specs  # noqa: E402


def _all_seed_specs() -> list[dict]:
    by: dict[str, dict] = {}
    for spec in list(all_error_specs()) + list(all_atr_specs()):
        seed = (spec.get("catalog_seed") or "").strip()
        if seed:
            by[seed] = spec
    return list(by.values())


def seed_errors(*, sync: bool = False) -> dict:
    import workisus_learn_policy as wlp

    if not wlp.is_card_production_enabled():
        return {"skipped": True, "reason": wlp.disabled_message()}
    added = synced = confirmed = 0
    for spec in _all_seed_specs():
        seed = (spec.get("catalog_seed") or "").strip()
        if not seed:
            continue
        existing = learn.find_card_by_seed(seed)
        if existing and not sync:
            continue
        card = wac.ensure_seed_card(seed, agent_id="workisus_sync", confirm=True)
        if not card:
            continue
        if existing:
            synced += 1
        else:
            added += 1
        if card.get("status") == "confirmed":
            confirmed += 1
    learn.export_pack()
    return {
        "added": added,
        "synced": synced,
        "confirmed": confirmed,
        "catalog": len(_all_seed_specs()),
        "stats": learn.stats(),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--add", action="store_true")
    p.add_argument("--sync", action="store_true")
    args = p.parse_args()
    if not (args.add or args.sync):
        p.print_help()
        return 1
    out = seed_errors(sync=args.sync)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
