#!/usr/bin/env python3
"""원키스US(workisus-chasu) 젬마만 활성화 + 1회 즉시 작업.

  cd board && PYTHONPATH=scripts python scripts/activate_workisus_agents.py
  cd board && PYTHONPATH=scripts python scripts/activate_workisus_agents.py --interval 0
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_log
import agent_registry

RETIRED = frozenset(
    {"workisus_curator", "workisus_sync", "workisus_atr_rl", "workisus_error_fix"}
)


def activate_workisus(*, interval_minutes: int | None = None) -> dict:
    data = agent_registry.load_registry()
    on_ids: list[str] = []
    off_ids: list[str] = []
    for a in data.get("agents") or []:
        if not isinstance(a, dict):
            continue
        if agent_registry.agent_division(a) != agent_registry.DIVISION_WORKISUS:
            continue
        aid = (a.get("id") or "").strip()
        if aid in RETIRED:
            a["mode_on"] = False
            off_ids.append(aid)
            continue
        a["mode_on"] = True
        a["last_run_at"] = None
        if interval_minutes is not None:
            a["interval_minutes"] = interval_minutes
            a["interval_label"] = "항상" if interval_minutes <= 0 else f"{interval_minutes}분"
        on_ids.append(aid)
    agent_registry.save_registry(data)
    return {"on": on_ids, "off": off_ids, "count_on": len(on_ids)}


def run_worker_once() -> int:
    os.environ["AGENT_OFFICE_WORKER_ENABLED"] = "1"
    os.environ["AGENT_OFFICE_FORCE_RUN"] = "1"
    os.environ["AGENT_OFFICE_WORKISUS_ONLY"] = "1"
    import agent_office_worker

    return agent_office_worker.main()


def main() -> int:
    import board_env

    board_env.load_board_env()

    p = argparse.ArgumentParser()
    p.add_argument(
        "--interval",
        type=int,
        default=None,
        help="작업 주기(분). 0=worker 호출마다. 미지정=레지스트리 유지",
    )
    p.add_argument("--no-run", action="store_true", help="활성화만, worker 미실행")
    args = p.parse_args()

    out = activate_workisus(interval_minutes=args.interval)
    agent_office_log.append_message(
        from_id="workisus_knowledge",
        kind="system",
        text=(
            f"원키스US 젬마 활성화 — ON {out['count_on']}종 "
            f"(퇴역 {len(out['off'])}종 OFF) · 즉시 작업 시작."
        ),
        division=agent_registry.DIVISION_WORKISUS,
    )

    print(f"workisus ON: {out['count_on']} — {', '.join(out['on'][:8])}…")
    if out["off"]:
        print(f"retired OFF: {', '.join(out['off'])}")

    if args.no_run:
        return 0
    return run_worker_once()


if __name__ == "__main__":
    raise SystemExit(main())
