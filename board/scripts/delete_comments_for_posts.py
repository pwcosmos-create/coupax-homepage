"""지정 글 ID 구간의 댓글 전부 삭제."""
from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path

DB = Path(os.environ.get("BOARD_DB_PATH", Path(__file__).resolve().parents[1] / "board.db"))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("from_id", type=int)
    p.add_argument("to_id", type=int)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    lo, hi = min(args.from_id, args.to_id), max(args.from_id, args.to_id)

    with sqlite3.connect(DB) as conn:
        n = conn.execute(
            "SELECT COUNT(*) FROM comments WHERE post_id BETWEEN ? AND ?",
            (lo, hi),
        ).fetchone()[0]
        by_post = conn.execute(
            """
            SELECT post_id, COUNT(*) FROM comments
            WHERE post_id BETWEEN ? AND ?
            GROUP BY post_id ORDER BY post_id
            """,
            (lo, hi),
        ).fetchall()
        print(f"글 #{lo}~#{hi} 댓글 {n}건")
        for pid, c in by_post:
            print(f"  글#{pid}: {c}건")

        if args.dry_run:
            return 0

        conn.execute(
            "DELETE FROM comments WHERE post_id BETWEEN ? AND ?",
            (lo, hi),
        )
        conn.commit()
        left = conn.execute(
            "SELECT COUNT(*) FROM comments WHERE post_id BETWEEN ? AND ?",
            (lo, hi),
        ).fetchone()[0]
        print(f"완료. 남은 댓글 {left}건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
