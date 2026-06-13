#!/usr/bin/env python3
"""원키스 US 차수 학습 카드 시드.

  python scripts/seed_workisus_cards.py --add
  python scripts/seed_workisus_cards.py --sync
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_wiki_store as wiki  # noqa: E402
import agent_office_workisus_learn as learn  # noqa: E402
import json_store  # noqa: E402
import workisus_agent_card_compose as wac  # noqa: E402
from workisus_card_catalog import all_workisus_specs  # noqa: E402


def _used_seeds() -> set[str]:
    out: set[str] = set()
    for c in learn.load_store().get("cards") or []:
        if isinstance(c, dict):
            seed = (c.get("catalog_seed") or "").strip()
            if seed:
                out.add(seed)
    return out


def seed_all(*, sync: bool = False, confirm: bool = True) -> dict:
    import workisus_learn_policy as wlp

    if not wlp.is_card_production_enabled():
        return {"skipped": True, "reason": wlp.disabled_message()}
    used = _used_seeds()
    added = synced = 0
    for spec in all_workisus_specs():
        seed = (spec.get("catalog_seed") or "").strip()
        if not seed:
            continue
        if not sync and seed in used:
            continue
        existing = learn.find_card_by_seed(seed)
        if existing and sync:
            learn.revise_card(
                int(existing["id"]),
                body=spec.get("body") or "",
                title=spec.get("title") or seed,
                catalog_seed=seed,
                reconfirm=existing.get("status") == "confirmed",
            )
            synced += 1
            card = learn.find_card_by_seed(seed)
        elif not existing:
            card = wac.ensure_seed_card(seed, agent_id="workisus_sync", confirm=False)
            if not card:
                card = learn.add_card(
                    body=spec.get("body") or "",
                    title=spec.get("title") or seed,
                    source="catalog_seed",
                    catalog_seed=seed,
                    category=spec.get("category") or "workisus",
                    use_council=False,
                )
            added += 1
        else:
            card = existing
        if confirm and card and card.get("status") != "confirmed" and card.get("id"):
            learn.confirm_card(int(card["id"]))
            try:
                wiki.save_workisus_card_to_knowledge(learn.find_card_by_seed(seed) or card)
            except Exception:
                pass
    learn.export_pack()
    return {"added": added, "synced": synced, "stats": learn.stats()}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--add", action="store_true")
    p.add_argument("--sync", action="store_true")
    args = p.parse_args()
    if not (args.add or args.sync):
        p.print_help()
        return 1
    out = seed_all(sync=args.sync)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
