#!/usr/bin/env python3
"""관상 학습 카드 시드.

  python scripts/seed_gwansang_cards.py --add
  python scripts/seed_gwansang_cards.py --sync
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_gwansang_learn as learn  # noqa: E402
import agent_office_wiki_store as wiki  # noqa: E402
from gwansang_card_catalog import all_gwansang_specs  # noqa: E402


def _used_seeds() -> set[str]:
    return {
        (c.get("catalog_seed") or "").strip()
        for c in learn.load_store().get("cards") or []
        if isinstance(c, dict) and (c.get("catalog_seed") or "").strip()
    }


def seed_all(*, sync: bool = False, confirm: bool = True) -> dict:
    used = _used_seeds()
    added = synced = 0
    for spec in all_gwansang_specs():
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
            card = learn.add_card(
                body=spec.get("body") or "",
                title=spec.get("title") or seed,
                source="catalog_seed",
                catalog_seed=seed,
                category=spec.get("category") or "",
            )
            added += 1
        else:
            card = existing
        if confirm and card and card.get("status") != "confirmed" and card.get("id"):
            learn.confirm_card(int(card["id"]))
            try:
                wiki.save_gwansang_card_to_knowledge(learn.find_card_by_seed(seed) or card)
            except Exception:
                pass
    learn.export_pack()
    return {"added": added, "synced": synced, "stats": learn.stats()}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--add", action="store_true")
    p.add_argument("--sync", action="store_true")
    args = p.parse_args()
    if not args.add and not args.sync:
        p.print_help()
        return 1
    out = seed_all(sync=args.sync)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
