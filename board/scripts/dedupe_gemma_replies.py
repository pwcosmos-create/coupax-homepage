#!/usr/bin/env python3
"""질문 글에서 연속·중복 젬마24 답변 댓글 삭제 (사용자 댓글당 1개 유지)."""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]

GEMMA = os.environ.get("HOME_QA_REPLY_AUTHOR", "젬마24").strip() or "젬마24"
MARKER = "[질문]"


def _db_path() -> Path:
    p = os.environ.get("BOARD_DB_PATH", "").strip()
    if p:
        return Path(p)
    return BOARD / "board.db"


def find_duplicate_gemma_ids(comments: list[sqlite3.Row]) -> list[int]:
    """사용자 댓글 직후 연속된 젬마24 답변 중 첫 번째만 남기고 나머지 id."""
    delete_ids: list[int] = []
    i = 0
    n = len(comments)
    while i < n:
        row = comments[i]
        if row["author"] == GEMMA:
            j = i + 1
            while j < n and comments[j]["author"] == GEMMA:
                delete_ids.append(int(comments[j]["id"]))
                j += 1
            i = j
            continue
        j = i + 1
        gemma_ids: list[int] = []
        while j < n and comments[j]["author"] == GEMMA:
            gemma_ids.append(int(comments[j]["id"]))
            j += 1
        if len(gemma_ids) > 1:
            delete_ids.extend(gemma_ids[1:])
        i += 1
    return delete_ids


def run(*, dry_run: bool = True, post_id: int | None = None) -> int:
    db_path = _db_path()
    if not db_path.is_file():
        print(f"DB not found: {db_path}")
        return 1

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    if post_id:
        posts = conn.execute(
            "SELECT id, title FROM posts WHERE id = ?", (post_id,)
        ).fetchall()
    else:
        posts = conn.execute(
            "SELECT id, title FROM posts WHERE content LIKE ? ORDER BY id DESC",
            (MARKER + "%",),
        ).fetchall()

    total = 0
    for post in posts:
        pid = int(post["id"])
        comments = conn.execute(
            "SELECT id, author, content, created FROM comments WHERE post_id=? ORDER BY id",
            (pid,),
        ).fetchall()
        dup_ids = list(dict.fromkeys(find_duplicate_gemma_ids(comments)))
        if not dup_ids:
            continue
        title = (post["title"] or "")[:50]
        print(f"post #{pid} {title!r}: delete {len(dup_ids)} gemma comment(s) {dup_ids}")
        for cid in dup_ids:
            c = conn.execute(
                "SELECT content FROM comments WHERE id=?", (cid,)
            ).fetchone()
            preview = (c["content"] or "")[:80].replace("\n", " ") if c else ""
            print(f"  - #{cid} {preview!r}")
        if not dry_run:
            for cid in dup_ids:
                conn.execute(
                    "DELETE FROM bot_comment_replies WHERE reply_comment_id=? OR source_comment_id=?",
                    (cid, cid),
                )
                conn.execute("DELETE FROM comments WHERE id=?", (cid,))
            total += len(dup_ids)

    if not dry_run:
        conn.commit()
    print(f"{'deleted' if not dry_run else 'would_delete'}={total}")
    conn.close()
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true", help="실제 삭제 (없으면 dry-run)")
    p.add_argument("--post-id", type=int, default=0, help="특정 글만")
    args = p.parse_args()
    return run(dry_run=not args.apply, post_id=args.post_id or None)


if __name__ == "__main__":
    raise SystemExit(main())
