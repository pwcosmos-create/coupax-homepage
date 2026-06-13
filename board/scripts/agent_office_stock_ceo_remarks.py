"""
기업 CEO·경영진 발언 — 관심종목·대형주 위주 웹 수집 + 시세 교차.

  python scripts/agent_office_stock_ceo_remarks.py
"""
from __future__ import annotations

import html as html_module
import os
import re
import time

import agent_office_stock_watch as sw

# 관심종목 없을 때 기본 검색 (회사명, 대표)
_DEFAULT_EXECUTIVES: list[tuple[str, str, str]] = [
    ("삼성전자", "이재용", "kr"),
    ("SK하이닉스", "박정호", "kr"),
    ("네이버", "최수연", "kr"),
    ("현대차", "정의선", "kr"),
    ("NVDA", "젠슨 황", "us"),
    ("Apple", "팀 쿡", "us"),
    ("Tesla", "일론 머스크", "us"),
    ("Microsoft", "사티아 나델라", "us"),
]

_PRESS_HOSTS = (
    "yna.co.kr",
    "hankyung.com",
    "mk.co.kr",
    "sedaily.com",
    "reuters.com",
    "bloomberg.com",
    "cnbc.com",
    "ft.com",
    "wsj.com",
)
_OFFICIAL_HOSTS = ("dart.fss.or.kr", "sec.gov", "ir.", "investor.")

_CEO_KEYWORDS = re.compile(
    r"(CEO|최고경영자|회장|사장|대표|chairman|chief executive|"
    r"경영진|인터뷰|발언|코멘트|전망|remarks|said|says)",
    re.I,
)


def _now() -> str:
    return sw._now()


def _top_watch(limit: int = 5) -> list[dict]:
    return sw.top_kr_equity_quotes(sw.load_snapshot(), limit)


def _guess_topic(title: str, snippet: str) -> str:
    text = f"{title} {snippet}".lower()
    if any(k in text for k in ("실적", "earnings", "가이던", "guidance", "매출")):
        return "earnings"
    if any(k in text for k in ("전망", "outlook", "forecast", "기대")):
        return "outlook"
    if any(k in text for k in ("ai", "인공지능", "반도체", "chip")):
        return "sector"
    if any(k in text for k in ("인하", "인상", "가격", "price", "비용")):
        return "pricing"
    if any(k in text for k in ("우려", "risk", "경고", "warning", "하락")):
        return "caution"
    if any(k in text for k in ("투자", "invest", "capex", "설비")):
        return "capex"
    return "remark"


def _extract_quote(snippet: str, max_len: int = 160) -> str:
    s = html_module.unescape((snippet or "").strip())
    for sep in (""", """, '"', "'", "「", "」", "‘", "’"):
        if sep in s and len(s) > 20:
            parts = re.split(r"[「」""'']", s)
            for p in parts:
                p = p.strip()
                if 12 <= len(p) <= max_len:
                    return p
    return s[:max_len] if s else ""


def _collect_ceo_web(
    queries: list[str],
    *,
    company: str = "",
    executive: str = "",
    symbol: str = "",
    region: str = "",
    change_pct: float | None = None,
    max_items: int = 10,
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
        for hit in ws.search_web(query, limit=3):
            title = html_module.unescape(hit.title or "")
            snippet = html_module.unescape(hit.snippet or "")
            combined = f"{title} {snippet}"
            if not _CEO_KEYWORDS.search(combined):
                continue
            key = (hit.url or title)[:100]
            if key in seen:
                continue
            seen.add(key)
            url = (hit.url or "").lower()
            source_type = "official" if any(h in url for h in _OFFICIAL_HOSTS) else "media"
            if any(h in url for h in _PRESS_HOSTS):
                source_type = "major_press"
            items.append(
                {
                    "company": company,
                    "executive": executive,
                    "symbol": symbol,
                    "region": region,
                    "topic": _guess_topic(title, snippet),
                    "source_type": source_type,
                    "title": title[:140],
                    "snippet": snippet[:320],
                    "quote": _extract_quote(snippet),
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


def _build_framework_notes() -> list[dict]:
    return [
        {
            "company": "",
            "executive": "",
            "topic": "impact",
            "source_type": "framework",
            "title": "CEO·경영진 멘트 해석 시 유의",
            "snippet": (
                "실적 발표·IR·인터뷰 멘트는 투자자 설득·규제 대응 목적이 섞여 있음. "
                "공시·컨센서스·당일 주가와 교차하고, 루머·SNS 인용은 원문·공식 보도로 확인."
            ),
            "quote": "",
            "url": "",
            "provider": "ceo_remarks",
        },
        {
            "company": "",
            "executive": "",
            "topic": "impact",
            "source_type": "framework",
            "title": "긍정 전망 vs 주가 괴리",
            "snippet": (
                "강한 가이던스·AI 수혜 언급에도 이미 선반영·밸류 부담이면 주가는 약할 수 있음. "
                "멘트 방향과 당일·주간 등락률을 함께 볼 것."
            ),
            "quote": "",
            "url": "",
            "provider": "ceo_remarks",
        },
    ]


def run_ceo_remarks_insights() -> dict:
    snap = sw.load_snapshot()
    if not snap.get("updated_at"):
        sw.sync_market_data(force=True)
        snap = sw.load_snapshot()

    limit = int(os.getenv("STOCK_CEO_WATCH_LIMIT", "5") or "5")
    watches = _top_watch(limit)

    items: list[dict] = []
    targets: list[tuple[str, str, str, str, float | None]] = []

    for q in watches:
        name = (q.get("name") or q.get("symbol") or "").strip()
        sym = (q.get("symbol") or "").strip()
        region = q.get("region") or "kr"
        chg = float(q.get("change_pct") or 0)
        targets.append((name, "", sym, region, chg))

    if len(targets) < 3:
        for company, exec_name, region in _DEFAULT_EXECUTIVES[:6]:
            if not any(t[0] == company for t in targets):
                targets.append((company, exec_name, "", region, None))

    for company, executive, symbol, region, chg in targets[:limit + 2]:
        region_label = "한국" if region == "kr" else "미국"
        exec_part = f"{executive} " if executive else ""
        queries = [
            f"{company} {exec_part}CEO 발언 인터뷰",
            f"{company} CEO 실적 발표 코멘트 {region_label}",
            f"{company} 경영진 전망 주가",
        ]
        if executive:
            queries.append(f"{executive} {company} 증시 발언")
        if region == "us":
            queries.append(f"{company} CEO remarks earnings stock")

        batch = _collect_ceo_web(
            queries,
            company=company,
            executive=executive,
            symbol=symbol,
            region=region,
            change_pct=chg,
            max_items=4,
        )
        items.extend(batch)

    general_queries = [
        "국내 대기업 CEO 증시 발언 2026",
        "미국 빅테크 CEO 주식 시장 코멘트",
        "실적 발표 CEO 가이던스",
        "CEO 인터뷰 금리 유가 전망",
    ]
    items.extend(_collect_ceo_web(general_queries, max_items=6))

    items = _build_framework_notes() + items

    seen: set[str] = set()
    deduped: list[dict] = []
    for it in items:
        k = (it.get("title") or "")[:80]
        if k in seen:
            continue
        seen.add(k)
        deduped.append(it)
    items = deduped[:20]

    summary_lines = [f"CEO멘트젬마 ({_now()})"]
    for it in items:
        if it.get("source_type") == "framework":
            summary_lines.append(f"  · {it.get('title', '')[:52]}")
    for it in items:
        if it.get("company") and it.get("url"):
            chg = it.get("market_change_pct")
            chg_s = f" ({float(chg):+.2f}%)" if chg is not None else ""
            summary_lines.append(
                f"  · [{it.get('company')}{chg_s}] {it.get('title', '')[:44]}"
            )
            if len(summary_lines) >= 12:
                break
    for it in items:
        if not it.get("company") and it.get("url"):
            summary_lines.append(f"  · {it.get('title', '')[:50]}")
            if len(summary_lines) >= 14:
                break

    extra = {"watch_count": len(watches), "target_count": len(targets)}
    block = sw.save_insights_section(
        "ceo_remarks",
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
    print(run_ceo_remarks_insights())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
