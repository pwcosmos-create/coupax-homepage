#!/usr/bin/env python3
"""심층·[2] 사주팔자 등 — 풍부한 사주팔자 본문으로 갱신 (PASS·llm_composed_at 유지)."""
from __future__ import annotations

import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_saju_learn as learn  # noqa: E402
from saju_card_reverify_enrich import (  # noqa: E402
    FOOTER_MARK,
    STANDARD_FOOTER,
    _caution,
    _rich_saju_palja_section,
    compose_new_card,
)

TARGETS = (
    "심층·[2] 사주팔자",
    "해석·사주팔자 · 년월일시 읽기",
)


def _body_for_deep_section2() -> str:
    body = _rich_saju_palja_section()
    if FOOTER_MARK not in body:
        body = body.rstrip("。. ") + " " + _caution()
    if FOOTER_MARK not in body:
        body = body.rstrip("。. ") + STANDARD_FOOTER
    return body[:24000]


def main() -> int:
    store = learn.load_store()
    updated = 0
    for c in store.get("cards") or []:
        if not isinstance(c, dict):
            continue
        title = (c.get("title") or "").strip()
        if title not in TARGETS:
            continue
        if title == "심층·[2] 사주팔자":
            body = _body_for_deep_section2()
        else:
            pkg = compose_new_card(title, c.get("body") or "", force=True)
            body = pkg["body"]
        cid = c.get("id")
        if not isinstance(cid, int):
            continue
        learn.update_confirmed_card(cid, body=body, summary=learn._summary(body, 160))
        updated += 1
        print("updated", cid, title[:40])
    if updated:
        learn.export_pack()
    # 신규 해석 카드
    titles = {x.get("title") for x in store.get("cards") or []}
    new_title = "해석·사주팔자 · 년월일시 읽기"
    if new_title not in titles:
        pkg = compose_new_card(new_title, "사주팔자 네 기둥 풀이", force=True)
        card = learn.add_card(
            body=pkg["body"], title=pkg["title"], source="palja_rich", card_style="interpretive"
        )
        cid = card.get("id")
        if isinstance(cid, int):
            learn.confirm_card(cid)
            updated += 1
            print("added", cid, new_title)
        learn.export_pack()
    print("total_updated_or_added", updated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
