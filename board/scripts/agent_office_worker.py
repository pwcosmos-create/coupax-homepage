"""
mode_on 에이전트의 주기 작업 실행 (cron용).

  */15 * * * * cd /home/ubuntu/coupax-homepage/board && .venv/bin/python scripts/agent_office_worker.py

환경 변수:
  AGENT_OFFICE_WORKER_ENABLED  기본 1
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
SCRIPTS = BOARD / "scripts"

_WORKISUS_RETIRED = frozenset(
    {"workisus_curator", "workisus_sync", "workisus_atr_rl", "workisus_error_fix"}
)


def _py() -> str:
    venv = BOARD / ".venv" / "bin" / "python"
    return str(venv) if venv.is_file() else sys.executable


def _parse_ts(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def _due(agent: dict, now: datetime, *, force: bool = False) -> bool:
    if force:
        return bool(agent.get("mode_on"))
    if not agent.get("mode_on"):
        return False
    interval = int(agent.get("interval_minutes") if agent.get("interval_minutes") is not None else 120)
    if interval <= 0:
        return True
    last = _parse_ts(agent.get("last_run_at"))
    if last is None:
        return True
    return now >= last + timedelta(minutes=interval)


def _run_job(agent: dict) -> tuple[bool, str]:
    aid = agent.get("id") or "?"

    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import agent_office_jobs
    import agent_office_log
    import agent_registry

    ok, msg = agent_office_jobs.run_job(agent)
    division = agent_registry.division_for_agent_id(aid)
    job = (agent.get("job") or "").strip()
    # 주기 작업마다 피드에 쌓지 않음(대화 로그 과다 방지). 실패·결론만 기록.
    if not ok:
        agent_office_log.append_message(
            from_id=aid, kind="system", text=msg[:1500], division=division
        )
    elif job in (
        "daily_conclusion",
        "saju_daily_conclusion",
        "saju_gap_autofill",
        "kiwoom_daily_conclusion",
        "kiwoom_gap_autofill",
        "kiwoom_rl_train",
        "kiwoom_card_compose",
        "kiwoom_catalog_maintain",
        "kiwoom_wonhero_monitor",
    ):
        agent_office_log.append_message(
            from_id=aid, kind="conclusion", text=msg[:1500], division=division
        )
    elif job == "kiwoom_account_pulse" and division == agent_registry.DIVISION_KIWOM:
        agent_office_log.append_message(
            from_id=aid, kind="task", text=msg[:1500], division=division
        )
    elif job.startswith("stock_") and division == agent_registry.DIVISION_STOCK:
        agent_office_log.append_message(
            from_id=aid, kind="task", text=msg[:1500], division=division
        )
    elif division == agent_registry.DIVISION_WORKISUS:
        kind = "conclusion" if job in ("workisus_wiki_pulse", "workisus_ops_pulse", "workisus_pulse") else "task"
        agent_office_log.append_message(
            from_id=aid, kind=kind, text=msg[:1500], division=division
        )
    elif division == agent_registry.DIVISION_GWANSANG:
        kind = "conclusion" if job in (
            "gwansang_pack_sync",
            "gwansang_card_compose",
            "gwansang_catalog_maintain",
            "gwansang_gap_autofill",
            "gwansang_daily_conclusion",
            "gwansang_wiki_sync",
        ) else "task"
        agent_office_log.append_message(
            from_id=aid, kind=kind, text=msg[:1500], division=division
        )
    return ok, msg


def main() -> int:
    import board_env

    board_env.load_board_env()
    if os.getenv("AGENT_OFFICE_WORKER_ENABLED", "1").strip() not in ("1", "true", "yes"):
        print("[worker] disabled")
        return 0

    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import agent_registry

    data = agent_registry.load_registry()
    now = datetime.now()
    ran = 0
    force = os.getenv("AGENT_OFFICE_FORCE_RUN", "").strip() in ("1", "true", "yes")

    workisus_only = os.getenv("AGENT_OFFICE_WORKISUS_ONLY", "").strip() in ("1", "true", "yes")
    gwansang_only = os.getenv("AGENT_OFFICE_GWANSANG_ONLY", "").strip() in ("1", "true", "yes")
    division_only = workisus_only or gwansang_only

    if agent_registry.is_office_active(data) and not division_only:
        for a in data.get("agents") or []:
            if isinstance(a, dict):
                a["mode_on"] = True

    for agent in data.get("agents") or []:
        if not isinstance(agent, dict) or not _due(agent, now, force=force):
            continue
        aid_check = (agent.get("id") or "").strip()
        if workisus_only:
            if agent_registry.agent_division(agent) != agent_registry.DIVISION_WORKISUS:
                continue
            if aid_check in _WORKISUS_RETIRED or not agent.get("mode_on"):
                continue
        elif gwansang_only:
            if agent_registry.agent_division(agent) != agent_registry.DIVISION_GWANSANG:
                continue
            if not agent.get("mode_on"):
                continue
        aid = agent.get("id") or "?"
        print(f"[worker] run {aid} job={agent.get('job')}", flush=True)
        try:
            ok, status = _run_job(agent)
            agent_registry.update_agent_run(aid, "ok" if ok else "error")
            ran += 1
            print(f"[worker] {aid} -> {status}", flush=True)
        except Exception as e:
            agent_registry.update_agent_run(aid, f"err:{e!s}"[:40])
            print(f"[worker] {aid} error: {e}", flush=True)

    try:
        import agent_office_task_runner

        tasks_done = agent_office_task_runner.process_queued_tasks(max_tasks=4)
        if tasks_done:
            print(f"[worker] tasks processed={tasks_done}", flush=True)
    except Exception as e:
        print(f"[worker] task_runner error: {e}", flush=True)

    try:
        import agent_office_saju_card_council

        if agent_office_saju_card_council.use_card_council():
            cyc = agent_office_saju_card_council.tick_cycle()
            if cyc.get("processed"):
                print(
                    f"[worker] saju council n={cyc.get('processed')} "
                    f"pass={cyc.get('tick_pass')} fail={cyc.get('tick_fail')}",
                    flush=True,
                )
    except Exception as e:
        print(f"[worker] saju council cycle error: {e}", flush=True)

    try:
        import agent_office_swiki_sync

        if agent_office_swiki_sync._enabled():
            n = agent_office_swiki_sync.sync_pending()
            if n:
                print(f"[worker] swiki pushed={n}", flush=True)
    except Exception as e:
        print(f"[worker] swiki sync error: {e}", flush=True)

    print(f"[worker] done ran={ran}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
