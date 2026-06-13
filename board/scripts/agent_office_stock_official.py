"""
공시(DART·SEC)·정부 보도자료·주요 기사 수집 — 웹 검색 + (선택) DART Open API.

  python scripts/agent_office_stock_official.py disclosure
  python scripts/agent_office_stock_official.py government
  python scripts/agent_office_stock_official.py press
  python scripts/agent_office_stock_official.py all
"""
from __future__ import annotations

import html as html_module
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

import agent_office_stock_watch as sw

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_KR_DISCLOSURE_HOSTS = (
    "dart.fss.or.kr",
    "kind.krx.co.kr",
    "fss.or.kr",
    "krx.co.kr",
    "disclosure.krx.co.kr",
)
_KR_GOV_HOSTS = (
    "fsc.go.kr",
    "bok.or.kr",
    "mosf.go.kr",
    "moef.go.kr",
    "korea.kr",
    "nts.go.kr",
    "fss.or.kr",
)
_US_OFFICIAL_HOSTS = (
    "sec.gov",
    "federalreserve.gov",
    "treasury.gov",
)
_PRESS_HOSTS = (
    "yna.co.kr",
    "news1.kr",
    "hankyung.com",
    "mk.co.kr",
    "sedaily.com",
    "hani.co.kr",
    "reuters.com",
    "bloomberg.com",
    "cnbc.com",
)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _top_watch_names(limit: int = 4) -> list[tuple[str, str]]:
    """(symbol, display_name) 변동 큰 국내 종목 (K200·KQ150 풀)."""
    rows = sw.top_kr_equity_quotes(sw.load_snapshot(), limit)
    return [(str(q.get("symbol") or ""), str(q.get("name") or q.get("symbol") or "")) for q in rows]


def _classify_url(url: str, kind: str) -> str:
    u = (url or "").lower()
    if kind == "disclosure":
        if any(h in u for h in _KR_DISCLOSURE_HOSTS + _US_OFFICIAL_HOSTS):
            return "official"
        return "media"
    if kind == "government":
        if any(h in u for h in _KR_GOV_HOSTS + _US_OFFICIAL_HOSTS):
            return "official"
        return "media"
    if kind == "press":
        if any(h in u for h in _PRESS_HOSTS):
            return "major_press"
    return "other"


def _collect_web(
    queries: list[str],
    *,
    kind: str,
    max_items: int = 12,
    per_query: int = 3,
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
        for hit in ws.search_web(query, limit=per_query):
            key = (hit.url or hit.title or "")[:100]
            if key in seen:
                continue
            seen.add(key)
            title = html_module.unescape(hit.title or "")[:140]
            snippet = html_module.unescape(hit.snippet or "")[:320]
            items.append(
                {
                    "kind": kind,
                    "source_type": _classify_url(hit.url, kind),
                    "title": title,
                    "snippet": snippet,
                    "url": hit.url,
                    "provider": hit.provider,
                    "query": query[:80],
                }
            )
            if len(items) >= max_items:
                return items
    return items


def _dart_list_recent(corp_name: str, symbol: str) -> list[dict]:
    """DART Open API — DART_API_KEY 필요."""
    key = (os.getenv("DART_API_KEY") or os.getenv("OPENDART_API_KEY") or "").strip()
    if not key:
        return []
    # 종목코드 6자리
    code = re.sub(r"[^0-9]", "", symbol.split(".")[0])[:6]
    if len(code) != 6:
        return []

    bgn = (datetime.now() - timedelta(days=14)).strftime("%Y%m%d")
    end = datetime.now().strftime("%Y%m%d")
    search_url = (
        "https://opendart.fss.or.kr/api/company.json?"
        + urllib.parse.urlencode({"crtfc_key": key, "stock_code": code})
    )
    try:
        req = urllib.request.Request(search_url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            comp = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return []

    corp_code = ""
    if comp.get("status") == "000" and comp.get("list"):
        row = comp["list"][0] if isinstance(comp["list"], list) else comp["list"]
        corp_code = (row.get("corp_code") or "").strip()

    if not corp_code:
        return []

    list_url = (
        "https://opendart.fss.or.kr/api/list.json?"
        + urllib.parse.urlencode(
            {
                "crtfc_key": key,
                "corp_code": corp_code,
                "bgn_de": bgn,
                "end_de": end,
                "page_count": "5",
                "page_no": "1",
            }
        )
    )
    try:
        req = urllib.request.Request(list_url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return []

    if data.get("status") != "000":
        return []

    out: list[dict] = []
    for row in data.get("list") or []:
        if not isinstance(row, dict):
            continue
        rcept = row.get("rcept_dt") or ""
        report = row.get("report_nm") or ""
        rcept_no = row.get("rcept_no") or ""
        if not report:
            continue
        url_view = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}" if rcept_no else ""
        out.append(
            {
                "kind": "disclosure",
                "source_type": "dart_api",
                "title": f"[DART] {corp_name} — {report}"[:140],
                "snippet": f"접수일 {rcept} · 공시번호 {rcept_no}"[:200],
                "url": url_view,
                "provider": "dart",
                "symbol": symbol,
                "name": corp_name,
            }
        )
    return out


def run_disclosure_insights() -> dict:
    picks = _top_watch_names(4)
    queries: list[str] = [
        "site:dart.fss.or.kr 전자공시 최근",
        "site:kind.krx.co.kr 공시",
        "금융감독원 전자공시 속보",
    ]
    for sym, name in picks:
        queries.append(f"site:dart.fss.or.kr {name} 공시 2026")
        if sym.endswith(".KS"):
            code = sym.replace(".KS", "")
            queries.append(f"DART {code} 공시")
        else:
            queries.append(f"site:sec.gov {name} 8-K filing 2026")

    items = _collect_web(queries, kind="disclosure", max_items=8, per_query=2)

    for sym, name in picks:
        if sym.endswith(".KS"):
            items = _dart_list_recent(name, sym) + items

    # official 우선 정렬
    items.sort(
        key=lambda x: (
            0 if x.get("source_type") in ("official", "dart_api") else 1,
            x.get("title") or "",
        )
    )
    items = items[:12]

    summary = f"공시젬마 ({_now()})\n"
    if items:
        for it in items[:5]:
            tag = it.get("source_type", "")
            summary += f"  · [{tag}] {it.get('title', '')[:55]}\n"
    else:
        summary += "  · 공시 검색 결과 없음 (DART_API_KEY 설정 시 API 보강)"
    return sw.save_insights_section("disclosure", items, summary=summary.strip())


def run_government_insights() -> dict:
    snap = sw.load_snapshot()
    kr_idx = ((snap.get("markets") or {}).get("kr") or {}).get("indices") or []
    kr_pct = float(kr_idx[0].get("change_pct") or 0) if kr_idx else 0.0

    queries = [
        "site:fsc.go.kr 보도자료 금융",
        "site:bok.or.kr 보도자료 통화정책",
        "site:mosf.go.kr 보도자료 경제",
        "site:nts.go.kr 보도자료 세제",
        f"금융위원회 정책 발표 증시 {kr_pct:+.1f}",
        "기획재정부 경제정책 브리핑",
        "site:federalreserve.gov press release monetary",
        "site:sec.gov news press release",
        "site:treasury.gov press release",
        "연준 FOMC 보도자료 2026",
    ]
    items = _collect_web(queries, kind="government", max_items=12, per_query=2)
    if len(items) < 4:
        fallback = [
            "금융위원회 보도자료 증시",
            "한국은행 통화정책 보도자료",
            "기획재정부 경제정책",
            "연준 FOMC 보도자료",
            "SEC press release market",
        ]
        items.extend(
            _collect_web(fallback, kind="government", max_items=8, per_query=2)
        )
    items.sort(key=lambda x: (0 if x.get("source_type") == "official" else 1))

    summary = f"정부발표젬마 ({_now()})\n"
    summary += "\n".join(
        f"  · [{it.get('source_type')}] {it.get('title', '')[:56]}"
        for it in items[:6]
    )
    if not items:
        summary += "  · 정부·중앙은행 보도자료 검색 없음"
    return sw.save_insights_section("government", items, summary=summary)


def run_press_insights() -> dict:
    """주요 언론·통신사 기사 (시장 해설·속보)."""
    snap = sw.load_snapshot()
    kr_idx = ((snap.get("markets") or {}).get("kr") or {}).get("indices") or []
    us_idx = ((snap.get("markets") or {}).get("us") or {}).get("indices") or []
    kr_pct = float(kr_idx[0].get("change_pct") or 0) if kr_idx else 0.0
    us_pct = float(us_idx[0].get("change_pct") or 0) if us_idx else 0.0

    queries = [
        f"site:yna.co.kr 코스피 증시 {kr_pct:+.1f}",
        f"site:hankyung.com 증시 코스피",
        f"site:mk.co.kr 주식시장",
        f"site:sedaily.com 증시",
        f"site:news1.kr 증시",
        f"site:reuters.com Korea stocks",
        f"site:cnbc.com stock market today {us_pct:+.1f}",
        "한국 증시 전망 기사 해설",
        "미국 증시 뉴욕 증시 기사 오늘",
    ]
    items = _collect_web(queries, kind="press", max_items=14, per_query=2)
    if len(items) < 4:
        fallback = [
            f"코스피 증시 기사 {kr_pct:+.1f}",
            "나스닥 증시 뉴욕 증시 기사",
            "한국 경제 신문 증시",
            "Reuters stocks Korea",
        ]
        items.extend(_collect_web(fallback, kind="press", max_items=8, per_query=2))
    seen: set[str] = set()
    deduped: list[dict] = []
    for it in items:
        k = (it.get("url") or it.get("title") or "")[:90]
        if k in seen:
            continue
        seen.add(k)
        deduped.append(it)
    items = deduped[:14]
    items.sort(key=lambda x: (0 if x.get("source_type") == "major_press" else 1))

    summary = f"기사젬마 ({_now()})\n"
    summary += "\n".join(
        f"  · {it.get('title', '')[:58]}" for it in items[:6]
    )
    if not items:
        summary += "  · 주요 기사 검색 없음"
    return sw.save_insights_section("press", items, summary=summary)


def run_all_official() -> dict:
    delay = float(os.getenv("STOCK_OFFICIAL_SECTION_DELAY_SEC", "2.0") or "2.0")
    d = run_disclosure_insights()
    time.sleep(delay)
    g = run_government_insights()
    time.sleep(delay)
    p = run_press_insights()
    time.sleep(delay)
    try:
        import agent_office_stock_macro as macro

        rd = macro.run_rates_dollar_insights()
    except Exception:
        rd = {"summary": "금리·달러 조사 스킵"}
    time.sleep(delay)
    try:
        import agent_office_stock_commodities as comm

        cm = comm.run_commodities_insights()
    except Exception:
        cm = {"summary": "원자재 조사 스킵"}
    time.sleep(delay)
    try:
        import agent_office_stock_bonds as bonds

        bd = bonds.run_bonds_insights()
    except Exception:
        bd = {"summary": "채권 조사 스킵"}
    time.sleep(delay)
    try:
        import agent_office_stock_oil_war as ow

        ow_block = ow.run_oil_war_insights()
    except Exception:
        ow_block = {"summary": "원유·전쟁 조사 스킵"}
    time.sleep(delay)
    try:
        import agent_office_stock_ceo_remarks as ceo

        cr = ceo.run_ceo_remarks_insights()
    except Exception:
        cr = {"summary": "CEO 멘트 조사 스킵"}
    time.sleep(delay)
    try:
        import agent_office_stock_youtube as yt

        yt_block = yt.run_youtube_insights()
    except Exception:
        yt_block = {"summary": "유튜브 조사 스킵"}
    time.sleep(delay)
    try:
        import agent_office_stock_analyst as an

        ar = an.run_analyst_insights()
    except Exception:
        ar = {"summary": "애널리스트 리포트 조사 스킵"}
    return {
        "disclosure": d,
        "government": g,
        "press": p,
        "rates_dollar": rd,
        "commodities": cm,
        "bonds": bd,
        "oil_war": ow_block,
        "ceo_remarks": cr,
        "youtube": yt_block,
        "analyst_reports": ar,
    }


def main() -> int:
    import sys

    try:
        import board_env

        board_env.load_board_env()
    except ImportError:
        pass

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "all").strip().lower()
    if cmd == "disclosure":
        print(run_disclosure_insights())
    elif cmd == "government":
        print(run_government_insights())
    elif cmd == "press":
        print(run_press_insights())
    elif cmd == "rates":
        import agent_office_stock_macro as macro

        print(macro.run_rates_dollar_insights())
    elif cmd == "commodities":
        import agent_office_stock_commodities as comm

        print(comm.run_commodities_insights())
    elif cmd == "bonds":
        import agent_office_stock_bonds as bonds

        print(bonds.run_bonds_insights())
    elif cmd in ("oil_war", "oil", "war"):
        import agent_office_stock_oil_war as ow

        print(ow.run_oil_war_insights())
    elif cmd in ("ceo", "ceo_remarks"):
        import agent_office_stock_ceo_remarks as ceo

        print(ceo.run_ceo_remarks_insights())
    elif cmd in ("youtube", "yt"):
        import agent_office_stock_youtube as yt

        print(yt.run_youtube_insights())
    elif cmd in ("analyst", "reports"):
        import agent_office_stock_analyst as an

        print(an.run_analyst_insights())
    else:
        print(run_all_official())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
