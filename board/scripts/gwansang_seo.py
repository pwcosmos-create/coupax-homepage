"""관상 학습 카드 SEO 보강 — 본문 200자+."""
from __future__ import annotations

import re

from gwansang_card_catalog import MIN_BODY_CHARS

_SEO_KW = ("관상", "관相", "얼굴", "이마", "눈", "코", "입", "인상", "길상", "오관")


def _count_chars(text: str) -> int:
    return len(re.sub(r"\s+", "", text or ""))


def enrich_body(title: str, body: str, *, catalog_seed: str = "") -> str:
    body = (body or "").strip()
    title = (title or "").strip()
    if _count_chars(body) >= MIN_BODY_CHARS:
        return body[:24000]
    footer_parts = [
        f"【SEO】 {title or catalog_seed or '관상'} — ",
        "관상 풀이·얼굴 관相 해석 참고 카드. ",
        "전통 오관(눈·코·입·귀·이마)과 삼정 비율을 바탕으로 성향·건강·인연 경향을 설명한다. ",
        "단정적 예언·불길 표현 없이 자기이해·커뮤니케이션·생활 습관 개선에 활용한다. ",
        "검색 키워드: 관상, 얼굴 관상, 이마·눈·코·입 관상, 길상, 인상 분석.",
    ]
    missing_kw = [k for k in _SEO_KW if k not in body and k not in title]
    if missing_kw:
        footer_parts.append(" 관련 키워드: " + ", ".join(missing_kw[:6]) + ".")
    out = body + "\n\n" + "".join(footer_parts)
    return out[:24000]
