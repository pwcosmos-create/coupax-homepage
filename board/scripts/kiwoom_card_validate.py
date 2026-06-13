"""원히어로·차수거래 학습 카드 품질 검증."""
from __future__ import annotations

import re

_REQUIRED_TAG_ANY = ("차수", "1차", "2차", "3차", "슬롯")
_RISK_TAG_ANY = ("익절", "분할", "ATR")
_BODY_KW = _REQUIRED_TAG_ANY + _RISK_TAG_ANY + (
    "체결",
    "계좌",
    "원히어로",
    "buy_gaps",
    "sell_pcts",
    "cascade",
)
_META_TITLE_PREFIXES = (
    "학습 카드 작성 오류",
    "자동 카드 제작",
    "카드제작 가이드",
    "매매원칙",
    "모니터 ·",
)


def is_meta_error_card(title: str) -> bool:
    t = (title or "").strip()
    return any(t.startswith(p) for p in _META_TITLE_PREFIXES)


def validate_spec(title: str, body: str, tags: list[str] | None = None) -> tuple[bool, str, str]:
    """(ok, error_kind, hint)"""
    t = (title or "").strip()
    b = (body or "").strip()
    if is_meta_error_card(t):
        if len(b) < 30:
            return False, "too_short", "본문 30자 이상 필요."
        if not t:
            return False, "unknown", "제목 필요."
        if re.search(r"\d{10,}", b):
            return False, "pii", "장문자 번호(계좌 등) 제거."
        return True, "", ""
    if len(b) < 30:
        return False, "too_short", "본문 30자 이상 필요."
    tag_set = set(tags or [])
    for kw in _BODY_KW:
        if kw in b:
            tag_set.add(kw)
    if not any(k in tag_set or k in b for k in _REQUIRED_TAG_ANY):
        return False, "tag_missing", "차수·슬롯·1·2·3차 중 하나를 본문에 포함."
    if not any(k in tag_set or k in b for k in _RISK_TAG_ANY):
        return False, "tag_missing", "익절·분할·ATR 중 하나를 본문에 포함."
    if re.search(r"\d{10,}", b):
        return False, "pii", "장문자 번호(계좌 등) 제거."
    if re.search(r"(?i)api[_-]?key|비밀번호", b):
        return False, "pii", "API키·비밀번호 금지."
    if not t:
        return False, "unknown", "제목 필요."
    return True, "", ""


def validate_card(card: dict) -> tuple[bool, str, str]:
    """저장된 카드 dict 재검증."""
    if not isinstance(card, dict):
        return False, "unknown", "카드 형식 오류."
    return validate_spec(
        str(card.get("title") or ""),
        str(card.get("body") or ""),
        list(card.get("tags") or []),
    )
