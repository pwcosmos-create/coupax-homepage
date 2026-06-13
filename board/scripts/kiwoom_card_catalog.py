"""원히어로 매매 규칙 학습 카드 카탈로그 — 자동 추가·갭 탐지용."""
from __future__ import annotations

from wonhero_card_catalog import WONHERO_META_CARDS, all_wonhero_specs

# 하위 호환: RL·gap_detector가 import 하는 이름
KIWOOM_AUTO_CARD_POOL: list[dict] = all_wonhero_specs()


def all_catalog_specs() -> list[dict]:
    """원히어로 규칙 카탈로그만 반환 (구 coupax 수동·phase2 시드 제외)."""
    return all_wonhero_specs()
