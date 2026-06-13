#!/usr/bin/env python3
"""심층 풀이 [1]~[10] 섹션 전용 학습 카드 — 인증 카드 조합·LLM 공통 프레임."""
from __future__ import annotations

import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_saju_learn as learn  # noqa: E402
import agent_office_wiki_store as wiki  # noqa: E402
from saju_deep_section_rich import all_rich_sections  # noqa: E402

SECTIONS: list[tuple[str, str]] = all_rich_sections()


def main() -> int:
    titles = {c.get("title") for c in learn.list_cards(limit=500)}
    added = 0
    for title, body in SECTIONS:
        if title in titles:
            continue
        card = learn.add_card(body=body, title=title, source="deep_sections")
        cid = card.get("id")
        if not isinstance(cid, int):
            continue
        learn.confirm_card(cid)
        store = learn.load_store()
        for c in store.get("cards") or []:
            if isinstance(c, dict) and c.get("id") == cid:
                wiki.save_saju_card_to_knowledge(c)
                break
        titles.add(title)
        added += 1
    learn.export_pack()
    st = learn.stats()
    print(f"sections={len(SECTIONS)} new={added} total={st['total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
