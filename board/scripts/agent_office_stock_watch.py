"""
국내·미국 주식 시세 스냅샷 수집 (Yahoo Finance chart API, API 키 불필요).

  python scripts/agent_office_stock_watch.py sync
  python scripts/agent_office_stock_watch.py status
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import json_store

BOARD = Path(__file__).resolve().parents[1]
DATA_DIR = BOARD / "data" / "stock_watch"
SNAPSHOT_PATH = DATA_DIR / "snapshots.json"
INSIGHTS_PATH = DATA_DIR / "insights.json"
DIVISION = "stock-watch"
KR_EQUITY_BUCKETS = ("kospi200", "kosdaq150", "watchlist")

_YAHOO_HOSTS = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d",
    "https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d",
)
_STOOQ_URL = "https://stooq.com/q/l/?s={symbol}&i=d"
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Yahoo 심볼 → Stooq (지수·미국주; 국내 개별주는 Yahoo 우선)
_STOOQ_SYMBOL: dict[str, str] = {
    "^KS11": "^kospi",
    "^GSPC": "^spx",
    "^IXIC": "^ndq",
    "^DJI": "^dji",
    "AAPL": "aapl.us",
    "MSFT": "msft.us",
    "NVDA": "nvda.us",
    "AMZN": "amzn.us",
    "GOOGL": "googl.us",
    "META": "meta.us",
}


def _enabled() -> bool:
    return os.getenv("STOCK_WATCH_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _default_snapshot() -> dict:
    return {
        "updated_at": "",
        "last_sync_ok": False,
        "last_error": "",
        "markets": {
            "kr": {
                "indices": [],
                "kospi200": [],
                "kosdaq150": [],
                "watchlist": [],
            },
            "us": {"indices": [], "watchlist": []},
        },
        "alerts": [],
        "history": [],
    }


def _symbol_list(env_key: str, default: str) -> list[str]:
    raw = (os.getenv(env_key) or default).strip()
    out: list[str] = []
    for part in re.split(r"[,;\s]+", raw):
        s = part.strip()
        if s:
            out.append(s)
    return out


def _kr_universe_enabled() -> bool:
    return os.getenv("STOCK_WATCH_KR_UNIVERSE", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def default_kr_index_symbols() -> list[str]:
    return _symbol_list("STOCK_WATCH_KR_INDEX_SYMBOLS", "^KS11,^KQ11")


def default_kr_extra_symbols() -> list[str]:
    return _symbol_list("STOCK_WATCH_KR_EXTRA_SYMBOLS", "")


def default_kr_symbols() -> list[str]:
    """지수 + (유니버스 비활성 시) 레거시 관심종목."""
    syms = list(default_kr_index_symbols())
    if not _kr_universe_enabled():
        syms.extend(
            _symbol_list(
                "STOCK_WATCH_KR_SYMBOLS",
                "005930.KS,035420.KS,000660.KS,051910.KS",
            )
        )
    syms.extend(default_kr_extra_symbols())
    return syms


def default_us_symbols() -> list[str]:
    return _symbol_list(
        "STOCK_WATCH_US_SYMBOLS",
        "^GSPC,^IXIC,^DJI,AAPL,MSFT,NVDA,AMZN,GOOGL,META",
    )


def load_snapshot() -> dict:
    try:
        data = json_store.load_json(SNAPSHOT_PATH, default=_default_snapshot())
    except json_store.JsonStoreError:
        return _default_snapshot()
    if not isinstance(data, dict):
        return _default_snapshot()
    data.setdefault("markets", {"kr": {}, "us": {}})
    data["markets"].setdefault("kr", {"indices": [], "kospi200": [], "kosdaq150": [], "watchlist": []})
    for key in ("kospi200", "kosdaq150"):
        data["markets"]["kr"].setdefault(key, [])
    data["markets"].setdefault("us", {"indices": [], "watchlist": []})
    data.setdefault("alerts", [])
    data.setdefault("history", [])
    return data


def save_snapshot(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    json_store.save_json(SNAPSHOT_PATH, data)


def _quote_row(
    symbol: str,
    name: str,
    price_f: float,
    prev_f: float,
    *,
    currency: str = "",
    market_state: str = "",
    provider: str = "",
) -> dict:
    chg = price_f - prev_f
    chg_pct = (chg / prev_f * 100.0) if prev_f else 0.0
    row = {
        "symbol": symbol,
        "name": (name or symbol)[:80],
        "price": round(price_f, 4),
        "prev_close": round(prev_f, 4),
        "change": round(chg, 4),
        "change_pct": round(chg_pct, 3),
        "currency": currency,
        "market_state": market_state,
        "fetched_at": _now(),
    }
    if provider:
        row["provider"] = provider
    return row


def _fetch_stooq(symbol: str) -> dict | None:
    stooq_sym = _STOOQ_SYMBOL.get(symbol)
    if not stooq_sym:
        return None
    url = _STOOQ_URL.format(symbol=urllib.parse.quote(stooq_sym, safe="^."))
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8", errors="replace").strip()
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    if not text or "N/D" in text.split("\n")[-1]:
        return None
    line = text.split("\n")[-1]
    parts = line.split(",")
    if len(parts) < 7:
        return None
    try:
        close = float(parts[6])
        open_p = float(parts[3])
    except (TypeError, ValueError):
        return None
    if close <= 0:
        return None
    name = parts[0].split(".")[0] if parts[0] else symbol
    currency = "KRW" if symbol.startswith("^K") or ".KS" in symbol else "USD"
    return _quote_row(
        symbol,
        name,
        close,
        open_p if open_p > 0 else close,
        currency=currency,
        market_state="STOOQ",
        provider="stooq",
    )


def _fetch_yahoo(symbol: str) -> dict | None:
    encoded = urllib.parse.quote(symbol, safe="^.")
    retries = int(os.getenv("STOCK_WATCH_YAHOO_RETRIES", "3") or "3")
    for attempt in range(retries):
        host = _YAHOO_HOSTS[attempt % len(_YAHOO_HOSTS)]
        url = host.format(symbol=encoded)
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            return None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            return None

        results = (payload.get("chart") or {}).get("result") or []
        if not results:
            return None
        meta = results[0].get("meta") or {}
        price = meta.get("regularMarketPrice")
        if price is None:
            price = meta.get("previousClose")
        if price is None:
            return None
        prev = meta.get("chartPreviousClose") or meta.get("previousClose") or price
        try:
            price_f = float(price)
            prev_f = float(prev)
        except (TypeError, ValueError):
            return None
        name = (meta.get("shortName") or meta.get("longName") or symbol).strip()
        return _quote_row(
            symbol,
            name,
            price_f,
            prev_f,
            currency=(meta.get("currency") or "").strip(),
            market_state=(meta.get("marketState") or "").strip(),
            provider="yahoo",
        )
    return None


def _fetch_quote(symbol: str) -> dict | None:
    q = _fetch_stooq(symbol)
    if q:
        return q
    return _fetch_yahoo(symbol)


def _split_market(symbols: list[str]) -> tuple[list[str], list[str]]:
    """앞 2개는 지수, 나머지는 관심종목."""
    if len(symbols) <= 2:
        return symbols, []
    return symbols[:2], symbols[2:]


def _detect_alerts(
    prev_quotes: dict[str, dict], new_quotes: list[dict], *, threshold_pct: float
) -> list[dict]:
    alerts: list[dict] = []
    for q in new_quotes:
        sym = q.get("symbol") or ""
        old = prev_quotes.get(sym) or {}
        old_pct = old.get("change_pct")
        new_pct = q.get("change_pct")
        if old_pct is None or new_pct is None:
            continue
        delta = abs(float(new_pct) - float(old_pct))
        if abs(float(new_pct)) >= threshold_pct or delta >= threshold_pct * 0.6:
            alerts.append(
                {
                    "symbol": sym,
                    "name": q.get("name"),
                    "change_pct": new_pct,
                    "note": f"등락 {new_pct:+.2f}%",
                    "ts": _now(),
                }
            )
    return alerts[:12]


def iter_kr_quotes(
    snap: dict, *, buckets: tuple[str, ...] | None = None
) -> list[dict]:
    """국내 시세 행 (bucket·region 필드 포함)."""
    mk = (snap.get("markets") or {}).get("kr") or {}
    use = buckets or ("indices",) + KR_EQUITY_BUCKETS
    out: list[dict] = []
    for bucket in use:
        for q in mk.get(bucket) or []:
            if isinstance(q, dict) and q.get("symbol"):
                row = dict(q)
                row.setdefault("region", "kr")
                row.setdefault("bucket", bucket)
                out.append(row)
    return out


def top_kr_equity_quotes(snap: dict, n: int = 5) -> list[dict]:
    rows = [
        q
        for q in iter_kr_quotes(snap, buckets=KR_EQUITY_BUCKETS)
        if not (q.get("symbol") or "").startswith("^")
    ]
    rows.sort(key=lambda x: abs(float(x.get("change_pct") or 0)), reverse=True)
    return rows[: max(1, n)]


def _fetch_quotes_batch(
    symbols: list[str],
    *,
    name_map: dict[str, str] | None = None,
    pool: str = "",
) -> tuple[list[dict], list[str]]:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if not symbols:
        return [], []
    workers = max(1, min(12, int(os.getenv("STOCK_WATCH_KR_WORKERS", "6") or "6")))
    stagger = float(os.getenv("STOCK_WATCH_FETCH_DELAY_SEC", "0.2") or "0.2")
    names = name_map or {}
    out: list[dict] = []
    errors: list[str] = []

    def _one(sym: str, idx: int) -> dict | None:
        time.sleep(stagger * (idx % workers))
        q = _fetch_quote(sym)
        if not q:
            return None
        if names.get(sym):
            q["name"] = names[sym]
        if pool:
            q["pool"] = pool
        return q

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_one, sym, i): sym for i, sym in enumerate(symbols)}
        for fut in as_completed(futs):
            sym = futs[fut]
            try:
                q = fut.result()
            except Exception:
                q = None
            if q:
                out.append(q)
            else:
                errors.append(sym)
    return out, errors


def sync_market_data(*, force: bool = False) -> dict:
    if not _enabled() and not force:
        return {"ok": False, "error": "disabled"}

    delay = float(os.getenv("STOCK_WATCH_FETCH_DELAY_SEC", "0.9") or "0.9")
    threshold = float(os.getenv("STOCK_WATCH_ALERT_PCT", "2.0") or "2.0")
    prev = load_snapshot()
    prev_quotes: dict[str, dict] = {}
    for region in ("kr", "us"):
        mk = (prev.get("markets") or {}).get(region) or {}
        buckets = ("indices", "watchlist")
        if region == "kr":
            buckets = ("indices",) + KR_EQUITY_BUCKETS
        for bucket in buckets:
            for q in mk.get(bucket) or []:
                if isinstance(q, dict) and q.get("symbol"):
                    prev_quotes[q["symbol"]] = q

    errors: list[str] = []
    all_new: list[dict] = []

    kr_k200: list[dict] = []
    kr_k150: list[dict] = []
    if _kr_universe_enabled():
        try:
            import stock_kr_universe as ku

            ku.ensure_universe_fresh()
            universe = ku.load_universe()
            names = ku.name_by_symbol(universe)
            syms200, syms150 = ku.yahoo_symbols(universe)
            kr_k200, e1 = _fetch_quotes_batch(syms200, name_map=names, pool="kospi200")
            errors.extend(e1)
            all_new.extend(kr_k200)
            kr_k150, e2 = _fetch_quotes_batch(syms150, name_map=names, pool="kosdaq150")
            errors.extend(e2)
            all_new.extend(kr_k150)
        except Exception as ex:
            errors.append(f"universe:{str(ex)[:40]}")

    kr_syms = default_kr_symbols()
    us_syms = default_us_symbols()

    def collect_indices_and_extra(symbols: list[str]) -> tuple[list[dict], list[dict]]:
        indices_syms, watch_syms = _split_market(symbols)
        indices_out: list[dict] = []
        watch_out: list[dict] = []
        for sym in indices_syms:
            q = _fetch_quote(sym)
            if q:
                q["pool"] = "indices"
                indices_out.append(q)
                all_new.append(q)
            else:
                errors.append(sym)
            time.sleep(delay)
        for sym in watch_syms:
            q = _fetch_quote(sym)
            if q:
                q["pool"] = "watchlist"
                watch_out.append(q)
                all_new.append(q)
            else:
                errors.append(sym)
            time.sleep(delay)
        return indices_out, watch_out

    kr_idx, kr_watch = collect_indices_and_extra(kr_syms)
    us_idx, us_watch = collect_indices_and_extra(us_syms)
    alerts = _detect_alerts(prev_quotes, all_new, threshold_pct=threshold)

    hist = list(prev.get("history") or [])
    if kr_idx:
        row = {"ts": _now(), "region": "kr"}
        for q in kr_idx:
            key = (q.get("symbol") or "").replace("^", "")
            row[key or "idx"] = q.get("price")
        hist.append(row)
    if us_idx:
        row = {"ts": _now(), "region": "us"}
        for q in us_idx:
            key = (q.get("symbol") or "").replace("^", "")
            row[key or "idx"] = q.get("price")
        hist.append(row)
    hist = hist[-96:]

    ok = bool(kr_idx or kr_k200 or kr_k150 or kr_watch or us_idx or us_watch)
    data = {
        "updated_at": _now(),
        "last_sync_ok": ok,
        "last_error": "; ".join(errors[:8]) if errors else "",
        "markets": {
            "kr": {
                "indices": kr_idx,
                "kospi200": kr_k200,
                "kosdaq150": kr_k150,
                "watchlist": kr_watch,
            },
            "us": {"indices": us_idx, "watchlist": us_watch},
        },
        "alerts": alerts,
        "history": hist,
    }
    save_snapshot(data)
    return {
        "ok": ok,
        "updated_at": data["updated_at"],
        "kr_count": len(kr_idx) + len(kr_k200) + len(kr_k150) + len(kr_watch),
        "kr_kospi200": len(kr_k200),
        "kr_kosdaq150": len(kr_k150),
        "us_count": len(us_idx) + len(us_watch),
        "alerts": len(alerts),
        "errors": errors[:20],
        "error_count": len(errors),
    }


def _default_insights() -> dict:
    return {
        "updated_at": "",
        "chart": {"ts": "", "items": [], "summary": ""},
        "finance": {"ts": "", "items": [], "summary": ""},
        "news": {"ts": "", "items": [], "summary": ""},
        "risk": {"ts": "", "items": [], "summary": "", "ok": True},
        "blog_hints": {"ts": "", "items": [], "summary": ""},
        "comments": {"ts": "", "items": [], "summary": ""},
        "disclosure": {"ts": "", "items": [], "summary": ""},
        "government": {"ts": "", "items": [], "summary": ""},
        "press": {"ts": "", "items": [], "summary": ""},
        "rates_dollar": {"ts": "", "items": [], "summary": "", "usdkrw": {}},
        "commodities": {"ts": "", "items": [], "summary": "", "quotes": []},
        "bonds": {"ts": "", "items": [], "summary": "", "quotes": []},
        "oil_war": {"ts": "", "items": [], "summary": "", "oil_quotes": []},
        "ceo_remarks": {"ts": "", "items": [], "summary": ""},
        "youtube": {"ts": "", "items": [], "summary": ""},
        "analyst_reports": {"ts": "", "items": [], "summary": ""},
        "rl_predictions": {
            "ts": "",
            "items": [],
            "summary": "",
            "model": "",
            "epsilon": 0.0,
            "settled_last_run": 0,
            "stats": {},
        },
    }


def load_insights() -> dict:
    try:
        data = json_store.load_json(INSIGHTS_PATH, default=_default_insights())
    except json_store.JsonStoreError:
        return _default_insights()
    if not isinstance(data, dict):
        return _default_insights()
    base = _default_insights()
    for key in base:
        if key not in data:
            data[key] = base[key]
        elif isinstance(base[key], dict) and isinstance(data[key], dict):
            for sk, sv in base[key].items():
                data[key].setdefault(sk, sv)
    return data


def save_insights_section(
    section: str,
    items: list,
    *,
    summary: str = "",
    ok: bool = True,
    extra: dict | None = None,
) -> dict:
    data = load_insights()
    block = {
        "ts": _now(),
        "items": items,
        "summary": (summary or "")[:2000],
    }
    if section == "risk":
        block["ok"] = ok
    if extra:
        block.update(extra)
    data[section] = block
    data["updated_at"] = _now()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    json_store.save_json(INSIGHTS_PATH, data)
    return block


def stats() -> dict:
    snap = load_snapshot()
    mk = snap.get("markets") or {}
    kr = mk.get("kr") or {}
    us = mk.get("us") or {}
    return {
        "updated_at": snap.get("updated_at") or "",
        "last_sync_ok": bool(snap.get("last_sync_ok")),
        "last_error": snap.get("last_error") or "",
        "kr_indices": len(kr.get("indices") or []),
        "kr_kospi200": len(kr.get("kospi200") or []),
        "kr_kosdaq150": len(kr.get("kosdaq150") or []),
        "kr_watchlist": len(kr.get("watchlist") or []),
        "us_indices": len(us.get("indices") or []),
        "us_watchlist": len(us.get("watchlist") or []),
        "alerts": len(snap.get("alerts") or []),
        "history_points": len(snap.get("history") or []),
        "enabled": _enabled(),
    }


def summary_text() -> str:
    st = stats()
    snap = load_snapshot()
    lines = [
        f"주식 시황 ({st['updated_at'] or '미수집'})",
        f"국내 지수 {st['kr_indices']} · K200 {st.get('kr_kospi200', 0)} · KQ150 {st.get('kr_kosdaq150', 0)}",
        f"미국 지수 {st['us_indices']} · 종목 {st['us_watchlist']}",
    ]
    alerts = snap.get("alerts") or []
    if alerts:
        lines.append("변동 알림: " + ", ".join(
            f"{a.get('name', a.get('symbol'))} {a.get('change_pct', 0):+.2f}%"
            for a in alerts[:5]
        ))
    for region, label in (("kr", "국내"), ("us", "미국")):
        mk = (snap.get("markets") or {}).get(region) or {}
        for q in (mk.get("indices") or [])[:2]:
            lines.append(
                f"  {label} {q.get('name', q.get('symbol'))}: "
                f"{q.get('price')} ({q.get('change_pct', 0):+.2f}%)"
            )
    if st.get("last_error"):
        lines.append(f"수집 실패 심볼: {st['last_error'][:120]}")
    return "\n".join(lines)[:1500]


def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="주식 시황 스냅샷")
    p.add_argument("cmd", choices=["sync", "status"], nargs="?", default="status")
    args = p.parse_args()
    if args.cmd == "sync":
        r = sync_market_data(force=True)
        print(r)
        print(summary_text())
        return 0 if r.get("ok") else 1
    print(stats())
    print(summary_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
