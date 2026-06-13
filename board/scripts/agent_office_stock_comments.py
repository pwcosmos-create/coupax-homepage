"""
종목·증시 관련 댓글 — 웹 검색·시세 스냅샷 교차 검증.

댓글은 익명·과장·오정보일 수 있으므로 단독 신뢰하지 않습니다.
"""
from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path

import agent_office_stock_watch as sw

BOARD = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("BOARD_DB_PATH", str(BOARD / "board.db")))

_STOCK_KW = re.compile(
    r"주식|코스피|코스닥|나스닥|증시|증권|매수|매도|상한가|하한가|"
    r"etf|배당|시총|공매도|급등|급락|반등|종목|차트|per\b|roe\b|"
    r"삼성|하이닉스|sk하이닉스|네이버|엔비디아|nvidia|테슬라|tsla|"
    r"apple|aapl|msft|코인|비트코인|연준|금리|환율|"
    r"s&p|sp500|다우|나스닥|월가",
    re.I,
)
_HYPE = re.compile(
    r"무조건|100\s*%|확정|대박|존버|올인|떡상\s*각|폭등\s*확실|"
    r"반드시\s*오른|절대\s*떨어|공짜|원금\s*보장|지금\s*안\s*사면",
    re.I,
)
_BEAR = re.compile(r"급락|폭락|붕괴|망했|망함|개미\s*털|싹\s*날|지옥|공포", re.I)
_BULL = re.compile(r"급등|상한가|폭등|대세\s*상승|불장|신고가|초대박|간다", re.I)
_BOT_AUTHOR = re.compile(r"gemma|젬마|gemma24|bot", re.I)


def _max_comments() -> int:
    try:
        return max(1, min(int(os.getenv("STOCK_COMMENT_VERIFY_MAX", "6") or "6"), 12))
    except ValueError:
        return 6


def _redact(text: str) -> str:
    try:
        from agent_office_wiki_store import _redact_pii

        return _redact_pii(text or "")
    except ImportError:
        t = text or ""
        t = re.sub(r"01[0-9]-?\d{3,4}-?\d{4}", "[전화]", t)
        return t


def _is_stock_related(text: str, post_title: str = "") -> bool:
    blob = f"{text} {post_title}"
    return bool(_STOCK_KW.search(blob))


def _load_recent_stock_comments(limit: int = 40) -> list[dict]:
    if not DB_PATH.is_file():
        return []
    rows: list[dict] = []
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        raw = conn.execute(
            """
            SELECT c.id, c.post_id, c.author, c.content, c.created,
                   p.title AS post_title
            FROM comments c
            LEFT JOIN posts p ON p.id = c.post_id
            ORDER BY c.id DESC
            LIMIT ?
            """,
            (limit * 3,),
        ).fetchall()
    for r in raw:
        author = (r["author"] or "").strip()
        if _BOT_AUTHOR.search(author):
            continue
        content = _redact(re.sub(r"\s+", " ", (r["content"] or "")).strip())
        if len(content) < 12:
            continue
        title = _redact((r["post_title"] or "").strip())
        if not _is_stock_related(content, title):
            continue
        rows.append(
            {
                "comment_id": int(r["id"]),
                "post_id": int(r["post_id"]),
                "author": author[:40],
                "content": content[:500],
                "excerpt": content[:160],
                "created": r["created"] or "",
                "post_title": title[:120],
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _index_change_pct(snap: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    mk = snap.get("markets") or {}
    kr_idx = ((mk.get("kr") or {}).get("indices") or [])
    us_idx = ((mk.get("us") or {}).get("indices") or [])
    if kr_idx:
        out["kospi"] = float(kr_idx[0].get("change_pct") or 0)
    if len(kr_idx) > 1:
        out["kosdaq"] = float(kr_idx[1].get("change_pct") or 0)
    if us_idx:
        out["sp500"] = float(us_idx[0].get("change_pct") or 0)
    if len(us_idx) > 1:
        out["nasdaq"] = float(us_idx[1].get("change_pct") or 0)
    return out


def _crosscheck_market(text: str) -> tuple[str, str]:
    """댓글 톤 vs 당일 스냅샷 지수."""
    snap = sw.load_snapshot()
    if not snap.get("updated_at"):
        return "스냅샷 없음", "시세 수집 후 비교 가능"
    idx = _index_change_pct(snap)
    if not idx:
        return "스냅샷 없음", "지수 데이터 없음"

    bear = bool(_BEAR.search(text))
    bull = bool(_BULL.search(text))
    kospi = idx.get("kospi", 0.0)
    nasdaq = idx.get("nasdaq", idx.get("sp500", 0.0))
    notes: list[str] = []

    if bear and kospi > 0.4:
        notes.append(f"약세 표현 vs 코스피 {kospi:+.2f}%")
    if bull and kospi < -0.4:
        notes.append(f"강세 표현 vs 코스피 {kospi:+.2f}%")
    if bear and nasdaq > 0.4:
        notes.append(f"약세 표현 vs 나스닥권 {nasdaq:+.2f}%")
    if bull and nasdaq < -0.4:
        notes.append(f"강세 표현 vs 나스닥권 {nasdaq:+.2f}%")

    summary = ", ".join(f"{k} {v:+.2f}%" for k, v in idx.items())
    if notes:
        return "불일치", f"{'; '.join(notes)} · 당일: {summary}"
    if bear or bull:
        return "대체 일치", f"톤·지수 방향 유사 · 당일: {summary}"
    return "중립", f"당일 지수: {summary}"


def _web_sources(text: str, post_title: str) -> list[dict]:
    try:
        import agent_office_web_search as ws
    except ImportError:
        return []
    if not ws.web_search_enabled():
        return []

    q1 = re.sub(r"\s+", " ", text)[:90]
    if not re.search(r"(검증|팩트|뉴스)", q1):
        q1 = f"{q1} 주식 팩트"
    q2 = f"{post_title[:50]} 증시 오늘" if post_title else "코스피 나스닥 오늘 시황"

    seen: set[str] = set()
    out: list[dict] = []
    for query in (q1, q2):
        for hit in ws.search_web(query, limit=3):
            key = (hit.url or hit.title or "")[:100]
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "title": hit.title[:120],
                    "snippet": hit.snippet[:240],
                    "url": hit.url,
                    "provider": hit.provider,
                    "query": query[:70],
                }
            )
            if len(out) >= 5:
                return out
    return out


def _compare_sources(sources: list[dict]) -> str:
    if len(sources) >= 2:
        providers = {s.get("provider") for s in sources if s.get("provider")}
        if len(providers) >= 2:
            return f"출처 {len(sources)}건·{len(providers)}채널 교차"
        return f"출처 {len(sources)}건 대조"
    if len(sources) == 1:
        return "출처 1건 — 추가 확인 권장"
    return "웹 출처 없음"


def _verdict(
    text: str,
    market_label: str,
    market_note: str,
    sources: list[dict],
) -> tuple[str, str]:
    hype = bool(_HYPE.search(text))
    src_note = _compare_sources(sources)
    mismatch = market_label == "불일치"

    if hype:
        return (
            "주의",
            f"과장·확정 표현 감지. {src_note}. {market_note}",
        )
    if mismatch and len(sources) < 2:
        return (
            "의심",
            f"댓글 톤이 당일 시세와 어긋남. {market_note} · {src_note}",
        )
    if mismatch and len(sources) >= 2:
        return (
            "불확실",
            f"댓글 vs 시세 불일치이나 웹 기사는 존재 — 직접 대조 필요. {market_note}",
        )
    if len(sources) >= 2:
        return (
            "교차확인",
            f"웹 {len(sources)}건 수집·시세 {market_label}. 댓글만으로 확정 불가. {market_note}",
        )
    if len(sources) == 1:
        return (
            "불확실",
            f"단일 출처. {market_note} · {src_note}",
        )
    return (
        "미검증",
        f"근거 부족 — 댓글을 사실로 보지 마세요. {market_note}",
    )


def verify_comment(row: dict) -> dict:
    text = row.get("content") or ""
    title = row.get("post_title") or ""
    market_label, market_note = _crosscheck_market(text)
    sources = _web_sources(text, title)
    verdict, detail = _verdict(text, market_label, market_note, sources)
    return {
        "comment_id": row.get("comment_id"),
        "post_id": row.get("post_id"),
        "author": row.get("author"),
        "created": row.get("created"),
        "excerpt": row.get("excerpt"),
        "post_title": title,
        "verdict": verdict,
        "verdict_detail": detail[:400],
        "market_check": f"{market_label}: {market_note}"[:200],
        "web_sources": sources[:4],
        "source_count": len(sources),
    }


def run_comment_verify() -> dict:
    rows = _load_recent_stock_comments(limit=_max_comments())
    if not rows:
        summary = f"댓글검증젬마 ({sw._now()}): 최근 증시 관련 댓글 없음"
        return sw.save_insights_section("comments", [], summary=summary)

    items = [verify_comment(r) for r in rows]
    counts: dict[str, int] = {}
    for it in items:
        v = it.get("verdict") or "?"
        counts[v] = counts.get(v, 0) + 1

    lines = [
        f"댓글검증젬마 ({sw._now()}) — {len(items)}건 (웹·시세 교차, 댓글 단독 불가)",
        "  ※ 댓글은 항상 검증 전제 — 과장·루머 가능",
    ]
    for v in ("주의", "의심", "미검증", "불확실", "교차확인"):
        if counts.get(v):
            lines.append(f"  · {v}: {counts[v]}건")
    for it in items[:4]:
        lines.append(
            f"  · 글#{it.get('post_id')} 댓글#{it.get('comment_id')} "
            f"[{it.get('verdict')}] {it.get('excerpt', '')[:50]}…"
        )
    return sw.save_insights_section("comments", items, summary="\n".join(lines))


def summary_text() -> str:
    ins = sw.load_insights().get("comments") or {}
    return (ins.get("summary") or "").strip() or "댓글 검증 기록 없음"
