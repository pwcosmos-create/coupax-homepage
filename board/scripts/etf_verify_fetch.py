"""
ETF 공개 API 이중 조회·일치 검증.

같은 종목을 두 번 조회해 결과가 일치할 때만 반영합니다.
"""
from __future__ import annotations

import time
from typing import Any, Callable, TypeVar

T = TypeVar("T")

DEFAULT_GAP_SEC = 0.55


def months_equal(a: list[float | None], b: list[float | None]) -> bool:
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if x is None and y is None:
            continue
        if x is None or y is None:
            return False
        if int(round(x)) != int(round(y)):
            return False
    return True


def fetch_twice(
    fetch_once: Callable[[], T | None],
    *,
    gap_sec: float = DEFAULT_GAP_SEC,
) -> tuple[T | None, T | None, str]:
    """
    Returns (result_if_match, first_result, status).
    status: ok | mismatch | empty | error
    """
    try:
        first = fetch_once()
    except Exception as e:
        return None, None, f"error:{e!s}"[:80]

    time.sleep(gap_sec)

    try:
        second = fetch_once()
    except Exception as e:
        return None, first, f"error2:{e!s}"[:80]

    if first is None and second is None:
        return None, None, "empty"
    if first is None:
        return second, first, "ok_second_only"
    if second is None:
        return first, first, "ok_first_only"

    return first, first, "ok"


def reconcile_months_price(
    first: tuple[list[float | None], int | None, str],
    second: tuple[list[float | None], int | None, str],
) -> tuple[list[float | None] | None, int | None, str]:
    m1, p1, s1 = first
    m2, p2, s2 = second
    if s1 != "ok" or s2 != "ok":
        if s1 == "ok":
            return m1, p1, "single_ok_1"
        if s2 == "ok":
            return m2, p2, "single_ok_2"
        return None, None, f"fail:{s1}/{s2}"

    if not months_equal(m1, m2):
        return None, None, "mismatch_months"
    if p1 != p2:
        return None, None, "mismatch_price"
    return m1, p1, "verified"


def meta_equal(a: dict[str, str], b: dict[str, str]) -> bool:
    keys = set(a) | set(b)
    return all(a.get(k) == b.get(k) for k in keys)


def reconcile_meta(
    first: dict[str, str] | None,
    second: dict[str, str] | None,
) -> tuple[dict[str, str] | None, str]:
    if not first and not second:
        return None, "empty"
    if first and not second:
        return first, "single_ok_1"
    if second and not first:
        return second, "single_ok_2"
    assert first and second
    merged: dict[str, str] = {}
    for k in set(first) | set(second):
        v1, v2 = first.get(k), second.get(k)
        if v1 and v2 and v1 != v2:
            return None, f"mismatch_{k}"
        merged[k] = v1 or v2 or ""
    return merged, "verified"
