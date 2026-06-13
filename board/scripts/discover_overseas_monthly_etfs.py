"""
국내 상장 ETF 중 search-etf 기준 월분배(notation=2)·해외전용(temp2=해외주식) 종목을
탐색해 monthly_dividend_etfs.json 에 병합합니다.

  python board/scripts/discover_overseas_monthly_etfs.py --dry-run
  python board/scripts/discover_overseas_monthly_etfs.py --write
"""
from __future__ import annotations

import argparse
import json
import re
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
NAVER_ETF_URL = "https://finance.naver.com/api/sise/etfItemList.nhn"
FETCH_GAP = 0.35

BRANDS = (
    "KODEX",
    "KoAct",
    "TIGER",
    "RISE",
    "PLUS",
    "ACE",
    "HANARO",
    "SOL",
    "TIME",
    "KIWOOM",
    "1Q",
    "ARIRANG",
    "KBSTAR",
    "TREX",
    "FOCUS",
)


def fetch_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
        raw = r.read()
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            return json.loads(raw.decode(enc))
        except UnicodeDecodeError:
            continue
    return json.loads(raw.decode("utf-8", errors="replace"))


def naver_etf_codes() -> list[tuple[str, str]]:
    data = fetch_json(NAVER_ETF_URL)
    items = data.get("result", {}).get("etfItemList", [])
    out: list[tuple[str, str]] = []
    for it in items:
        code = str(it.get("itemcode", "")).strip().upper()
        name = str(it.get("itemname", "")).strip()
        if code and name:
            out.append((code, name))
    return out


def guess_brand(name: str) -> str:
    for b in BRANDS:
        if name.upper().startswith(b.upper()) or name.startswith(b):
            return b
    return name.split()[0] if name.split() else "—"


def overseas_monthly_record(div_info: dict[str, Any]) -> dict[str, Any] | None:
    for y in (YEAR, YEAR - 1):
        rec = div_info.get(str(y))
        if not isinstance(rec, dict):
            continue
        if str(rec.get("notation", "")).strip() != "2":
            continue
        if "해외" in str(rec.get("temp2") or ""):
            return rec
    return None


def months_from_record(rec: dict[str, Any]) -> list[float | None]:
    out: list[float | None] = [None] * 12
    for m in range(1, 13):
        raw = rec.get(f"month{m}")
        if raw is None or raw == "" or raw == "-":
            continue
        try:
            v = float(raw)
            if v > 0:
                out[m - 1] = round(v)
        except (TypeError, ValueError):
            pass
    return out


def build_row(code: str, naver_name: str, year_rec: dict[str, Any]) -> dict[str, Any]:
    name = str(year_rec.get("stock_name") or naver_name).strip() or naver_name
    months = months_from_record(year_rec)
    total = int(sum(m for m in months if m is not None)) if any(m is not None for m in months) else None
    price_raw = year_rec.get("price")
    try:
        price = int(round(float(price_raw))) if price_raw not in (None, "", "-") else None
    except (TypeError, ValueError):
        price = None
    div_y = round((total / price) * 100, 2) if total and price and price > 0 else None
    listed = str(year_rec.get("listing_date") or "")
    if re.match(r"^\d{4}-\d{2}-\d{2}$", listed):
        y, mo, d = listed.split("-")
        listed = f"{y[2:]}.{mo}.{d}"
    elif not listed:
        listed = "—"
    fee = year_rec.get("fee")
    ter = f"{fee}%" if fee not in (None, "", "-") else "—"
    return {
        "brand": guess_brand(name),
        "name": name,
        "code": code,
        "cycle": "월배",
        "listed": listed,
        "market_cap": "—",
        "expense_ratio": ter,
        "months": months,
        "dividend_total": total,
        "current_price": price,
        "dividend_yield_pct": div_y,
        "price_return_pct": None,
        "total_return_pct": None,
        "scope": "overseas",
    }


def probe_code(code: str) -> dict[str, Any] | None:
    try:
        info = fetch_json(INFO_URL.format(code=code))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None
    if info.get("status") != "success":
        return None
    data = info.get("data")
    if not isinstance(data, dict):
        return None
    div_info = data.get("dividend_info")
    if not isinstance(div_info, dict):
        return None
    rec = overseas_monthly_record(div_info)
    if not rec:
        return None
    rec26 = div_info.get(str(YEAR))
    if isinstance(rec26, dict) and str(rec26.get("notation", "")).strip() == "2":
        if "해외" in str(rec26.get("temp2") or ""):
            return rec26
    return rec


def main() -> int:
    import etf_ops_policy
    import search_etf_policy

    etf_ops_policy.exit_if_pipeline_disabled()
    search_etf_policy.exit_if_blocked()
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="탐색 상한(0=전체)")
    parser.add_argument("--gap", type=float, default=FETCH_GAP)
    args = parser.parse_args()
    dry = not args.write

    sheet = json.loads(SHEET_PATH.read_text(encoding="utf-8"))
    by_code: dict[str, dict[str, Any]] = {}
    for row in sheet.get("rows", []):
        c = str(row.get("code", "")).upper()
        if c:
            by_code[c] = row

    universe = naver_etf_codes()
    print(f"Naver ETF universe: {len(universe)}")
    found: list[str] = []
    added = 0

    todo = universe[: args.limit] if args.limit > 0 else universe
    for i, (code, naver_name) in enumerate(todo, 1):
        if i % 50 == 0:
            print(f"  scan {i}/{len(todo)} overseas_found={len(found)}", flush=True)
        rec = probe_code(code)
        if not rec:
            time.sleep(args.gap)
            continue
        found.append(code)
        if code in by_code:
            by_code[code]["scope"] = "overseas"
            time.sleep(args.gap)
            continue
        row = build_row(code, naver_name, rec)
        by_code[code] = row
        added += 1
        print(f"  + {code} {row['name'][:40]}", flush=True)
        time.sleep(args.gap)

    merged = list(by_code.values())
    from sync_dividend_sheet import sort_rows_by_total_return

    sort_rows_by_total_return(merged, reverse=True)
    overseas_n = sum(1 for r in merged if r.get("scope") == "overseas")

    sheet["rows"] = merged
    sheet["pipeline_note"] = (
        "국내 상장 월배당·월분배 ETF(국내·해외전용)를 운용사·거래소·공개 API로 정리했습니다. "
        "해외전용은 search-etf temp2=해외주식·notation=2 기준입니다."
    )
    sheet["note"] = (
        f"국내 상장 월분배 ETF {len(merged)}종 "
        f"(해외전용 {overseas_n}종 포함, API·CSV 병합). 분배금·수익률은 변동하며 투자 권유가 아닙니다."
    )

    print(f"\nOverseas monthly (API): {len(found)}")
    print(f"New rows added: {added}")
    print(f"Total rows: {len(merged)} (scope=overseas: {overseas_n})")

    if not dry:
        SHEET_PATH.write_text(json.dumps(sheet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("written", SHEET_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
