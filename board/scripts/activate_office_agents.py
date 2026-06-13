"""
사무실 전체 에이전트 활성화 + 1회 즉시 가동.

  python scripts/activate_office_agents.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_log
import agent_registry


def main() -> int:
    data = agent_registry.activate_all_agents()
    for a in data.get("agents") or []:
        if isinstance(a, dict):
            a["last_run_at"] = None
    agent_registry.save_registry(data)

    agent_office_log.append_message(
        from_id="ceo",
        kind="system",
        text="전체 에이전트 활성화 — office_always_on ON, 주기 작업 1회 실행.",
    )
    feed = agent_office_log.load_feed()
    feed["updated_at"] = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")
    agent_office_log.save_feed(feed)

    os.environ["AGENT_OFFICE_WORKER_ENABLED"] = "1"
    os.environ["AGENT_OFFICE_FORCE_RUN"] = "1"
    os.environ["AGENT_OFFICE_ACTIVATE_LIGHT"] = "1"

    import agent_office_worker

    return agent_office_worker.main()


if __name__ == "__main__":
    raise SystemExit(main())
