#!/usr/bin/env python3
"""Gemini API 연결 테스트 (키 값은 출력하지 않음)."""
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))
try:
    import board_env

    board_env.load_board_env()
except ImportError:
    pass

from saju_card_llm_compose import (  # noqa: E402
    _gemini_generate,
    gemini_api_key,
    gemini_model,
    polish_card_after_pass,
)
import agent_office_saju_learn as learn  # noqa: E402


def main() -> int:
    print("key_set", bool(gemini_api_key()))
    print("model", gemini_model())
    t, label = _gemini_generate("한국어로 두 문장만 인사해 주세요.")
    print("ping_ok", bool(t), "label", label, "len", len(t or ""))
    if not t:
        t2, label2 = _gemini_generate("Say hi in one short sentence.")
        print("ping_en_ok", bool(t2), "label2", label2)

    cid = int(sys.argv[1]) if len(sys.argv) > 1 else 1055
    card = learn.get_card(cid)
    if card:
        r = polish_card_after_pass(cid, mode="debug")
        print(
            "compose",
            {
                k: r.get(k)
                for k in ("ok", "error", "provider", "model", "body_len")
                if k in r or k == "body_len"
            },
        )
        if r.get("ok"):
            print("body_len", len((learn.get_card(cid) or {}).get("body") or ""))
    return 0 if t else 1


if __name__ == "__main__":
    raise SystemExit(main())
