#!/usr/bin/env python3
"""catalog_seed 중복 카드 정리 — 확정·최신 id 1장만 유지.

  python scripts/dedupe_kiwoom_cards_by_seed.py --dry-run
  python scripts/dedupe_kiwoom_cards_by_seed.py
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_kiwoom_learn as learn  # noqa: E402


def _pick_keeper(rows: list[dict]) -> dict:
    confirmed = [c for c in rows if c.get("status") == "confirmed"]
    pool = confirmed or rows
    return max(pool, key=lambda c: (c.get("id") or 0))


def run(*, dry_run: bool = True) -> dict:
    store = learn.load_store()
    cards = [c for c in store.get("cards") or [] if isinstance(c, dict)]
    by_seed: dict[str, list[dict]] = defaultdict(list)
    no_seed: list[dict] = []

    for c in cards:
        seed = (c.get("catalog_seed") or "").strip()
        if seed:
            by_seed[seed].append(c)
        else:
            no_seed.append(c)

    delete_ids: list[int] = []
    for seed, rows in by_seed.items():
        if len(rows) < 2:
            continue
        keeper = _pick_keeper(rows)
        for c in rows:
            cid = c.get("id")
            if isinstance(cid, int) and cid != keeper.get("id"):
                delete_ids.append(cid)

    deleted = 0
    if not dry_run:
        for cid in sorted(delete_ids):
            if learn.delete_card(cid):
                deleted += 1
        if deleted:
            learn.export_pack()
            try:
                import sync_kiwoom_wiki

                sync_kiwoom_wiki.main()
            except Exception:
                pass

    return {
        "dry_run": dry_run,
        "total": len(cards),
        "no_seed": len(no_seed),
        "duplicate_seeds": sum(1 for r in by_seed.values() if len(r) > 1),
        "would_delete": len(delete_ids),
        "deleted": deleted,
        "delete_ids": delete_ids[:30],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", default=False)
    ap.add_argument("--apply", action="store_true", help="실제 삭제")
    args = ap.parse_args()
    dry = not args.apply
    out = run(dry_run=dry)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
