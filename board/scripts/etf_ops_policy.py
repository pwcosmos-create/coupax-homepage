"""
coupax ETF 파이프라인·공개 페이지 전역 정책.

2026-05 search-etf.com 중단 요청에 따라 기본값은 전면 중지입니다.
COUPAX_ETF_ENABLED=1 일 때만 파이프라인·공개 ETF 페이지가 동작합니다.
"""
from __future__ import annotations

import os
import sys

DISABLED_REASON = (
    "ETF 데이터 파이프라인·공개 페이지가 중지되었습니다 (외부 데이터 이용 중단, 2026-05). "
    "COUPAX_ETF_ENABLED=1 로만 재개 가능합니다."
)


def etf_ops_enabled() -> bool:
    return os.getenv("COUPAX_ETF_ENABLED", "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def block_message() -> str:
    return DISABLED_REASON


def exit_if_pipeline_disabled(*, exit_code: int = 0) -> None:
    if etf_ops_enabled():
        return
    print(f"[etf-ops] SKIP: {DISABLED_REASON}", flush=True)
    raise SystemExit(exit_code)
