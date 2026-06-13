#!/usr/bin/env python3
"""
질문 글의 젬마24 답변 전체를 최신 build_reply 로직으로 재작성.

  python scripts/refresh_all_gemma_replies.py
  python scripts/refresh_all_gemma_replies.py --dry-run
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD) not in sys.path:
    sys.path.insert(0, str(BOARD))

import home_qa_reply  # noqa: E402

GEMMA = home_qa_reply.GEMMA24_AUTHOR
MARKER = "[질문]"


def _db_path() -> Path:
    p = BOARD / "board.db"
    if p.is_file():
        return p
    return Path("/home/ubuntu/coupax-homepage/board/board.db")


def _topic_from_title(title: str) -> str:
    m = re.search(r"\[([^\]]+)\]", title or "")
    return m.group(1) if m else "기타"


def _question_from_post(post: sqlite3.Row) -> tuple[str, str] | None:
    """홈 질문 글 본문에서 질문자·질문 텍스트 추출."""
    content = post["content"] or ""
    if not content.startswith(MARKER):
        return None
    author = (post["author"] or "").strip() or "질문자"
    m = re.search(
        r'question-post-text">([^<]+)</p>',
        content,
        re.I,
    )
    if m:
        return author, m.group(1).strip()
    m2 = re.search(r"\[([^\]]+)\]\s*(.+)", content.replace(MARKER, "", 1).strip())
    if m2:
        return author, m2.group(2).strip()[:500]
    return author, (post["title"] or "").replace("Q.", "").strip()


def _source_question(
    conn: sqlite3.Connection, post_id: int, gemma_id: int
) -> tuple[str, str] | None:
    prev = conn.execute(
        "SELECT author, content FROM comments "
        "WHERE post_id=? AND id < ? AND author != ? ORDER BY id DESC LIMIT 1",
        (post_id, gemma_id, GEMMA),
    ).fetchone()
    if prev:
        return prev["author"], prev["content"]
    first = conn.execute(
        "SELECT author, content FROM comments "
        "WHERE post_id=? AND author != ? ORDER BY id LIMIT 1",
        (post_id, GEMMA),
    ).fetchone()
    if first:
        return first["author"], first["content"]
    post = conn.execute(
        "SELECT title, author, content FROM posts WHERE id=?", (post_id,)
    ).fetchone()
    if post:
        return _question_from_post(post)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT c.id, c.post_id, c.content, p.title "
        "FROM comments c JOIN posts p ON p.id = c.post_id "
        "WHERE c.author=? AND p.content LIKE ? ORDER BY c.id",
        (GEMMA, MARKER + "%"),
    ).fetchall()

    updated = 0
    skipped = 0
    for r in rows:
        src = _source_question(conn, int(r["post_id"]), int(r["id"]))
        if not src:
            skipped += 1
            print(f"skip #{r['id']} post={r['post_id']} (no source question)")
            continue
        author, qtext = src
        title = r["title"] or ""
        topic = _topic_from_title(title)
        new_body = home_qa_reply.build_reply(author, qtext, title, topic)
        old = (r["content"] or "").strip()
        if old == new_body.strip():
            skipped += 1
            continue
        if args.dry_run:
            print(f"would update #{r['id']} post={r['post_id']} len {len(old)} -> {len(new_body)}")
            updated += 1
            continue
        conn.execute(
            "UPDATE comments SET content=? WHERE id=?",
            (new_body, r["id"]),
        )
        updated += 1
        print(f"updated #{r['id']} post={r['post_id']}")

    if not args.dry_run:
        conn.commit()
        added = 0
        posts = conn.execute(
            "SELECT id, title, content FROM posts WHERE content LIKE ?",
            (MARKER + "%",),
        ).fetchall()
        for post in posts:
            comments = conn.execute(
                "SELECT id, author, content FROM comments WHERE post_id=? ORDER BY id",
                (post["id"],),
            ).fetchall()
            for i, c in enumerate(comments):
                if c["author"] == GEMMA:
                    continue
                nxt = comments[i + 1] if i + 1 < len(comments) else None
                if nxt and nxt["author"] == GEMMA:
                    continue
                topic = _topic_from_title(post["title"] or "")
                home_qa_reply.attach_reply(
                    conn,
                    int(post["id"]),
                    int(c["id"]),
                    c["author"],
                    c["content"],
                    post["title"] or "",
                    topic,
                )
                added += 1
                print(f"backfill post={post['id']} comment={c['id']}")
        if added:
            conn.commit()
        print(f"backfill_added={added}")

    print(f"done updated={updated} skipped={skipped} total_gemma={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
