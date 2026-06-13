"""
주식 시황 스냅샷·인사이트 → gemma_knowledge (finance Wiki) 요약 주입.

  python scripts/agent_office_stock_wiki.py build
  python scripts/agent_office_stock_wiki.py sync
"""
from __future__ import annotations

import os
from datetime import datetime

import agent_office_stock_watch as sw
import agent_office_wiki_store as wiki

WIKI_ID = "wiki_stock_pulse"
SOURCE = "stock_watch"
_AGENT_PRIMARY = "stock_radar"
_AGENT_SYNTH = "stock_chart"

_INSIGHT_KEYS = (
    ("chart", "차트·추세"),
    ("rl_predictions", "RL 예측"),
    ("rates_dollar", "금리·달러"),
    ("news", "뉴스"),
    ("risk", "리스크"),
    ("analyst_reports", "애널리스트"),
)


def _enabled() -> bool:
    return os.getenv("STOCK_WIKI_SYNC_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _fmt_quote(q: dict) -> str:
    name = (q.get("name") or q.get("symbol") or "").strip()
    price = q.get("price")
    pct = float(q.get("change_pct") or 0)
    if abs(pct) > 80:
        pct_note = f"{pct:+.1f}% (원시값·검증 권장)"
    else:
        pct_note = f"{pct:+.2f}%"
    if price is not None:
        try:
            p = float(price)
            if p >= 1000:
                price_s = f"{p:,.0f}"
            else:
                price_s = f"{p:.2f}"
        except (TypeError, ValueError):
            price_s = str(price)
        return f"{name} {price_s} ({pct_note})"
    return f"{name} ({pct_note})"


def _index_lines(snap: dict, region: str, label: str) -> list[str]:
    mk = (snap.get("markets") or {}).get(region) or {}
    lines: list[str] = []
    for q in mk.get("indices") or []:
        if isinstance(q, dict):
            lines.append(f"  · {label} {_fmt_quote(q)}")
    return lines[:6]


def _mover_lines(snap: dict, n: int = 6) -> tuple[list[str], list[str]]:
    rows = [
        q
        for q in sw.iter_kr_quotes(snap, buckets=sw.KR_EQUITY_BUCKETS)
        if not (q.get("symbol") or "").startswith("^")
    ]
    gainers = sorted(rows, key=lambda x: float(x.get("change_pct") or 0), reverse=True)
    losers = sorted(rows, key=lambda x: float(x.get("change_pct") or 0))
    up = [_fmt_quote(q) for q in gainers[:n] if float(q.get("change_pct") or 0) > 0]
    down = [_fmt_quote(q) for q in losers[:n] if float(q.get("change_pct") or 0) < 0]
    return up, down


def _insight_block(ins: dict, key: str, label: str) -> str | None:
    block = ins.get(key) if isinstance(ins, dict) else None
    if not isinstance(block, dict):
        return None
    summary = (block.get("summary") or "").strip()
    ts = (block.get("ts") or "").strip()
    if not summary and not block.get("items"):
        return None
    head = f"[{label}]"
    if ts:
        head += f" ({ts})"
    if summary:
        return f"{head}\n{summary[:600]}"
    items = block.get("items") or []
    bits: list[str] = []
    for it in items[:4]:
        if not isinstance(it, dict):
            continue
        note = (it.get("note") or it.get("title") or it.get("name") or "").strip()
        if note:
            bits.append(note[:120])
    if bits:
        return f"{head}\n" + " · ".join(bits)
    return None


def build_stock_pulse_wiki() -> dict | None:
    """스냅샷·인사이트로 finance Wiki 카드 본문 구성."""
    snap = sw.load_snapshot()
    updated = (snap.get("updated_at") or "").strip()
    if not updated:
        return None

    ins = sw.load_insights()
    st = sw.stats()
    lines: list[str] = [
        f"주식 시황 스냅샷 기준 시각: {updated}",
        f"국내 K200 {st.get('kr_kospi200', 0)}종 · KQ150 {st.get('kr_kosdaq150', 0)}종 · "
        f"미국 종목 {st.get('us_watchlist', 0)}",
        "",
        "■ 지수",
    ]
    lines.extend(_index_lines(snap, "kr", "국내") or ["  · (지수 미수집)"])
    lines.extend(_index_lines(snap, "us", "미국"))

    alerts = snap.get("alerts") or []
    if alerts:
        lines.append("")
        lines.append("■ 변동 알림")
        for a in alerts[:8]:
            if isinstance(a, dict):
                lines.append(f"  · {_fmt_quote(a)}")

    up, down = _mover_lines(snap, n=5)
    if up:
        lines.append("")
        lines.append("■ 국내 상승 TOP")
        for row in up:
            lines.append(f"  · {row}")
    if down:
        lines.append("")
        lines.append("■ 국내 하락 TOP")
        for row in down:
            lines.append(f"  · {row}")

    insight_lines: list[str] = []
    for key, label in _INSIGHT_KEYS:
        block = _insight_block(ins, key, label)
        if block:
            insight_lines.append(block)
    if insight_lines:
        lines.append("")
        lines.append("■ 시황부 인사이트")
        lines.extend(insight_lines)

    err = (snap.get("last_error") or "").strip()
    if err:
        lines.append("")
        lines.append(f"■ 수집 참고: {err[:200]}")

    lines.append("")
    lines.append(
        "※ 투자 권유가 아닌 정보 정리입니다. 실시간 시세는 사무실 시황부·블로그 종목 시리즈를 참고하세요."
    )

    body = "\n".join(lines)[:7500]
    title = f"주식 시황 일지 {_today()}"
    summary = wiki._summary_from_result(body, max_len=220)
    tags = [
        "주식",
        "시황",
        "코스피",
        "코스닥",
        "시세",
        "RL",
        "금리",
        "블로그",
    ]
    for t in wiki.extract_tags(title, body, limit=4):
        if t not in tags:
            tags.append(t)

    return {
        "id": WIKI_ID,
        "domain": wiki.DOMAIN_FINANCE,
        "layer": "10_Wiki",
        "title": title[:120],
        "summary": summary,
        "body": wiki._redact_pii(body),
        "source": SOURCE,
        "storage_tier": "slim_runtime",
        "agent_primary": _AGENT_PRIMARY,
        "agent_synth": _AGENT_SYNTH,
        "ts": updated,
        "tags": tags[:12],
        "stock_snapshot_at": updated,
    }


def sync_to_knowledge() -> dict:
    """Wiki 카드 upsert. enabled·스냅샷 없으면 skip."""
    if not _enabled():
        return {"ok": True, "skipped": True, "reason": "STOCK_WIKI_SYNC_ENABLED=0"}
    card = build_stock_pulse_wiki()
    if not card:
        return {"ok": False, "error": "no_snapshot"}
    saved = wiki.save_stock_pulse_to_knowledge(card)
    if not saved:
        return {"ok": False, "error": "save_failed"}
    return {
        "ok": True,
        "wiki_id": saved.get("id"),
        "title": saved.get("title"),
        "ts": saved.get("ts"),
    }


def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="주식 시황 → gemma_knowledge")
    p.add_argument("cmd", choices=["build", "sync"], nargs="?", default="sync")
    args = p.parse_args()
    if args.cmd == "build":
        card = build_stock_pulse_wiki()
        if not card:
            print("no_snapshot")
            return 1
        print(card.get("title"))
        print(card.get("summary"))
        print("---")
        print(card.get("body", "")[:1200])
        return 0
    r = sync_to_knowledge()
    print(r)
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
