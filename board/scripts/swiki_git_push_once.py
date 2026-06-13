#!/usr/bin/env python3
"""Committed swiki repo push (uses SWIKI_GIT_TOKEN from board .env)."""
from __future__ import annotations

import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

try:
    import board_env

    board_env.load_board_env()
except ImportError:
    pass

import agent_office_swiki_sync as s  # noqa: E402

repo = s._repo_path()
branch = s._git_branch()
lock = repo / ".git" / "index.lock"
if lock.is_file():
    lock.unlink(missing_ok=True)
st = s._run_git(["status", "--porcelain"], repo)
if (st.stdout or "").strip():
    s._ensure_git_identity(repo)
    s._run_git(["add", "-A"], repo)
    s._run_git(["commit", "-m", "sync: batch push pending"], repo)
pull = s._run_git(["pull", "--rebase", "origin", branch], repo)
if pull.returncode != 0:
    err = (pull.stderr or pull.stdout or "").lower()
    if "unstaged" in err or "uncommitted" in err:
        s._run_git(["add", "-A"], repo)
        s._run_git(["commit", "-m", "sync: pending before pull"], repo)
        pull = s._run_git(["pull", "--rebase", "origin", branch], repo)
if pull.returncode != 0:
    print("pull failed:", pull.stderr or pull.stdout)
    raise SystemExit(1)
push = s._run_git(["push", "origin", branch], repo)
print("push:", push.returncode, (push.stderr or push.stdout or "ok")[:400])
raise SystemExit(0 if push.returncode == 0 else 1)
