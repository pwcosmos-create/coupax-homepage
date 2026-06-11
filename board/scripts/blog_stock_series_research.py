"""
시황일지 업로드 전 — 시황부 전 에이전트 조사 + 종목 맞춤 웹 조사 + 취합.

blog_stock_series.publish / update_series_comments 에서 호출.
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import json_store

BOARD = Path(__file__).resolve().parents[1]
DOSSIER_PATH = BOARD / "data" / "blog_stock_series_dossiers.json"

_AGENT_JOBS: list[tuple[str, str]] = [
    ("시세젬마", "sync"),
    ("차트젬마", "chart"),
    ("RL예측젬마", "rl"),
    ("제무젬마", "finance"),
    ("최신정보젬마", "news"),
    ("리스크젬마", "risk"),
    ("국내시황젬마", "kr"),
    ("해외시황젬마", "us"),
    ("글감젬마", "blog_hints"),
    ("댓글검증젬마", "comment_verify"),
    ("공시젬마", "disclosure"),
    ("정부발표젬마", "government"),
    ("기사젬마", "press"),
    ("금리·달러젬마", "rates"),
    ("원자재젬마", "commodities"),
    ("채권젬마", "bonds"),
    ("원유·전쟁젬마", "oil_war"),
    ("CEO멘트젬마", "ceo"),
    ("유튜브젬마", "youtube"),
    ("애널리스트젬마", "analyst"),
]

_SYMBOL_QUERIES: list[tuple[str, str]] = [
    ("최신정보젬마", "{name} 주식 뉴스 시황 오늘"),
    ("제무젬마", "{name} 실적 PER ROE 재무 전망"),
    ("공시젬마", "{name} 공시 DART 전자공시"),
    ("애널리스트젬마", "{name} 목표가 투자의견 컨센서스"),
    ("CEO멘트젬마", "{name} CEO 경영진 인터뷰 발언"),
    ("기사젬마", "{name} 증권사 리포트 분석"),
    ("리스크젬마", "{name} 주가 변동성 리스크 이슈"),
]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _enabled() -> bool:
    return os.getenv("BLOG_STOCK_SERIES_AGENT_RESEARCH", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _dummy_agent() -> dict:
    return {"id": "stock_series_council", "name": "시황일지 취합"}


def _run_job(key: str) -> str:
    import agent_office_stock_jobs as sj
    import agent_office_stock_watch as sw

    agent = _dummy_agent()
    if key == "sync":
        r = sw.sync_market_data(force=True)
        return f"시세 동기화 · KR {r.get('kr_count', 0)} · 알림 {r.get('alerts', 0)}"
    runners: dict[str, Callable] = {
        "chart": lambda: sj.job_stock_chart_pulse(agent),
        "rl": lambda: sj.job_stock_rl_predict(agent),
        "finance": lambda: sj.job_stock_finance_pulse(agent),
        "news": lambda: sj.job_stock_news_pulse(agent),
        "risk": lambda: sj.job_stock_risk_scan(agent),
        "kr": lambda: sj.job_stock_kr_brief(agent),
        "us": lambda: sj.job_stock_us_brief(agent),
        "blog_hints": lambda: sj.job_stock_blog_hints(agent),
        "comment_verify": lambda: sj.job_stock_comment_verify(agent),
        "disclosure": lambda: sj.job_stock_disclosure_pulse(agent),
        "government": lambda: sj.job_stock_government_pulse(agent),
        "press": lambda: sj.job_stock_press_pulse(agent),
        "rates": lambda: sj.job_stock_rates_dollar_pulse(agent),
        "commodities": lambda: sj.job_stock_commodities_pulse(agent),
        "bonds": lambda: sj.job_stock_bonds_pulse(agent),
        "oil_war": lambda: sj.job_stock_oil_war_pulse(agent),
        "ceo": lambda: sj.job_stock_ceo_remarks_pulse(agent),
        "youtube": lambda: sj.job_stock_youtube_pulse(agent),
        "analyst": lambda: sj.job_stock_analyst_pulse(agent),
    }
    fn = runners.get(key)
    if not fn:
        return "—"
    ok, msg = fn()
    status = "OK" if ok else "주의"
    return f"[{status}] {(msg or '')[:400]}"


def run_all_stock_agents() -> dict[str, str]:
    """시황부 전 에이전트 1회 조사 — insights.json 갱신."""
    out: dict[str, str] = {}
    for label, key in _AGENT_JOBS:
        try:
            out[label] = _run_job(key)
        except Exception as ex:
            out[label] = f"오류: {str(ex)[:120]}"
    return out


def _search_symbol(agent: str, query: str, *, limit: int = 2) -> list[dict]:
    try:
        import agent_office_web_search as ws
    except ImportError:
        return []
    if not ws.web_search_enabled():
        return []
    items: list[dict] = []
    for hit in ws.search_web(query, limit=limit):
        items.append(
            {
                "agent": agent,
                "title": (hit.title or "")[:120],
                "snippet": (hit.snippet or "")[:280],
                "url": hit.url or "",
                "provider": hit.provider or "",
            }
        )
    return items


def research_symbol(symbol: str, name: str, *, max_agents: int = 5) -> dict[str, list[dict]]:
    """종목 맞춤 — 에이전트별 웹 조사 (상위 N개 쿼리만)."""
    panels: dict[str, list[dict]] = {}
    for agent, tpl in _SYMBOL_QUERIES[:max_agents]:
        q = tpl.format(name=name, symbol=symbol)
        hits = _search_symbol(agent, q, limit=2)
        if hits:
            panels.setdefault(agent, []).extend(hits)
    return panels


def _pick_insights_for_symbol(ins: dict, symbol: str) -> dict[str, str]:
    picks: dict[str, str] = {}

    def _items(key: str, sym_field: str = "symbol") -> list:
        block = ins.get(key) or {}
        return [it for it in (block.get("items") or []) if isinstance(it, dict)]

    for it in _items("chart"):
        if it.get("symbol") == symbol:
            picks["차트젬마"] = f"{it.get('signal')} — {it.get('note', '')}"[:200]
            break
    for it in _items("finance"):
        if it.get("symbol") == symbol:
            picks.setdefault("제무젬마", "")
            picks["제무젬마"] += f" {it.get('title', '')[:60]}"
    for it in _items("rl_predictions"):
        if it.get("symbol") == symbol:
            picks["RL예측젬마"] = (
                f"{it.get('predicted_ko')} (신뢰 {float(it.get('confidence') or 0)*100:.0f}%) "
                f"— {it.get('reason', '')}"
            )[:220]
            break
    for it in _items("analyst_reports"):
        if it.get("symbol") == symbol or (it.get("name") or "") in symbol:
            picks.setdefault("애널리스트젬마", it.get("title", "")[:100])
    for key, label in (
        ("news", "최신정보젬마"),
        ("disclosure", "공시젬마"),
        ("government", "정부발표젬마"),
        ("press", "기사젬마"),
        ("ceo_remarks", "CEO멘트젬마"),
        ("rates_dollar", "금리·달러젬마"),
        ("commodities", "원자재젬마"),
        ("bonds", "채권젬마"),
        ("oil_war", "원유·전쟁젬마"),
        ("youtube", "유튜브젬마"),
        ("risk", "리스크젬마"),
    ):
        block = ins.get(key) or {}
        summ = (block.get("summary") or "").strip()
        if summ:
            first = summ.split("\n", 1)[0][:120]
            picks[label] = first
    return {k: v.strip() for k, v in picks.items() if v and v.strip()}


def build_dossier(
    symbol: str,
    name: str,
    *,
    global_agents: dict[str, str] | None = None,
    snap: dict | None = None,
    ins: dict | None = None,
    skip_web: bool = False,
) -> dict[str, Any]:
    import agent_office_stock_watch as sw

    snap = snap or sw.load_snapshot()
    ins = ins or sw.load_insights()
    max_web = max(3, min(7, int(os.getenv("BLOG_STOCK_SERIES_WEB_AGENTS", "5") or "5")))
    symbol_panels = {} if skip_web else research_symbol(symbol, name, max_agents=max_web)
    return {
        "symbol": symbol,
        "name": name,
        "ts": _now(),
        "date": _today(),
        "global_agents": global_agents or {},
        "symbol_panels": symbol_panels,
        "insights_pick": _pick_insights_for_symbol(ins, symbol),
        "snap_updated": snap.get("updated_at") or "",
        "ins_updated": ins.get("updated_at") or "",
    }


def prepare_upload_research(symbols: list[dict]) -> dict[str, dict]:
    """
    시황일지 업로드 직전: 전 에이전트 조사 → 종목별 dossier.
    symbols: [{"symbol","name"}, ...]
    """
    if not _enabled():
        import agent_office_stock_watch as sw

        snap = sw.load_snapshot()
        ins = sw.load_insights()
        return {
            (row.get("symbol") or ""): build_dossier(
                row.get("symbol") or "",
                row.get("name") or row.get("symbol") or "",
                snap=snap,
                ins=ins,
                skip_web=True,
            )
            for row in symbols
            if row.get("symbol")
        }

    import agent_office_stock_watch as sw

    global_agents = run_all_stock_agents()
    snap = sw.load_snapshot()
    ins = sw.load_insights()

    dossiers: dict[str, dict] = {}
    for row in symbols:
        sym = (row.get("symbol") or "").strip()
        if not sym:
            continue
        nm = (row.get("name") or sym).strip()
        dossiers[sym] = build_dossier(
            sym,
            nm,
            global_agents=global_agents,
            snap=snap,
            ins=ins,
        )

    _save_dossiers_cache(dossiers)
    return dossiers


def _save_dossiers_cache(dossiers: dict[str, dict]) -> None:
    try:
        data = json_store.load_json(DOSSIER_PATH, default={"date": "", "items": {}})
        data["date"] = _today()
        data["updated_at"] = _now()
        items = data.get("items") if isinstance(data.get("items"), dict) else {}
        items.update(dossiers)
        data["items"] = items
        json_store.save_json(DOSSIER_PATH, data)
    except Exception:
        pass


def get_dossier(symbol: str) -> dict | None:
    try:
        data = json_store.load_json(DOSSIER_PATH, default={})
        if data.get("date") != _today():
            return None
        items = data.get("items") or {}
        d = items.get(symbol)
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def synthesize_council_lines(dossier: dict | None) -> list[str]:
    """사서 젬마 취합 — 에이전트별 한 줄 요약."""
    if not dossier:
        return []
    lines: list[str] = []
    seen: set[str] = set()

    def add(agent: str, text: str) -> None:
        t = re.sub(r"\s+", " ", (text or "").strip())
        if not t or agent in seen:
            return
        seen.add(agent)
        lines.append(f"· {agent}: {t[:160]}")

    for agent, text in (dossier.get("insights_pick") or {}).items():
        add(agent, text)

    for agent, hits in (dossier.get("symbol_panels") or {}).items():
        if not hits:
            continue
        h = hits[0]
        snippet = h.get("snippet") or h.get("title") or ""
        add(agent, snippet)

    for agent, text in (dossier.get("global_agents") or {}).items():
        if agent in seen:
            continue
        clean = re.sub(r"\[OK\]|\[주의\]", "", text).strip()
        if "오류:" in clean:
            continue
        first = clean.split("\n", 1)[0][:140]
        add(agent, first)

    return lines[:14]
