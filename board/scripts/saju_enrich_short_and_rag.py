#!/usr/bin/env python3
"""짧은 사주 카드 구체화 + 제목 보정 + Wiki/RAG 동기화."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

try:
    import board_env

    board_env.load_board_env()
except ImportError:
    pass

import agent_office_saju_learn as learn  # noqa: E402
import agent_office_wiki_store as wiki  # noqa: E402
import saju_card_reverify_enrich as enrich  # noqa: E402

TITLE_FIXES: dict[int, str] = {
    445: "해석·경술 일주 성향",
    446: "변수·십신 재생관",
}


def fix_titles() -> list[dict]:
    done: list[dict] = []
    for cid, title in TITLE_FIXES.items():
        card = learn.get_card(cid)
        if not card or (card.get("status") or "") != "confirmed":
            done.append({"id": cid, "ok": False, "error": "not_found"})
            continue
        if (card.get("title") or "").strip() == title:
            done.append({"id": cid, "ok": True, "skipped": True})
            continue
        row = learn.update_confirmed_card(
            cid,
            title=title,
            note=f"{(card.get('note') or '').strip()}\n[제목보정] {(card.get('title') or '')} -> {title}".strip()[:500],
        )
        done.append({"id": cid, "ok": bool(row), "title": title})
    return done


def sync_rag() -> dict:
    n = 0
    for c in learn.load_store().get("cards") or []:
        if isinstance(c, dict) and c.get("status") == "confirmed":
            wiki.save_saju_card_to_knowledge(c)
            n += 1
    pack = learn.export_pack()
    return {"wiki_synced": n, "pack_cards": pack.get("card_count"), "pack_version": pack.get("version")}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--min-len", type=int, default=400)
    p.add_argument("--count", type=int, default=80)
    p.add_argument("--skip-enrich", action="store_true")
    p.add_argument("--skip-title-fix", action="store_true")
    p.add_argument("--skip-rag", action="store_true")
    args = p.parse_args()

    if not args.skip_title_fix:
        print("title_fixes", fix_titles())
        for cid in TITLE_FIXES:
            print("enrich_one", enrich.apply_enrich(cid, force=True))

    if not args.skip_enrich:
        print(
            "batch_enrich",
            enrich.batch_enrich(
                args.count,
                force=True,
                only_short=True,
                min_len=args.min_len,
            ),
        )

    if not args.skip_rag:
        print("rag", sync_rag())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
