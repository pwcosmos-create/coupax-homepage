"""
search-etf.com 공개 API로 국내 ETF 2026년 월별 분배금(1좌당)을 조회해
monthly_dividend_etfs.json 의 months 배열을 채웁니다.

사용:
  python board/scripts/fill_domestic_dividends.py --dry-run
  python board/scripts/fill_domestic_dividends.py --write
"""
from __future__ import annotations

import argparse
import json
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
YEAR = 2026
SHEET_PATH = Path(__file__).resolve().parents[1] / "data" / "monthly_dividend_etfs.json"
INFO_URL = "https://search-etf.com/backend/get_etf_stock_info.php?stock_code={code}"


def fetch_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))


def _parse_amount(raw: Any) -> float | None:
    if raw is None or raw == "" or raw == "-":
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    return val if val > 0 else None


def months_from_year_record(rec: dict[str, Any]) -> list[float | None]:
    out: list[float | None] = [None] * 12
    for m in range(1, 13):
        raw = rec.get(f"month{m}") or rec.get(f"{m:02d}")
        val = _parse_amount(raw)
        if val is not None:
            out[m - 1] = round(val)
    return out


def months_from_dividend_info(dividend_info: dict[str, Any], year: int) -> list[float | None]:
    rec = dividend_info.get(str(year))
    if not isinstance(rec, dict):
        return [None] * 12
    return months_from_year_record(rec)


def sum_months(months: list[float | None]) -> int | None:
    vals = [m for m in months if m is not None]
    return int(sum(vals)) if vals else None


def fetch_row_months(code: str) -> tuple[list[float | None], int | None, str]:
    code = code.strip().upper()
    time.sleep(0.35)
    try:
        info = fetch_json(INFO_URL.format(code=code))
    except urllib.error.HTTPError as e:
        return [None] * 12, None, f"HTTP {e.code}"
    except Exception as e:
        return [None] * 12, None, str(e)[:60]

    if info.get("status") != "success":
        return [None] * 12, None, str(info.get("message", "no success"))[:60]

    data = info.get("data")
    if not isinstance(data, dict):
        return [None] * 12, None, "no data"

    div_info = data.get("dividend_info")
    months = months_from_dividend_info(div_info, YEAR) if isinstance(div_info, dict) else [None] * 12

    price: int | None = None
    if isinstance(div_info, dict):
        year_rec = div_info.get(str(YEAR))
        if isinstance(year_rec, dict):
            p = _parse_amount(year_rec.get("price"))
            if p is not None:
                price = int(round(p))
    if price is None:
        sd = data.get("stock_detail")
        if isinstance(sd, dict):
            p = _parse_amount(sd.get("price") or sd.get("current_price"))
            if p is not None:
                price = int(round(p))

    n = sum(1 for m in months if m is not None)
    return months, price, ("ok" if n else "empty")


def apply_to_sheet(sheet: dict[str, Any], dry_run: bool) -> int:
    rows = sheet.get("rows", [])
    with_data = 0
    for row in rows:
        code = str(row.get("code", ""))
        months, price, status = fetch_row_months(code)
        n = sum(1 for m in months if m is not None)
        total = sum_months(months)
        name = (row.get("name") or "")[:28]
        print(f"  {code} {name:28} n={n:2} total={str(total or '-'):>4} price={str(price or '-'):>6} {status}")
        if n:
            with_data += 1
        if dry_run:
            continue
        row["months"] = months
        row["dividend_total"] = total
        if price is not None:
            row["current_price"] = price
        if total and row.get("current_price"):
            cp = row["current_price"]
            if cp and cp > 0:
                row["dividend_yield_pct"] = round((total / cp) * 100, 2)

    if not dry_run:
        sheet["note"] = (
            f"국내 월배당 ETF {len(rows)}종. {YEAR}년 월별 분배금(1좌당 원)은 "
            "search-etf.com(get_etf_stock_info) 기준 자동 반영. 미지급 월은 null. "
            "수익률·시총 등 메타는 kisstock CSV와 병합. 투자 권유가 아닙니다."
        )
        SHEET_PATH.write_text(json.dumps(sheet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return with_data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="JSON 파일에 저장")
    parser.add_argument("--dry-run", action="store_true", help="조회만")
    args = parser.parse_args()
    dry_run = not args.write

    sheet = json.loads(SHEET_PATH.read_text(encoding="utf-8"))
    print(f"Fetching {YEAR} monthly dividends for {len(sheet['rows'])} ETFs...")
    n = apply_to_sheet(sheet, dry_run=dry_run)
    print(f"\n{'[dry-run] ' if dry_run else '[saved] '}{n}/{len(sheet['rows'])} rows with data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
