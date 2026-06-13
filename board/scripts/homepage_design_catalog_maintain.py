#!/usr/bin/env python3
"""홈페이지 디자인 카탈로그 → 학습 카드 sync + 토론 1건.

  python scripts/homepage_design_catalog_maintain.py run
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
from homepage_design_card_catalog import all_design_specs  # noqa: E402


def sync_catalog(*, confirm: bool = True, dry_run: bool = False) -> dict:
    added = revised = confirmed = 0
    for spec in all_design_specs():
        seed = (spec.get("catalog_seed") or "").strip()
        if not seed:
            continue
        title = spec.get("title") or seed
        body = spec.get("body") or ""
        category = spec.get("category") or ""
        existing = learn.find_card_by_seed(seed)
        if dry_run:
            if not existing:
                added += 1
            continue
        if existing:
            learn.revise_card(
                int(existing["id"]),
                body=body,
                title=title,
                catalog_seed=seed,
                reconfirm=existing.get("status") == "confirmed",
            )
            revised += 1
            card = learn.find_card_by_seed(seed)
        else:
            card = learn.add_card(
                body=body,
                title=title,
                source="catalog_seed",
                catalog_seed=seed,
                category=category,
                use_council=category == "debate",
                revise_if_seed_exists=False,
            )
            added += 1
        if confirm and card and card.get("status") != "confirmed" and isinstance(card.get("id"), int):
            learn.confirm_card(int(card["id"]))
            confirmed += 1
            try:
                wiki.save_design_card_to_knowledge(learn.find_card_by_seed(seed) or card)
            except Exception:
                pass
    learn.export_pack()
    return {"added": added, "revised": revised, "confirmed": confirmed}


def run(*, debate: bool = True, dry_run: bool = False) -> dict:
    out = {"sync": sync_catalog(confirm=True, dry_run=dry_run)}
    if debate and not dry_run:
        try:
            import homepage_design_council as hdc

            out["debate"] = hdc.run_debate_cycle()
        except Exception as e:
            out["debate"] = {"ok": False, "error": str(e)}
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("cmd", nargs="?", default="run")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-debate", action="store_true")
    args = p.parse_args()
    if args.cmd != "run":
        p.print_help()
        return 1
    print(json.dumps(run(debate=not args.no_debate, dry_run=args.dry_run), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
