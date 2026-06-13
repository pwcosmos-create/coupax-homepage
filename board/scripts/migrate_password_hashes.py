"""
기존 posts·comments 평문 비밀번호를 pbkdf2 해시로 일괄 변환.

  cd board
  python scripts/migrate_password_hashes.py
  python scripts/migrate_password_hashes.py --dry-run
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD) not in sys.path:
    sys.path.insert(0, str(BOARD))

import security_utils  # noqa: E402

DB_PATH = Path(__import__("os").environ.get("BOARD_DB_PATH", str(BOARD / "board.db")))


def migrate_table(conn: sqlite3.Connection, table: str, dry_run: bool) -> int:
    n = 0
    rows = conn.execute(f"SELECT id, password FROM {table}").fetchall()
    for row_id, stored in rows:
        if security_utils.is_password_hash(stored):
            continue
        if not stored:
            continue
        n += 1
        if dry_run:
            print(f"  [dry-run] {table}#{row_id} -> hash")
            continue
        conn.execute(
            f"UPDATE {table} SET password=? WHERE id=?",
            (security_utils.hash_password(stored), row_id),
        )
    return n


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not DB_PATH.is_file():
        print(f"DB not found: {DB_PATH}", file=sys.stderr)
        return 1
    conn = sqlite3.connect(DB_PATH)
    try:
        posts = migrate_table(conn, "posts", args.dry_run)
        comments = migrate_table(conn, "comments", args.dry_run)
        if not args.dry_run:
            conn.commit()
        print(f"posts: {posts} · comments: {comments} migrated")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
