"""
에이전트 사무실 피드(agent_office_feed.json)에 메시지를 추가합니다.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import json_store

BOARD = Path(__file__).resolve().parents[1]
FEED_PATH = BOARD / "data" / "agent_office_feed.json"
MAX_MESSAGES = 300

KIND_LABELS = {
    "chat": "잡담",
    "task": "작업",
    "handoff": "핸드오프",
    "debate": "토론",
    "system": "시스템",
    "conclusion": "결론",
}


def _default_feed() -> dict:
    return {
        "office_name": "젬마24 에이전트 사무실",
        "description": "",
        "updated_at": "",
        "agents": [],
        "messages": [],
    }


def _normalize_feed(data: dict) -> dict:
    if not isinstance(data, dict):
        return _default_feed()
    data.setdefault("agents", [])
    data.setdefault("messages", [])
    if not isinstance(data["messages"], list):
        data["messages"] = []
    return data


def load_feed() -> dict:
    try:
        data = json_store.load_json(FEED_PATH, default=_default_feed())
    except json_store.JsonStoreError:
        return _default_feed()
    return _normalize_feed(data)


def save_feed(data: dict) -> None:
    data = _normalize_feed(data)
    messages = data.get("messages")
    if isinstance(messages, list) and len(messages) > MAX_MESSAGES:
        data["messages"] = messages[-MAX_MESSAGES:]
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    json_store.save_json(FEED_PATH, data)


def append_message(
    *,
    from_id: str,
    text: str,
    kind: str = "task",
    to_id: str | None = None,
    division: str | None = None,
) -> dict:
    if kind not in KIND_LABELS:
        kind = "task"
    text = (text or "").strip()
    if not text:
        raise ValueError("text is required")
    from_id = (from_id or "").strip()
    if not from_id:
        raise ValueError("from_id is required")

    if not division:
        try:
            import agent_registry

            division = agent_registry.division_for_agent_id(from_id)
            if to_id and division == agent_registry.DIVISION_FINANCE:
                to_div = agent_registry.division_for_agent_id(to_id)
                if to_div != agent_registry.DIVISION_FINANCE:
                    division = to_div
        except Exception:
            division = "finance"

    out: dict = {}

    def _mutate(data: dict) -> dict:
        data = _normalize_feed(data)
        messages = data["messages"]
        next_id = 1
        for m in messages:
            if isinstance(m, dict) and isinstance(m.get("id"), int):
                next_id = max(next_id, m["id"] + 1)
        row = {
            "id": next_id,
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "from": from_id,
            "to": to_id,
            "kind": kind,
            "text": text[:2000],
            "division": (division or "finance").strip(),
        }
        messages.append(row)
        data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        out["row"] = row
        return data

    try:
        json_store.update_json(FEED_PATH, default=_default_feed, mutator=_mutate)
    except json_store.JsonStoreError:
        data = load_feed()
        _mutate(data)
        save_feed(data)
    return out.get("row", {})


def main() -> int:
    p = argparse.ArgumentParser(description="Append a message to agent office feed")
    p.add_argument("--from", dest="from_id", required=True)
    p.add_argument("--to", dest="to_id", default=None)
    p.add_argument("--kind", default="task", choices=list(KIND_LABELS.keys()))
    p.add_argument("--text", required=True)
    args = p.parse_args()
    row = append_message(
        from_id=args.from_id,
        to_id=args.to_id,
        kind=args.kind,
        text=args.text,
    )
    print(json.dumps(row, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
