#!/usr/bin/env python3
"""심층·[1]~[10] 카드 본문을 풍부한 버전으로 일괄 갱신."""
from __future__ import annotations

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
from saju_deep_section_rich import DEEP_SECTION_TITLES, all_rich_sections, rich_body_for_title  # noqa: E402

try:
    from saju_card_copy_optimize import optimize_summary, optimize_tags, optimize_title
except ImportError:

    def optimize_title(card):  # type: ignore
        return card.get("title")

    def optimize_summary(title, body):  # type: ignore
        return learn._summary(body, 160)

    def optimize_tags(body, title, tags):  # type: ignore
        return learn._extract_tags(f"{title}\n{body}")[:16]


def main() -> int:
    bodies = dict(all_rich_sections())
    store = learn.load_store()
    updated = 0
    added = 0
    titles_existing = {c.get("title") for c in store.get("cards") or []}

    for title in DEEP_SECTION_TITLES:
        body = bodies[title]
        found = False
        for c in store.get("cards") or []:
            if not isinstance(c, dict) or (c.get("title") or "").strip() != title:
                continue
            found = True
            cid = c.get("id")
            if not isinstance(cid, int):
                break
            pkg_title = optimize_title({"title": title, "body": body})
            summary = optimize_summary(pkg_title, body)
            tags = optimize_tags(body, pkg_title, c.get("tags"))
            learn.update_confirmed_card(
                cid,
                title=pkg_title,
                body=body,
                summary=summary,
                tags=tags,
            )
            updated += 1
            print(f"updated #{cid} {title} len={len(body)}")
            break
        if not found:
            card = learn.add_card(
                body=body,
                title=title,
                source="deep_sections_rich",
                card_style="interpretive",
            )
            cid = card.get("id")
            if isinstance(cid, int):
                learn.confirm_card(cid, export_pack_now=False)
                added += 1
                print(f"added #{cid} {title} len={len(body)}")
            titles_existing.add(title)

    store = learn.load_store()
    for c in store.get("cards") or []:
        if not isinstance(c, dict):
            continue
        t = (c.get("title") or "").strip()
        if t in DEEP_SECTION_TITLES and (c.get("status") or "") == "confirmed":
            wiki.save_saju_card_to_knowledge(c)

    learn.export_pack()
    print(f"updated={updated} added={added} total={learn.stats()['total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
