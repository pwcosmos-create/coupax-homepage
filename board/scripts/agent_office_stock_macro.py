"""
금리·달러(환율) — 시장 영향 조사 (웹 + 시세 스냅샷 교차).

  python scripts/agent_office_stock_macro.py
"""
from __future__ import annotations

import html as html_module
import os
import re
import time

import agent_office_stock_watch as sw

_BOK_HOSTS = ("bok.or.kr", "fed.gov", "federalreserve.gov", "treasury.gov")
_FX_HOSTS = ("bok.or.kr", "keb.co.kr", "hana.bank", "reuters.com", "bloomberg.com")


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


def _fetch_usdkrw() -> dict | None:
    for sym in ("KRW=X", "USDKRW=X", "USD/KRW"):
        q = sw._fetch_quote(sym)
        if q and q.get("price"):
            row = dict(q)
            row["pair"] = "USD/KRW"
            return row
    return None


def _collect_macro_web(queries: list[str], *, max_items: int = 10) -> list[dict]:
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
            topic = "rate"
            if any(k in query.lower() for k in ("환율", "달러", "dxy", "원달러", "usd")):
                topic = "dollar"
            if "영향" in query or "증시" in query:
                topic = "impact"
            source_type = "official"
            if topic == "rate" and not any(h in url for h in _BOK_HOSTS):
                source_type = "media"
            if topic == "dollar" and not any(
                h in url for h in _FX_HOSTS + _BOK_HOSTS
            ):
                source_type = "media"
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
    return items


def _build_impact_notes(
    snap: dict, fx: dict | None, kr_pct: float | None, us_pct: float | None
) -> list[dict]:
    """금리·달러가 증시에 미치는 영향 — 당일 스냅샷과 함께 해석 (일반론+당일 대조)."""
    notes: list[dict] = []
    fx_chg = float(fx.get("change_pct") or 0) if fx else None
    fx_price = fx.get("price") if fx else None

    notes.append(
        {
            "topic": "impact",
            "source_type": "framework",
            "title": "금리 상승(긴축)일 때 일반적 시사",
            "snippet": (
                "성장·기술주 밸류에이션 압박, 금융주·현금흐름 안정 업종 상대적 관심. "
                "채권 수익률 상승 시 주식 할인율 부담. 개별 국면·업종마다 다름."
            ),
            "url": "",
            "provider": "macro",
        }
    )
    notes.append(
        {
            "topic": "impact",
            "source_type": "framework",
            "title": "금리 인하(완화)일 때 일반적 시사",
            "snippet": (
                "유동성·위험자산 선호 회복 기대, 성장주·배당·리츠 등에 우호적 해석 가능. "
                "인플레·금리 반등 리스크는 병행 점검."
            ),
            "url": "",
            "provider": "macro",
        }
    )
    notes.append(
        {
            "topic": "impact",
            "source_type": "framework",
            "title": "달러 강세·원화 약세(USD/KRW 상승) 시사",
            "snippet": (
                "수출·달러 매출 비중 큰 업종(반도체·자동차·화학 등) 이익 환산 효과 기대 가능. "
                "외국인 수급·원자재·에너지 수입 비용 부담, 수입 inflation 압력."
            ),
            "url": "",
            "provider": "macro",
        }
    )
    notes.append(
        {
            "topic": "impact",
            "source_type": "framework",
            "title": "달러 약세·원화 강세(USD/KRW 하락) 시사",
            "snippet": (
                "수입 물가·여행·내수 소비에 우호적 해석 가능. "
                "수출 경쟁력·해외 매출 환산에는 부담. 외국인 증시 매수 여건과 함께 봄."
            ),
            "url": "",
            "provider": "macro",
        }
    )

    today_bits: list[str] = []
    if kr_pct is not None:
        today_bits.append(f"코스피 {kr_pct:+.2f}%")
    if us_pct is not None:
        today_bits.append(f"미국 지수권 {us_pct:+.2f}%")
    if fx_price is not None and fx_chg is not None:
        today_bits.append(f"USD/KRW {fx_price} ({fx_chg:+.2f}%)")

    if fx_chg is not None and abs(fx_chg) >= 0.15:
        direction = "원화 약세(달러 강세)" if fx_chg > 0 else "원화 강세(달러 약세)"
        align = []
        if kr_pct is not None:
            if fx_chg > 0 and kr_pct > 0:
                align.append("코스피 상승과 동시에 원화 약세 — 수출·외인 수급·실적 모멘텀 등 복합 요인 가능")
            elif fx_chg > 0 and kr_pct < 0:
                align.append("원화 약세에도 코스피 하락 — 글로벌 리스크·금리·업종 쏠림 등 다른 요인 우세 가능")
            elif fx_chg < 0 and kr_pct > 0:
                align.append("원화 강세에도 코스피 상승 — 내수·정책·실적 모멘텀 등이 환율 효과 상쇄 가능")
        notes.append(
            {
                "topic": "impact",
                "source_type": "today",
                "title": f"당일 환율 신호: {direction}",
                "snippet": (
                    f"{'; '.join(today_bits)}. "
                    + (" ".join(align) if align else "지수·환율 단독 해석 금지, 뉴스·금리 병행 확인.")
                )[:320],
                "url": "",
                "provider": "macro",
            }
        )

    if kr_pct is not None and us_pct is not None:
        spread = kr_pct - us_pct
        if abs(spread) >= 1.0:
            notes.append(
                {
                    "topic": "impact",
                    "source_type": "today",
                    "title": "국내·미국 지수 등락 차이",
                    "snippet": (
                        f"코스피 {kr_pct:+.2f}% vs 미국 {us_pct:+.2f}% (차이 {spread:+.2f}%p). "
                        "환율·금리·반도체·환헤지 수급 등으로 양국 디커플링 가능 — 글로벌 동조만 가정하지 말 것."
                    )[:320],
                    "url": "",
                    "provider": "macro",
                }
            )

    return notes


def run_rates_dollar_insights() -> dict:
    snap = sw.load_snapshot()
    if not snap.get("updated_at"):
        sw.sync_market_data(force=True)
        snap = sw.load_snapshot()

    kr_pct = _index_pct(snap, "kr", 0)
    us_pct = _index_pct(snap, "us", 0)
    fx = _fetch_usdkrw()

    queries = [
        "한국은행 기준금리 통화정책 2026",
        "site:bok.or.kr 기준금리",
        "연준 금리 FOMC 증시 영향",
        "site:federalreserve.gov interest rate",
        "미국 10년물 국채금리 주식",
        "원달러 환율 코스피 영향",
        "달러인덱스 DXY 증시",
        f"원/달러 환율 {fx.get('price') if fx else ''} 전망",
        "금리 인하 기대 증시 섹터",
        "고금리 장기화 주식시장 영향",
    ]
    items = _collect_macro_web(queries, max_items=10)
    if len(items) < 4:
        fallback = [
            "한국 기준금리 연준 금리 차이",
            "원달러 환율 수출주 영향",
            "금리 주식시장 영향 해설",
            "dollar won exchange rate stocks",
        ]
        items.extend(_collect_macro_web(fallback, max_items=6))

    impact_notes = _build_impact_notes(snap, fx, kr_pct, us_pct)
    items = impact_notes + items

    seen: set[str] = set()
    deduped: list[dict] = []
    for it in items:
        k = (it.get("title") or "")[:80]
        if k in seen:
            continue
        seen.add(k)
        deduped.append(it)
    items = deduped[:16]

    fx_block = {}
    if fx:
        fx_block = {
            "pair": fx.get("pair", "USD/KRW"),
            "price": fx.get("price"),
            "change_pct": fx.get("change_pct"),
            "fetched_at": fx.get("fetched_at"),
        }

    summary_lines = [f"금리·달러젬마 ({_now()})"]
    if fx_block:
        summary_lines.append(
            f"  · USD/KRW {fx_block.get('price')} ({float(fx_block.get('change_pct') or 0):+.2f}%)"
        )
    if kr_pct is not None:
        summary_lines.append(f"  · 코스피 {kr_pct:+.2f}% (금리·환율과 단독 인과 금지)")
    for it in items:
        if it.get("source_type") in ("today", "framework"):
            summary_lines.append(f"  · {it.get('title', '')[:52]}")
            if len(summary_lines) >= 8:
                break
    for it in items:
        if it.get("topic") in ("rate", "dollar") and it.get("url"):
            summary_lines.append(f"  · [{it.get('topic')}] {it.get('title', '')[:48]}")
            if len(summary_lines) >= 11:
                break

    extra = {"usdkrw": fx_block, "kospi_pct": kr_pct, "us_indices_pct": us_pct}
    block = sw.save_insights_section(
        "rates_dollar",
        items,
        summary="\n".join(summary_lines),
        extra=extra,
    )
    block["usdkrw"] = fx_block
    return block


def main() -> int:
    try:
        import board_env

        board_env.load_board_env()
    except ImportError:
        pass
    print(run_rates_dollar_insights())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
