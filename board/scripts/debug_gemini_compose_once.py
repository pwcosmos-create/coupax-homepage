#!/usr/bin/env python3
"""One-shot Gemini compose debug (no secrets printed)."""
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
from saju_card_llm_compose import (  # noqa: E402
    _build_prompt,
    _normalize_body,
    eligible,
    generate_polish_text,
)

REQ = (
    "【인사·성향】",
    "【명식·구조】",
    "【오행·십신 해석】",
    "【테마 풀이】",
    "【주의】",
)


def main() -> int:
    cid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    card = learn.get_card(cid) if cid else None
    if not card:
        for c in learn.load_store().get("cards") or []:
            if isinstance(c, dict) and eligible(c, mode="initial"):
                card = c
                break
    if not card:
        print("no eligible card")
        return 1
    cid = int(card["id"])
    print("card_id", cid, "title", (card.get("title") or "")[:50])
    raw, model, prov = generate_polish_text(_build_prompt(card))
    print("provider", prov, "model", model, "raw_len", len(raw or ""))
    if not raw:
        return 2
    for m in REQ:
        print("has", m, m in raw)
    nb = _normalize_body(raw)
    print("normalized_len", len(nb))
    if not nb:
        print("raw_head", (raw or "")[:400])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
