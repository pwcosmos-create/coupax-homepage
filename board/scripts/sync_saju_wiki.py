#!/usr/bin/env python3
"""확정 사주 학습 카드를 gemma_knowledge(Wiki)에 동기화."""
from __future__ import annotations

import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_saju_learn as learn  # noqa: E402
import agent_office_wiki_store as wiki  # noqa: E402


def main() -> int:
    n = 0
    for c in learn.list_cards(limit=100):
        if c.get("status") != "confirmed":
            continue
        if wiki.save_saju_card_to_knowledge(c):
            n += 1
    print(f"wiki_synced={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
