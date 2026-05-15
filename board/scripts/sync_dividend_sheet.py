"""
월배당 시트(JSON) 갱신용 스크립트 뼈대.

데이터는 운용사 홈페이지·공시(DART 등), 거래소, 증권사 Open API(시세·체결·분배 내역 등)에서
수집한 뒤 단위 통일·검증·합계 산출 등 재가공하여 board/data/monthly_dividend_etfs.json 에 반영하는
흐름을 가정합니다. API 키·앱시크릿은 코드에 넣지 말고 환경 변수(.env)로만 주입하세요.

실제 HTTP 호출은 증권사·운용사 약관 및 이용 한도에 맞게 별도 구현하면 됩니다.
이 파일은 JSON 스키마 검증과 파일 읽기/쓰기만 제공합니다.

사용 예:
  python board/scripts/sync_dividend_sheet.py --validate
  python board/scripts/sync_dividend_sheet.py --input path/to/partial.json --output board/data/monthly_dividend_etfs.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

REQUIRED_ROW_KEYS = (
    "no",
    "brand",
    "name",
    "code",
    "cycle",
    "listed",
    "market_cap",
    "expense_ratio",
    "months",
    "dividend_total",
    "current_price",
    "dividend_yield_pct",
    "price_return_pct",
    "total_return_pct",
)


def _sheet_path() -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "data", "monthly_dividend_etfs.json")


def validate_sheet(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["루트는 객체(JSON object)여야 합니다."]
    for k in ("year", "rows"):
        if k not in data:
            errors.append(f"필수 키 누락: {k}")
    rows = data.get("rows")
    if not isinstance(rows, list):
        errors.append("rows 는 배열이어야 합니다.")
        return errors
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"rows[{i}] 는 객체여야 합니다.")
            continue
        for rk in REQUIRED_ROW_KEYS:
            if rk not in row:
                errors.append(f"rows[{i}] 필수 키 누락: {rk}")
        months = row.get("months")
        if months is not None:
            if not isinstance(months, list) or len(months) != 12:
                errors.append(f"rows[{i}].months 는 길이 12 배열이어야 합니다.")
            else:
                for j, m in enumerate(months):
                    if m is not None and not isinstance(m, (int, float)):
                        errors.append(f"rows[{i}].months[{j}] 는 숫자 또는 null 이어야 합니다.")
    return errors


def load_json(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="월배당 시트 JSON 검증/복사")
    parser.add_argument("--validate", action="store_true", help="기본 시트 파일만 검증")
    parser.add_argument("--input", type=str, help="재가공 결과를 담은 JSON 경로")
    parser.add_argument("--output", type=str, help="저장 경로(기본: data/monthly_dividend_etfs.json)")
    args = parser.parse_args()
    out_default = _sheet_path()

    if args.validate and not args.input:
        path = out_default
        data = load_json(path)
        err = validate_sheet(data)
        if err:
            for e in err:
                print(e, file=sys.stderr)
            return 1
        print("OK", path)
        return 0

    if args.input:
        data = load_json(args.input)
        err = validate_sheet(data)
        if err:
            for e in err:
                print(e, file=sys.stderr)
            return 1
        dest = args.output or out_default
        save_json(dest, data)
        print("written", dest)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
