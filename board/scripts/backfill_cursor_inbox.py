"""최근 완료/대기 작업을 Cursor 인박스에 한 번 채움 (서버에서 실행)."""
from __future__ import annotations

import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_cursor_bridge as bridge
import agent_office_tasks

tasks = agent_office_tasks.load_tasks().get("tasks") or []
n = 0
for t in sorted(tasks, key=lambda x: x.get("id") or 0)[-20:]:
    if not isinstance(t, dict):
        continue
    bridge.push_instruction(t)
    if t.get("status") == "done" and t.get("result"):
        bridge.push_completion(
            t,
            result=t.get("result") or "",
            wiki_id=t.get("wiki_id"),
            blog_draft_id=t.get("blog_draft_id"),
        )
    n += 1
print(f"backfill tasks={n} pending={len(bridge.list_pending())}")
