#!/usr/bin/env python3
"""동일 제목 카드 중복 제거 — 제목당 1장 유지.

유지 우선순위: 위원회 PASS > llm_composed_at > 본문 길이 > 낮은 id

  python scripts/dedupe_saju_cards.py --dry-run
  python scripts/dedupe_saju_cards.py --apply
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_saju_learn as learn  # noqa: E402
import saju_knowledge_tier as tier  # noqa: E402


def _score(card: dict) -> tuple:
    title = (card.get("title") or "").strip()
    body = card.get("body") or ""
    cid = int(card.get("id") or 0)
    return (
        1 if tier.is_council_pass(card) else 0,
        1 if (card.get("llm_composed_at") or "").strip() else 0,
        len(body),
        -cid,
    )


def dedupe(*, apply: bool = False) -> dict:
    cards = [c for c in learn.load_store().get("cards") or [] if isinstance(c, dict)]
    by_title: dict[str, list[dict]] = defaultdict(list)
    for c in cards:
        t = (c.get("title") or "").strip()
        if not t:
            continue
        by_title[t].append(c)

    remove_ids: list[int] = []
    keep_map: dict[str, int] = {}
    dup_groups: list[dict] = []

    for title, items in sorted(by_title.items(), key=lambda x: x[0]):
        if len(items) < 2:
            continue
        items.sort(key=_score, reverse=True)
        keep = items[0]
        keep_id = int(keep.get("id") or 0)
        keep_map[title] = keep_id
        dups = [int(c.get("id") or 0) for c in items[1:] if int(c.get("id") or 0) != keep_id]
        remove_ids.extend(dups)
        dup_groups.append(
            {
                "title": title,
                "keep_id": keep_id,
                "remove_ids": dups,
                "count": len(items),
            }
        )

    removed = 0
    if apply and remove_ids:
        for cid in sorted(set(remove_ids)):
            if learn.delete_card(cid):
                removed += 1
        learn.export_pack()
        try:
            import sync_saju_wiki_council as swc

            swc.main()
        except Exception:
            pass

    before = len(cards)
    after = before - len(set(remove_ids)) if apply else before - len(set(remove_ids))
    return {
        "apply": apply,
        "before": before,
        "after": after if apply else before - len(set(remove_ids)),
        "duplicate_titles": len(dup_groups),
        "to_remove": len(set(remove_ids)),
        "removed": removed,
        "groups": dup_groups,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    out = dedupe(apply=args.apply and not args.dry_run)
    print(json.dumps({k: v for k, v in out.items() if k != "groups"}, ensure_ascii=False, indent=2))
    if out.get("groups"):
        print("\n--- duplicate groups (top 30) ---")
        for g in out["groups"][:30]:
            print(
                f"x{g['count']} {g['title']} -> keep #{g['keep_id']}, "
                f"remove {len(g['remove_ids'])}"
            )
        if len(out["groups"]) > 30:
            print(f"... and {len(out['groups']) - 30} more titles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
