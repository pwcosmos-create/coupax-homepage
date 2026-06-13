"""
차수거래 학습 카드 — 본문·카테고리 기반 제목 자동 생성(중복 회피).

  KIWOM_TITLE_LLM=1  + GEMINI_API_KEY → Gemini로 1줄 제목(선택)
  기본: 규칙 기반 제목 + 유일성 접미
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

try:
    import board_env

    board_env.load_board_env()
except ImportError:
    pass

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

_ERROR_KIND_LABEL = {
    "too_short": "본문·길이 부족",
    "pii": "PII·보안",
    "tag_missing": "태그·키워드",
    "duplicate": "제목 중복",
    "confirm_failed": "확정 실패",
    "unknown": "형식·검수",
}

_TOPIC_KW = (
    ("VI", "VI·거래정지"),
    ("거래정지", "거래정지"),
    ("배당", "배당·락"),
    ("권리락", "배당·락"),
    ("ETF", "ETF·배당"),
    ("CMA", "CMA·이체"),
    ("이체", "계좌 이체"),
    ("계좌간", "계좌간 이동"),
    ("공매도", "공매도"),
    ("프로그램", "프로그램 매매"),
    ("해외", "해외·환전"),
    ("환전", "해외·환전"),
    ("신용", "신용·레버"),
    ("레버", "레버리지"),
    ("연금", "연금·ISA"),
    ("ISA", "연금·ISA"),
    ("HTS", "HTS·주문"),
    ("미체결", "미체결"),
    ("손절", "손절·익절"),
    ("익절", "손절·익절"),
    ("3차", "3차 차수"),
    ("2차", "2차 차수"),
    ("1차", "1차 차수"),
)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _now_short() -> str:
    return datetime.now().strftime("%m%d")


def title_llm_enabled() -> bool:
    return os.getenv("KIWOM_TITLE_LLM", "1").strip().lower() in ("1", "true", "yes", "on")


def _gemini_key() -> str:
    return (os.getenv("GEMINI_API_KEY") or "").strip()


def _first_clause(text: str, n: int = 32) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    if not t:
        return ""
    for sep in (".", "。", "—", "·", "\n"):
        if sep in t[:80]:
            t = t.split(sep, 1)[0]
            break
    return t[:n].strip(" ·-")


def _detect_topic(body: str, seed: str = "") -> str:
    blob = f"{seed} {body}"
    for needle, label in _TOPIC_KW:
        if needle in blob:
            return label
    if "차수" in blob:
        return "차수 운용"
    if "계좌" in blob:
        return "계좌·예수금"
    return "차수거래 메모"


def rule_title(
    *,
    body: str,
    category: str = "",
    error_kind: str = "",
    seed: str = "",
) -> str:
    """규칙 기반 한 줄 제목."""
    cat = (category or "").strip().lower()
    kind = (error_kind or "").strip()
    topic = _detect_topic(body, seed)

    if cat == "meta" or kind or (seed or "").startswith("학습 카드 작성") or "오류" in (seed or ""):
        label = _ERROR_KIND_LABEL.get(kind) or (kind if kind else "") or _first_clause(body, 20) or "제작·검수"
        hook = _first_clause(body, 24)
        parts = [f"카드제작 가이드 · {label}"]
        if hook and hook not in parts[0]:
            parts.append(hook)
        return " — ".join(parts)[:118]

    hook = _first_clause(body, 36)
    if seed and not seed.startswith("__") and len(seed) < 50:
        base = seed.split("—")[0].strip()[:40]
        if base != hook:
            return f"{topic} · {hook}"[:118] if hook else f"{topic} · {base}"[:118]
    if hook:
        return f"{topic} · {hook}"[:118]
    return f"{topic} · 운용 메모"[:118]


def _gemini_title(body: str, category: str, error_kind: str) -> str | None:
    if not title_llm_enabled() or not _gemini_key():
        return None
    model = (os.getenv("KIWOM_TITLE_GEMINI_MODEL") or os.getenv("SAJU_CARD_GEMINI_MODEL") or "gemini-2.5-flash").strip()
    kind_note = f"오류 유형: {error_kind}. " if error_kind else ""
    prompt = (
        f"{kind_note}카테고리: {category or 'general'}.\n"
        "아래 원히어로 매매 규칙 학습 카드 본문을 읽고, 한국어 제목 한 줄만 작성하세요.\n"
        "규칙: 8~45자, 투자 권유 금지, 슬롯·ATR·익절·1·2차·계좌 중 1개 이상 포함, "
        "따옴표·번호·접두 '학습 카드 작성 오류' 사용 금지.\n"
        f"본문:\n{(body or '')[:1200]}\n"
        "출력: 제목만."
    )
    url = f"{GEMINI_API_BASE}/models/{model}:generateContent?key={_gemini_key()}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 80},
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        parts = (
            (data.get("candidates") or [{}])[0]
            .get("content", {})
            .get("parts")
            or []
        )
        text = "".join(p.get("text", "") for p in parts).strip()
        text = re.sub(r"^[\"'「『\s]+|[\"'」』\s]+$", "", text.split("\n", 1)[0])
        if 6 <= len(text) <= 120:
            return text[:120]
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError):
        return None
    return None


def generate_title(
    *,
    body: str,
    category: str = "",
    error_kind: str = "",
    seed: str = "",
    taken: set[str] | None = None,
) -> str:
    import agent_office_kiwoom_learn as learn

    titles = taken if taken is not None else learn.existing_titles()
    llm = _gemini_title(body, category, error_kind)
    base = learn.normalize_title(llm or rule_title(
        body=body, category=category, error_kind=error_kind, seed=seed
    ))
    if not base:
        base = learn.normalize_title(rule_title(body=body, category=category, error_kind=error_kind))
    return learn.ensure_unique_title(base, titles)


def enrich_spec(spec: dict, *, error_kind: str = "", taken: set[str] | None = None) -> dict:
    """본문은 유지, 제목만 자동 생성·유일화. catalog_seed에 원제목 보관."""
    import agent_office_kiwoom_learn as learn

    row = dict(spec)
    body = (row.get("body") or "").strip()
    if not body:
        return row
    cat = str(row.get("category") or "")
    seed = (row.get("catalog_seed") or row.get("title") or "").strip()
    if seed and not row.get("catalog_seed"):
        row["catalog_seed"] = seed
    kind = error_kind or str(row.get("error_kind") or "")
    if cat == "meta" and not kind and "too_short" in seed:
        kind = "too_short"
    row["title"] = generate_title(
        body=body,
        category=cat,
        error_kind=kind,
        seed=seed,
        taken=taken,
    )
    return row


def enrich_specs(specs: list[dict], **kw) -> list[dict]:
    import agent_office_kiwoom_learn as learn

    titles = learn.existing_titles()
    out: list[dict] = []
    for spec in specs:
        row = enrich_spec(spec, taken=titles, **kw)
        t = learn.normalize_title(row.get("title") or "")
        if t:
            titles.add(t)
        out.append(row)
    return out
