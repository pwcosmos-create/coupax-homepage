#!/usr/bin/env python3
"""compose 품질 자가 점검 — CI·배포 전."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import saju_reading_engine as engine  # noqa: E402


def _check(label: str, ctx: dict) -> list[str]:
    errs: list[str] = []
    r = engine.build_reading(ctx)
    if not r.get("ok"):
        errs.append(f"{label}: not ok")
        return errs
    chat = (r.get("text_chat") or "").strip()
    if r.get("mode") == "card_compose" and len(chat) < 80:
        errs.append(f"{label}: text_chat too short ({len(chat)})")
    if "에서 에 해당" in chat or "함께 으로만" in chat:
        errs.append(f"{label}: broken phrase in chat")
    if r.get("mode") == "card_compose" and len(chat) > 3500:
        errs.append(f"{label}: text_chat too long ({len(chat)})")
    if "심층·[2]" in chat and ctx.get("reading_kind") == "daily":
        errs.append(f"{label}: daily contains deep palja")
    return errs


def main() -> int:
    cases = [
        ("summary", {"reading_kind": "summary", "tags": ["용신", "일주"]}),
        ("daily", {"reading_kind": "daily", "tags": ["일운", "오늘"]}),
        ("monthly", {"reading_kind": "monthly", "tags": ["월운", "다음달"]}),
        ("intent_nae", {"user_query": "나의 운세", "tags": ["병화"]}),
        ("intent_wealth", {"user_query": "재물운 어때", "tags": ["재성"]}),
        ("surface_chat", {"surface": "chat", "tags": ["정관"]}),
    ]
    all_errs: list[str] = []
    for label, ctx in cases:
        all_errs.extend(_check(label, ctx))
    if all_errs:
        print("FAIL")
        for e in all_errs:
            print(" -", e)
        return 1
    print("OK", len(cases), "cases")
    sample = engine.build_reading({"user_query": "나의 운세", "tags": ["용신"]})
    print(
        json.dumps(
            {
                "kind": sample.get("reading_kind"),
                "chat_len": len(sample.get("text_chat") or ""),
                "intent": sample.get("intent"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
