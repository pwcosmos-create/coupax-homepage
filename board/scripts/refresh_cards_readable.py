#!/usr/bin/env python3
"""확정 카드 본문 — 절·기둥 단락·중복 문장 정리 (일괄 갱신)."""
from __future__ import annotations

import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_saju_learn as learn  # noqa: E402
from saju_reading_display import optimize_card_body  # noqa: E402


def main() -> int:
    changed = 0
    for c in learn.load_store().get("cards") or []:
        if not isinstance(c, dict) or (c.get("status") or "") != "confirmed":
            continue
        cid = c.get("id")
        if not isinstance(cid, int):
            continue
        old = (c.get("body") or "").strip()
        new = optimize_card_body(old)
        if new == old:
            continue
        learn.update_confirmed_card(cid, body=new)
        changed += 1
    if changed:
        learn.export_pack()
        try:
            import sync_saju_wiki_council as swc

            swc.main()
        except Exception:
            pass
    print(f"readable_format updated={changed} total={learn.stats()['total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
