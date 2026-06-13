"""
search-etf.com API로 상장일·시가총액·총보수 등 메타를 채웁니다.
각 종목은 API를 두 번 조회하고, 값이 일치할 때만 반영합니다.

  python board/scripts/fill_etf_meta.py --dry-run
  python board/scripts/fill_etf_meta.py --write
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import time
import urllib.request
from pathlib import Path
from typing import Any

from etf_verify_fetch import reconcile_meta

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
SHEET_PATH = Path(__file__).resolve().parents[1] / "data" / "monthly_dividend_etfs.json"
INFO_URL = "https://search-etf.com/backend/get_etf_stock_info.php?stock_code={code}"
FETCH_GAP = 0.55


def fetch_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))


def _listed_from_sd(sd: dict[str, Any]) -> str | None:
    raw = (sd.get("listdate") or sd.get("inception_date") or "").strip()
    if not raw:
        return None
    m = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})", raw)
    if m:
        y, mo, d = m.groups()
        return f"{y[2:]}.{mo.zfill(2)}.{d.zfill(2)}"
    parts = raw.split("-")
    if len(parts) == 3 and len(parts[0]) == 4:
        return f"{parts[0][2:]}.{parts[1]}.{parts[2]}"
    return None


def _mcap_from_sd(sd: dict[str, Any]) -> str | None:
    tot = sd.get("etftotcap")
    if tot is not None and str(tot).strip() not in ("", "-", "0"):
        try:
            return f"{int(float(tot))}억"
        except (TypeError, ValueError):
            pass
    text = (sd.get("market_cap_text") or "").strip()
    if not text:
        return None
    text = text.replace(",", "").replace(" ", "")
    text = re.sub(r"만", "", text)
    if text.endswith("억"):
        return text
    return f"{text}억" if text else None


def _fee_from_sd(sd: dict[str, Any]) -> str | None:
    raw = (sd.get("total_fee") or "").strip()
    while raw.endswith("%"):
        raw = raw[:-1].rstrip()
    if not raw:
        return None
    try:
        val = float(raw)
    except ValueError:
        return f"{raw}%"
    if val >= 1:
        return f"{val:.2f}%"
    if val >= 0.1:
        s = f"{val:.2f}"
        s = s.rstrip("0").rstrip(".")
        return f"{s}%"
    s = f"{val:.3f}".rstrip("0").rstrip(".")
    return f"{s}%"


def _meta_from_api(code: str) -> dict[str, str] | None:
    try:
        info = fetch_json(INFO_URL.format(code=code.strip().upper()))
    except Exception:
        return None
    if info.get("status") != "success":
        return None
    data = info.get("data")
    if not isinstance(data, dict):
        return None
    sd = data.get("stock_detail")
    if not isinstance(sd, dict):
        return None
    out: dict[str, str] = {}
    listed = _listed_from_sd(sd)
    mcap = _mcap_from_sd(sd)
    fee = _fee_from_sd(sd)
    if listed:
        out["listed"] = listed
    if mcap:
        out["market_cap"] = mcap
    if fee:
        out["expense_ratio"] = fee
    return out or None


def fetch_meta_verified(code: str) -> tuple[dict[str, str] | None, str]:
    c = code.strip().upper()
    first = _meta_from_api(c)
    time.sleep(FETCH_GAP)
    second = _meta_from_api(c)
    meta, status = reconcile_meta(first, second)
    return meta, status


def _needs_fill(row: dict[str, Any], key: str) -> bool:
    v = row.get(key)
    return v in (None, "", "—")


def main() -> int:
    import etf_ops_policy
    import search_etf_policy

    etf_ops_policy.exit_if_pipeline_disabled()
    search_etf_policy.exit_if_blocked()
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    dry_run = not args.write

    sheet = json.loads(SHEET_PATH.read_text(encoding="utf-8"))
    rows = sheet.get("rows", [])
    updated = 0
    skipped = 0

    for row in rows:
        code = str(row.get("code", "")).strip().upper()
        if not code:
            continue
        if not any(_needs_fill(row, k) for k in ("listed", "market_cap", "expense_ratio")):
            continue
        meta, status = fetch_meta_verified(code)
        name = (row.get("name") or "")[:32]
        if not meta:
            print(f"  {code} {name:32} skip ({status})")
            if status.startswith("mismatch"):
                skipped += 1
            continue
        if status != "verified" and not status.startswith("single_ok"):
            print(f"  {code} {name:32} skip ({status})")
            skipped += 1
            continue
        changes = []
        for key in ("listed", "market_cap", "expense_ratio"):
            if _needs_fill(row, key) and key in meta:
                changes.append(f"{key}={meta[key]}")
                if not dry_run:
                    row[key] = meta[key]
        if changes:
            updated += 1
            tag = "verified" if status == "verified" else status
            print(f"  {code} {name:32} [{tag}] " + " ".join(changes))

    if skipped:
        print(f"\n  [warn] 이중 조회 불일치/실패 {skipped}종 — 기존 값 유지")

    if not dry_run and updated:
        from sync_dividend_sheet import sort_rows_by_total_return

        sort_rows_by_total_return(rows, reverse=True)
        SHEET_PATH.write_text(
            json.dumps(sheet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(f"\n{'[dry-run] ' if dry_run else '[saved] '}updated {updated} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
