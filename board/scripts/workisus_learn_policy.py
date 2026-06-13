"""원키스 US 학습 카드 제작 on/off — 기본 중지."""
from __future__ import annotations

import os

_DISABLED_MSG = "원키스 US 학습 카드 제작이 중지되었습니다 (WORKISUS_CARD_PRODUCTION=0)."


def is_card_production_enabled() -> bool:
    return (os.getenv("WORKISUS_CARD_PRODUCTION", "0") or "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def disabled_message() -> str:
    return _DISABLED_MSG


def require_card_production() -> None:
    if not is_card_production_enabled():
        raise RuntimeError(_DISABLED_MSG)
