"""
사주 심층 풀이 — 인증(PASS) 카드 조합(무료) vs LLM.

  python scripts/saju_reading_engine.py demo --tags 일주,병화,정관격,용신
  python scripts/saju_reading_engine.py inventory   # PASS·버킷별 장수

가이드: docs/SAJU-DEEP-READING-CARD-GUIDE.md

환경 변수:
  SAJU_READING_MIN_PASS_CARDS=2   무료 조합 최소 PASS **매칭** 수
  SAJU_READING_CHAT_EXCERPT_CHARS=650   text_chat 절 excerpt 상한
  SAJU_READING_FULL_EXCERPT_CHARS=2800  text_full 절 excerpt 상한
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import saju_knowledge_tier as tier  # noqa: E402

_TOKEN_RE = re.compile(r"[가-힣]{2,}|[a-zA-Z]{2,}")

DEEP_TITLE_BY_SECTION: dict[str, str] = {
    "[1] 인사·성향": "심층·[1] 인사·성향",
    "[2] 사주팔자": "심층·[2] 사주팔자",
    "[3] 오행 균형": "심층·[3] 오행 균형",
    "[4] 십신·격국": "심층·[4] 십신·격국",
    "[5] 용신·기신": "심층·[5] 용신·기신",
    "[6] 대운·세운": "심층·[6] 대운·세운",
    "[7] 재물": "심층·[7] 재물",
    "[8] 연애·관계": "심층·[8] 연애·관계",
    "[9] 직업": "심층·[9] 직업",
    "[10] 실천·주의": "심층·[10] 실천·주의",
}

SECTION_HINTS: list[tuple[str, list[str]]] = [
    ("[1] 인사·성향", ["인사", "성향", "일주", "일간", "천간"]),
    ("[2] 사주팔자", ["사주", "팔자", "년", "월", "일", "시", "천간", "지지"]),
    ("[3] 오행 균형", ["오행", "목", "화", "토", "금", "수", "상생", "상극", "과다", "부족"]),
    ("[4] 십신·격국", ["십신", "격국", "격", "비견", "겁재", "식신", "상관", "재성", "관성", "인성"]),
    ("[5] 용신·기신", ["용신", "기신", "보완", "조절"]),
    ("[6] 대운·세운", ["대운", "세운", "월운", "운"]),
    ("[7] 재물", ["재물", "정재", "편재", "재성"]),
    ("[8] 연애·관계", ["연애", "배우자", "도화", "관성", "합", "충"]),
    ("[9] 직업", ["직업", "직장", "사업", "식신", "상관"]),
    ("[10] 실천·주의", ["실천", "주의", "참고", "금지", "예언"]),
]

DAILY_SECTION_HINTS: list[tuple[str, list[str]]] = [
    ("[오늘] 오늘의 운세", ["일운", "오늘", "당일", "운", "십신"]),
]

MONTHLY_SECTION_HINTS: list[tuple[str, list[str]]] = [
    ("[월] 시기·운세", ["월운", "다음달", "이번달", "당월", "월", "운"]),
]

# 채팅 요약 — 「나의 운세」 등 짧은 풀이
SUMMARY_SECTION_KEYS: list[str] = [
    "[1] 인사·성향",
    "[5] 용신·기신",
    "[6] 대운·세운",
]

_DAILY_KIND_ALIASES = frozenset(
    {"daily", "today", "day", "ilun", "오늘", "오늘의운세", "오늘운세", "일운"}
)
_MONTHLY_KIND_ALIASES = frozenset(
    {
        "monthly",
        "month",
        "wolun",
        "월운",
        "다음달",
        "이번달",
        "당월",
        "nextmonth",
    }
)
_SUMMARY_KIND_ALIASES = frozenset(
    {"summary", "chat", "brief", "short", "요약", "채팅", "나의운세"}
)
_TOPIC_KIND_ALIASES = frozenset({"topic", "theme", "테마", "주제"})

# context.topic → 섹션 (1개 주제 풀이)
_TOPIC_SECTION_MAP: dict[str, list[tuple[str, list[str]]]] = {
    "재물": [("[7] 재물", ["재물", "정재", "편재", "재성"])],
    "연애": [("[8] 연애·관계", ["연애", "배우자", "도화", "관성", "합"])],
    "직업": [("[9] 직업", ["직업", "직장", "사업", "식신", "상관"])],
    "건강": [("[10] 실천·주의", ["건강", "컨디션", "번아웃", "실천"])],
}

API_VERSION = 2

_FALLBACK_CHAT = (
    "※ 해당 주제에 맞는 인증 카드가 아직 충분하지 않습니다. "
    "잠시 후 다시 시도하시거나 심층 풀이·AI 보조를 이용해 주세요."
)


def _explicit_kind_raw(context: dict) -> str:
    return str(
        context.get("reading_kind")
        or context.get("reading_mode")
        or context.get("fortune_kind")
        or context.get("mode")
        or ""
    ).strip().lower().replace(" ", "")


def reading_kind(context: dict | None) -> str:
    """full | daily | monthly | summary | topic."""
    if not isinstance(context, dict):
        return "full"
    raw = _explicit_kind_raw(context)
    if raw in _DAILY_KIND_ALIASES:
        return "daily"
    if raw in _MONTHLY_KIND_ALIASES:
        return "monthly"
    if raw in _SUMMARY_KIND_ALIASES:
        return "summary"
    if raw in _TOPIC_KIND_ALIASES:
        return "topic"
    if raw and raw not in ("full", "default"):
        return raw
    try:
        from saju_reading_intent import infer_reading_kind

        inferred = infer_reading_kind(context)
        if inferred:
            return inferred
    except ImportError:
        pass
    surface = str(context.get("surface") or "").lower()
    if surface in ("chat", "message", "상담"):
        return "summary"
    return "full"


def _topic_section_defs(context: dict) -> list[tuple[str, list[str]]] | None:
    topic = (context.get("topic") or "").strip()
    if not topic:
        return None
    for key, defs in _TOPIC_SECTION_MAP.items():
        if key in topic:
            return defs
    return None


def min_pass_cards_for(kind: str) -> int:
    if kind in ("daily", "monthly", "topic"):
        return max(1, int(os.getenv("SAJU_READING_MIN_PASS_DAILY", "1") or "1"))
    if kind == "summary":
        return max(1, int(os.getenv("SAJU_READING_MIN_PASS_SUMMARY", "1") or "1"))
    return min_pass_cards()


def min_pass_cards() -> int:
    return max(2, int(os.getenv("SAJU_READING_MIN_PASS_CARDS", "2") or "2"))


def _excerpt_limits(kind: str) -> tuple[int, int]:
    """(chat_excerpt_chars, full_excerpt_chars)."""
    full_max = max(1200, int(os.getenv("SAJU_READING_FULL_EXCERPT_CHARS", "2800") or "2800"))
    chat_max = max(400, int(os.getenv("SAJU_READING_CHAT_EXCERPT_CHARS", "650") or "650"))
    if kind == "daily":
        return (
            min(chat_max, int(os.getenv("SAJU_READING_DAILY_EXCERPT_CHARS", "500") or "500")),
            min(full_max, 900),
        )
    if kind == "monthly":
        return (min(chat_max, 700), min(full_max, 1200))
    if kind == "summary":
        return (chat_max, min(full_max, 1400))
    return (chat_max, full_max)


def _section_defs_for_kind(kind: str, context: dict | None = None) -> list[tuple[str, list[str]]]:
    if kind == "topic" and context:
        defs = _topic_section_defs(context)
        if defs:
            return defs
    if kind == "daily":
        return DAILY_SECTION_HINTS
    if kind == "monthly":
        return MONTHLY_SECTION_HINTS
    if kind == "summary":
        return [s for s in SECTION_HINTS if s[0] in SUMMARY_SECTION_KEYS]
    return SECTION_HINTS


def _cap_chat_text(text: str, *, max_total: int | None = None) -> str:
    limit = max_total or int(os.getenv("SAJU_READING_CHAT_TOTAL_CHARS", "2200") or "2200")
    t = (text or "").strip()
    if len(t) <= limit:
        return t
    cut = t[: limit - 1].rstrip()
    if "【" in cut[-80:]:
        cut = cut.rsplit("【", 1)[0].rstrip()
    return cut + "…"


def _tokens(blob: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(blob or "") if len(t) >= 2}


def pass_cards_count() -> int:
    return len(_load_pass_cards())


def card_bucket(card: dict) -> str:
    title = (card.get("title") or "").strip()
    tags = " ".join(card.get("tags") or [])
    blob = f"{title} {tags}"
    if title.startswith("심층·") or title.startswith("해석·"):
        return "other"
    if title.startswith("변수·띠"):
        return "stem-chen"
    if title.startswith("변수·격"):
        return "gyeok"
    if title.startswith("변수·지지"):
        return "branch"
    if title.startswith("변수·희신"):
        return "yongsin"
    if title.startswith("변수·천간"):
        return "stem-day"
    if "기신" in blob and "용신" not in title:
        return "gisin"
    if "용신" in blob or "희신" in blob:
        return "yongsin"
    if "칠살" in blob or "종격" in blob or "격" in title:
        return "gyeok"
    if "띠" in title or "띠" in blob or "生肖" in blob:
        return "stem-chen"
    if "일주" in blob or ("일간" in blob and "천간" in blob):
        return "stem-day"
    if title.startswith("변수·"):
        return "other"
    return "other"


def pass_inventory() -> dict:
    cards = _load_pass_cards()
    buckets: dict[str, int] = {}
    styles: dict[str, int] = {}
    llm_done = 0
    for c in cards:
        b = card_bucket(c)
        buckets[b] = buckets.get(b, 0) + 1
        st = (c.get("card_style") or "—").strip() or "—"
        styles[st] = styles.get(st, 0) + 1
        if (c.get("llm_composed_at") or "").strip():
            llm_done += 1
    return {
        "pass_total": len(cards),
        "buckets": dict(sorted(buckets.items(), key=lambda x: (-x[1], x[0]))),
        "card_styles": styles,
        "llm_composed": llm_done,
        "llm_pending_interpretive": sum(
            1
            for c in cards
            if not (c.get("llm_composed_at") or "").strip()
            and (
                (c.get("card_style") or "") == "interpretive"
                or (c.get("title") or "").startswith("해석·")
            )
        ),
        "min_pass_match": min_pass_cards(),
        "section_count": len(SECTION_HINTS),
        "api_version": API_VERSION,
    }


def _load_pass_cards() -> list[dict]:
    import agent_office_saju_learn

    cards = [
        c
        for c in agent_office_saju_learn.load_store().get("cards") or []
        if isinstance(c, dict)
        and c.get("status") == "confirmed"
        and tier.compose_eligible(c)
    ]
    return cards


def _card_score(card: dict, query_tokens: set[str], *, kind: str = "full") -> int:
    title = (card.get("title") or "").strip()
    title_l = title.lower()
    body = (card.get("body") or "").lower()
    tags = " ".join(card.get("tags") or []).lower()
    blob = f"{title_l} {tags} {body[:400]}"
    score = 0
    for t in query_tokens:
        tl = t.lower()
        if tl in title_l:
            score += 4
        if tl in tags:
            score += 3
        if tl in body:
            score += 1
    if kind == "daily":
        if title.startswith("심층·"):
            return -999
        if "일운" in title or title.startswith("변수·일운"):
            score += 20
        if "오늘" in title:
            score += 16
        if title.startswith("변수·십신"):
            score += 10
        if any(x in blob for x in ("일운", "오늘", "당일")):
            score += 8
        if any(
            x in title
            for x in (
                "심층·",
                "사주팔자",
                "오행 균형",
                "십신·격국",
                "용신·기신",
                "대운·",
                "세운·",
                "월운",
                "재물",
                "연애·관계",
                "직업",
            )
        ):
            score -= 12
    elif kind == "monthly":
        if title.startswith("심층·"):
            score -= 8
        if "이번 달" in title or title == "해석·이번 달 운세":
            score += 20
        if "월운" in title or "세운" in title or "시기" in title:
            score += 14
        if title.startswith("변수·") and any(x in title for x in ("월운", "세운", "대운")):
            score += 10
        if "사주팔자" in title or title.startswith("심층·[2]"):
            score -= 10
    elif kind == "topic":
        if title.startswith("심층·") or title.startswith("해석·"):
            score += 8
        elif title.startswith("변수·"):
            score += 2
        if title.startswith("해석·") and "운" in title:
            score += 14
    elif kind == "summary":
        if title in ("해석·나의 운세", "해석·사주 풀이"):
            score += 28
        elif title.startswith("해석·") and any(
            x in title for x in ("나의 운세", "사주 풀이", "운세")
        ):
            score += 18
        if title.startswith("심층·"):
            score += 6
        elif title.startswith("해석·"):
            score += 10
    else:
        if title.startswith("심층·"):
            score += 12
        elif title.startswith("해석·"):
            score += 6
        elif title.startswith("변수·"):
            score -= 2
        if "심층 풀이" in title and any(
            t in query_tokens for t in ("심층풀이", "심층", "전체풀이", "풀리딩")
        ):
            score += 22
    if len((card.get("body") or "")) >= 900:
        score += 2
    return score


def _daily_eligible(card: dict) -> bool:
    title = (card.get("title") or "").strip()
    if title.startswith("심층·"):
        return False
    if title.startswith("변수·일운") or "오늘" in title:
        return True
    if title.startswith("변수·십신"):
        return True
    tags = " ".join(card.get("tags") or [])
    blob = f"{title} {tags}"
    return any(k in blob for k in ("일운", "오늘", "당일"))


def _monthly_eligible(card: dict) -> bool:
    title = (card.get("title") or "").strip()
    if title.startswith("심층·[2]") or "사주팔자" in title:
        return False
    tags = " ".join(card.get("tags") or [])
    blob = f"{title} {tags}"
    return any(k in blob for k in ("월운", "세운", "시기", "대운", "다음", "당월"))


def _eligible_for_kind(card: dict, kind: str) -> bool:
    if kind == "daily":
        return _daily_eligible(card)
    if kind == "monthly":
        return _monthly_eligible(card)
    return True


def _pool_card_allowed(card: dict, section_title: str, *, kind: str, deep_filled: bool) -> bool:
    """full/summary에서 심층 섹션에 변수·해석 카드가 심층을 대체하지 않도록."""
    title = (card.get("title") or "").strip()
    if kind not in ("full", "summary"):
        return True
    if title.startswith("심층·"):
        return True
    if not deep_filled:
        return True
    deep_title = DEEP_TITLE_BY_SECTION.get(section_title, "")
    if deep_title:
        return False
    if title.startswith("변수·") and section_title not in ("[5] 용신·기신", "[6] 대운·세운"):
        return False
    return True


def match_pass_cards(context: dict, *, limit: int = 12) -> list[dict]:
    kind = reading_kind(context)
    if kind == "daily":
        limit = min(limit, max(4, int(os.getenv("SAJU_READING_DAILY_MATCH_LIMIT", "6") or "6")))
    elif kind == "monthly":
        limit = min(limit, max(4, int(os.getenv("SAJU_READING_MONTHLY_MATCH_LIMIT", "8") or "8")))
    parts = [
        context.get("user_query") or "",
        context.get("question") or "",
        context.get("message") or "",
        context.get("summary") or "",
        context.get("topic") or "",
        " ".join(context.get("tags") or []),
        context.get("day_master") or "",
        context.get("geok") or "",
        " ".join(context.get("elements") or []),
        " ".join(context.get("ten_gods") or []),
    ]
    if kind == "daily":
        parts.extend(
            [
                context.get("day_fortune") or "",
                context.get("ilun") or "",
                context.get("today_ten_god") or "",
                "일운 오늘",
            ]
        )
    elif kind == "monthly":
        parts.extend(
            [
                context.get("month_fortune") or "",
                context.get("wolun") or "",
                "월운 다음달 이번달",
            ]
        )
    query_tokens = _tokens(" ".join(parts))
    for key in ("pillars", "keywords"):
        val = context.get(key)
        if isinstance(val, list):
            query_tokens |= _tokens(" ".join(str(x) for x in val))
        elif isinstance(val, str):
            query_tokens |= _tokens(val)

    scored: list[tuple[int, dict]] = []
    for card in _load_pass_cards():
        if not _eligible_for_kind(card, kind):
            continue
        s = _card_score(card, query_tokens, kind=kind)
        if s > 0:
            scored.append((s, card))
    scored.sort(key=lambda x: (-x[0], -(x[1].get("id") or 0)))
    return [c for _, c in scored[:limit]]


def _deep_cards_index() -> dict[str, dict]:
    return {
        (c.get("title") or "").strip(): c
        for c in _load_pass_cards()
        if (c.get("title") or "").strip().startswith("심층·")
    }


def _pick_section_cards(
    matched: list[dict], context: dict, *, kind: str = "full"
) -> list[tuple[str, dict]]:
    query_tokens = _tokens(
        " ".join(
            [
                context.get("summary") or "",
                " ".join(context.get("tags") or []),
                context.get("day_fortune") or "",
                context.get("ilun") or "",
                context.get("today_ten_god") or "",
                context.get("month_fortune") or "",
                context.get("wolun") or "",
            ]
        )
    )
    section_defs = _section_defs_for_kind(kind, context)
    deep_idx = _deep_cards_index() if kind in ("full", "summary") else {}
    pool = list(matched)
    seen_ids = {c.get("id") for c in pool}
    for c in _load_pass_cards():
        if not _eligible_for_kind(c, kind):
            continue
        if c.get("id") not in seen_ids:
            pool.append(c)
            seen_ids.add(c.get("id"))
    used: set[int] = set()
    picks: list[tuple[str, dict]] = []
    for section_title, hints in section_defs:
        deep_title = DEEP_TITLE_BY_SECTION.get(section_title, "")
        deep_filled = False
        if kind in ("full", "summary") and deep_title and deep_title in deep_idx:
            dc = deep_idx[deep_title]
            cid = dc.get("id")
            if cid not in used:
                used.add(cid)
                picks.append((section_title, dc))
                deep_filled = True
                continue

        hint_tokens = _tokens(" ".join(hints))
        best: tuple[int, dict] | None = None
        for card in pool:
            cid = card.get("id")
            if cid in used:
                continue
            if not _pool_card_allowed(card, section_title, kind=kind, deep_filled=deep_filled):
                continue
            s = _card_score(card, query_tokens | hint_tokens, kind=kind)
            if s <= 0:
                continue
            if best is None or s > best[0]:
                best = (s, card)
        if best:
            used.add(best[1].get("id"))
            picks.append((section_title, best[1]))
    return picks


def _section_heading(sec_title: str, kind: str) -> str:
    if kind == "daily":
        return "오늘의 운세"
    if kind == "monthly":
        return "이번 달·월운"
    m = re.match(r"\[(\d+)\]\s*(.+)", sec_title)
    if m:
        return f"{m.group(1)}. {m.group(2)}"
    return sec_title


def compose_from_cards(
    matched: list[dict], context: dict, *, kind: str = "full"
) -> dict[str, str | list[dict]]:
    """PASS 카드 조합 — text_chat(짧음) / text_full(심층·전체)."""
    try:
        from saju_reading_display import prepare_section_excerpt
    except ImportError:

        def prepare_section_excerpt(  # noqa: E731
            body, *, max_len=2800, section_title="", card_title="", allow_pillar=False
        ):
            return (body or "")[:max_len]

    chat_max, full_max = _excerpt_limits(kind)

    if kind == "daily":
        intro = (
            "※ **오늘의 운세** — 당일·일운 기준 참고 풀이입니다. "
            "심층 사주·대운·세운 전체 풀이는 별도 메뉴에서 확인하세요."
        )
    elif kind == "monthly":
        intro = (
            "※ **월운·시기** — 해당 월·세운 흐름 참고입니다. "
            "사주팔자 전체·십 년 대운은 심층 풀이에서 확인하세요."
        )
    elif kind == "summary":
        intro = (
            "※ **요약 풀이** — 인사·용신·시기 중심입니다. "
            "10절 심층 풀이는 메뉴에서 이어서 보실 수 있습니다."
        )
    elif kind == "topic":
        topic = (context.get("topic") or "주제").strip()
        intro = f"※ **{topic}** 관련 참고 풀이입니다. 다른 테마는 질문으로 구분해 주세요."
    else:
        intro = (
            "※ 아래는 사주위원회 **인증(PASS)** 학습 카드를 조합한 참고 풀이입니다. "
            "개인 사주에 맞게 해석·보완이 필요합니다."
        )

    chat_intro = intro
    if kind == "full":
        chat_intro += " (채팅에는 핵심 3절 요약만 표시됩니다.)"

    chat_lines: list[str] = [chat_intro, ""]
    full_lines: list[str] = [intro, ""]
    if context.get("summary") and kind not in ("daily", "monthly"):
        full_lines.append(f"【명식 요약】{context['summary'][:300]}")
        full_lines.append("")
        if kind == "summary":
            chat_lines.append(f"【명식 요약】{context['summary'][:200]}")
            chat_lines.append("")

    section_picks = _pick_section_cards(matched, context, kind=kind)
    chat_picks = section_picks
    if kind == "full" and len(section_picks) > 3:
        summary_keys = set(SUMMARY_SECTION_KEYS)
        filtered = [(t, c) for t, c in section_picks if t in summary_keys]
        chat_picks = filtered if filtered else section_picks[:3]

    chat_card_ids = {c.get("id") for _, c in chat_picks}
    section_payloads: list[dict] = []

    if section_picks:
        for sec_title, card in section_picks:
            body = (card.get("body") or "").strip()
            card_title = (card.get("title") or "").strip()
            allow_pillar = sec_title == "[2] 사주팔자"
            full_excerpt = prepare_section_excerpt(
                body,
                max_len=full_max,
                section_title=sec_title,
                card_title=card_title,
                allow_pillar=allow_pillar,
            )
            heading = _section_heading(sec_title, kind)
            full_lines.extend([heading, full_excerpt, ""])
            chat_excerpt = ""
            if card.get("id") in chat_card_ids:
                chat_excerpt = prepare_section_excerpt(
                    body,
                    max_len=chat_max,
                    section_title=sec_title,
                    card_title=card_title,
                    allow_pillar=allow_pillar,
                )
                if len(chat_excerpt.strip()) < 60:
                    chat_excerpt = prepare_section_excerpt(
                        body, max_len=chat_max, card_title=card_title
                    )
                chat_lines.extend([heading, chat_excerpt, ""])
            section_payloads.append(
                {
                    "title": sec_title,
                    "card_id": card.get("id"),
                    "card_title": card_title,
                    "excerpt": chat_excerpt or full_excerpt[:chat_max],
                }
            )
    else:
        fallback = matched[: min(2 if kind in ("daily", "monthly") else 4, len(matched))]
        for card in fallback:
            title = (card.get("title") or "").strip()
            body = (card.get("body") or "").strip()
            chat_excerpt = prepare_section_excerpt(
                body, max_len=chat_max, card_title=title
            )
            full_excerpt = prepare_section_excerpt(
                body, max_len=full_max, card_title=title
            )
            chat_lines.extend([f"· {title}", chat_excerpt, ""])
            full_lines.extend([f"· {title}", full_excerpt, ""])

    footer = (
        "【안내】확정 예언이 아닌 참고용입니다. "
        "상담·추가 질문은 AI 또는 전문가 검토를 권장합니다."
    )
    chat_lines.append(footer)
    full_lines.append(footer)

    text_chat = _cap_chat_text("\n".join(chat_lines).strip())
    text_full = "\n".join(full_lines).strip()
    if len(text_chat) < 80 and section_payloads:
        parts = [intro, ""]
        for sp in section_payloads[:3]:
            parts.append(_section_heading(sp["title"], kind))
            parts.append((sp.get("excerpt") or "")[:chat_max])
            parts.append("")
        parts.append(footer)
        text_chat = _cap_chat_text("\n".join(parts).strip())
    return {
        "text": text_chat,
        "text_chat": text_chat,
        "text_full": text_full,
        "sections": section_payloads,
    }


def build_reading(context: dict) -> dict:
    ctx = context if isinstance(context, dict) else {}
    try:
        from saju_reading_intent import apply_intent_to_context

        ctx = apply_intent_to_context(ctx)
    except ImportError:
        pass
    kind = reading_kind(ctx)
    matched = match_pass_cards(ctx)
    need = min_pass_cards_for(kind)
    pass_total = len(_load_pass_cards())

    if len(matched) >= need:
        composed = compose_from_cards(matched, ctx, kind=kind)
        section_picks = _pick_section_cards(matched, ctx, kind=kind)
        text_chat = (composed.get("text_chat") or "").strip()
        text_full = (composed.get("text_full") or "").strip()
        if len(text_chat) < 80:
            text_chat = _FALLBACK_CHAT
        headline = (ctx.get("summary") or "")[:120] or ctx.get("topic") or ""
        sec_list = composed.get("sections") or []
        return {
            "ok": True,
            "mode": "card_compose",
            "api_version": API_VERSION,
            "reading_kind": kind,
            "text": text_chat,
            "text_chat": text_chat,
            "text_full": text_full,
            "display": {
                "headline": headline,
                "body": text_chat,
            },
            "llm_required": False,
            "cost_krw": 0,
            "matched_count": len(matched),
            "section_count": len(section_picks),
            "min_pass_required": need,
            "pass_cards_total": pass_total,
            "matched_cards": [
                {
                    "id": c.get("id"),
                    "title": c.get("title"),
                    "tier": tier.TIER_CERTIFIED,
                }
                for c in matched[:10]
            ],
            "sections": sec_list
            if sec_list
            else [
                {"title": t, "card_id": c.get("id"), "card_title": c.get("title")}
                for t, c in section_picks
            ],
            "intent": {
                "reading_kind": kind,
                "topic": ctx.get("topic") or "",
                "inferred": bool(ctx.get("_intent_inferred")),
            },
        }

    llm_hint = (
        "※ 이 주제에 맞는 인증(PASS) 카드가 아직 부족합니다. "
        "AI 보조 풀이를 이용하시거나, 잠시 후 다시 조회해 주세요. "
        f"(매칭 {len(matched)}건 / 필요 {need}건 이상)"
    )
    return {
        "ok": True,
        "mode": "llm",
        "api_version": API_VERSION,
        "reading_kind": kind,
        "text": llm_hint,
        "text_chat": llm_hint,
        "text_full": "",
        "display": {"headline": ctx.get("topic") or "", "body": llm_hint},
        "llm_required": True,
        "cost_krw": None,
        "matched_count": len(matched),
        "min_pass_required": need,
        "pass_cards_total": pass_total,
        "matched_cards": [
            {
                "id": c.get("id"),
                "title": c.get("title"),
                "tier": tier.council_tier(c),
            }
            for c in matched[:5]
        ],
        "reason": (
            f"인증(PASS) 카드 매칭 {len(matched)}건 — 무료 조합에는 {need}건 이상 필요 "
            f"(현재 전체 PASS {pass_total}건, kind={kind})"
        ),
    }


def main() -> int:
    import board_env

    board_env.load_board_env()
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["demo", "stats", "inventory", "demo-daily", "demo-summary"])
    p.add_argument("--tags", default="일주,병화,정관,용신,오행")
    args = p.parse_args()
    if args.cmd == "stats":
        print("pass_cards", len(_load_pass_cards()))
        print("min_pass", min_pass_cards())
        return 0
    if args.cmd == "inventory":
        import json

        print(json.dumps(pass_inventory(), ensure_ascii=False, indent=2))
        return 0
    ctx = {"tags": [t.strip() for t in args.tags.split(",") if t.strip()]}
    if args.cmd == "demo-daily":
        ctx["reading_kind"] = "daily"
        ctx["tags"] = list(ctx["tags"]) + ["일운", "오늘"]
    if args.cmd == "demo-summary":
        ctx["reading_kind"] = "summary"
    import json

    print(json.dumps(build_reading(ctx), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
