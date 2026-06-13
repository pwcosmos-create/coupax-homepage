"""
종목 애널리스트 리포트·목표가·투자의견 — 관심종목 위주 웹 조사.

  python scripts/agent_office_stock_analyst.py
"""
from __future__ import annotations

import html as html_module
import os
import re
import time

import agent_office_stock_watch as sw

_REPORT_HOSTS = (
    "wisereport.co.kr",
    "comp.wisereport",
    "fnguide.com",
    "naver.com",
    "finance.naver",
    "hankyung.com",
    "mk.co.kr",
    "sedaily.com",
    "reuters.com",
    "bloomberg.com",
    "marketscreener.com",
    "seekingalpha.com",
    "tipranks.com",
)

_ANALYST_KEYWORDS = re.compile(
    r"(애널리스트|analyst|리포트|report|목표가|target\s*price|"
    r"투자의견|투자 의견|rating|컨센서스|consensus|매수|매도|중립|"
    r"상향|하향|upgrade|downgrade|목표주가|TP\b)",
    re.I,
)

_TARGET_PRICE = re.compile(
    r"(목표가|목표주가|target\s*price|TP)\s*[:：]?\s*([0-9,]+)\s*(만?원|원|KRW|USD|\$)?",
    re.I,
)

_DEFAULT_NAMES: list[tuple[str, str]] = [
    ("삼성전자", "005930.KS"),
    ("SK하이닉스", "000660.KS"),
    ("네이버", "035420.KS"),
    ("NVDA", "NVDA"),
    ("Apple", "AAPL"),
]


def _now() -> str:
    return sw._now()


def _top_watch(limit: int = 6) -> list[dict]:
    snap = sw.load_snapshot()
    out = sw.top_kr_equity_quotes(snap, limit)
    if len(out) >= limit:
        return out
    mk = snap.get("markets") or {}
    us = mk.get("us") or {}
    extras: list[dict] = []
    for q in (us.get("watchlist") or []):
        if isinstance(q, dict) and q.get("symbol"):
            row = dict(q)
            row["region"] = "us"
            extras.append(row)
    extras.sort(key=lambda x: abs(float(x.get("change_pct") or 0)), reverse=True)
    for q in extras:
        if len(out) >= limit:
            break
        if not any(x.get("symbol") == q.get("symbol") for x in out):
            out.append(q)
    return out


def _guess_topic(title: str, snippet: str) -> str:
    text = f"{title} {snippet}"
    if any(k in text for k in ("상향", "upgrade", "매수", "buy", "목표가 상향")):
        return "upgrade"
    if any(k in text for k in ("하향", "downgrade", "매도", "sell", "목표가 하향")):
        return "downgrade"
    if any(k in text for k in ("목표가", "target price", "TP", "목표주가")):
        return "target"
    if any(k in text for k in ("컨센서스", "consensus", "실적", "earnings")):
        return "consensus"
    if any(k in text for k in ("리포트", "report", "애널리스트")):
        return "report"
    return "opinion"


def _is_report_url(url: str) -> bool:
    u = (url or "").lower()
    return any(h in u for h in _REPORT_HOSTS)


def _extract_target_price(text: str) -> str:
    m = _TARGET_PRICE.search(text or "")
    if not m:
        return ""
    num = (m.group(2) or "").replace(",", "")
    unit = (m.group(3) or "").strip()
    return f"{num}{unit}" if num else ""


def _collect_analyst_web(
    queries: list[str],
    *,
    company: str = "",
    symbol: str = "",
    region: str = "",
    change_pct: float | None = None,
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
        for hit in ws.search_web(query, limit=4):
            title = html_module.unescape(hit.title or "")
            snippet = html_module.unescape(hit.snippet or "")
            combined = f"{title} {snippet}"
            if not _ANALYST_KEYWORDS.search(combined) and not _is_report_url(
                hit.url or ""
            ):
                continue
            key = (hit.url or title)[:100]
            if key in seen:
                continue
            seen.add(key)
            url = (hit.url or "").lower()
            source_type = "aggregator"
            if any(h in url for h in ("wisereport", "fnguide", "finance.naver")):
                source_type = "data"
            elif any(h in url for h in _REPORT_HOSTS):
                source_type = "media"
            broker = ""
            for b in (
                "골드만",
                "Goldman",
                "모건",
                "Morgan",
                "JP",
                "메릴",
                "Merrill",
                "미래",
                "한국투자",
                "KB",
                "NH",
                "신한",
                "삼성증권",
                "대신",
                "키움",
            ):
                if b.lower() in combined.lower():
                    broker = b
                    break
            target_px = _extract_target_price(combined)
            items.append(
                {
                    "company": company,
                    "symbol": symbol,
                    "region": region,
                    "broker": broker,
                    "topic": _guess_topic(title, snippet),
                    "source_type": source_type,
                    "title": title[:140],
                    "snippet": snippet[:320],
                    "target_price": target_px,
                    "url": hit.url,
                    "provider": hit.provider,
                    "query": query[:70],
                    "market_change_pct": change_pct,
                }
            )
            if len(items) >= max_items:
                return items
        time.sleep(0.35)
    return items


def _framework_notes() -> list[dict]:
    return [
        {
            "company": "",
            "symbol": "",
            "topic": "impact",
            "source_type": "framework",
            "title": "애널리스트 리포트 해석 시 유의",
            "snippet": (
                "증권사 리포트는 투자 권유·홍보 성격이 있을 수 있고, "
                "목표가·의견은 이미 주가에 반영됐을 수 있습니다. "
                "공시·DART·당일 시세와 반드시 교차하세요."
            ),
            "target_price": "",
            "broker": "",
            "url": "",
            "provider": "analyst",
        },
        {
            "company": "",
            "symbol": "",
            "topic": "impact",
            "source_type": "framework",
            "title": "목표가·컨센서스",
            "snippet": (
                "여러 증권사 목표가 평균(컨센서스)과 개별 리포트 차이를 보며, "
                "단일 리포트·헤드라인만으로 매매하지 마세요."
            ),
            "target_price": "",
            "broker": "",
            "url": "",
            "provider": "analyst",
        },
    ]


def run_analyst_insights() -> dict:
    snap = sw.load_snapshot()
    if not snap.get("updated_at"):
        sw.sync_market_data(force=True)

    limit = int(os.getenv("STOCK_ANALYST_WATCH_LIMIT", "6") or "6")
    watches = _top_watch(limit)
    items: list[dict] = []

    targets: list[tuple[str, str, str, float | None]] = []
    for q in watches:
        name = (q.get("name") or q.get("symbol") or "").strip()
        sym = (q.get("symbol") or "").strip()
        region = q.get("region") or "kr"
        chg = float(q.get("change_pct") or 0)
        targets.append((name, sym, region, chg))

    for name, sym in _DEFAULT_NAMES:
        region = "kr" if ".KS" in sym or sym.startswith("00") else "us"
        if not any(t[0] == name or t[1] == sym for t in targets):
            targets.append((name, sym, region, None))

    for company, symbol, region, chg in targets[: limit + 2]:
        region_ko = "한국" if region == "kr" else "미국"
        queries = [
            f"{company} 목표가 투자의견",
            f"{company} 애널리스트 리포트",
            f"site:finance.naver.com {company} 목표가",
            f"site:comp.wisereport.co.kr {company}",
        ]
        if region == "us":
            queries.append(f"{company} analyst price target rating")
        items.extend(
            _collect_analyst_web(
                queries,
                company=company,
                symbol=symbol,
                region=region,
                change_pct=chg,
                max_items=3,
            )
        )
        time.sleep(0.5)

    general = [
        "코스피 애널리스트 리포트 추천",
        "증권사 리포트 목표가 상향",
        "미국 주식 analyst rating",
    ]
    items.extend(_collect_analyst_web(general, max_items=5))

    items = _framework_notes() + items

    seen: set[str] = set()
    deduped: list[dict] = []
    for it in items:
        k = (it.get("title") or "")[:80]
        if k in seen:
            continue
        seen.add(k)
        deduped.append(it)
    items = deduped[:22]

    summary_lines = [f"애널리스트젬마 ({_now()})"]
    linked = [it for it in items if it.get("url")]
    if not linked:
        summary_lines.append("  · 웹 검색 결과 없음 — 잠시 후 재시도 또는 TAVILY_API_KEY")
    for it in items:
        if it.get("company") and it.get("url"):
            tp = f" 목표가 {it['target_price']}" if it.get("target_price") else ""
            br = f" [{it['broker']}]" if it.get("broker") else ""
            chg = it.get("market_change_pct")
            chg_s = f" ({float(chg):+.2f}%)" if chg is not None else ""
            summary_lines.append(
                f"  · {it.get('company')}{chg_s}{br}{tp}: {it.get('title', '')[:42]}"
            )
            if len(summary_lines) >= 12:
                break

    extra = {"watch_count": len(watches), "report_count": len(items)}
    block = sw.save_insights_section(
        "analyst_reports",
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
    print(run_analyst_insights())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
