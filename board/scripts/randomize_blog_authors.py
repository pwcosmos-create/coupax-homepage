"""모든 글 작성자를 ID 기준 필명으로 DB 반영."""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
DB = Path(os.environ.get("BOARD_DB_PATH", BOARD / "board.db"))

BLOG_PEN_NAMES = (
    "재테크왈라", "머니로드", "절세메이트", "ETF살펴보기", "배당플로우",
    "연금탐구", "청약체크", "금융한줄", "투자습관", "현금흐름랩",
    "코드노트", "살림손익", "자산지도", "월급쪼개기", "복리메모",
    "세금노트", "주식습관", "펀드체크", "배당일기", "재무설계",
    "경제읽기", "포트폴리오랩", "절약실험", "투자기록", "자산성장",
)


def blog_pen_name(post_id: int) -> str:
    pid = int(post_id or 0)
    return BLOG_PEN_NAMES[(pid * 2654435761) % len(BLOG_PEN_NAMES)]


def main() -> int:
    with sqlite3.connect(DB) as conn:
        rows = conn.execute("SELECT id FROM posts ORDER BY id").fetchall()
        for (pid,) in rows:
            conn.execute(
                "UPDATE posts SET author=? WHERE id=?",
                (blog_pen_name(pid), pid),
            )
        conn.commit()
    print(f"updated {len(rows)} posts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
