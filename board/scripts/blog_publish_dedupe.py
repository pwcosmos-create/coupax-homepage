"""
블로그 발행 — 기존 공개 글과 제목·본문 중복 판별.
"""
from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass

import blog_adsense_enrich as adsense

_GENERIC_TITLE = re.compile(
    r"^(블로그\s*글감|사무실\s*작업|작업\s*#?\d+|예약\s*작업|금융\s*위원회|팩트\s*펄스).*$",
    re.I,
)
_STOP = frozenset(
    {
        "그리고",
        "있습니다",
        "합니다",
        "대한",
        "경우",
        "통해",
        "이번",
        "관련",
        "정보",
        "제공",
        "목적",
        "참고",
        "확인",
        "수 있습니다",
        "있으며",
        "따라",
        "때문",
        "gemma",
        "coupax",
        "adsense",
        "enriched",
    }
)


@dataclass
class PublishedDoc:
    post_id: int
    title: str
    title_norm: str
    title_tokens: frozenset[str]
    body_tokens: frozenset[str]


def normalize_title(title: str) -> str:
    t = (title or "").strip().lower()
    t = re.sub(r"\[.*?\]", "", t)
    t = re.sub(r"\s+", "", t)
    t = re.sub(r"[^\w가-힣]", "", t)
    return t


def _tokens_from_text(text: str, *, limit: int = 120) -> frozenset[str]:
    raw = adsense._strip_html(text or "").lower()
    found = re.findall(r"[가-힣]{2,}|[a-z]{3,}|\d{2,}", raw)
    out: list[str] = []
    seen: set[str] = set()
    for tok in found:
        if tok in _STOP or tok in seen:
            continue
        seen.add(tok)
        out.append(tok)
        if len(out) >= limit:
            break
    return frozenset(out)


def title_similarity(a: str, b: str) -> float:
    na, nb = normalize_title(a), normalize_title(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if len(na) >= 8 and len(nb) >= 8 and (na in nb or nb in na):
        return 0.92
    ta, tb = _tokens_from_text(a, limit=12), _tokens_from_text(b, limit=12)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def body_similarity(html_a: str, html_b: str) -> float:
    ta = _tokens_from_text(html_a)
    tb = _tokens_from_text(html_b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def load_published_index(
    conn: sqlite3.Connection,
    *,
    lookback: int | None = None,
) -> list[PublishedDoc]:
    n = int(os.getenv("BLOG_PUBLISH_DEDUP_LOOKBACK", "400") or "400")
    if lookback is not None:
        n = lookback
    n = max(50, min(n, 2000))
    rows = conn.execute(
        """
        SELECT id, title, content FROM posts
        WHERE COALESCE(is_draft, 0) = 0
        ORDER BY id DESC
        LIMIT ?
        """,
        (n,),
    ).fetchall()
    out: list[PublishedDoc] = []
    for pid, title, content in rows:
        t = title or ""
        out.append(
            PublishedDoc(
                post_id=int(pid),
                title=t,
                title_norm=normalize_title(t),
                title_tokens=_tokens_from_text(t, limit=16),
                body_tokens=_tokens_from_text(content or "", limit=120),
            )
        )
    return out


def is_duplicate_of_published(
    title: str,
    content: str,
    published: list[PublishedDoc],
    *,
    exclude_post_id: int | None = None,
) -> tuple[bool, str]:
    """True면 기존 공개 글과 중복으로 판단."""
    title_thr = float(os.getenv("BLOG_PUBLISH_DEDUP_TITLE_SIM", "0.82") or "0.82")
    body_thr = float(os.getenv("BLOG_PUBLISH_DEDUP_BODY_SIM", "0.52") or "0.52")
    tnorm = normalize_title(title)
    generic = bool(_GENERIC_TITLE.match((title or "").strip()))
    body_tok = _tokens_from_text(content or "")

    for doc in published:
        if exclude_post_id is not None and doc.post_id == exclude_post_id:
            continue

        if not generic and tnorm and doc.title_norm and tnorm == doc.title_norm:
            return True, f"제목 동일 (공개 #{doc.post_id})"

        ts = title_similarity(title, doc.title)
        if not generic and ts >= title_thr:
            return True, f"제목 유사 {ts:.0%} (공개 #{doc.post_id})"

        if body_tok and doc.body_tokens:
            inter = len(body_tok & doc.body_tokens)
            union = len(body_tok | doc.body_tokens)
            sim = inter / union if union else 0.0
            if sim >= body_thr:
                return True, f"본문 유사 {sim:.0%} (공개 #{doc.post_id})"

        if generic and body_tok and doc.body_tokens:
            inter = len(body_tok & doc.body_tokens)
            union = len(body_tok | doc.body_tokens)
            sim = inter / union if union else 0.0
            if sim >= min(0.62, body_thr + 0.08):
                return True, f"글감형 본문 중복 {sim:.0%} (공개 #{doc.post_id})"

    return False, ""


def filter_unique_candidates(
    conn: sqlite3.Connection,
    candidates: list[dict],
) -> tuple[list[dict], list[dict]]:
    """중복 제외 후보 / 스킵 목록."""
    published = load_published_index(conn)
    unique: list[dict] = []
    skipped: list[dict] = []
    seen_body: list[frozenset[str]] = []

    for c in sorted(candidates, key=lambda x: (-x.get("score", 0), x.get("id", 0))):
        pid = c.get("id")
        row = conn.execute(
            "SELECT title, content FROM posts WHERE id=?", (pid,)
        ).fetchone()
        if not row:
            continue
        title, content = row[0] or "", row[1] or ""
        dup, reason = is_duplicate_of_published(title, content, published)
        if dup:
            skipped.append({**c, "skip_reason": reason})
            continue
        bt = _tokens_from_text(content)
        for prev in seen_body:
            inter = len(bt & prev)
            union = len(bt | prev)
            if union and inter / union >= float(
                os.getenv("BLOG_PUBLISH_DEDUP_QUEUE_SIM", "0.58") or "0.58"
            ):
                skipped.append({**c, "skip_reason": "대기 초안끼리 본문 유사"})
                break
        else:
            seen_body.append(bt)
            unique.append(c)

    return unique, skipped
