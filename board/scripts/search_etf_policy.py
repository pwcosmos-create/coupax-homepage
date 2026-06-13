"""
search-etf.com API 호출 정책.

2026-05 search-etf.com 관리자 중단 요청에 따라 기본값은 호출 금지입니다.
명시적으로 SEARCH_ETF_CALLS_ALLOWED=1 일 때만 스크립트가 해당 API에 접속합니다.
"""
from __future__ import annotations

import os
import sys

DISABLED_REASON = (
    "search-etf.com API 호출이 중단되었습니다 (관리자 중단 요청, 2026-05). "
    "SEARCH_ETF_CALLS_ALLOWED=1 로만 재개 가능합니다."
)


def search_etf_calls_allowed() -> bool:
    try:
        import etf_ops_policy

        if not etf_ops_policy.etf_ops_enabled():
            return False
    except ImportError:
        pass
    return os.getenv("SEARCH_ETF_CALLS_ALLOWED", "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def block_message() -> str:
    return DISABLED_REASON


def exit_if_blocked(*, exit_code: int = 0) -> None:
    """차단 시 메시지 출력 후 종료 (기본 exit 0 — 일일 sync 파이프라인 중단 방지)."""
    if search_etf_calls_allowed():
        return
    print(f"[search-etf] SKIP: {DISABLED_REASON}", flush=True)
    raise SystemExit(exit_code)
