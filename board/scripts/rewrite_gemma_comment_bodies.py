#!/usr/bin/env python3
"""젬마24 댓글 재작성 — refresh_all_gemma_replies.py 로 대체됨."""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD) not in sys.path:
    sys.path.insert(0, str(BOARD))

import home_qa_reply  # noqa: E402
import gemma24_local  # noqa: E402

GEMMA = home_qa_reply.GEMMA24_AUTHOR
_BAD = re.compile(
    r"지식망을 바탕으로|월배당 ETF \d+건|동기화 전문|메타 카드|사서 젬마|⚙️|✓ ETF 데이터",
    re.I,
)


def main() -> int:
    db_path = BOARD / "board.db"
    if not db_path.exists():
        db_path = Path("/home/ubuntu/coupax-homepage/board/board.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT c.id, c.post_id, c.content, p.title "
        "FROM comments c JOIN posts p ON p.id=c.post_id "
        "WHERE c.author=? AND p.content LIKE '[질문]%' ORDER BY c.id",
        (GEMMA,),
    ).fetchall()
    n = 0
    for r in rows:
        body = r["content"] or ""
        if not _BAD.search(body):
            continue
        # 질문 댓글(바로 앞 사용자 댓글) 찾기
        prev = conn.execute(
            "SELECT author, content FROM comments WHERE post_id=? AND id < ? AND author != ? ORDER BY id DESC LIMIT 1",
            (r["post_id"], r["id"], GEMMA),
        ).fetchone()
        if not prev:
            continue
        import re as _re

        title = r["title"] or ""
        m = _re.search(r"\[([^\]]+)\]", title)
        topic = m.group(1) if m else "기타"
        new_body = home_qa_reply.build_reply(
            prev["author"], prev["content"], title, topic
        )
        conn.execute(
            "UPDATE comments SET content=? WHERE id=?",
            (new_body, r["id"]),
        )
        n += 1
        print(f"rewrote comment {r['id']} post={r['post_id']}")
    conn.commit()
    print(f"done rewritten={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
