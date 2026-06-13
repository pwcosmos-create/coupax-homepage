#!/usr/bin/env python3
"""예약·위원회 큐 상태 점검."""
import os
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))
sys.path.insert(0, str(BOARD))

import agent_office_tasks
import agent_office_reserved_tasks
import agent_office_saju_reserved_tasks

try:
    import agent_office_council
except ImportError:
    agent_office_council = None

os.environ.setdefault("BOARD_DB_PATH", str(BOARD / "board.db"))


def count_by_source(*sources: str) -> dict[str, int]:
    out = {s: 0 for s in sources}
    for t in agent_office_tasks.load_tasks().get("tasks") or []:
        if not isinstance(t, dict):
            continue
        st = (t.get("status") or "queued")
        if st not in ("queued", "in_progress"):
            continue
        src = (t.get("source") or "").strip()
        if src in out:
            out[src] += 1
    return out


def main() -> int:
    use_council = (
        agent_office_council.use_council() if agent_office_council else False
    )
    finance_reserved = agent_office_reserved_tasks.count_reserved_active()
    finance_queued = agent_office_reserved_tasks.count_reserved_queued()
    saju_reserved = agent_office_saju_reserved_tasks.count_reserved_active()
    saju_queued = agent_office_saju_reserved_tasks.count_reserved_queued()
    by_src = count_by_source(
        "reserved",
        "reserved_saju",
        "council_finance",
        "council_saju",
    )
    target_fin = int(os.getenv("AGENT_OFFICE_RESERVED_QUEUE", "3") or "3")
    target_saju = int(os.getenv("AGENT_OFFICE_SAJU_RESERVED_QUEUE", "3") or "3")
    council_fin = (
        agent_office_council.count_council_active(agent_office_council.DIVISION_FINANCE)
        if agent_office_council
        else 0
    )
    council_saju = (
        agent_office_council.count_council_active(agent_office_council.DIVISION_SAJU)
        if agent_office_council
        else 0
    )

    print("AGENT_OFFICE_USE_COUNCIL=", "1" if use_council else "0")
    print(f"UI target finance={target_fin} saju={target_saju}")
    print(f"finance reserved active={finance_reserved} queued={finance_queued}")
    print(f"saju reserved active={saju_reserved} queued={saju_queued}")
    print("by source (queued+in_progress):", by_src)
    if use_council:
        print(f"council active finance={council_fin} saju={council_saju}")
        print(
            "ensure would maintain council:",
            f"finance={os.getenv('AGENT_OFFICE_COUNCIL_FINANCE_QUEUE', '1')}",
            f"saju={os.getenv('AGENT_OFFICE_COUNCIL_SAJU_QUEUE', '1')}",
        )
    if agent_office_council:
        fq = agent_office_council.queue_status(agent_office_council.DIVISION_FINANCE)
        sq = agent_office_council.queue_status(agent_office_council.DIVISION_SAJU)
        print("queue_status finance:", fq)
        print("queue_status saju:", sq)
        ok_fin = fq["active"] >= fq["target"] and fq["target"] > 0
        ok_saju = sq["active"] >= sq["target"] and sq["target"] > 0
    else:
        ok_fin = finance_reserved >= min(1, target_fin)
        ok_saju = saju_reserved >= min(1, target_saju)
    print("OK finance queue:", ok_fin)
    print("OK saju queue:", ok_saju)
    return 0 if (ok_fin and ok_saju) else 1


if __name__ == "__main__":
    raise SystemExit(main())
