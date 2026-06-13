"""월배당 ETF 가이드 글 1편 등록."""
from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
DB = Path(os.environ.get("BOARD_DB_PATH", BOARD / "board.db"))

TITLE = "월배당 ETF 완전 가이드: 분배금·세금·종목 고르는 법 (2026년)"

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from update_post231_content import CONTENT  # noqa: E402


def main() -> int:
    if not DB.is_file():
        print(f"DB not found: {DB}")
        return 1
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    with sqlite3.connect(DB) as conn:
        cur = conn.execute(
            "INSERT INTO posts (title, author, content, password, created, views) VALUES (?,?,?,?,?,0)",
            (TITLE, "머니인사이트", CONTENT, "coupax2026", now),
        )
        conn.commit()
        pid = cur.lastrowid
    print(f"OK post_id={pid} title={TITLE[:50]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
