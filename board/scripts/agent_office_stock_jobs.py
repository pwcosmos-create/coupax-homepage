"""주식 시황부 — 차트·제무·뉴스·리스크·지역 브리핑 job."""
from __future__ import annotations

import os
from datetime import datetime

import agent_office_stock_watch as sw


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _all_quotes(snap: dict) -> list[dict]:
    out: list[dict] = []
    mk = snap.get("markets") or {}
    for region in ("kr", "us"):
        block = mk.get(region) or {}
        buckets = ("indices", "watchlist")
        if region == "kr":
            buckets = ("indices",) + sw.KR_EQUITY_BUCKETS
        for bucket in buckets:
            for q in block.get(bucket) or []:
                if isinstance(q, dict):
                    row = dict(q)
                    row["region"] = region
                    row.setdefault("bucket", bucket)
                    out.append(row)
    return out


def _history_trend(snap: dict, region: str, key_hint: str) -> str | None:
    hist = snap.get("history") or []
    pts: list[float] = []
    for row in reversed(hist):
        if not isinstance(row, dict) or row.get("region") != region:
            continue
        for k, v in row.items():
            if k in ("ts", "region"):
                continue
            if key_hint.lower() in k.lower() and isinstance(v, (int, float)):
                pts.append(float(v))
                break
        if len(pts) >= 2:
            break
    if len(pts) < 2:
        return None
    newer, older = pts[0], pts[1]
    if older == 0:
        return None
    d = (newer - older) / older * 100.0
    if d > 0.3:
        return f"최근 스냅샷 추세 +{d:.2f}%"
    if d < -0.3:
        return f"최근 스냅샷 추세 {d:.2f}%"
    return "최근 스냅샷 횡보"


def _signal_label(pct: float) -> str:
    if pct >= 3.0:
        return "강세"
    if pct >= 1.0:
        return "약한 상승"
    if pct <= -3.0:
        return "약세"
    if pct <= -1.0:
        return "약한 하락"
    return "중립"


def run_chart_insights() -> dict:
    snap = sw.load_snapshot()
    items: list[dict] = []
    for q in _all_quotes(snap):
        pct = float(q.get("change_pct") or 0)
        sym = q.get("symbol") or ""
        region = q.get("region") or ""
        hint = "KS11" if region == "kr" and sym.startswith("^") else "SPX"
        trend = _history_trend(snap, region, hint) if sym.startswith("^") else None
        note = f"당일 {_signal_label(pct)} ({pct:+.2f}%)"
        if trend:
            note += f" · {trend}"
        items.append(
            {
                "symbol": sym,
                "name": q.get("name") or sym,
                "region": region,
                "signal": _signal_label(pct),
                "change_pct": pct,
                "note": note,
            }
        )
    items.sort(key=lambda x: abs(float(x.get("change_pct") or 0)), reverse=True)
    cap = int(os.getenv("STOCK_WATCH_CHART_TOP_N", "40") or "40")
    return sw.save_insights_section("chart", items[:cap], summary=_chart_summary(items))


def _chart_summary(items: list[dict]) -> str:
    if not items:
        return "차트: 스냅샷 없음"
    hot = [i for i in items if abs(float(i.get("change_pct") or 0)) >= 2.0][:4]
    if not hot:
        hot = items[:3]
    lines = [f"차트젬마 ({_now()})"]
    for i in hot:
        lines.append(
            f"  · {i.get('name')}: {i.get('signal')} ({float(i.get('change_pct') or 0):+.2f}%)"
        )
    return "\n".join(lines)


def run_finance_insights() -> dict:
    snap = sw.load_snapshot()
    picks = sw.top_kr_equity_quotes(snap, 3)
    if not picks:
        return sw.save_insights_section(
            "finance", [], summary=f"제무젬마 ({_now()}): 국내 종목 스냅샷 없음"
        )

    try:
        import agent_office_web_search as ws
    except ImportError:
        return sw.save_insights_section(
            "finance", [], summary="제무젬마: web_search 모듈 없음"
        )

    if not ws.web_search_enabled():
        return sw.save_insights_section(
            "finance", [], summary="제무젬마: 웹 검색 비활성"
        )

    items: list[dict] = []
    for q in picks:
        name = (q.get("name") or q.get("symbol") or "").strip()
        region = "한국" if q.get("region") == "kr" else "미국"
        query = f"{name} {region} 주식 실적 PER ROE 재무 2026"
        for hit in ws.search_web(query, limit=3):
            items.append(
                {
                    "symbol": q.get("symbol"),
                    "name": name,
                    "title": hit.title[:120],
                    "snippet": hit.snippet[:280],
                    "url": hit.url,
                    "provider": hit.provider,
                }
            )
            if len(items) >= 8:
                break
        if len(items) >= 8:
            break

    summary = f"제무젬마 ({_now()})\n"
    if items:
        summary += "\n".join(
            f"  · {it.get('name')}: {it.get('title')[:50]}" for it in items[:4]
        )
    else:
        summary += "  · 재무·밸류에이션 검색 결과 없음"
    return sw.save_insights_section("finance", items, summary=summary)


def run_news_insights() -> dict:
    try:
        import agent_office_web_search as ws
    except ImportError:
        return sw.save_insights_section("news", [], summary="최신정보젬마: web_search 없음")

    if not ws.web_search_enabled():
        return sw.save_insights_section("news", [], summary="최신정보젬마: 웹 검색 비활성")

    snap = sw.load_snapshot()
    kr_idx = ((snap.get("markets") or {}).get("kr") or {}).get("indices") or []
    us_idx = ((snap.get("markets") or {}).get("us") or {}).get("indices") or []
    kr_pct = float(kr_idx[0].get("change_pct") or 0) if kr_idx else 0.0
    us_pct = float(us_idx[0].get("change_pct") or 0) if us_idx else 0.0

    queries = [
        f"코스피 코스닥 주식 시장 오늘 뉴스 {kr_pct:+.1f}%",
        f"미국 주식 S&P 나스닥 오늘 뉴스 {us_pct:+.1f}%",
        "글로벌 증시 속보 연준 금리",
    ]
    items: list[dict] = []
    seen: set[str] = set()
    for query in queries:
        for hit in ws.search_web(query, limit=4):
            key = (hit.url or hit.title or "")[:80]
            if key in seen:
                continue
            seen.add(key)
            items.append(
                {
                    "title": hit.title[:120],
                    "snippet": hit.snippet[:300],
                    "url": hit.url,
                    "provider": hit.provider,
                    "query": query[:60],
                }
            )
            if len(items) >= 10:
                break
        if len(items) >= 10:
            break

    summary = f"최신정보젬마 ({_now()})\n"
    summary += "\n".join(f"  · {it.get('title', '')[:56]}" for it in items[:5])
    if not items:
        summary += "  · 뉴스 검색 결과 없음"
    return sw.save_insights_section("news", items, summary=summary)


def run_risk_scan() -> dict:
    snap = sw.load_snapshot()
    quotes = _all_quotes(snap)
    alerts = list(snap.get("alerts") or [])
    volatile = [
        q
        for q in quotes
        if abs(float(q.get("change_pct") or 0)) >= float(
            __import__("os").getenv("STOCK_WATCH_ALERT_PCT", "2.0") or "2.0"
        )
    ]
    items = [
        {
            "symbol": q.get("symbol"),
            "name": q.get("name"),
            "change_pct": q.get("change_pct"),
            "note": "변동성 주의",
        }
        for q in volatile
    ]
    ok = len(volatile) <= 6 and len(alerts) <= 8
    summary = (
        f"리스크젬마 ({_now()}): 변동 큰 종목 {len(volatile)}건 · "
        f"알림 {len(alerts)}건"
    )
    if volatile:
        summary += "\n" + "\n".join(
            f"  · {v.get('name')}: {float(v.get('change_pct') or 0):+.2f}%"
            for v in volatile[:6]
        )
    return sw.save_insights_section(
        "risk", items, summary=summary, ok=ok, extra={"alert_count": len(alerts)}
    )


def run_kr_brief() -> str:
    snap = sw.load_snapshot()
    mk = (snap.get("markets") or {}).get("kr") or {}
    n200 = len(mk.get("kospi200") or [])
    n150 = len(mk.get("kosdaq150") or [])
    lines = [f"국내시황젬마 ({_now()}) · K200 {n200} · KQ150 {n150}"]
    for q in mk.get("indices") or []:
        lines.append(
            f"  · {q.get('name', q.get('symbol'))}: {q.get('price')} "
            f"({float(q.get('change_pct') or 0):+.2f}%)"
        )
    for q in sw.top_kr_equity_quotes(snap, 6):
        tag = q.get("bucket") or q.get("pool") or ""
        lines.append(
            f"  · [{tag}] {q.get('name', q.get('symbol'))}: {q.get('price')} "
            f"({float(q.get('change_pct') or 0):+.2f}%)"
        )
    if len(lines) == 1:
        lines.append("  · 국내 스냅샷 없음")
    return "\n".join(lines)


def run_us_brief() -> str:
    snap = sw.load_snapshot()
    mk = (snap.get("markets") or {}).get("us") or {}
    lines = [f"해외시황젬마 ({_now()})"]
    for q in (mk.get("indices") or []) + (mk.get("watchlist") or []):
        lines.append(
            f"  · {q.get('name', q.get('symbol'))}: {q.get('price')} "
            f"({float(q.get('change_pct') or 0):+.2f}%)"
        )
    if len(lines) == 1:
        lines.append("  · 미국 스냅샷 없음")
    return "\n".join(lines)


def run_blog_hints() -> str:
    try:
        import agent_office_web_search as ws
    except ImportError:
        return f"글감젬마 ({_now()}): web_search 없음"

    snap = sw.load_snapshot()
    title = f"주식 시황 {snap.get('updated_at') or _now()}"
    body = sw.summary_text()
    topics = ws.suggest_blog_topics(title, body, ["코스피", "나스닥", "ETF", "금리"])
    lines = [f"글감젬마 ({_now()})"]
    if not topics:
        lines.append("  · 글감 후보 없음")
    else:
        for i, t in enumerate(topics, 1):
            lines.append(f"  {i}. {t.topic[:70]}")
            lines.append(f"     → {t.reason[:80]}")
    sw.save_insights_section(
        "blog_hints",
        [{"topic": t.topic, "reason": t.reason, "url": t.url} for t in topics],
        summary="\n".join(lines),
    )
    return "\n".join(lines)


def run_rl_predictions() -> dict:
    import agent_office_stock_rl_predict as rl

    return rl.run_predictions()


def job_stock_chart_pulse(agent: dict) -> tuple[bool, str]:
    if not sw.load_snapshot().get("updated_at"):
        return True, f"차트젬마 ({_now()}): 시세 스냅샷 대기 중"
    r = run_chart_insights()
    return True, r.get("summary") or "차트 분석 완료"


def job_stock_rl_predict(agent: dict) -> tuple[bool, str]:
    if not sw.load_snapshot().get("updated_at"):
        return True, f"RL예측젬마 ({_now()}): 시세 스냅샷 대기 중"
    r = run_rl_predictions()
    return True, r.get("summary") or f"RL 예측 {r.get('items', 0)}종목"


def job_stock_finance_pulse(agent: dict) -> tuple[bool, str]:
    if not sw.load_snapshot().get("updated_at"):
        return True, f"제무젬마 ({_now()}): 시세 스냅샷 대기 중"
    r = run_finance_insights()
    return True, r.get("summary") or "제무 조사 완료"


def job_stock_news_pulse(agent: dict) -> tuple[bool, str]:
    r = run_news_insights()
    return True, r.get("summary") or "뉴스 수집 완료"


def job_stock_risk_scan(agent: dict) -> tuple[bool, str]:
    r = run_risk_scan()
    ok = bool(r.get("ok", True))
    return ok, r.get("summary") or "리스크 점검 완료"


def job_stock_kr_brief(agent: dict) -> tuple[bool, str]:
    return True, run_kr_brief()


def job_stock_us_brief(agent: dict) -> tuple[bool, str]:
    return True, run_us_brief()


def job_stock_blog_hints(agent: dict) -> tuple[bool, str]:
    return True, run_blog_hints()


def run_comment_verify() -> dict:
    import agent_office_stock_comments as sc

    return sc.run_comment_verify()


def run_official_all() -> dict:
    import agent_office_stock_official as off

    return off.run_all_official()


def job_stock_disclosure_pulse(agent: dict) -> tuple[bool, str]:
    import agent_office_stock_official as off

    r = off.run_disclosure_insights()
    return True, r.get("summary") or "공시 조사 완료"


def job_stock_government_pulse(agent: dict) -> tuple[bool, str]:
    import agent_office_stock_official as off

    r = off.run_government_insights()
    return True, r.get("summary") or "정부 발표 조사 완료"


def job_stock_rates_dollar_pulse(agent: dict) -> tuple[bool, str]:
    import agent_office_stock_macro as macro

    r = macro.run_rates_dollar_insights()
    return True, r.get("summary") or "금리·달러 조사 완료"


def job_stock_commodities_pulse(agent: dict) -> tuple[bool, str]:
    import agent_office_stock_commodities as comm

    r = comm.run_commodities_insights()
    return True, r.get("summary") or "원자재 동향 조사 완료"


def job_stock_bonds_pulse(agent: dict) -> tuple[bool, str]:
    import agent_office_stock_bonds as bonds

    r = bonds.run_bonds_insights()
    return True, r.get("summary") or "채권 동향 조사 완료"


def job_stock_oil_war_pulse(agent: dict) -> tuple[bool, str]:
    import agent_office_stock_oil_war as ow

    r = ow.run_oil_war_insights()
    return True, r.get("summary") or "원유·전쟁 조사 완료"


def job_stock_ceo_remarks_pulse(agent: dict) -> tuple[bool, str]:
    import agent_office_stock_ceo_remarks as ceo

    r = ceo.run_ceo_remarks_insights()
    return True, r.get("summary") or "CEO·경영진 멘트 조사 완료"


def job_stock_youtube_pulse(agent: dict) -> tuple[bool, str]:
    import agent_office_stock_youtube as yt

    r = yt.run_youtube_insights()
    return True, r.get("summary") or "유튜브 조사 완료"


def job_stock_analyst_pulse(agent: dict) -> tuple[bool, str]:
    import agent_office_stock_analyst as an

    r = an.run_analyst_insights()
    return True, r.get("summary") or "애널리스트 리포트 조사 완료"


def job_stock_press_pulse(agent: dict) -> tuple[bool, str]:
    import agent_office_stock_official as off

    r = off.run_press_insights()
    return True, r.get("summary") or "기사 조사 완료"


def job_stock_comment_verify(agent: dict) -> tuple[bool, str]:
    import agent_office_stock_comments as sc

    r = sc.run_comment_verify()
    warn = sum(
        1
        for it in r.get("items") or []
        if (it.get("verdict") or "") in ("주의", "의심", "미검증")
    )
    ok = warn <= int(os.getenv("STOCK_COMMENT_WARN_MAX", "8") or "8")
    return ok, r.get("summary") or sc.summary_text()
