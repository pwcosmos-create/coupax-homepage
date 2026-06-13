"""
사주 카드 자동 제작 — 풀이 매칭 빈도·버킷 부족분 기준 우선순위.

docs/SAJU-DEEP-READING-CARD-GUIDE.md 섹션 [1]~[10] 힌트와 연동.
"""
from __future__ import annotations

import re
from typing import Any

# 섹션별 매칭 가중치 (높을수록 풀이에 자주 노출)
SECTION_USAGE_WEIGHT: list[tuple[str, int, tuple[str, ...]]] = [
    ("[1] 인사·성향", 100, ("일주", "일간", "천간", "성향", "인사")),
    ("[2] 사주팔자", 90, ("사주", "팔자", "년", "월", "일", "시")),
    ("[3] 오행 균형", 95, ("오행", "목", "화", "토", "금", "수", "상생", "상극")),
    ("[4] 십신·격국", 100, ("십신", "격국", "격", "비견", "겁재", "식신", "상관", "재성", "관성", "인성")),
    ("[5] 용신·기신", 85, ("용신", "기신", "희신", "보완", "신강", "신약")),
    ("[6] 대운·세운", 80, ("대운", "세운", "월운", "운", "교운")),
    ("[7] 재물", 90, ("재물", "정재", "편재", "재성", "수입")),
    ("[8] 연애·관계", 95, ("연애", "배우자", "도화", "합", "충", "궁합", "관계")),
    ("[9] 직업", 85, ("직업", "직장", "사업", "이직", "역마")),
    ("[10] 실천·주의", 70, ("실천", "주의", "조언", "면책")),
]

# 버킷별 목표 장수 — 부족할수록 우선
BUCKET_TARGETS: dict[str, int] = {
    "stem-day": 20,
    "gyeok": 18,
    "branch": 20,
    "yongsin": 30,
    "gisin": 12,
    "other": 0,
}

_TOKEN_RE = re.compile(r"[가-힣]{2,}")


def _tokens(blob: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(blob or "") if len(t) >= 2}


def usage_score_for_spec(spec: dict, *, inventory: dict | None = None) -> int:
    """풀 항목 우선순위 점수 (높을수록 먼저 제작)."""
    title = (spec.get("title") or "").strip()
    body = (spec.get("body") or "").strip()
    blob = f"{title} {body} {' '.join(spec.get('tags') or [])}"
    tokens = _tokens(blob)

    score = 0
    for _sec, weight, hints in SECTION_USAGE_WEIGHT:
        hits = sum(1 for h in hints if h in blob or h in tokens)
        if hits:
            score += weight + hits * 8

    # 해석· / 일주 / 명식 조합 — 실제 풀이 매칭에 유리
    if title.startswith("해석·"):
        score += 40
    if "일주" in blob:
        score += 50
    if any(k in blob for k in ("명식", "재물", "연애", "관성", "식신", "대운", "세운")):
        score += 25
    if title.startswith("변수·"):
        score += 15
    # 희규·보조 주제는 후순위
    low = ("납음", "태원", "명궁", "복인", "윤달", "일운", "조합 풀이", "학당")
    if any(k in title for k in low):
        score -= 80

    if inventory:
        try:
            import saju_reading_engine as eng

            buckets = inventory.get("buckets") or {}
            fake = {"title": title, "tags": list(tokens)[:12]}
            b = eng.card_bucket(fake)
            target = BUCKET_TARGETS.get(b, 0)
            have = int(buckets.get(b, 0))
            if target and have < target:
                score += (target - have) * 12
        except Exception:
            pass

    return score


def sort_specs_by_usage(
    specs: list[dict],
    *,
    inventory: dict | None = None,
) -> list[dict]:
    return sorted(
        specs,
        key=lambda s: usage_score_for_spec(s, inventory=inventory),
        reverse=True,
    )


def filter_pending_high_usage(
    specs: list[dict],
    existing_titles: set[str],
    *,
    min_score: int = 120,
) -> list[dict]:
    """아직 없고, 사용 빈도 점수가 min_score 이상인 항목만."""
    out: list[dict] = []
    for s in specs:
        t = (s.get("title") or "").strip()
        if not t or t in existing_titles:
            continue
        if usage_score_for_spec(s) >= min_score:
            out.append(s)
    return out


def get_inventory() -> dict:
    try:
        import saju_reading_engine as eng

        return eng.pass_inventory()
    except Exception:
        return {}
