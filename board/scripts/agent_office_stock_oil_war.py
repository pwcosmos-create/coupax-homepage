"""
원유·전쟁(지정학) — 유가 스냅샷 + 분쟁·공급 이슈 + 증시 영향.

  python scripts/agent_office_stock_oil_war.py
"""
from __future__ import annotations

import html as html_module
import time

import agent_office_stock_watch as sw

_OIL_SYMBOLS: list[tuple[str, str]] = [
    ("CL=F", "WTI 원유"),
    ("BZ=F", "브렌트유"),
]

_WAR_HOSTS = (
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "un.org",
    "state.gov",
    "mod.go.kr",
    "yna.co.kr",
    "news1.kr",
)
_OIL_HOSTS = _WAR_HOSTS + ("eia.gov", "iea.org", "opec.org", "oilprice.com")


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


def _fetch_oil_quotes() -> list[dict]:
    rows: list[dict] = []
    for sym, label in _OIL_SYMBOLS:
        q = sw._fetch_quote(sym)
        if not q or not q.get("price"):
            continue
        rows.append(
            {
                "symbol": sym,
                "name": label,
                "price": q.get("price"),
                "change_pct": q.get("change_pct"),
                "fetched_at": q.get("fetched_at") or _now(),
            }
        )
        time.sleep(0.12)
    return rows


def _collect_web(queries: list[str], *, max_items: int = 12) -> list[dict]:
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
            qlow = query.lower()
            topic = "war"
            if any(k in qlow for k in ("유가", "원유", "wti", "브렌트", "opec", "공급")):
                topic = "oil"
            elif any(k in qlow for k in ("증시", "코스피", "영향", "stocks")):
                topic = "impact"
            elif any(k in qlow for k in ("중동", "우크라", "지정학", "geopolit")):
                topic = "geopolitics"
            hosts = _OIL_HOSTS if topic == "oil" else _WAR_HOSTS
            source_type = "official" if any(h in url for h in hosts) else "media"
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
    oil_quotes: list[dict], kr_pct: float | None, us_pct: float | None
) -> list[dict]:
    notes: list[dict] = [
        {
            "topic": "impact",
            "source_type": "framework",
            "title": "전쟁·지정학 리스크 → 유가",
            "snippet": (
                "중동·호르무즈·러시아·우크라 등 공급 차질·제재 뉴스는 단기 유가 급등 요인. "
                "휴전·협상 기대는 유가 완화. 실제 재고·OPEC+ 증산과 함께 확인."
            ),
            "url": "",
            "provider": "oil_war",
        },
        {
            "topic": "impact",
            "source_type": "framework",
            "title": "유가 급등 시 국내 증시 업종 시사",
            "snippet": (
                "정유·에너지·해양플랜트 등 수혜 기대 vs 항공·화학·제조(에너지비) 부담. "
                "방산·안전자산(금)은 지정학과 함께 거래되는 경우 많음."
            ),
            "url": "",
            "provider": "oil_war",
        },
        {
            "topic": "impact",
            "source_type": "framework",
            "title": "전쟁 뉴스만으로 매매 금지",
            "snippet": (
                "헤드라인·SNS와 실제 유가·재고·환율·금리 방향이 어긋날 수 있음. "
                "당일 WTI·브렌트·코스피·VIX(변동성)를 함께 볼 것."
            ),
            "url": "",
            "provider": "oil_war",
        },
    ]

    if not oil_quotes:
        return notes

    top = max(oil_quotes, key=lambda x: abs(float(x.get("change_pct") or 0)))
    chg = float(top.get("change_pct") or 0)
    if abs(chg) >= 0.5:
        direction = "급등" if chg > 0 else "급락"
        bits = [f"{top.get('name')} {top.get('price')} ({chg:+.2f}%)"]
        if kr_pct is not None:
            bits.append(f"코스피 {kr_pct:+.2f}%")
        if us_pct is not None:
            bits.append(f"미국 지수 {us_pct:+.2f}%")
        hint = ""
        if chg > 1.0:
            hint = (
                "유가 급등 — 지정학·공급 우려 가능. 정유·에너지 vs 수입 inflation·금리 경로 병행 점검."
            )
        elif chg < -1.0:
            hint = "유가 급락 — 수요 둔화·달러 강세·협상 기대 등 복합. 성장주·항공에 우호적일 수 있으나 단독 판단 금지."
        else:
            hint = "유가 변동과 지수 방향을 업종별로 분해해 볼 것."
        notes.append(
            {
                "topic": "oil",
                "source_type": "today",
                "title": f"당일 원유 {direction} 신호",
                "snippet": f"{'; '.join(bits)}. {hint}"[:320],
                "url": "",
                "provider": "oil_war",
            }
        )

    wti = next((q for q in oil_quotes if "WTI" in (q.get("name") or "")), None)
    brent = next((q for q in oil_quotes if "브렌트" in (q.get("name") or "")), None)
    if wti and brent:
        try:
            spread = float(wti.get("price") or 0) - float(brent.get("price") or 0)
            notes.append(
                {
                    "topic": "oil",
                    "source_type": "today",
                    "title": "WTI·브렌트 스프레드",
                    "snippet": (
                        f"WTI {wti.get('price')} / 브렌트 {brent.get('price')} "
                        f"(차이 {spread:+.2f}). 지역별 공급·운송비·지정학 프리미엄 참고."
                    )[:300],
                    "url": "",
                    "provider": "oil_war",
                }
            )
        except (TypeError, ValueError):
            pass

    return notes


def run_oil_war_insights() -> dict:
    snap = sw.load_snapshot()
    if not snap.get("updated_at"):
        sw.sync_market_data(force=True)
        snap = sw.load_snapshot()

    kr_pct = _index_pct(snap, "kr", 0)
    us_pct = _index_pct(snap, "us", 0)
    oil_quotes = _fetch_oil_quotes()

    queries = [
        "국제유가 WTI 브렌트 전망 2026",
        "중동 분쟁 유가 영향",
        "우크라이나 러시아 전쟁 유가",
        "OPEC 감산 원유 공급",
        "지정학 리스크 증시",
        "전쟁 뉴스 코스피 영향",
        "호르무즈 해협 유조선",
        "이스라엘 이란 유가",
        "site:reuters.com oil war",
        "site:eia.gov petroleum supply",
        "원유 수입 한국 정유주",
        "유가 급등 방산주",
    ]
    items = _collect_web(queries, max_items=12)
    if len(items) < 4:
        fallback = [
            "crude oil geopolitical risk stocks",
            "middle east conflict oil price",
            "war news stock market impact",
        ]
        items.extend(_collect_web(fallback, max_items=6))

    impact_notes = _build_impact_notes(oil_quotes, kr_pct, us_pct)
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

    summary_lines = [f"원유·전쟁젬마 ({_now()})"]
    for q in oil_quotes:
        summary_lines.append(
            f"  · {q.get('name')}: {q.get('price')} ({float(q.get('change_pct') or 0):+.2f}%)"
        )
    if kr_pct is not None:
        summary_lines.append(f"  · 코스피 {kr_pct:+.2f}% (지정학·유가 단독 인과 금지)")
    for it in items:
        if it.get("source_type") in ("today", "framework"):
            summary_lines.append(f"  · {it.get('title', '')[:52]}")
            if len(summary_lines) >= 9:
                break
    for it in items:
        if it.get("url") and it.get("topic") in ("war", "geopolitics", "oil"):
            summary_lines.append(f"  · [{it.get('topic')}] {it.get('title', '')[:48]}")
            if len(summary_lines) >= 13:
                break

    extra = {"oil_quotes": oil_quotes, "kospi_pct": kr_pct, "us_indices_pct": us_pct}
    block = sw.save_insights_section(
        "oil_war",
        items,
        summary="\n".join(summary_lines),
        extra=extra,
    )
    block["oil_quotes"] = oil_quotes
    return block


def main() -> int:
    try:
        import board_env

        board_env.load_board_env()
    except ImportError:
        pass
    print(run_oil_war_insights())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
