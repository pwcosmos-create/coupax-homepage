"""
사무실 폼 지시 ↔ Cursor(젬마24 채팅) 연동 인박스.

  - 지시 전달·작업 완료 시 cursor_office_inbox.json 갱신
  - CURSOR_OFFICE_INBOX.md 자동 생성 (채팅에서 @ 참조)

  python scripts/agent_office_cursor_bridge.py render
  python scripts/sync_cursor_office_inbox.py pull
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import json_store

BOARD = Path(__file__).resolve().parents[1]
REPO_ROOT = BOARD.parent
INBOX_PATH = BOARD / "data" / "cursor_office_inbox.json"
MARKDOWN_PATH = REPO_ROOT / "CURSOR_OFFICE_INBOX.md"
MAX_ITEMS = 80


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _default_inbox() -> dict:
    return {
        "updated_at": _now(),
        "cursor_sync_hint": "python board/scripts/sync_cursor_office_inbox.py pull",
        "items": [],
    }


def load_inbox() -> dict:
    try:
        data = json_store.load_json(INBOX_PATH, default=_default_inbox())
    except json_store.JsonStoreError:
        return _default_inbox()
    if not isinstance(data, dict):
        return _default_inbox()
    data.setdefault("items", [])
    return data


def save_inbox(data: dict) -> None:
    data["updated_at"] = _now()
    items = data.get("items")
    if isinstance(items, list) and len(items) > MAX_ITEMS:
        data["items"] = items[-MAX_ITEMS:]
    json_store.save_json(INBOX_PATH, data)
    render_markdown(data)


def render_markdown(data: dict | None = None) -> str:
    data = data or load_inbox()
    items = [i for i in (data.get("items") or []) if isinstance(i, dict)]
    pending = [i for i in items if i.get("cursor_status") == "pending"]
    lines = [
        "# Cursor ↔ 젬마24 사무실 인박스",
        "",
        f"갱신: **{data.get('updated_at', '—')}**",
        "",
        "대표님이 [에이전트 사무실](https://coupax.co.kr/agents/office) **지시 전달** 폼에 올린 내용이 여기에 복제됩니다. "
        "Cursor에서 젬마24(이 채팅)가 `cursor_status: pending` 항목을 읽고 처리한 뒤 `done`으로 표시하세요.",
        "",
        f"**대기 중(pending): {len(pending)}건** · 전체 {len(items)}건",
        "",
        f"로컬 동기화: `{data.get('cursor_sync_hint', 'board/scripts/sync_cursor_office_inbox.py pull')}`",
        "",
        "---",
        "",
    ]
    if not items:
        lines.append("_아직 인박스 항목이 없습니다._")
    else:
        for it in reversed(items[-30:]):
            st = it.get("cursor_status") or "pending"
            icon = {"pending": "🔴", "in_progress": "🟡", "done": "✅", "skipped": "⏭️"}.get(
                st, "·"
            )
            lines.append(f"## {icon} {it.get('id', '?')} · {it.get('type', 'event')} · `{st}`")
            lines.append("")
            lines.append(f"- **시각:** {it.get('ts', '—')}")
            if it.get("task_id"):
                lines.append(f"- **작업 #:** {it['task_id']}")
            if it.get("title"):
                lines.append(f"- **제목:** {it['title']}")
            if it.get("assign_to"):
                lines.append(f"- **담당:** {it.get('assign_to')} → {it.get('resolved_to', '')}")
            if it.get("priority"):
                lines.append(f"- **우선순위:** {it['priority']}")
            if it.get("server_status"):
                lines.append(f"- **서버 작업 상태:** {it['server_status']}")
            if it.get("blog_draft_id"):
                lines.append(f"- **블로그 초안:** post #{it['blog_draft_id']}")
            if it.get("wiki_id"):
                lines.append(f"- **Wiki:** {it['wiki_id']}")
            lines.append("")
            lines.append("### 지시/내용")
            lines.append("")
            lines.append((it.get("body") or "").strip() or "_(없음)_")
            if it.get("result_preview"):
                lines.append("")
                lines.append("### 서버 취합 요약")
                lines.append("")
                lines.append(it["result_preview"].strip())
            if it.get("cursor_note"):
                lines.append("")
                lines.append(f"**Cursor 처리 메모:** {it['cursor_note']}")
            lines.append("")
            lines.append("---")
            lines.append("")
    text = "\n".join(lines).rstrip() + "\n"
    MARKDOWN_PATH.write_text(text, encoding="utf-8")
    return text


def _item_id(kind: str, task_id: int) -> str:
    return f"{kind}-{task_id}"


def push_instruction(task: dict) -> dict:
    """폼 지시 전달 직후 — Cursor 인박스에 pending 추가."""
    if os.getenv("AGENT_OFFICE_CURSOR_BRIDGE", "1").strip() not in ("1", "true", "yes"):
        return {}
    tid = int(task.get("id") or 0)
    if not tid:
        return {}
    item = {
        "id": _item_id("ins", tid),
        "type": "instruction",
        "task_id": tid,
        "ts": task.get("ts") or _now(),
        "title": (task.get("title") or "")[:120],
        "body": (task.get("body") or "")[:4000],
        "assign_to": task.get("assign_to") or "all",
        "resolved_to": task.get("resolved_to") or "",
        "priority": task.get("priority") or "normal",
        "source": task.get("source") or "",
        "server_status": task.get("status") or "queued",
        "cursor_status": "pending",
        "cursor_note": "",
    }

    def _mutate(data: dict) -> dict:
        data = data if isinstance(data, dict) else _default_inbox()
        items = [i for i in data.get("items") or [] if isinstance(i, dict)]
        items = [i for i in items if i.get("id") != item["id"]]
        items.append(item)
        data["items"] = items
        return data

    json_store.update_json(INBOX_PATH, default=_default_inbox, mutator=_mutate)
    render_markdown(load_inbox())
    return item


def push_completion(
    task: dict,
    *,
    result: str = "",
    wiki_id: str | None = None,
    blog_draft_id: int | None = None,
) -> dict:
    """서버 작업 완료 후 — Cursor가 후속 작업(코드·발행 등)할 수 있도록 갱신."""
    if os.getenv("AGENT_OFFICE_CURSOR_BRIDGE", "1").strip() not in ("1", "true", "yes"):
        return {}
    tid = int(task.get("id") or 0)
    if not tid:
        return {}
    ins_id = _item_id("ins", tid)
    done_id = _item_id("done", tid)

    def _mutate(data: dict) -> dict:
        data = data if isinstance(data, dict) else _default_inbox()
        items = [i for i in data.get("items") or [] if isinstance(i, dict)]
        updated = False
        for i in items:
            if i.get("id") == ins_id:
                i["server_status"] = "done"
                i["result_preview"] = (result or "")[:2000]
                if wiki_id:
                    i["wiki_id"] = wiki_id
                if blog_draft_id:
                    i["blog_draft_id"] = blog_draft_id
                if i.get("cursor_status") == "pending":
                    i["cursor_status"] = "pending"
                updated = True
        if not updated:
            items.append(
                {
                    "id": ins_id,
                    "type": "instruction",
                    "task_id": tid,
                    "ts": task.get("finished_at") or _now(),
                    "title": (task.get("title") or "")[:120],
                    "body": (task.get("body") or "")[:4000],
                    "server_status": "done",
                    "result_preview": (result or "")[:2000],
                    "wiki_id": wiki_id,
                    "blog_draft_id": blog_draft_id,
                    "cursor_status": "pending",
                }
            )
        items = [i for i in items if i.get("id") != done_id]
        items.append(
            {
                "id": done_id,
                "type": "completion",
                "task_id": tid,
                "ts": _now(),
                "title": (task.get("title") or f"작업 #{tid} 완료")[:120],
                "body": (task.get("body") or "")[:500],
                "server_status": "done",
                "result_preview": (result or "")[:2000],
                "wiki_id": wiki_id,
                "blog_draft_id": blog_draft_id,
                "cursor_status": "pending",
            }
        )
        data["items"] = items
        return data

    json_store.update_json(INBOX_PATH, default=_default_inbox, mutator=_mutate)
    render_markdown(load_inbox())
    return {"instruction_id": ins_id, "completion_id": done_id}


def set_cursor_status(item_id: str, status: str, *, note: str = "") -> bool:
    status = (status or "").strip().lower()
    if status not in ("pending", "in_progress", "done", "skipped"):
        return False

    found = False

    def _mutate(data: dict) -> dict:
        nonlocal found
        for i in data.get("items") or []:
            if isinstance(i, dict) and i.get("id") == item_id:
                i["cursor_status"] = status
                if note:
                    i["cursor_note"] = note[:500]
                i["cursor_updated_at"] = _now()
                found = True
                break
        return data

    json_store.update_json(INBOX_PATH, default=_default_inbox, mutator=_mutate)
    if found:
        render_markdown(load_inbox())
    return found


def list_pending() -> list[dict]:
    return [
        i
        for i in load_inbox().get("items") or []
        if isinstance(i, dict) and i.get("cursor_status") == "pending"
    ]


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["render", "list"])
    args = p.parse_args()
    if args.cmd == "render":
        print(render_markdown()[:200], "...")
    else:
        for it in list_pending():
            print(it.get("id"), it.get("title") or it.get("body", "")[:60])
