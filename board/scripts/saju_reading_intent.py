"""사주 풀이 — 사용자 질문·컨텍스트에서 reading_kind·topic 추론 (saju-v2 미전송 대비)."""
from __future__ import annotations

import re

# 질문 정규화
_NORM_RE = re.compile(r"[\s\-_/·,.!?~\"'\"\"''\[\]()]+")

_DAILY_HINTS = (
    "오늘의운세",
    "오늘운세",
    "오늘운",
    "일운",
    "당일운",
    "todayfortune",
)
_MONTHLY_HINTS = (
    "다음달",
    "이번달",
    "내달",
    "월운",
    "이번월",
    "다음월",
    "nextmonth",
)
_SUMMARY_HINTS = (
    "나의운세",
    "내운세",
    "나운세",
    "운세보기",
    "사주풀이",
    "사주보기",
    "내사주",
    "종합운",
)
_FULL_HINTS = (
    "심층풀이",
    "10절",
    "전체풀이",
    "심층사주",
    "풀리딩",
)
_TOPIC_HINTS: dict[str, tuple[str, ...]] = {
    "재물": ("재물운", "재물", "돈운", "금전", "수입", "투자"),
    "연애": ("연애운", "연애", "애정", "결혼", "배우자", "궁합", "이성"),
    "직업": ("직업운", "직업", "직장", "이직", "사업", "취업"),
    "건강": ("건강운", "건강", "컨디션", "번아웃"),
}


def _norm(text: str) -> str:
    return _NORM_RE.sub("", (text or "").strip().lower())


def _blob_from_context(ctx: dict) -> str:
    parts = [
        ctx.get("user_query") or "",
        ctx.get("question") or "",
        ctx.get("message") or "",
        ctx.get("topic") or "",
        " ".join(ctx.get("tags") or []),
    ]
    return _norm(" ".join(parts))


def infer_topic(ctx: dict) -> str | None:
    """재물 | 연애 | 직업 | 건강 | None."""
    blob = _blob_from_context(ctx)
    if not blob:
        return None
    best: tuple[int, str] | None = None
    for name, hints in _TOPIC_HINTS.items():
        score = sum(1 for h in hints if h in blob)
        if score and (best is None or score > best[0]):
            best = (score, name)
    return best[1] if best else None


def infer_reading_kind(ctx: dict) -> str | None:
    """
    명시적 kind가 없을 때 질문에서 추론.
    반환: daily | monthly | summary | full | topic | None
    """
    blob = _blob_from_context(ctx)
    if not blob:
        return None
    if any(h in blob for h in _DAILY_HINTS):
        return "daily"
    if any(h in blob for h in _MONTHLY_HINTS):
        return "monthly"
    if any(h in blob for h in _FULL_HINTS):
        return "full"
    if infer_topic(ctx):
        return "topic"
    if any(h in blob for h in _SUMMARY_HINTS) or blob in ("운세", "사주", "나의운세"):
        return "summary"
    return None


def apply_intent_to_context(ctx: dict, *, surface: str = "") -> dict:
    """
    컨텍스트에 reading_kind·topic 보강 (기존 명시값은 유지).
    surface=chat 이면 kind 미지정 시 summary 기본.
    """
    out = dict(ctx)
    explicit_keys = ("reading_kind", "reading_mode", "fortune_kind", "mode")
    has_explicit = any(
        str(out.get(k) or "").strip().lower() not in ("", "full", "default")
        for k in explicit_keys
    )

    topic = infer_topic(out)
    if topic and not (out.get("topic") or "").strip():
        out["topic"] = topic

    inferred = infer_reading_kind(out)
    if inferred and not has_explicit:
        out["reading_kind"] = inferred
        out["_intent_inferred"] = True
    elif not has_explicit and (surface or out.get("surface") or "").lower() in (
        "chat",
        "message",
        "상담",
    ):
        out["reading_kind"] = inferred or "summary"
        out["_intent_inferred"] = True

    return out
