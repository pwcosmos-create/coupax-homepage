"""
사무실 작업지시 큐 (agent_office_tasks.json).

  python scripts/agent_office_tasks.py add --to researcher --text "오늘 금리 이슈 조사"
  python scripts/agent_office_tasks.py list
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import json_store

BOARD = Path(__file__).resolve().parents[1]
TASKS_PATH = BOARD / "data" / "agent_office_tasks.json"
MAX_TASKS = 200


def _default_tasks() -> dict:
    return {"tasks": []}


def _normalize_tasks(data: dict) -> dict:
    if not isinstance(data, dict):
        return _default_tasks()
    tasks = data.get("tasks")
    data["tasks"] = tasks if isinstance(tasks, list) else []
    return data


def load_tasks() -> dict:
    try:
        data = json_store.load_json(TASKS_PATH, default=_default_tasks())
    except json_store.JsonStoreError:
        return _default_tasks()
    return _normalize_tasks(data)


def save_tasks(data: dict) -> None:
    data = _normalize_tasks(data)
    tasks = data.get("tasks")
    if isinstance(tasks, list) and len(tasks) > MAX_TASKS:
        data["tasks"] = tasks[-MAX_TASKS:]
    json_store.save_json(TASKS_PATH, data)


def add_task(
    *,
    body: str,
    assign_to: str = "all",
    priority: str = "normal",
    title: str = "",
    created_by: str = "대표님",
    source: str = "",
    quiet: bool = False,
    division: str = "finance",
) -> dict:
    body = (body or "").strip()
    if not body:
        raise ValueError("body is required")
    assign_to = (assign_to or "all").strip() or "all"
    priority = (priority or "normal").strip().lower()
    if priority not in ("normal", "high"):
        priority = "normal"

    try:
        import agent_office_research

        resolved = agent_office_research.pick_agent_for_instruction(
            body, assign_to, division=(division or "finance").strip()
        )
    except Exception:
        resolved = (
            assign_to
            if assign_to != "all"
            else ("saju_reader" if (division or "").strip() == "saju-learn" else "researcher")
        )

    row_holder: dict = {}

    def _mutate(data: dict) -> dict:
        data = _normalize_tasks(data)
        tasks = data["tasks"]
        next_id = 1
        for t in tasks:
            if isinstance(t, dict) and isinstance(t.get("id"), int):
                next_id = max(next_id, t["id"] + 1)
        row = {
            "id": next_id,
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "title": (title or "").strip()[:120],
            "body": body[:4000],
            "assign_to": assign_to,
            "resolved_to": resolved,
            "priority": priority,
            "status": "queued",
            "created_by": created_by[:40],
            "division": (division or "finance").strip(),
        }
        if source:
            row["source"] = source
        tasks.append(row)
        row_holder["row"] = row
        return data

    try:
        json_store.update_json(TASKS_PATH, default=_default_tasks, mutator=_mutate)
    except json_store.JsonStoreError:
        data = load_tasks()
        _mutate(data)
        save_tasks(data)

    row = row_holder.get("row", {})

    if row:
        try:
            import agent_office_cursor_bridge

            agent_office_cursor_bridge.push_instruction(row)
        except Exception:
            pass

    if not quiet and row:
        try:
            import agent_office_log
            import agent_office_research

            target = agent_office_research.agent_display(row.get("resolved_to", resolved))
            div = (row.get("division") or "finance").strip()
            if source in ("council_saju", "council_finance"):
                prefix = "위원회"
                from_id = "saju_rl" if source == "council_saju" else "rl"
                log_div = "saju-learn" if source == "council_saju" else "finance"
            elif source == "reserved_saju" or div == "saju-learn":
                prefix = "명리예약"
                from_id = "saju_rl"
                log_div = "saju-learn"
            elif source == "reserved":
                prefix = "예약"
                from_id = "rl"
                log_div = "finance"
            else:
                prefix = "작업지시"
                from_id = "ceo"
                log_div = div
            agent_office_log.append_message(
                from_id=from_id,
                to_id=row.get("resolved_to"),
                kind="task",
                text=f"[{prefix} #{row.get('id')} → {target}] {body[:500]}",
                division=log_div,
            )
        except Exception:
            pass

    return row


def find_task(task_id: int) -> dict | None:
    for t in load_tasks().get("tasks") or []:
        if isinstance(t, dict) and t.get("id") == task_id:
            return t
    return None


def update_task(task_id: int, **fields) -> dict | None:
    found: dict = {}

    def _mutate(data: dict) -> dict:
        data = _normalize_tasks(data)
        for t in data.get("tasks") or []:
            if isinstance(t, dict) and t.get("id") == task_id:
                for k, v in fields.items():
                    if v is not None:
                        t[k] = v
                found["row"] = t
                break
        return data

    try:
        json_store.update_json(TASKS_PATH, default=_default_tasks, mutator=_mutate)
    except json_store.JsonStoreError:
        data = load_tasks()
        _mutate(data)
        save_tasks(data)
    return found.get("row")


def list_queued_tasks() -> list[dict]:
    out = []
    for t in load_tasks().get("tasks") or []:
        if isinstance(t, dict) and (t.get("status") or "queued") == "queued":
            out.append(t)
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--to", default="all")
    a.add_argument("--text", required=True)
    a.add_argument("--priority", default="normal", choices=["normal", "high"])
    a.add_argument("--title", default="")

    sub.add_parser("list")
    sub.add_parser("process")
    er = sub.add_parser("ensure-reserved")
    er.add_argument("--target", type=int, default=3)
    es = sub.add_parser("ensure-reserved-saju")
    es.add_argument("--target", type=int, default=3)
    ecd = sub.add_parser("ensure-reserved-chief-dev")
    ecd.add_argument("--target", type=int, default=3)

    args = p.parse_args()
    if args.cmd == "add":
        row = add_task(
            body=args.text,
            assign_to=args.to,
            priority=args.priority,
            title=args.title,
        )
        print(json.dumps(row, ensure_ascii=False))
        return 0
    if args.cmd == "list":
        for t in load_tasks().get("tasks") or []:
            print(f"#{t.get('id')} [{t.get('status')}] -> {t.get('assign_to')}: {t.get('body', '')[:80]}")
        return 0
    if args.cmd == "process":
        import agent_office_task_runner

        n = agent_office_task_runner.process_queued_tasks()
        print(f"processed={n}")
        return 0
    if args.cmd == "ensure-reserved":
        import agent_office_reserved_tasks

        n = agent_office_reserved_tasks.ensure_reserved_queue(args.target)
        print(f"added={n} queued={agent_office_reserved_tasks.count_reserved_queued()}")
        return 0
    if args.cmd == "ensure-reserved-saju":
        import agent_office_saju_reserved_tasks

        n = agent_office_saju_reserved_tasks.ensure_reserved_queue(args.target)
        print(f"added={n} queued={agent_office_saju_reserved_tasks.count_reserved_queued()}")
        return 0
    if args.cmd == "ensure-reserved-chief-dev":
        import agent_office_chief_dev_reserved_tasks

        n = agent_office_chief_dev_reserved_tasks.ensure_reserved_queue(args.target)
        print(f"added={n} queued={agent_office_chief_dev_reserved_tasks.count_reserved_queued()}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
