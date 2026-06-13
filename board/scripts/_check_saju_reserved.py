#!/usr/bin/env python3
"""명리(사주) 예약·위원회 큐 상세 점검."""
import os
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))
sys.path.insert(0, str(BOARD))

import agent_office_tasks
import agent_office_saju_reserved_tasks
import agent_registry

try:
    import agent_office_council
    import agent_office_saju_learn
except ImportError:
    agent_office_council = None
    agent_office_saju_learn = None

DIV = agent_registry.DIVISION_SAJU


def main() -> int:
    use_c = agent_office_council.use_council() if agent_office_council else False
    target_env = int(os.getenv("AGENT_OFFICE_SAJU_RESERVED_QUEUE", "3") or "3")
    council_target = (
        agent_office_council.council_queue_target(DIV) if agent_office_council else 0
    )

    print("=== 설정 ===")
    print("AGENT_OFFICE_USE_COUNCIL:", "1" if use_c else "0")
    print("AGENT_OFFICE_SAJU_RESERVED_QUEUE (env):", target_env)
    print("AGENT_OFFICE_COUNCIL_SAJU_QUEUE:", council_target)

    if agent_office_council:
        qs = agent_office_council.queue_status(DIV)
        print("UI queue_status:", qs)

    print("\n=== 예약(reserved_saju) 카운트 ===")
    print("queued:", agent_office_saju_reserved_tasks.count_reserved_queued())
    print("active (queued+in_progress):", agent_office_saju_reserved_tasks.count_reserved_active())

    if agent_office_council:
        print("\n=== 위원회(council_saju) ===")
        print("active:", agent_office_council.count_council_active(DIV))

    print("\n=== 명리 작업 목록 (대기·진행) ===")
    for t in agent_office_tasks.load_tasks().get("tasks") or []:
        if not isinstance(t, dict):
            continue
        if (t.get("division") or "").strip() != DIV:
            continue
        st = t.get("status") or "queued"
        if st not in ("queued", "in_progress"):
            continue
        src = t.get("source") or ""
        if src not in ("reserved_saju", "council_saju", "reserved"):
            continue
        print(
            f"  #{t.get('id')} [{st}] source={src} "
            f"title={(t.get('title') or '')[:30]!r}"
        )

    if agent_office_saju_learn:
        st = agent_office_saju_learn.stats()
        print("\n=== 학습부 ===")
        print(f"  전체 {st.get('total')} · 대기 {st.get('pending')} · 확정 {st.get('confirmed')}")

    print("\n=== 판정 ===")
    if use_c:
        ok = agent_office_council.count_council_active(DIV) >= council_target
        print(
            f"위원회 모드: {'OK' if ok else '부족'} "
            f"(목표 {council_target}건, 예약 3건과 별개)"
        )
    else:
        ok = agent_office_saju_reserved_tasks.count_reserved_active() >= target_env
        print(
            f"예약 모드: {'OK' if ok else '부족'} "
            f"(목표 {target_env}건)"
        )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
