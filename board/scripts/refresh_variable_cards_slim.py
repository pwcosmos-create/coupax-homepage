#!/usr/bin/env python3
"""변수·/해석· 카드 본문 슬림 재작성 (심층· 제외). --dry-run / --limit N"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_saju_learn as learn  # noqa: E402
from saju_card_reverify_enrich import compose_new_card  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int, default=0, help="0=전체")
    args = p.parse_args()

    updated = 0
    scanned = 0
    for c in learn.load_store().get("cards") or []:
        if not isinstance(c, dict) or c.get("status") != "confirmed":
            continue
        title = (c.get("title") or "").strip()
        if title.startswith("심층·"):
            continue
        if not (title.startswith("변수·") or title.startswith("해석·")):
            continue
        scanned += 1
        if args.limit and updated >= args.limit:
            break
        cid = c.get("id")
        if not isinstance(cid, int):
            continue
        pkg = compose_new_card(
            title,
            c.get("body") or c.get("summary") or "",
            force=True,
            at_create=False,
        )
        new_body = (pkg.get("body") or "").strip()
        old_body = (c.get("body") or "").strip()
        if new_body == old_body:
            continue
        updated += 1
        if not args.dry_run:
            learn.update_confirmed_card(
                cid,
                body=new_body,
                summary=pkg.get("summary"),
                tags=pkg.get("tags"),
            )
    if updated and not args.dry_run:
        learn.export_pack()
    print(f"slim_refresh scanned={scanned} updated={updated} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
