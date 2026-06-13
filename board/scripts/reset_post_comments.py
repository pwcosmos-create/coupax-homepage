"""
특정 글의 댓글을 전부 지우고 지정 댓글 1개만 남깁니다.

  python scripts/reset_post_comments.py 23 --author 코드노트 --file comment.txt
"""
from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("BOARD_DB_PATH", str(BOARD / "board.db")))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("post_id", type=int)
    p.add_argument("--author", default="코드노트")
    p.add_argument("--text-file", required=True, help="댓글 본문 UTF-8 파일")
    p.add_argument("--password", default="")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    text = Path(args.text_file).read_text(encoding="utf-8").strip()
    if not text:
        print("댓글 본문이 비어 있습니다.")
        return 1

    if not DB_PATH.is_file():
        print(f"DB not found: {DB_PATH}")
        return 1

    with sqlite3.connect(DB_PATH) as conn:
        post = conn.execute(
            "SELECT id, title FROM posts WHERE id=?", (args.post_id,)
        ).fetchone()
        if not post:
            print(f"글 #{args.post_id} 없음")
            return 1

        before = conn.execute(
            "SELECT COUNT(*) FROM comments WHERE post_id=?", (args.post_id,)
        ).fetchone()[0]
        print(f"글 #{args.post_id} ({post[1][:50]}) — 기존 댓글 {before}건")

        if args.dry_run:
            print(f"삭제 후 1건 등록: author={args.author}, len={len(text)}")
            return 0

        conn.execute("DELETE FROM comments WHERE post_id=?", (args.post_id,))
        conn.execute(
            "INSERT INTO comments (post_id, author, content, password, created) VALUES (?,?,?,?,?)",
            (
                args.post_id,
                args.author,
                text,
                args.password,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ),
        )
        conn.commit()
        after = conn.execute(
            "SELECT COUNT(*) FROM comments WHERE post_id=?", (args.post_id,)
        ).fetchone()[0]
        print(f"완료. 댓글 {after}건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
