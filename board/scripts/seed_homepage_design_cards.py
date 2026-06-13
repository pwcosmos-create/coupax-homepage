#!/usr/bin/env python3
"""홈페이지 디자인 학습 카드 시드.

  python scripts/seed_homepage_design_cards.py --add
  python scripts/seed_homepage_design_cards.py --sync
  python scripts/seed_homepage_design_cards.py --reset
  python scripts/seed_homepage_design_cards.py --debate   # 토론 주제만 위원회 합성
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_homepage_design_learn as learn  # noqa: E402
import agent_office_wiki_store as wiki  # noqa: E402
import json_store  # noqa: E402
from homepage_design_card_catalog import all_design_specs, debate_specs  # noqa: E402


def reset_cards() -> None:
    data = {"updated_at": learn._now(), "cards": []}
    json_store.save_json(learn.CARDS_PATH, data)


def _used_seeds() -> set[str]:
    out: set[str] = set()
    for c in learn.load_store().get("cards") or []:
        if isinstance(c, dict):
            seed = (c.get("catalog_seed") or "").strip()
            if seed:
                out.add(seed)
    return out


def seed_all(*, sync: bool = False, confirm: bool = True) -> dict:
    used = _used_seeds()
    added = synced = 0
    for spec in all_design_specs():
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
                use_council=(spec.get("category") == "debate"),
            )
            added += 1
        else:
            card = existing
        if confirm and card and card.get("status") != "confirmed" and card.get("id"):
            learn.confirm_card(int(card["id"]))
            try:
                wiki.save_design_card_to_knowledge(learn.find_card_by_seed(seed) or card)
            except Exception:
                pass
    learn.export_pack()
    return {"added": added, "synced": synced, "stats": learn.stats()}


def seed_debates() -> dict:
    import homepage_design_council as hdc

    results = []
    for spec in debate_specs():
        out = hdc.run_one_debate(auto_confirm=True)
        results.append({"seed": spec.get("catalog_seed"), **out})
    return {"debates": results, "stats": learn.stats()}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--reset", action="store_true")
    p.add_argument("--add", action="store_true")
    p.add_argument("--sync", action="store_true")
    p.add_argument("--debate", action="store_true")
    p.add_argument("--no-confirm", action="store_true")
    args = p.parse_args()
    if args.reset:
        reset_cards()
    if args.debate:
        print(json.dumps(seed_debates(), ensure_ascii=False, indent=2))
        return 0
    if args.add or args.sync or args.reset:
        print(
            json.dumps(
                seed_all(sync=args.sync or args.reset, confirm=not args.no_confirm),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
