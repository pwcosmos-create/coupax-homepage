"""
시황일지 댓글 — 애널리스트형 일일 리포트 (500자+).

blog_stock_series.update_series_comments 에서 사용.
"""
from __future__ import annotations

import re
from typing import Any

COMMENT_PREFIX = "[시황일지]"
MIN_CHARS = 500

_SECTOR_HINTS: list[tuple[str, str]] = [
    ("에어로|방산|LIG|한화시스템|현대로템", "방산·항공우주"),
    ("삼성전|SK하이닉|하이닉스|반도체|마이크론", "반도체"),
    ("현대차|기아|모비스|자동차", "자동차·모빌리티"),
    ("KB금융|신한|하나금융|금융", "금융"),
    ("바이오|셀트리|의료|제약", "바이오·헬스케어"),
    ("네이버|카카오|플랫폼", "인터넷·플랫폼"),
    ("전기|배터리|에너지|풍력|중공업", "에너지·중공업"),
    ("화학|정유|LG화학", "화학·소재"),
]


def _sector_hint(name: str) -> str:
    for pat, label in _SECTOR_HINTS:
        if re.search(pat, name or "", re.I):
            return label
    return "대형주" if name else "종목"


def _trend_word(pct: float) -> str:
    if pct >= 5:
        return "급등"
    if pct >= 2:
        return "강세"
    if pct >= 0.5:
        return "상승"
    if pct <= -5:
        return "급락"
    if pct <= -2:
        return "약세"
    if pct <= -0.5:
        return "하락"
    return "보합"


def _fmt_price(v: Any) -> str:
    if v is None:
        return "—"
    try:
        f = float(v)
        if f >= 1000:
            return f"{f:,.0f}원"
        return f"{f:,.2f}"
    except (TypeError, ValueError):
        return str(v)


def _index_from_snap(snap: dict, region: str, idx: int = 0) -> dict:
    mk = (snap.get("markets") or {}).get(region) or {}
    indices = mk.get("indices") or []
    if len(indices) > idx and isinstance(indices[idx], dict):
        return indices[idx]
    return {}


def _rl_for_symbol(ins: dict, symbol: str) -> dict:
    for it in (ins.get("rl_predictions") or {}).get("items") or []:
        if isinstance(it, dict) and it.get("symbol") == symbol:
            return it
    return {}


def _chart_signal(ins: dict, symbol: str) -> str:
    for it in (ins.get("chart") or {}).get("items") or []:
        if isinstance(it, dict) and it.get("symbol") == symbol:
            sig = it.get("signal") or ""
            note = it.get("note") or ""
            return f"{sig} ({note})" if sig and note else (sig or note or "")
    return ""


def _pool_peers(snap: dict, pool: str, symbol: str, *, limit: int = 3) -> list[dict]:
    import agent_office_stock_watch as sw

    rows: list[dict] = []
    for q in sw.iter_kr_quotes(snap):
        if (q.get("pool") or "") != pool:
            continue
        if (q.get("symbol") or "") == symbol:
            continue
        rows.append(q)
    rows.sort(key=lambda x: abs(float(x.get("change_pct") or 0)), reverse=True)
    return rows[:limit]


def _macro_lines(ins: dict, snap: dict) -> list[str]:
    lines: list[str] = []
    kospi = _index_from_snap(snap, "kr", 0)
    kosdaq = _index_from_snap(snap, "kr", 1)
    if kospi.get("price") is not None:
        lines.append(
            f"코스피 {kospi.get('price')} ({float(kospi.get('change_pct') or 0):+.2f}%)"
        )
    if kosdaq.get("price") is not None:
        lines.append(
            f"코스닥 {kosdaq.get('price')} ({float(kosdaq.get('change_pct') or 0):+.2f}%)"
        )
    usdkrw = (ins.get("rates_dollar") or {}).get("usdkrw") or {}
    if usdkrw.get("price"):
        lines.append(
            f"USD/KRW {float(usdkrw.get('price')):,.2f} "
            f"({float(usdkrw.get('change_pct') or 0):+.2f}%)"
        )
    for key in ("macro", "rates_dollar", "commodities", "bonds"):
        block = ins.get(key) if key != "macro" else ins.get("rates_dollar")
        if not isinstance(block, dict):
            continue
        for it in (block.get("items") or [])[:2]:
            if not isinstance(it, dict):
                continue
            title = (it.get("title") or "").strip()
            snippet = (it.get("snippet") or "").strip()
            if snippet:
                lines.append(snippet[:100] if not title else f"{title}: {snippet[:80]}")
    return lines[:5]


def _relative_vs_index(pct: float, snap: dict) -> str:
    kospi_pct = float(_index_from_snap(snap, "kr", 0).get("change_pct") or 0)
    diff = pct - kospi_pct
    if diff >= 2:
        return f"코스피 대비 상대강도 우위 (+{diff:.2f}%p)"
    if diff <= -2:
        return f"코스피 대비 상대약세 ({diff:.2f}%p)"
    return f"코스피 대비 등락 차이 {diff:+.2f}%p (동조·괴리 혼재 가능)"


def build_analyst_comment(
    entry: dict,
    q: dict,
    snap: dict,
    ins: dict,
    today: str,
    *,
    min_chars: int = MIN_CHARS,
    dossier: dict | None = None,
) -> str:
    sym = entry.get("symbol") or ""
    name = entry.get("name") or sym
    pool = entry.get("pool") or "kospi200"
    pool_label = "KOSPI 200" if pool == "kospi200" else "KOSDAQ 150" if pool == "kosdaq150" else pool

    price = q.get("price")
    pct = float(q.get("change_pct") or 0)
    prev_pct = entry.get("last_change_pct")
    prev_price = entry.get("last_price")
    trend = _trend_word(pct)
    sector = _sector_hint(name)

    rl = _rl_for_symbol(ins, sym)
    pred_ko = rl.get("predicted_ko") or "—"
    conf = rl.get("confidence")
    conf_s = f"{float(conf) * 100:.0f}%" if conf is not None else "—"
    rl_reason = (rl.get("reason") or "").strip()

    chart_sig = _chart_signal(ins, sym)
    peers = _pool_peers(snap, pool, sym)
    macro = _macro_lines(ins, snap)
    rel = _relative_vs_index(pct, snap)

    parts: list[str] = [
        f"{COMMENT_PREFIX} {today}",
        "",
        f"■ {name} ({sym}) — 일일 시황 리포트",
        "",
        "【1. 시세 요약】",
        f"종가(기준가) {_fmt_price(price)} · 당일 {pct:+.2f}% ({trend}). "
        f"{pool_label} 구성 종목이며 업종 프록시는 {sector} 계열로 분류합니다.",
    ]

    if prev_price is not None and price is not None:
        try:
            dp = float(price) - float(prev_price)
            parts.append(
                f"전일 시황일지 대비 가격 변화 {dp:+,.0f}원, "
                f"등락률 {float(prev_pct or 0):+.2f}% → {pct:+.2f}%로 "
                f"{'변동성이 확대' if abs(pct - float(prev_pct or 0)) >= 1 else '방향성이 이어지는'} 흐름입니다."
            )
        except (TypeError, ValueError):
            pass
    else:
        parts.append(
            "시리즈 추적 초기 구간으로 전일 대비 시계열은 다음 거래일부터 누적됩니다."
        )

    parts.extend(["", "【2. 시장 환경】"])
    if macro:
        parts.append(" · ".join(macro))
    else:
        parts.append("당일 지수·환율 스냅샷 미수집 — 사무실 시황부 동기화 후 보강됩니다.")
    parts.append(rel + ". 단일 요인으로 종목 방향을 단정하지 않습니다.")

    parts.extend(["", "【3. 종목 관찰】"])
    obs: list[str] = []
    if chart_sig:
        obs.append(f"차트 신호: {chart_sig}")
    if pred_ko != "—":
        obs.append(
            f"시황부 RL 참고(ε-greedy): 다음 구간 {pred_ko} (신뢰 {conf_s})"
            + (f" — {rl_reason}" if rl_reason else "")
        )
    if peers:
        peer_txt = ", ".join(
            f"{p.get('name') or p.get('symbol')} {float(p.get('change_pct') or 0):+.1f}%"
            for p in peers
        )
        obs.append(f"동일 유니버스({pool_label}) 당일 변동 상위: {peer_txt}")
    obs.append(
        f"{sector} 업종은 거시(금리·환율·유가)와 수급(기관·외국인)이 동시에 작용하기 쉬워 "
        f"지수 대비 괴리·수렴을 함께 확인하는 것이 유리합니다."
    )
    parts.append(" ".join(obs))

    parts.extend(["", "【4. 체크포인트】"])
    if pct <= -3:
        parts.append(
            "단기 과매도 구간 여부, 거래대금·공매도 비중, 동종 업종 대장주 동반 조정인지 "
            "구분합니다. 반등 시에는 전일 고점 회복 여부보다 거래량 동반 여부를 우선 봅니다."
        )
    elif pct >= 3:
        parts.append(
            "급등 구간에서는 추격 매수 리스크와 차익실현 매물 출회 가능성을 점검합니다. "
            "뉴스·공시 없는 수급 주도 상승은 변동성 확대 신호로 해석할 수 있습니다."
        )
    else:
        parts.append(
            "박스권·완만한 추세에서는 20·60일 이동평균 기울기, 외국인·기관 순매수 추이, "
            "다음 실적·배당·공시 일정을 캘린더에 두고 관찰합니다."
        )
    parts.append(
        "실제 매매·세무·법률 판단은 HTS 시세·DART 공시·증권사 리포트 등 1차 자료를 확인하세요."
    )

    if dossier:
        try:
            import blog_stock_series_research as sr

            council = sr.synthesize_council_lines(dossier)
        except Exception:
            council = []
        if council:
            parts.extend(["", "【5. 시황부 에이전트 취합】(사서 젬마 정리)"])
            parts.extend(council)
            agents_n = len(council)
            parts.append(
                f"총 {agents_n}개 에이전트 조사 결과를 종목 맞춤으로 교차 검토했습니다. "
                "상충되는 뉴스·리포트는 공시·실적 시즌 일정과 함께 재확인하세요."
            )

    parts.extend([
        "",
        "※ coupax 시황부 전 에이전트 조사·취합 후 자동 작성. 투자 권유·종목 추천이 아닙니다.",
    ])

    body = "\n".join(parts)
    while len(body) < min_chars:
        body += (
            "\n\n[보충] 동일 종목 시리즈는 거래일마다 본 시황일지로 가격·등락·시장 맥락을 "
            "누적 기록합니다. 과거 댓글과 비교하면 변동성 구간과 추세 전환 시점을 "
            "돌아보기 쉽습니다."
        )
    return body
