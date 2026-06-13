"""
kisstock CSV(kr_monthly_dividend_etfs.csv) 종목을 coupax monthly_dividend_etfs.json 에 병합.
- 기존 종목: months·분배금 등 유지
- CSV에만 있는 종목: 메타만 추가(months는 null)

사용:
  python board/scripts/merge_kr_monthly_csv_symbols.py --csv path/to/kr_monthly_dividend_etfs.csv --write
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

SHEET_PATH = Path(__file__).resolve().parents[1] / "data" / "monthly_dividend_etfs.json"
EMPTY_MONTHS: list[None] = [None] * 12


def _ter_str(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return "—"
    if raw.endswith("%"):
        return raw.replace("%%", "%")
    try:
        f = float(raw)
        if f < 1:
            return f"{f:.2f}%".rstrip("0").rstrip(".") + "%" if "." in f"{f:.2f}" else f"{int(f * 100) if f < 0.1 else f}%"
        return f"{f}%"
    except ValueError:
        return raw


def _listed_str(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return "—"
    # 2024-11-04 -> 24.11.04
    parts = raw.split("-")
    if len(parts) == 3 and len(parts[0]) == 4:
        return f"{parts[0][2:]}.{parts[1]}.{parts[2]}"
    return raw


def _parse_float(raw: str) -> float | None:
    try:
        return float(str(raw).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def row_from_csv(rec: dict[str, str]) -> dict[str, Any]:
    price = _parse_float(rec.get("price", ""))
    div_y = _parse_float(rec.get("div_yield_ytd", ""))
    price_y = _parse_float(rec.get("price_yield_ytd", ""))
    total_y = _parse_float(rec.get("total_yield_ytd", ""))
    return {
        "brand": (rec.get("brand") or "").strip() or "—",
        "name": (rec.get("name") or "").strip() or "—",
        "code": (rec.get("code") or "").strip().upper(),
        "cycle": (rec.get("cycle") or "월배").strip(),
        "listed": _listed_str(rec.get("list_date", "")),
        "market_cap": (rec.get("mcap") or "—").strip() or "—",
        "expense_ratio": _ter_str(rec.get("ter_pct", "")),
        "months": list(EMPTY_MONTHS),
        "dividend_total": None,
        "current_price": int(price) if price is not None else None,
        "dividend_yield_pct": div_y,
        "price_return_pct": price_y,
        "total_return_pct": total_y,
        "_sort_total_yield": total_y if total_y is not None else -999.0,
    }


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    import etf_ops_policy

    etf_ops_policy.exit_if_pipeline_disabled()
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    sheet = json.loads(SHEET_PATH.read_text(encoding="utf-8"))
    existing_by_code: dict[str, dict[str, Any]] = {}
    for row in sheet.get("rows", []):
        code = str(row.get("code", "")).upper()
        if code:
            existing_by_code[code] = row

    csv_rows = load_csv(args.csv)
    csv_codes = set()
    added = 0
    updated_meta = 0

    for rec in csv_rows:
        code = (rec.get("code") or "").strip().upper()
        if not code:
            continue
        csv_codes.add(code)
        if code in existing_by_code:
            row = existing_by_code[code]
            fresh = row_from_csv(rec)
            for k in (
                "brand",
                "name",
                "cycle",
                "listed",
                "market_cap",
                "expense_ratio",
                "current_price",
                "dividend_yield_pct",
                "price_return_pct",
                "total_return_pct",
            ):
                if fresh.get(k) is not None:
                    row[k] = fresh[k]
            row["_sort_total_yield"] = fresh["_sort_total_yield"]
            updated_meta += 1
        else:
            existing_by_code[code] = row_from_csv(rec)
            added += 1

    # CSV에 없지만 기존에 있던 종목(예: 0052D0) 유지
    extras = [c for c in existing_by_code if c not in csv_codes]

    merged = list(existing_by_code.values())
    for row in merged:
        if "_sort_total_yield" in row:
            del row["_sort_total_yield"]

    from sync_dividend_sheet import sort_rows_by_total_return

    sort_rows_by_total_return(merged, reverse=True)

    sheet["rows"] = merged
    sheet["note"] = (
        f"국내 월배당 ETF {len(merged)}종 "
        f"(kisstock CSV {len(csv_rows)}종 + 기존 단독 {len(extras)}종). "
        "분배금·수익률은 공개 자료 기준. 미지급 월은 null. 투자 권유가 아닙니다."
    )

    print(f"CSV rows: {len(csv_rows)}")
    print(f"Added: {added}, meta touch: {updated_meta}, extras kept: {len(extras)} ({', '.join(extras)})")
    print(f"Total rows: {len(merged)}")

    if args.write:
        SHEET_PATH.write_text(json.dumps(sheet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("written", SHEET_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
