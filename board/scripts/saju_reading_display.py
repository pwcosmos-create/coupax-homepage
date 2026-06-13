"""심층 풀이·카드 표시용 본문 정리 — 메타 절 제거·중복 헤더 병합·섹션 excerpt."""
from __future__ import annotations

import re

from saju_card_reverify_enrich import FOOTER_MARK, STANDARD_FOOTER, format_readable_body

# 상담 화면에 노출하지 않을 작성 가이드 절
_META_HEADERS = frozenset(
    {
        "풀이 절차",
        "활용 키워드",
        "핵심",
        "예시 서술",
        "풀이 예문",
        "프레임",
    }
)

# 작성 가이드·메타 문장 (상담 excerpt에서 제거)
_GUIDE_SENTENCE_RE = re.compile(
    r"(으로만\s*서술|"
    r"일간·월지·격국·용신·대운·세운과\s*함께|"
    r"학파별|"
    r"신강·신약·억부로\s*방향|"
    r"2~4문장씩\s*서술|"
    r"절당\s*2~4문장|"
    r"테마를\s*오행·십신·격국·용신·대운\s*순으로)",
    re.I,
)

_EMPTY_BRACKET_RE = re.compile(r"「\s*」")

_SECTION_RE = re.compile(r"【([^】]+)】")

# 심층 섹션 제목 → 우선 추출할 【절】 라벨
_SECTION_LABEL_PRIORITY: dict[str, list[str]] = {
    "[1] 인사·성향": ["인사·성향", "인사", "성향"],
    "[2] 사주팔자": ["사주팔자", "사주", "팔자"],
    "[3] 오행 균형": ["오행", "오행·십신", "오행·십신 해석"],
    "[4] 십신·격국": ["십신", "격국", "십신·격국", "오행·십신 해석"],
    "[5] 용신·기신": ["용신", "기신", "희신", "명식·구조"],
    "[6] 대운·세운": ["시기·운세", "대운", "세운", "월운"],
    "[7] 재물": ["테마 풀이", "재물", "재성"],
    "[8] 연애·관계": ["테마 풀이", "연애", "관계", "궁합"],
    "[9] 직업": ["테마 풀이", "직업", "식신", "관성"],
    "[10] 실천·주의": ["실천 조언", "실천", "주의"],
    "[오늘] 오늘의 운세": ["일운", "오늘", "오늘의 운세", "인사·성향", "시기·운세"],
    "[월] 시기·운세": ["시기·운세", "월운", "세운", "대운", "테마 풀이"],
}

# 팔자 4기둥 장문 — 해당 섹션이 아니면 excerpt에서 제외
_PILLAR_BLOCK_RE = re.compile(r"(년주|월주|일주|시주)\([年月日時]柱\)")

# 카드 제목 힌트 → 우선 절
_CARD_TITLE_LABEL_HINTS: list[tuple[str, list[str]]] = [
    ("일운", ["일운", "오늘", "시기·운세"]),
    ("오늘", ["일운", "오늘", "인사·성향"]),
    ("용신", ["용신", "희신"]),
    ("기신", ["기신"]),
    ("희신", ["희신", "용신"]),
    ("월운", ["시기·운세", "월운", "세운"]),
    ("세운", ["시기·운세", "세운"]),
    ("대운", ["시기·운세", "대운"]),
    ("재물", ["테마 풀이", "재물"]),
    ("연애", ["테마 풀이", "연애"]),
    ("직업", ["테마 풀이", "직업"]),
]


def _strip_footer(text: str) -> str:
    out = (text or "").strip()
    while FOOTER_MARK in out:
        out = out[: out.find(FOOTER_MARK)].rstrip()
    return out


def fix_empty_brackets(text: str) -> str:
    """「」 빈칸·「 에 」류 정리."""
    out = _EMPTY_BRACKET_RE.sub("", text or "")
    out = re.sub(r"에서\s+에\s+해당", "에서 해당", out)
    out = re.sub(r"함께\s+으로만", "함께", out)
    out = re.sub(r"\s{2,}", " ", out)
    return out.strip()


def strip_guide_sentences(text: str) -> str:
    """작성 가이드 문장 제거."""
    if not text:
        return text
    parts = re.split(r"(?<=[.。!?])\s+", text.strip())
    kept = [p for p in parts if p and not _GUIDE_SENTENCE_RE.search(p)]
    return " ".join(kept).strip() if kept else text.strip()


def _dedupe_sentences(text: str) -> str:
    """동일 문장 반복 제거 — 단락(빈 줄) 구조는 유지."""
    raw = (text or "").strip()
    if not raw:
        return raw
    blocks = re.split(r"\n\s*\n", raw)
    out_blocks: list[str] = []
    for block in blocks:
        chunk = block.strip()
        if not chunk:
            continue
        if chunk.startswith("【") or re.search(r"(년주|월주|일주|시주)\(.", chunk):
            out_blocks.append(chunk)
            continue
        parts = re.split(r"(?<=[.。!?])\s+", chunk)
        seen: set[str] = set()
        kept: list[str] = []
        for p in parts:
            key = re.sub(r"\s+", " ", p.strip())
            if not key or len(key) < 12:
                continue
            if key in seen:
                continue
            seen.add(key)
            kept.append(p.strip())
        out_blocks.append(" ".join(kept) if kept else chunk)
    return "\n\n".join(out_blocks)


def _fix_pillar_header_runtogether(text: str) -> str:
    """기둥 제목 줄과 본문이 한 줄에 붙은 경우만 단락 분리."""
    splits = (
        (r"년주\(年柱\)\s*—[^\n]+", r"(?=조상·)"),
        (r"월주\(月柱\)\s*—[^\n]+", r"(?=부모·)"),
        (r"일주\(日柱\)\s*—[^\n]+", r"(?=본인\()"),
        (r"시주\(時柱\)\s*—[^\n]+", r"(?=자녀·)"),
    )
    out = text
    for head, lookahead in splits:
        out = re.sub(rf"({head})\s+{lookahead}", r"\1\n\n", out, count=1)
    return out


def _header_label(raw: str) -> str:
    """【테마 풀이】【연애·관계】 → 연애·관계 (표시용)."""
    parts = [p.strip() for p in raw.split("】") if p.strip()]
    parts = [p.replace("【", "").strip() for p in parts if p.replace("【", "").strip()]
    if not parts:
        return raw.strip()
    for p in reversed(parts):
        if p not in ("테마 풀이", "오행·십신 해석", "시기·운세", "명식·구조"):
            return p
    return parts[-1]


def split_body_sections(body: str) -> list[tuple[str, str]]:
    """본문을 (헤더라벨, 내용) 목록으로 분리."""
    text = fix_empty_brackets(_strip_footer(body))
    if not text:
        return []
    matches = list(_SECTION_RE.finditer(text))
    if not matches:
        return [("", text)]
    out: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        label = _header_label(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = strip_guide_sentences(text[start:end].strip())
        if chunk:
            out.append((label, chunk))
    return out


def _labels_for_excerpt(section_title: str, card_title: str) -> list[str]:
    """섹션·카드 제목에서 우선 추출할 절 라벨 순서."""
    labels: list[str] = []
    seen: set[str] = set()

    def add(*items: str) -> None:
        for x in items:
            if x and x not in seen:
                seen.add(x)
                labels.append(x)

    add(*_SECTION_LABEL_PRIORITY.get(section_title, []))
    ct = (card_title or "").strip()
    for hint, prefs in _CARD_TITLE_LABEL_HINTS:
        if hint in ct:
            add(*prefs)
    if ct.startswith("변수·"):
        sub = ct.replace("변수·", "")
        if "용신" in sub:
            add("용신", "희신")
        if "기신" in sub:
            add("기신")
        if "일운" in sub or "오늘" in sub:
            add("일운", "오늘", "시기·운세")
    add("테마 풀이", "실천 조언", "인사·성향")
    return labels


def _chunk_has_pillar_essay(chunk: str) -> bool:
    return bool(_PILLAR_BLOCK_RE.search(chunk)) and len(chunk) > 400


def excerpt_for_section(
    body: str,
    section_title: str,
    card_title: str = "",
    *,
    max_len: int = 700,
    allow_pillar: bool = False,
) -> str:
    """
    조합·채팅용 — 섹션/카드에 맞는 【절】만 추출.
    allow_pillar=True 이면 [2] 사주팔자 등에서 기둥 설명 허용.
    """
    sections = split_body_sections(body)
    if not sections:
        raw = strip_guide_sentences(fix_empty_brackets(_strip_footer(body)))
        return raw[:max_len] + ("…" if len(raw) > max_len else "")

    want = _labels_for_excerpt(section_title, card_title)
    picked: list[str] = []

    for label in want:
        for sec_label, chunk in sections:
            if label in sec_label or sec_label in label:
                if not allow_pillar and _chunk_has_pillar_essay(chunk):
                    short = strip_guide_sentences(chunk[:320].strip())
                    if short:
                        picked.append(f"【{sec_label}】\n{short}")
                    continue
                text = _dedupe_sentences(strip_guide_sentences(chunk))
                if len(text) >= 20:
                    picked.append(f"【{sec_label}】\n{text}")
                break
        if picked and sum(len(p) for p in picked) >= max_len * 0.85:
            break

    if not picked:
        for sec_label, chunk in sections:
            if sec_label in _META_HEADERS:
                continue
            if not allow_pillar and _chunk_has_pillar_essay(chunk):
                continue
            text = _dedupe_sentences(strip_guide_sentences(chunk))
            if len(text) >= 40:
                picked.append(f"【{sec_label}】\n{text}")
                break

    out = "\n\n".join(picked).strip()
    if not out:
        out = strip_guide_sentences((body or "")[:max_len])

    if len(out) > max_len:
        out = out[: max_len - 1].rstrip() + "…"
    return format_readable_body(out)


def normalize_body_for_reading(body: str, *, min_chars: int = 0) -> str:
    """
    메타 절 제거, 동일 헤더 병합, 주의 1회만.
    상담 화면·조합 출력용.
    """
    body = fix_empty_brackets(body)
    sections = split_body_sections(body)
    if not sections:
        return format_readable_body(_strip_footer(body))

    merged: dict[str, list[str]] = {}
    order: list[str] = []
    caution_parts: list[str] = []

    for label, chunk in sections:
        if not label:
            key = "__intro__"
        elif label in _META_HEADERS or label.startswith("개요") and len(chunk) < 120:
            continue
        elif label in ("주의", "주의·마무리"):
            caution_parts.append(chunk)
            continue
        else:
            key = label
        if key not in merged:
            merged[key] = []
            order.append(key)
        merged[key].append(_dedupe_sentences(chunk))

    lines: list[str] = []
    for key in order:
        if key == "__intro__":
            intro = " ".join(merged[key]).strip()
            if intro:
                lines.append(_fix_pillar_header_runtogether(intro))
            continue
        text = " ".join(merged[key]).strip()
        if len(text) < 40:
            continue
        text = _fix_pillar_header_runtogether(text)
        lines.append(f"【{key}】\n{text}")

    if caution_parts:
        caution = " ".join(caution_parts).strip()
        if caution and "주의" not in "".join(lines[-1:] if lines else []):
            lines.append(f"【주의】\n{caution}")

    result = "\n\n".join(lines).strip()
    if FOOTER_MARK not in result and len(result) >= min_chars:
        result = result.rstrip("。. ") + STANDARD_FOOTER
    return format_readable_body(result)


def optimize_card_body(body: str, *, min_chars: int = 0) -> str:
    """카드 저장·표시용 본문 — 절 분리·기둥 단락·중복 문장 제거."""
    text = format_readable_body(fix_empty_brackets((body or "").strip()))
    text = normalize_body_for_reading(text, min_chars=min_chars)
    return text.strip()


def prepare_section_excerpt(
    body: str,
    *,
    max_len: int = 2800,
    section_title: str = "",
    card_title: str = "",
    allow_pillar: bool = False,
) -> str:
    """섹션 조합용 — 절 단위 excerpt 우선, 없으면 정리 후 자르기."""
    if section_title or card_title:
        return excerpt_for_section(
            body,
            section_title,
            card_title,
            max_len=max_len,
            allow_pillar=allow_pillar,
        )
    cleaned = normalize_body_for_reading(body)
    core = _strip_footer(cleaned)
    if len(core) <= max_len:
        return cleaned
    return cleaned[: max_len - 1].rstrip() + "…"


def body_has_quality_issues(body: str) -> list[str]:
    """카드 본문 품질 이슈 (빈 「」, 가이드만 있는 절)."""
    issues: list[str] = []
    if _EMPTY_BRACKET_RE.search(body or ""):
        issues.append("empty_brackets")
    if re.search(r"에서\s+에\s+해당", body or ""):
        issues.append("broken_theme_phrase")
    if _GUIDE_SENTENCE_RE.search(body or "") and len((body or "")) < 500:
        issues.append("guide_heavy_short")
    return issues
