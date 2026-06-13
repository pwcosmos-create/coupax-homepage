#!/usr/bin/env python3
"""
확정 사주 카드 전체 — 풍부한 템플릿 구체화 + (선택) Gemini 해설.

  python scripts/refresh_all_saju_cards_rich.py
  python scripts/refresh_all_saju_cards_rich.py --gemini --gemini-count 40
"""
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
from saju_card_reverify_enrich import _strip_footer, batch_enrich  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, default=500)
    p.add_argument("--min-len", type=int, default=480)
    p.add_argument("--gemini", action="store_true", help="해석·/심층· PASS 카드 Gemini 다듬기")
    p.add_argument("--gemini-count", type=int, default=30)
    p.add_argument("--gemini-sleep", type=float, default=4)
    p.add_argument(
        "--only-short",
        action="store_true",
        help="본문이 짧은 카드만 템플릿 구체화",
    )
    args = p.parse_args()

    cards = [
        c
        for c in learn.load_store().get("cards") or []
        if isinstance(c, dict) and c.get("status") == "confirmed"
    ]
    short_n = sum(
        1 for c in cards if len(_strip_footer(c.get("body") or "")) < args.min_len
    )
    print(f"confirmed={len(cards)} short_under_{args.min_len}={short_n}")

    r1 = batch_enrich(
        args.count,
        force=True,
        sleep_sec=0.05,
        only_short=args.only_short,
        min_len=args.min_len,
    )
    print("template_enrich", r1)

    if args.gemini:
        import saju_card_llm_compose as llm

        r2 = llm.batch_polish(
            args.gemini_count, sleep_sec=args.gemini_sleep, only_missing=True
        )
        print("gemini", r2)

    print("stats", learn.stats())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
