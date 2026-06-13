"""
채권·국채 수익률 동향 — 스냅샷 + 웹 조사 + 증시 영향.

  python scripts/agent_office_stock_bonds.py
"""
from __future__ import annotations

import html as html_module
import time

import agent_office_stock_watch as sw

# Yahoo: 수익률 지수(^TNX 등) + 국채 ETF(보조)
_BOND_SYMBOLS: list[tuple[str, str, str, str]] = [
    ("^TNX", "미국 10년물", "us", "yield"),
    ("^FVX", "미국 5년물", "us", "yield"),
    ("^TYX", "미국 30년물", "us", "yield"),
    ("^IRX", "미국 3개월물", "us", "yield"),
    ("KR10YT=RR", "한국 10년물", "kr", "yield"),
    ("TLT", "미국 장기채 ETF", "us", "etf"),
    ("IEF", "미국 중기채 ETF", "us", "etf"),
]

_OFFICIAL_HOSTS = (
    "treasury.gov",
    "federalreserve.gov",
    "fed.gov",
    "bok.or.kr",
    "kofia.or.kr",
    "korea.kr",
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


def _fetch_bond_quotes() -> list[dict]:
    rows: list[dict] = []
    for sym, label, region, kind in _BOND_SYMBOLS:
        q = sw._fetch_quote(sym)
        if not q or not q.get("price"):
            continue
        unit = "%" if kind == "yield" else "USD"
        rows.append(
            {
                "symbol": sym,
                "name": label,
                "region": region,
                "kind": kind,
                "unit": unit,
                "price": q.get("price"),
                "change_pct": q.get("change_pct"),
                "fetched_at": q.get("fetched_at") or _now(),
            }
        )
        time.sleep(0.12)
    return rows


def _collect_bond_web(queries: list[str], *, max_items: int = 10) -> list[dict]:
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
            topic = "treasury"
            if any(k in query for k in ("한국", "국고채", "국채", "bok")):
                topic = "kr_bond"
            elif any(k in query for k in ("회사채", "신용", "스프레드", "credit")):
                topic = "credit"
            elif "영향" in query or "증시" in query or "주식" in query:
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


def _yield_by_name(quotes: list[dict], *names: str) -> dict | None:
    for q in quotes:
        if q.get("kind") != "yield":
            continue
        if q.get("name") in names or q.get("symbol") in names:
            return q
    return None


def _build_impact_notes(
    quotes: list[dict], kr_pct: float | None, us_pct: float | None
) -> list[dict]:
    notes: list[dict] = [
        {
            "topic": "impact",
            "source_type": "framework",
            "title": "국채 수익률 상승(채권 가격 하락) 시 일반적 시사",
            "snippet": (
                "할인율 상승으로 성장주·장기 cash-flow 밸류에이션 압박. "
                "은행·보험 등 금리 민감 금융주는 국면별 상이. "
                "채권 보유 비중 높은 포트폴리오는 평가손실 가능."
            ),
            "url": "",
            "provider": "bond",
        },
        {
            "topic": "impact",
            "source_type": "framework",
            "title": "국채 수익률 하락(채권 가격 상승) 시 일반적 시사",
            "snippet": (
                "위험자산 선호·배당·리츠·성장주에 우호적 해석 가능. "
                "인플레 재점화·재정 우려 시 장기채만 약세일 수 있음."
            ),
            "url": "",
            "provider": "bond",
        },
        {
            "topic": "impact",
            "source_type": "framework",
            "title": "수익률 곡선(장단기 금리차)과 경기",
            "snippet": (
                "장기 금리 < 단기 금리(역전)는 경기 둔화 신호로 자주 인용되나 "
                "완만한 역전·정책 요인을 구분해야 함. "
                "한·미 스프레드는 환율·외국인 채권 수급과 연동."
            ),
            "url": "",
            "provider": "bond",
        },
        {
            "topic": "impact",
            "source_type": "framework",
            "title": "회사채·신용스프레드",
            "snippet": (
                "국채 대비 회사채 금리 스프레드 확대는 신용 경계 심리. "
                "투자등급·하이일드·부실채권은 증시 리스크와 동조되는 경우가 많음."
            ),
            "url": "",
            "provider": "bond",
        },
    ]

    us10 = _yield_by_name(quotes, "미국 10년물", "^TNX")
    us2_proxy = _yield_by_name(quotes, "미국 3개월물", "^IRX")
    kr10 = _yield_by_name(quotes, "한국 10년물", "KR10YT=RR")

    if us10 and us2_proxy:
        try:
            spread = float(us10.get("price") or 0) - float(us2_proxy.get("price") or 0)
            if spread < 0:
                notes.append(
                    {
                        "topic": "impact",
                        "source_type": "today",
                        "title": "미국 단기·장기 금리 역전 구간",
                        "snippet": (
                            f"10년 {us10.get('price')}% vs 3개월 {us2_proxy.get('price')}% "
                            f"(차이 {spread:+.2f}%p). 경기 둔화·정책 기대와 함께 해석, 단독 매매 신호 아님."
                        )[:320],
                        "url": "",
                        "provider": "bond",
                    }
                )
        except (TypeError, ValueError):
            pass

    if us10 and kr10:
        try:
            diff = float(kr10.get("price") or 0) - float(us10.get("price") or 0)
            notes.append(
                {
                    "topic": "impact",
                    "source_type": "today",
                    "title": "한·미 10년물 금리 차",
                    "snippet": (
                        f"한국 {kr10.get('price')}% vs 미국 {us10.get('price')}% "
                        f"(차이 {diff:+.2f}%p). 환율·외국인 채권·주식 수급과 함께 확인."
                    )[:320],
                    "url": "",
                    "provider": "bond",
                }
            )
        except (TypeError, ValueError):
            pass

    if us10 and us10.get("change_pct") is not None:
        chg = float(us10.get("change_pct") or 0)
        if abs(chg) >= 0.5:
            direction = "상승" if chg > 0 else "하락"
            bits = [f"미 10년물 수익률 {direction} ({chg:+.2f}%p 수준 변동)"]
            if kr_pct is not None:
                bits.append(f"코스피 {kr_pct:+.2f}%")
            hint = ""
            if chg > 0 and kr_pct is not None and kr_pct < 0:
                hint = "금리 상승·주식 약세 — 디스카운트율·리스크오프 동조 가능"
            elif chg < 0 and kr_pct is not None and kr_pct > 0:
                hint = "금리 하락·주식 강세 — 유동성·밸류에이션 완화 기대 가능"
            else:
                hint = "금리·주식 방향만으로 섹터 판단 금지"
            notes.append(
                {
                    "topic": "impact",
                    "source_type": "today",
                    "title": f"당일 미국 10년물 수익률 {direction}",
                    "snippet": f"{'; '.join(bits)}. {hint}"[:320],
                    "url": "",
                    "provider": "bond",
                }
            )

    if kr_pct is not None and us_pct is not None and us10:
        notes.append(
            {
                "topic": "impact",
                "source_type": "today",
                "title": "채권·주식 동시 체크",
                "snippet": (
                    f"미 10년 {us10.get('price')}% · 코스피 {kr_pct:+.2f}% · "
                    f"미국 지수 {us_pct:+.2f}%. "
                    "금리는 주식 할인율·섹터 로테이션·환율과 동시에 작용."
                )[:320],
                "url": "",
                "provider": "bond",
            }
        )

    return notes


def run_bonds_insights() -> dict:
    snap = sw.load_snapshot()
    if not snap.get("updated_at"):
        sw.sync_market_data(force=True)
        snap = sw.load_snapshot()

    kr_pct = _index_pct(snap, "kr", 0)
    us_pct = _index_pct(snap, "us", 0)
    quotes = _fetch_bond_quotes()

    queries = [
        "미국 10년물 국채금리 동향 2026",
        "한국 국고채 10년물 수익률",
        "site:bok.or.kr 국고채",
        "site:treasury.gov yield",
        "채권금리 상승 주식시장 영향",
        "수익률 곡선 역전 경기",
        "회사채 신용스프레드 증시",
        "FOMC 국채 시장",
        "국채 ETF TLT 동향",
        "한미 금리차 환율",
    ]
    items = _collect_bond_web(queries, max_items=10)
    if len(items) < 4:
        fallback = [
            "bond yield stock market impact",
            "treasury yield curve inversion",
            "korea government bond yield",
        ]
        items.extend(_collect_bond_web(fallback, max_items=6))

    impact_notes = _build_impact_notes(quotes, kr_pct, us_pct)
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

    summary_lines = [f"채권젬마 ({_now()})"]
    for q in quotes:
        if q.get("kind") == "yield":
            summary_lines.append(
                f"  · {q.get('name')}: {q.get('price')}{q.get('unit', '%')} "
                f"({float(q.get('change_pct') or 0):+.2f}%)"
            )
            if len([x for x in summary_lines if x.startswith("  ·")]) >= 6:
                break
    if kr_pct is not None:
        summary_lines.append(f"  · 코스피 {kr_pct:+.2f}% (금리·채권·주식 단독 인과 금지)")
    for it in items:
        if it.get("source_type") in ("today", "framework"):
            summary_lines.append(f"  · {it.get('title', '')[:52]}")
            if len(summary_lines) >= 10:
                break
    for it in items:
        if it.get("url") and it.get("topic") in ("treasury", "kr_bond", "credit"):
            summary_lines.append(f"  · [{it.get('topic')}] {it.get('title', '')[:48]}")
            if len(summary_lines) >= 13:
                break

    extra = {"quotes": quotes, "kospi_pct": kr_pct, "us_indices_pct": us_pct}
    block = sw.save_insights_section(
        "bonds",
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
    print(run_bonds_insights())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
