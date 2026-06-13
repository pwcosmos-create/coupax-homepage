"""
원자재 동향 — 시세 스냅샷 + 웹 조사 + 증시 영향 해석.

  python scripts/agent_office_stock_commodities.py
"""
from __future__ import annotations

import html as html_module
import os
import time

import agent_office_stock_watch as sw

# Yahoo Finance 선물·현물 심볼
_COMMODITY_SYMBOLS: list[tuple[str, str, str]] = [
    ("CL=F", "WTI 유가", "oil"),
    ("BZ=F", "브렌트유", "oil"),
    ("GC=F", "금", "gold"),
    ("SI=F", "은", "metal"),
    ("HG=F", "구리", "metal"),
    ("NG=F", "천연가스", "energy"),
    ("ZC=F", "옥수수", "agri"),
]

_OFFICIAL_HOSTS = (
    "eia.gov",
    "iea.org",
    "opec.org",
    "lme.com",
    "worldbank.org",
    "bok.or.kr",
    "reuters.com",
    "bloomberg.com",
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


def _fetch_commodity_quotes() -> list[dict]:
    rows: list[dict] = []
    for sym, label, category in _COMMODITY_SYMBOLS:
        q = sw._fetch_quote(sym)
        if not q or not q.get("price"):
            continue
        rows.append(
            {
                "symbol": sym,
                "name": label,
                "category": category,
                "price": q.get("price"),
                "change_pct": q.get("change_pct"),
                "fetched_at": q.get("fetched_at") or _now(),
            }
        )
        time.sleep(0.12)
    return rows


def _collect_commodity_web(queries: list[str], *, max_items: int = 10) -> list[dict]:
    try:
        import agent_office_web_search as ws
    except ImportError:
        return []
    if not ws.web_search_enabled():
        return []

    items: list[dict] = []
    seen: set[str] = set()
    for query in queries:
        for hit in ws.search_web(query, limit=3):
            key = (hit.url or hit.title or "")[:100]
            if key in seen:
                continue
            seen.add(key)
            url = (hit.url or "").lower()
            topic = "trend"
            if any(k in query for k in ("유가", "원유", "oil", "WTI", "브렌트")):
                topic = "oil"
            elif any(k in query for k in ("금", "gold", "은", "구리", "metal")):
                topic = "metal"
            elif any(k in query for k in ("가스", "LNG", "천연가스")):
                topic = "energy"
            elif "영향" in query or "증시" in query or "코스피" in query:
                topic = "impact"
            source_type = "official" if any(h in url for h in _OFFICIAL_HOSTS) else "media"
            items.append(
                {
                    "topic": topic,
                    "source_type": source_type,
                    "title": html_module.unescape(hit.title or "")[:140],
                    "snippet": html_module.unescape(hit.snippet or "")[:300],
                    "url": hit.url,
                    "provider": hit.provider,
                    "query": query[:70],
                }
            )
            if len(items) >= max_items:
                return items
        time.sleep(0.35)
    return items


def _build_impact_notes(
    quotes: list[dict], kr_pct: float | None
) -> list[dict]:
    notes: list[dict] = [
        {
            "topic": "impact",
            "source_type": "framework",
            "title": "유가 상승 시 일반적 시사",
            "snippet": (
                "정유·화학·해운·항공(비용 부담) 등 업종별 상반. "
                "에너지·정유주는 단기 호재, 내수·제조·물류는 마진 압박 가능. "
                "인플레·금리 경로와 함께 봄."
            ),
            "url": "",
            "provider": "commodity",
        },
        {
            "topic": "impact",
            "source_type": "framework",
            "title": "유가 하락 시 일반적 시사",
            "snippet": (
                "인플레 완화 기대·금리 민감주에 우호적 해석 가능. "
                "정유·에너지 이익은 압박, 항공·화학(원료비) 등은 비용 절감 기대."
            ),
            "url": "",
            "provider": "commodity",
        },
        {
            "topic": "impact",
            "source_type": "framework",
            "title": "금·은 등 귀금속 상승 시사",
            "snippet": (
                "안전자산·실질금리·달러와 연동. 위험회피·지정학 리스크 시 금리 하락 기대와 겹치면 "
                "성장주·금융주와의 상관은 국면마다 다름."
            ),
            "url": "",
            "provider": "commodity",
        },
        {
            "topic": "impact",
            "source_type": "framework",
            "title": "구리·산업금속과 경기 선행",
            "snippet": (
                "글로벌 제조·건설·전기차 수요 선행 지표로 자주 인용. "
                "구리 강세는 경기 회복 기대, 약세는 수요 둔화 신호로 해석되기도 함 — 단독 매매 신호 아님."
            ),
            "url": "",
            "provider": "commodity",
        },
    ]

    oil_moves = [
        q for q in quotes if q.get("category") == "oil" and q.get("change_pct") is not None
    ]
    if oil_moves:
        top = max(oil_moves, key=lambda x: abs(float(x.get("change_pct") or 0)))
        chg = float(top.get("change_pct") or 0)
        if abs(chg) >= 0.3:
            direction = "상승" if chg > 0 else "하락"
            bits = [f"{top.get('name')} {chg:+.2f}%"]
            if kr_pct is not None:
                bits.append(f"코스피 {kr_pct:+.2f}%")
                if chg > 0.5 and kr_pct > 0:
                    hint = "유가 급등에도 지수 상승 — 업종별(정유·화학·2차전지) 쏠림·환율·실적이 유가 단독보다 클 수 있음"
                elif chg > 0.5 and kr_pct < 0:
                    hint = "유가 상승과 지수 약세 — 인플레·금리·수입비용 우려가 동시 작용 가능"
                elif chg < -0.5 and kr_pct > 0:
                    hint = "유가 하락·지수 상승 — 비용 절감·금리 민감주 우호 국면 가능"
                else:
                    hint = "유가·지수 방향만으로 섹터 판단 금지"
            else:
                hint = "코스피 스냅샷과 병행 확인"
            notes.append(
                {
                    "topic": "impact",
                    "source_type": "today",
                    "title": f"당일 에너지 신호: {top.get('name')} {direction}",
                    "snippet": f"{'; '.join(bits)}. {hint}"[:320],
                    "url": "",
                    "provider": "commodity",
                }
            )

    metal_moves = [
        q
        for q in quotes
        if q.get("category") in ("gold", "metal") and abs(float(q.get("change_pct") or 0)) >= 0.4
    ]
    if metal_moves:
        m = metal_moves[0]
        notes.append(
            {
                "topic": "impact",
                "source_type": "today",
                "title": f"당일 {m.get('name')} 변동 {float(m.get('change_pct') or 0):+.2f}%",
                "snippet": (
                    "귀금속·산업금속은 달러·금리·중국 수요와 연동. "
                    "국내 증시는 반도체·철강·2차전지·광업 관련주에 제한적 전이."
                )[:300],
                "url": "",
                "provider": "commodity",
            }
        )

    return notes


def run_commodities_insights() -> dict:
    snap = sw.load_snapshot()
    if not snap.get("updated_at"):
        sw.sync_market_data(force=True)
        snap = sw.load_snapshot()

    kr_pct = _index_pct(snap, "kr", 0)
    quotes = _fetch_commodity_quotes()

    queries = [
        "국제유가 WTI 브렌트 동향 2026",
        "원자재 가격 전망 증시 영향",
        "유가 상승 코스피 섹터",
        "금값 은값 동향 안전자산",
        "구리 가격 경기 선행지표",
        "천연가스 LNG 가격 동향",
        "곡물 원자재 가격 인플레",
        "OPEC 감산 유가",
        "site:eia.gov petroleum",
        "한국 수입 원자재 물가",
    ]
    items = _collect_commodity_web(queries, max_items=10)
    if len(items) < 4:
        fallback = [
            "crude oil price stocks impact",
            "commodity prices inflation stocks",
            "copper gold market outlook",
        ]
        items.extend(_collect_commodity_web(fallback, max_items=6))

    impact_notes = _build_impact_notes(quotes, kr_pct)
    items = impact_notes + items

    seen: set[str] = set()
    deduped: list[dict] = []
    for it in items:
        k = (it.get("title") or "")[:80]
        if k in seen:
            continue
        seen.add(k)
        deduped.append(it)
    items = deduped[:18]

    summary_lines = [f"원자재젬마 ({_now()})"]
    for q in quotes[:6]:
        summary_lines.append(
            f"  · {q.get('name')}: {q.get('price')} ({float(q.get('change_pct') or 0):+.2f}%)"
        )
    if kr_pct is not None:
        summary_lines.append(f"  · 코스피 {kr_pct:+.2f}% (원자재·지수 단독 인과 금지)")
    for it in items:
        if it.get("source_type") in ("today", "framework"):
            summary_lines.append(f"  · {it.get('title', '')[:52]}")
            if len(summary_lines) >= 10:
                break
    for it in items:
        if it.get("url") and it.get("topic") in ("oil", "trend", "metal"):
            summary_lines.append(f"  · [{it.get('topic')}] {it.get('title', '')[:48]}")
            if len(summary_lines) >= 13:
                break

    extra = {"quotes": quotes, "kospi_pct": kr_pct}
    block = sw.save_insights_section(
        "commodities",
        items,
        summary="\n".join(summary_lines),
        extra=extra,
    )
    block["quotes"] = quotes
    return block


def main() -> int:
    try:
        import board_env

        board_env.load_board_env()
    except ImportError:
        pass
    print(run_commodities_insights())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
