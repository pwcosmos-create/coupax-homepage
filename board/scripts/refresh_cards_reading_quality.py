#!/usr/bin/env python3
"""
상담 품질 일괄 개선 — 메타 절(풀이 절차·활용 키워드) 제거·짧은 본문 재작성.

  python scripts/refresh_cards_reading_quality.py --dry-run
  python scripts/refresh_cards_reading_quality.py --limit 500
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_saju_learn as learn  # noqa: E402
import saju_card_reverify_enrich as enrich  # noqa: E402

META_MARKERS = ("【풀이 절차】", "【활용 키워드】")
MIN_LEN = enrich.MIN_BODY


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def needs_upgrade(card: dict) -> bool:
    if (card.get("status") or "") != "confirmed":
        return False
    body = card.get("body") or ""
    core = enrich._strip_footer(body)
    if any(m in body for m in META_MARKERS):
        return True
    if len(core) < MIN_LEN:
        return True
    return not enrich._has_rich_structure(body)


def run(*, limit: int = 500, dry_run: bool = False) -> dict:
    cards = [
        c
        for c in learn.load_store().get("cards") or []
        if isinstance(c, dict) and needs_upgrade(c)
    ]
    cards.sort(key=lambda c: len(c.get("body") or ""))
    changed = 0
    samples: list[dict] = []

    for c in cards[:limit]:
        cid = int(c["id"])
        if dry_run:
            changed += 1
            if len(samples) < 8:
                samples.append(
                    {
                        "id": cid,
                        "title": (c.get("title") or "")[:40],
                        "len": len(c.get("body") or ""),
                    }
                )
            continue

        fields, patches = enrich.enrich_card_fields(c, force=True)
        if not patches:
            continue
        note = f"{(c.get('note') or '').strip()}\n[상담품질 {_now()}] {', '.join(patches)}".strip()[
            :500
        ]
        ok = learn.update_confirmed_card(
            cid,
            title=fields.get("title"),
            body=fields.get("body"),
            summary=fields.get("summary"),
            tags=fields.get("tags"),
            note=note,
            reading_quality_at=_now(),
        )
        if ok:
            changed += 1
            if len(samples) < 5:
                samples.append({"id": cid, "patches": patches})

    if changed and not dry_run:
        learn.export_pack()
        import agent_office_saju_card_council as council

        for row in samples:
            council.verify_card_by_id(int(row["id"]), mode="reverify_pass")

    return {
        "dry_run": dry_run,
        "candidates": len(cards),
        "changed": changed,
        "samples": samples,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int, default=500)
    args = p.parse_args()
    import board_env

    board_env.load_board_env()
    print(run(limit=args.limit, dry_run=args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
