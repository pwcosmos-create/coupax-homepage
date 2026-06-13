"""
search-etf.com API로 연초~현재(YTD) 주가수익률·총수익률을 채웁니다.

- price_history: 전년 말(또는 연중 상장 시 연초 첫 거래일) 대비 현재가
- total_return_pct: 주가 YTD와 누적 배당수익률을 복리 근사 (1+p)(1+d)-1

CSV·기존 값이 있는 행은 덮어쓰지 않습니다. 월별 분배·dividend_yield_pct 는
fill_domestic_dividends 이후 실행하는 것을 권장합니다.

  python board/scripts/fill_etf_ytd_returns.py --dry-run
  python board/scripts/fill_etf_ytd_returns.py --write
"""
from __future__ import annotations

import argparse
import json
import ssl
import time
import urllib.request
from pathlib import Path
from typing import Any

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
SHEET_PATH = Path(__file__).resolve().parents[1] / "data" / "monthly_dividend_etfs.json"
INFO_URL = "https://search-etf.com/backend/get_etf_stock_info.php?stock_code={code}"
FETCH_GAP = 0.55
YEAR = 2026


def fetch_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))


def _parse_price_ytd_once(code: str) -> tuple[float | None, float | None, float | None, str]:
    """Returns (pct, base_px, end_px, status)."""
    code = code.strip().upper()
    try:
        info = fetch_json(INFO_URL.format(code=code))
    except Exception as e:
        return None, None, None, str(e)[:60]

    if info.get("status") != "success":
        return None, None, None, "no_success"
    data = info.get("data")
    if not isinstance(data, dict):
        return None, None, None, "no_data"
    sd = data.get("stock_detail")
    if not isinstance(sd, dict):
        return None, None, None, "no_stock_detail"

    end_raw = sd.get("price")
    try:
        end_px = float(end_raw)
    except (TypeError, ValueError):
        end_px = 0.0
    if end_px <= 0:
        return None, None, None, "no_price"

    ph = data.get("price_history")
    if isinstance(ph, dict):
        plist = ph.get("price_list") or []
    else:
        plist = []
    if not isinstance(plist, list) or not plist:
        return None, None, None, "no_history"

    prefix = f"{YEAR}-01-01"
    pre = [p for p in plist if isinstance(p, dict) and str(p.get("date", "")) < prefix]
    ytd = [p for p in plist if isinstance(p, dict) and str(p.get("date", "")).startswith(str(YEAR))]

    base_px: float | None = None
    if pre:
        last = pre[-1]
        try:
            base_px = float(last.get("price"))
        except (TypeError, ValueError):
            base_px = None
    elif ytd:
        first = ytd[0]
        try:
            base_px = float(first.get("price"))
        except (TypeError, ValueError):
            base_px = None

    if base_px is None or base_px <= 0:
        return None, None, None, "no_base"

    pct = round((end_px / base_px - 1) * 100, 2)
    return pct, base_px, end_px, "ok"


def fetch_price_ytd_verified(code: str) -> tuple[float | None, str]:
    c = code.strip().upper()

    def once() -> tuple[float | None, float | None, float | None, str]:
        return _parse_price_ytd_once(c)

    first = once()
    time.sleep(FETCH_GAP)
    second = once()
    p1, b1, e1, s1 = first
    p2, b2, e2, s2 = second
    if s1 != "ok" or s2 != "ok":
        if s1 == "ok":
            return p1, f"single_ok_1:{s2}"
        if s2 == "ok":
            return p2, f"single_ok_2:{s1}"
        return None, f"fail:{s1}/{s2}"
    if p1 is None or p2 is None:
        return None, "fail:empty_pct"
    if round(p1, 2) != round(p2, 2):
        return None, "mismatch_pct"
    if b1 is not None and b2 is not None and abs(b1 - b2) > 0.01:
        return None, "mismatch_base"
    if e1 is not None and e2 is not None and abs(e1 - e2) > 0.01:
        return None, "mismatch_end"
    return p1, "verified"


def _div_yield_pct(row: dict[str, Any]) -> float:
    raw = row.get("dividend_yield_pct")
    if raw is None:
        return 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def compound_total(price_pct: float, div_yield_pct: float) -> float:
    """(1+p)(1+d)-1 in percent."""
    p = price_pct / 100.0
    d = div_yield_pct / 100.0
    return round(((1 + p) * (1 + d) - 1) * 100, 2)


def main() -> int:
    import etf_ops_policy
    import search_etf_policy

    etf_ops_policy.exit_if_pipeline_disabled()
    search_etf_policy.exit_if_blocked()
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    dry = not args.write

    sheet = json.loads(SHEET_PATH.read_text(encoding="utf-8"))
    rows = sheet.get("rows", [])
    updated = 0
    skipped = 0

    for row in rows:
        need_p = row.get("price_return_pct") is None
        need_t = row.get("total_return_pct") is None
        if not need_p and not need_t:
            continue
        code = str(row.get("code", "")).strip().upper()
        if not code:
            continue
        name = (row.get("name") or "")[:30]

        status = "verified"
        price_pct: float | None = None
        if need_p:
            price_pct, status = fetch_price_ytd_verified(code)
            if price_pct is None:
                print(f"  {code} {name:30} skip ({status})")
                skipped += 1
                continue
            if status != "verified" and not status.startswith("single_ok"):
                print(f"  {code} {name:30} skip ({status})")
                skipped += 1
                continue
        else:
            try:
                price_pct = float(row.get("price_return_pct"))
            except (TypeError, ValueError):
                print(f"  {code} {name:30} skip (bad existing price_return_pct)")
                skipped += 1
                continue

        dy = _div_yield_pct(row)
        total_pct = compound_total(price_pct, dy)
        tag = status
        if need_p and need_t:
            print(f"  {code} {name:30} price_ytd={price_pct:>8} total={total_pct:>8} [{tag}]")
        elif need_t:
            print(f"  {code} {name:30} (price 기존) total={total_pct:>8} [{tag}]")

        if not dry:
            if need_p:
                row["price_return_pct"] = price_pct
            if need_t:
                row["total_return_pct"] = total_pct
        updated += 1

    if skipped:
        print(f"\n  [warn] 건너뜀 {skipped}건")

    if not dry and updated:
        from sync_dividend_sheet import sort_rows_by_total_return

        sort_rows_by_total_return(rows, reverse=True)
        SHEET_PATH.write_text(json.dumps(sheet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"\n{'[dry-run] ' if dry else '[saved] '}touched {updated} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
