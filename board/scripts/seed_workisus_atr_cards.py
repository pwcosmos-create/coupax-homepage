#!/usr/bin/env python3
"""원키스US ATR 지식 카드만 시드·확정.

  python scripts/seed_workisus_atr_cards.py --add
  python scripts/seed_workisus_atr_cards.py --sync
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
import workisus_atr_card_rl_compose as rl_comp  # noqa: E402
from workisus_atr_cards import all_atr_specs  # noqa: E402


def seed_atr(*, sync: bool = False, rl_enrich: bool = True) -> dict:
    import workisus_learn_policy as wlp

    if not wlp.is_card_production_enabled():
        return {"skipped": True, "reason": wlp.disabled_message()}
    added = synced = rl_tagged = 0
    for spec in all_atr_specs():
        seed = (spec.get("catalog_seed") or "").strip()
        if not seed:
            continue
        existing = learn.find_card_by_seed(seed)
        if existing and not sync:
            continue
        body_spec = rl_comp.enrich_spec(spec) if rl_enrich else spec
        if existing and sync:
            learn.revise_card(
                int(existing["id"]),
                body=body_spec.get("body") or "",
                title=body_spec.get("title") or None,
                catalog_seed=seed,
                reconfirm=existing.get("status") == "confirmed",
            )
            store = learn.load_store()
            for c in store.get("cards") or []:
                if isinstance(c, dict) and c.get("id") == existing.get("id"):
                    c["category"] = "atr_rl"
                    c["source"] = c.get("source") or "atr_rl_seed"
                    c["rl_enriched"] = True
                    learn.save_store(store)
                    break
            rl_tagged += 1
            continue
        wac.ensure_seed_card(seed, agent_id="workisus_atr_rl", confirm=True)
        ex2 = learn.find_card_by_seed(seed)
        if ex2:
            store = learn.load_store()
            for c in store.get("cards") or []:
                if isinstance(c, dict) and c.get("catalog_seed") == seed:
                    c["category"] = "atr_rl"
                    c["source"] = "atr_rl_seed"
                    c["rl_enriched"] = True
                    learn.save_store(store)
                    rl_tagged += 1
                    break
        added += 1
    learn.export_pack()
    return {
        "added": added,
        "synced": synced,
        "rl_tagged": rl_tagged,
        "catalog": len(all_atr_specs()),
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
    print(json.dumps(seed_atr(sync=args.sync), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
