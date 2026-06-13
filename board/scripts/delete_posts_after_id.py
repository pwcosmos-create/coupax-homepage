"""
지정 ID 초과 블로그 글·댓글 삭제.

  python scripts/delete_posts_after_id.py 25
  python scripts/delete_posts_after_id.py 25 --dry-run
"""
from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("BOARD_DB_PATH", str(BOARD / "board.db")))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("max_keep_id", type=int, help="이 ID 이하만 유지 (예: 25)")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    keep = args.max_keep_id

    if not DB_PATH.is_file():
        print(f"DB not found: {DB_PATH}")
        return 1

    with sqlite3.connect(DB_PATH) as conn:
        post_ids = [
            r[0]
            for r in conn.execute(
                "SELECT id FROM posts WHERE id > ? ORDER BY id", (keep,)
            ).fetchall()
        ]
        if not post_ids:
            print(f"삭제할 글이 없습니다 (id > {keep}).")
            return 0

        comment_n = conn.execute(
            f"SELECT COUNT(*) FROM comments WHERE post_id > ?",
            (keep,),
        ).fetchone()[0]

        print(f"유지: id 1~{keep}")
        print(f"삭제 예정: 글 {len(post_ids)}건 (id {post_ids[0]}~{post_ids[-1]}), 댓글 {comment_n}건")

        if args.dry_run:
            for pid in post_ids[:5]:
                row = conn.execute(
                    "SELECT title, created FROM posts WHERE id=?", (pid,)
                ).fetchone()
                print(f"  #{pid} {row}")
            if len(post_ids) > 5:
                print(f"  ... 외 {len(post_ids) - 5}건")
            return 0

        conn.execute("DELETE FROM comments WHERE post_id > ?", (keep,))
        conn.execute("DELETE FROM posts WHERE id > ?", (keep,))
        conn.commit()

        remain = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        print(f"완료. 남은 글 {remain}건 (id <= {keep})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
