#!/usr/bin/env python3
"""젬마24 답변이 빠진 질문 댓글에 답변 보강."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD) not in sys.path:
    sys.path.insert(0, str(BOARD))

import home_qa_reply  # noqa: E402

GEMMA = home_qa_reply.GEMMA24_AUTHOR
MARKER = "[질문]"


def main() -> int:
    db_path = BOARD / "board.db"
    if not db_path.exists():
        db_path = Path("/home/ubuntu/coupax-homepage/board/board.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    posts = conn.execute(
        "SELECT id, title, content FROM posts WHERE content LIKE ?",
        (MARKER + "%",),
    ).fetchall()
    fixed = 0
    for post in posts:
        comments = conn.execute(
            "SELECT id, author, content FROM comments WHERE post_id=? ORDER BY id",
            (post["id"],),
        ).fetchall()
        import re

        title = post["title"] or ""
        m = re.search(r"\[([^\]]+)\]", title)
        topic = m.group(1) if m else "기타"
        pid = int(post["id"])
        for c in comments:
            if c["author"] == GEMMA:
                continue
            cid = int(c["id"])
            if not home_qa_reply.user_comment_needs_reply(conn, pid, cid):
                continue
            before = conn.execute(
                "SELECT COUNT(*) FROM comments WHERE post_id=? AND author=?",
                (pid, GEMMA),
            ).fetchone()[0]
            home_qa_reply.attach_reply(
                conn,
                pid,
                cid,
                c["author"],
                c["content"],
                title,
                topic,
            )
            after = conn.execute(
                "SELECT COUNT(*) FROM comments WHERE post_id=? AND author=?",
                (pid, GEMMA),
            ).fetchone()[0]
            if after > before:
                fixed += 1
                print(f"post={pid} comment={cid} -> reply added")
    print(f"done fixed={fixed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
