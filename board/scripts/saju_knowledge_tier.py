"""사주 학습 카드·Wiki — 위원회 인증 등급 (RAG·풀이 조합용)."""
from __future__ import annotations

TIER_CERTIFIED = "certified"  # PASS — ✓ 사주위원회 인증
TIER_REVIEW = "review"  # Wiki/확정 있으나 PASS 없음 — ◷ 검수 반영
TIER_EXCLUDED = "excluded"  # FAIL — 매칭·조합 제외


def is_council_pass(card: dict | None) -> bool:
    if not isinstance(card, dict):
        return False
    return (card.get("council_status") or "").strip() == "pass" or card.get("council_pass") is True


def is_council_fail(card: dict | None) -> bool:
    if not isinstance(card, dict):
        return False
    return (card.get("council_status") or "").strip() == "fail"


def council_tier(card: dict | None) -> str:
    if not isinstance(card, dict):
        return TIER_REVIEW
    if is_council_fail(card):
        return TIER_EXCLUDED
    if is_council_pass(card):
        return TIER_CERTIFIED
    if (card.get("status") or "") == "confirmed":
        return TIER_REVIEW
    return TIER_REVIEW


def tier_label(tier: str) -> str:
    if tier == TIER_CERTIFIED:
        return "사주위원회 인증"
    if tier == TIER_REVIEW:
        return "사주위원회 검수 반영"
    return ""


def tier_badge_html(tier: str) -> str:
    if tier == TIER_CERTIFIED:
        return (
            '<span class="saju-wiki-tier saju-wiki-tier--cert" title="명리 위원회 PASS">'
            '<span class="saju-wiki-tier__icon" aria-hidden="true">✓</span>사주위원회 인증</span>'
        )
    if tier == TIER_REVIEW:
        return (
            '<span class="saju-wiki-tier saju-wiki-tier--review" title="지식 반영·위원회 PASS 대기">'
            '<span class="saju-wiki-tier__icon" aria-hidden="true">◷</span>사주위원회 검수 반영</span>'
        )
    return ""


def rag_eligible(card: dict | None) -> bool:
    """FAIL 제외, PASS·검수 반영은 RAG 후보."""
    return council_tier(card) != TIER_EXCLUDED


def compose_eligible(card: dict | None) -> bool:
    """무료 조합 풀이 — PASS만."""
    return is_council_pass(card)


def enrich_wiki_from_card(wiki: dict, card: dict | None) -> dict:
    if not isinstance(wiki, dict):
        return wiki
    out = dict(wiki)
    tier = council_tier(card)
    out["council_tier"] = tier
    out["council_status"] = (card or {}).get("council_status") or ""
    out["council_pass"] = bool((card or {}).get("council_pass"))
    out["council_at"] = (card or {}).get("council_at") or ""
    out["rag_eligible"] = tier != TIER_EXCLUDED
    out["compose_eligible"] = tier == TIER_CERTIFIED
    return out


def load_cards_by_id() -> dict[int, dict]:
    import agent_office_saju_learn

    out: dict[int, dict] = {}
    for c in agent_office_saju_learn.load_store().get("cards") or []:
        if isinstance(c, dict) and c.get("id") is not None:
            out[int(c["id"])] = c
    return out
