"""
코스피200·코스닥150 유니버스 — 네이버 금융 시가총액 순 상위 종목 (지수 편입과 소폭 차이 가능).

  python scripts/stock_kr_universe.py refresh
  python scripts/stock_kr_universe.py status
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import json_store  # noqa: E402

UNIVERSE_PATH = BOARD / "data" / "stock_watch" / "kr_index_universe.json"
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_ROW_RE = re.compile(
    r'<a href="/item/main\.naver\?code=(\d{6})"[^>]*class="tltle">([^<]+)</a>'
)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _default_universe() -> dict:
    return {
        "updated_at": "",
        "source": "naver_market_sum",
        "note": "KOSPI 시총 상위 200·KOSDAQ 시총 상위 150 (네이버 금융, 지수 공식 편입과 다를 수 있음)",
        "kospi200": [],
        "kosdaq150": [],
    }


def load_universe() -> dict:
    try:
        data = json_store.load_json(UNIVERSE_PATH, default=_default_universe())
    except json_store.JsonStoreError:
        return _default_universe()
    if not isinstance(data, dict):
        return _default_universe()
    data.setdefault("kospi200", [])
    data.setdefault("kosdaq150", [])
    return data


def save_universe(data: dict) -> None:
    data["updated_at"] = _now()
    UNIVERSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    json_store.save_json(UNIVERSE_PATH, data)


def _universe_enabled() -> bool:
    return os.getenv("STOCK_WATCH_KR_UNIVERSE", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _kospi_limit() -> int:
    return max(1, min(250, int(os.getenv("STOCK_WATCH_KOSPI200_LIMIT", "200") or "200")))


def _kosdaq_limit() -> int:
    return max(1, min(200, int(os.getenv("STOCK_WATCH_KOSDAQ150_LIMIT", "150") or "150")))


def _fetch_market_page(sosok: int, page: int) -> list[tuple[str, str]]:
    url = (
        f"https://finance.naver.com/sise/sise_market_sum.naver"
        f"?sosok={sosok}&page={page}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            html = resp.read().decode("euc-kr", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        return []
    return _ROW_RE.findall(html)


def _fetch_top_by_market_cap(sosok: int, limit: int) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    delay = float(os.getenv("STOCK_WATCH_UNIVERSE_PAGE_DELAY_SEC", "0.35") or "0.35")
    for page in range(1, 20):
        rows = _fetch_market_page(sosok, page)
        if not rows:
            break
        for code, name in rows:
            if code in seen:
                continue
            seen.add(code)
            market = "kospi" if sosok == 0 else "kosdaq"
            suffix = "KS" if sosok == 0 else "KQ"
            out.append(
                {
                    "code": code,
                    "name": name.strip()[:80],
                    "market": market,
                    "yahoo_symbol": f"{code}.{suffix}",
                }
            )
            if len(out) >= limit:
                return out
        time.sleep(delay)
    return out[:limit]


def refresh_universe(*, force: bool = False) -> dict:
    max_age_days = int(os.getenv("STOCK_WATCH_UNIVERSE_MAX_AGE_DAYS", "7") or "7")
    if not force:
        cur = load_universe()
        ts = (cur.get("updated_at") or "").strip()
        if ts and len(cur.get("kospi200") or []) >= 50:
            try:
                dt = datetime.strptime(ts[:10], "%Y-%m-%d")
                if datetime.now() - dt < timedelta(days=max_age_days):
                    return {
                        "ok": True,
                        "action": "skipped_fresh",
                        "kospi200": len(cur.get("kospi200") or []),
                        "kosdaq150": len(cur.get("kosdaq150") or []),
                    }
            except ValueError:
                pass

    k200 = _fetch_top_by_market_cap(0, _kospi_limit())
    time.sleep(0.5)
    k150 = _fetch_top_by_market_cap(1, _kosdaq_limit())
    data = _default_universe()
    data["kospi200"] = k200
    data["kosdaq150"] = k150
    save_universe(data)
    return {
        "ok": bool(k200 or k150),
        "action": "refreshed",
        "kospi200": len(k200),
        "kosdaq150": len(k150),
    }


def yahoo_symbols(universe: dict | None = None) -> tuple[list[str], list[str]]:
    u = universe or load_universe()
    k200 = [x["yahoo_symbol"] for x in u.get("kospi200") or [] if x.get("yahoo_symbol")]
    k150 = [x["yahoo_symbol"] for x in u.get("kosdaq150") or [] if x.get("yahoo_symbol")]
    return k200, k150


def name_by_symbol(universe: dict | None = None) -> dict[str, str]:
    u = universe or load_universe()
    out: dict[str, str] = {}
    for pool in ("kospi200", "kosdaq150"):
        for row in u.get(pool) or []:
            sym = row.get("yahoo_symbol") or ""
            if sym:
                out[sym] = row.get("name") or sym
    return out


def ensure_universe_fresh() -> dict:
    if not _universe_enabled():
        return {"ok": True, "action": "disabled"}
    return refresh_universe(force=False)


def status() -> dict:
    u = load_universe()
    return {
        "enabled": _universe_enabled(),
        "path": str(UNIVERSE_PATH),
        "updated_at": u.get("updated_at"),
        "kospi200": len(u.get("kospi200") or []),
        "kosdaq150": len(u.get("kosdaq150") or []),
        "note": u.get("note"),
    }


def main() -> int:
    try:
        import board_env

        board_env.load_board_env()
    except ImportError:
        pass

    p = argparse.ArgumentParser(description="KOSPI200·KOSDAQ150 유니버스")
    p.add_argument("cmd", choices=["refresh", "status"], nargs="?", default="status")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    if args.cmd == "refresh":
        out = refresh_universe(force=args.force)
    else:
        out = status()
    print(out)
    return 0 if out.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
