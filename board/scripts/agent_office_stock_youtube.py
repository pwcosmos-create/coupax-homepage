"""
유튜브 — 증시·매크로·CEO 관련 영상 조사.

  python scripts/agent_office_stock_youtube.py
"""
from __future__ import annotations

import html as html_module
import os
import time

import agent_office_stock_watch as sw

_DEFAULT_CHANNELS_HINT = (
    "삼프로", "슈카", "신사임당", "김단테", "워뇨띠", "미국주식", "코스피"
)


def _now() -> str:
    return sw._now()


def _index_pct(snap: dict, region: str, idx: int = 0) -> float | None:
    mk = (snap.get("markets") or {}).get(region) or {}
    indices = mk.get("indices") or []
    if len(indices) > idx and isinstance(indices[idx], dict):
        try:
            return float(indices[idx].get("change_pct") or 0)
        except (TypeError, ValueError):
            return None
    return None


def _top_watch(limit: int = 4) -> list[dict]:
    return sw.top_kr_equity_quotes(sw.load_snapshot(), limit)


def _channel_from_title(title: str) -> str:
    t = title or ""
    if " - YouTube" in t:
        return t.rsplit(" - YouTube", 1)[0].strip()[:60]
    if "|" in t:
        return t.split("|", 1)[0].strip()[:60]
    return ""


def _guess_topic(query: str, title: str) -> str:
    text = f"{query} {title}".lower()
    if any(k in text for k in ("ceo", "인터뷰", "실적", "earnings")):
        return "ceo"
    if any(k in text for k in ("금리", "채권", "연준", "fed", "환율")):
        return "macro"
    if any(k in text for k in ("유가", "원유", "전쟁", "지정학")):
        return "oil_war"
    if any(k in text for k in ("나스닥", "s&p", "미국", "nvda", "tesla")):
        return "us"
    if any(k in text for k in ("코스피", "코스닥", "국내", "한국")):
        return "kr"
    return "market"


def _collect_youtube(
    queries: list[str],
    *,
    company: str = "",
    max_items: int = 8,
) -> list[dict]:
    try:
        import agent_office_web_search as ws
    except ImportError:
        return []
    if not ws.web_search_enabled():
        return []

    items: list[dict] = []
    seen: set[str] = set()
    for query in queries:
        for hit in ws.search_youtube(query, limit=4):
            vid = ws.youtube_video_id(hit.url)
            if not vid or vid in seen:
                continue
            seen.add(vid)
            title = html_module.unescape(hit.title or "")[:140]
            items.append(
                {
                    "topic": _guess_topic(query, title),
                    "company": company,
                    "title": title,
                    "snippet": html_module.unescape(hit.snippet or "")[:280],
                    "url": hit.url,
                    "video_id": vid,
                    "provider": hit.provider,
                    "query": query[:70],
                    "channel": _channel_from_title(title),
                }
            )
            if len(items) >= max_items:
                return items
        time.sleep(0.4)
    return items


def _framework_notes() -> list[dict]:
    return [
        {
            "topic": "impact",
            "source_type": "framework",
            "title": "유튜브 영상 해석 시 유의",
            "snippet": (
                "개인·채널 의견이며 투자 권유가 아닐 수 있습니다. "
                "조회수·자극적 제목과 사실·공시·당일 시세를 반드시 교차하세요."
            ),
            "url": "",
            "video_id": "",
            "provider": "youtube",
        },
    ]


def run_youtube_insights() -> dict:
    snap = sw.load_snapshot()
    if not snap.get("updated_at"):
        sw.sync_market_data(force=True)
        snap = sw.load_snapshot()

    kr_pct = _index_pct(snap, "kr", 0)
    us_pct = _index_pct(snap, "us", 0)

    queries = [
        "코스피 증시 시황 분석",
        "미국 주식 나스닥 시황",
        "금리 환율 주식 영향",
        "유가 원유 전망 주식",
        "CEO 실적 발표 인터뷰",
        "반도체 주식 전망",
        f"주식 시황 {_now()[:10]}",
    ]

    watch_limit = int(os.getenv("STOCK_YOUTUBE_WATCH_LIMIT", "4") or "4")
    for q in _top_watch(watch_limit):
        name = (q.get("name") or q.get("symbol") or "").strip()
        if name:
            queries.append(f"{name} 주식 분석 전망")

    ceo_queries = [
        "삼성전자 CEO 발언",
        "SK하이닉스 CEO",
        "테슬라 머스크 주식",
    ]
    items = _collect_youtube(queries[:14], max_items=14)
    items.extend(_collect_youtube(ceo_queries, max_items=4))

    items = _framework_notes() + items

    seen: set[str] = set()
    deduped: list[dict] = []
    for it in items:
        k = it.get("video_id") or (it.get("title") or "")[:60]
        if k in seen:
            continue
        seen.add(k)
        deduped.append(it)
    items = deduped[:22]

    summary_lines = [f"유튜브젬마 ({_now()})"]
    if kr_pct is not None:
        summary_lines.append(f"  · 코스피 {kr_pct:+.2f}%")
    if us_pct is not None:
        summary_lines.append(f"  · 미국 지수 {us_pct:+.2f}%")
    for it in items:
        if it.get("video_id") and it.get("title"):
            summary_lines.append(f"  · [{it.get('topic')}] {it.get('title', '')[:48]}")
            if len(summary_lines) >= 12:
                break

    extra = {"kospi_pct": kr_pct, "us_indices_pct": us_pct, "video_count": len(items)}
    block = sw.save_insights_section(
        "youtube",
        items,
        summary="\n".join(summary_lines),
        extra=extra,
    )
    return block


def main() -> int:
    try:
        import board_env

        board_env.load_board_env()
    except ImportError:
        pass
    print(run_youtube_insights())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
