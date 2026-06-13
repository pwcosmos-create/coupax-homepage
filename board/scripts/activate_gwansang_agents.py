#!/usr/bin/env python3
"""관상 학습 젬마 활성화 + 카탈로그 시드 + 1회 작업."""
from __future__ import annotations

import os
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_log
import agent_registry


def main() -> int:
    import board_env

    board_env.load_board_env()
    data = agent_registry.load_registry()
    on: list[str] = []
    for a in data.get("agents") or []:
        if not isinstance(a, dict):
            continue
        if agent_registry.agent_division(a) != "gwansang-learn":
            continue
        a["mode_on"] = True
        a["last_run_at"] = None
        a["interval_minutes"] = 0
        a["interval_label"] = "항상"
        on.append(a.get("id") or "")
    agent_registry.save_registry(data)

    import seed_gwansang_cards as sg

    seed_out = sg.seed_all(sync=True, confirm=True)

    os.environ["AGENT_OFFICE_WORKER_ENABLED"] = "1"
    os.environ["AGENT_OFFICE_FORCE_RUN"] = "1"
    os.environ["AGENT_OFFICE_GWANSANG_ONLY"] = "1"
    import agent_office_worker

    agent_office_log.append_message(
        from_id="gwansang_curator",
        kind="system",
        text=f"관상 학습 젬마 활성화 — ON {len(on)}종 · 시드 +{seed_out.get('added', 0)}",
        division="gwansang-learn",
    )
    print(f"gwansang ON: {len(on)}", seed_out)
    return agent_office_worker.main()


if __name__ == "__main__":
    raise SystemExit(main())
