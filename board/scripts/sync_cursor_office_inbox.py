"""
서버 ↔ 로컬 Cursor 인박스 동기화.

  pull  — 서버 inbox JSON·MD를 워크스페이스로 가져옴 (SSH)
  push-done — 로컬에서 처리 완료 표시 후 서버에 반영

  python board/scripts/sync_cursor_office_inbox.py pull
  python board/scripts/sync_cursor_office_inbox.py push-done --id ins-35 --note "배포 완료"
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
REPO = BOARD.parent
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

DEFAULT_SERVER = os.getenv("COUPAX_SSH_HOST", "ubuntu@168.107.31.153")
DEFAULT_KEY = os.path.expanduser(os.getenv("COUPAX_SSH_KEY", "~/.ssh/shinserver.key"))
REMOTE_BOARD = os.getenv("COUPAX_REMOTE_BOARD", "/home/ubuntu/coupax-homepage/board")
REMOTE_INBOX = f"{REMOTE_BOARD}/data/cursor_office_inbox.json"
LOCAL_INBOX = BOARD / "data" / "cursor_office_inbox.json"
LOCAL_MD = REPO / "CURSOR_OFFICE_INBOX.md"


def _scp_pull() -> int:
    key = ["-i", DEFAULT_KEY] if Path(DEFAULT_KEY).expanduser().is_file() else []
    LOCAL_INBOX.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["scp", *key, "-o", "StrictHostKeyChecking=accept-new", f"{DEFAULT_SERVER}:{REMOTE_INBOX}", str(LOCAL_INBOX)],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0 and "No such file" in (r.stderr or ""):
        print("[pull] remote inbox missing - empty local created")
        LOCAL_INBOX.write_text(
            json.dumps({"updated_at": "", "items": []}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    elif r.returncode != 0:
        print(r.stderr or r.stdout)
        return r.returncode
    import agent_office_cursor_bridge as bridge

    bridge.INBOX_PATH = LOCAL_INBOX
    bridge.MARKDOWN_PATH = LOCAL_MD
    bridge.render_markdown()
    print(f"OK pull -> {LOCAL_INBOX}")
    print(f"OK markdown -> {LOCAL_MD}")
    pending = bridge.list_pending()
    print(f"pending for Cursor: {len(pending)}")
    for it in pending[:5]:
        print(f"  - {it.get('id')}: {(it.get('title') or it.get('body') or '')[:50]}")
    return 0


def _scp_push_status(item_id: str, status: str, note: str) -> int:
    import agent_office_cursor_bridge as bridge

    bridge.INBOX_PATH = LOCAL_INBOX
    bridge.MARKDOWN_PATH = LOCAL_MD
    if LOCAL_INBOX.is_file():
        ok = bridge.set_cursor_status(item_id, status, note=note)
        if not ok:
            print(f"missing local item: {item_id}")
            return 1
    else:
        print("run pull first")
        return 1

    key = ["-i", DEFAULT_KEY] if Path(DEFAULT_KEY).expanduser().is_file() else []
    r = subprocess.run(
        ["scp", *key, "-o", "StrictHostKeyChecking=accept-new", str(LOCAL_INBOX), f"{DEFAULT_SERVER}:{REMOTE_INBOX}"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(r.stderr or r.stdout)
        return r.returncode
    r2 = subprocess.run(
        [
            "ssh",
            *key,
            "-o",
            "StrictHostKeyChecking=accept-new",
            DEFAULT_SERVER,
            f"cd {REMOTE_BOARD} && .venv/bin/python scripts/agent_office_cursor_bridge.py render",
        ],
        capture_output=True,
        text=True,
    )
    print(f"OK {item_id} -> {status}")
    return r2.returncode


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pull")
    pd = sub.add_parser("push-done")
    pd.add_argument("--id", required=True, help="ins-35 or done-35")
    pd.add_argument("--note", default="")
    pi = sub.add_parser("push-progress")
    pi.add_argument("--id", required=True)
    pi.add_argument("--note", default="")

    args = p.parse_args()
    if args.cmd == "pull":
        return _scp_pull()
    if args.cmd == "push-done":
        return _scp_push_status(args.id, "done", args.note)
    if args.cmd == "push-progress":
        return _scp_push_status(args.id, "in_progress", args.note)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
