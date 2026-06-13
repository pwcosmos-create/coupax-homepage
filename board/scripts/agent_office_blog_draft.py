"""
사무실 작업 완료 → 블로그 초안(is_draft=1) 자동 생성.

  AGENT_OFFICE_BLOG_DRAFT_ENABLED=1  (기본 1)
  AGENT_OFFICE_BLOG_DRAFT_PASSWORD   (기본 coupax2026 — 수정·발행 시 사용)
"""
from __future__ import annotations

import html
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD) not in sys.path:
    sys.path.insert(0, str(BOARD))
import security_utils  # noqa: E402
DB_PATH = Path(os.environ.get("BOARD_DB_PATH", str(BOARD / "board.db")))

_CATEGORY_RULES = (
    ("ETF·주식", ("etf", "월배당", "배당", "종목", "지수", "커버드콜")),
    ("연금·보험", ("연금", "irp", "퇴직", "dc형", "isa")),
    ("절세·세금", ("세금", "절세", "소득세", "공제", "연말정산")),
    ("부동산·청약", ("청약", "전세", "부동산", "주택")),
    ("적금·예금", ("예금", "적금", "파킹", "금리")),
    ("이슈·트렌드", ("이슈", "금리", "환율", "매크로")),
)


def _enabled() -> bool:
    return os.getenv("AGENT_OFFICE_BLOG_DRAFT_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _draft_password() -> str:
    return os.getenv("AGENT_OFFICE_BLOG_DRAFT_PASSWORD", "coupax2026").strip() or "coupax2026"


def ensure_posts_schema(db_path: Path | None = None) -> None:
    """posts.is_draft 컬럼이 없으면 추가."""
    path = db_path or DB_PATH
    if not path.is_file():
        return
    with sqlite3.connect(path) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(posts)").fetchall()}
        if "is_draft" not in cols:
            conn.execute("ALTER TABLE posts ADD COLUMN is_draft INTEGER DEFAULT 0")
            conn.commit()


def _pick_category(task: dict, result: str) -> str:
    blob = f"{task.get('title') or ''} {task.get('body') or ''} {result}".lower()
    for label, keys in _CATEGORY_RULES:
        if any(k in blob for k in keys):
            return label
    return "이슈·트렌드"


def _pick_title(task: dict) -> str:
    title = (task.get("title") or "").strip()
    if title:
        return title[:120]
    body = (task.get("body") or "").strip().split("\n")[0]
    return (body[:80] or "사무실 작업 보고").strip()


def _section_html(title: str, body: str) -> str:
    parts = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("■"):
            parts.append(f"<h3>{html.escape(line.lstrip('■ '))}</h3>")
        elif line.startswith("·") or line.startswith("-"):
            parts.append(f"<li>{html.escape(line.lstrip('·- '))}</li>")
        else:
            parts.append(f"<p>{html.escape(line)}</p>")
    inner = "\n".join(parts)
    if "<li>" in inner:
        inner = re.sub(
            r"(<li>.*?</li>\n?)+",
            lambda m: "<ul>\n" + m.group(0) + "</ul>\n",
            inner,
            flags=re.S,
        )
    return f"<h3>{html.escape(title)}</h3>\n{inner}"


def build_draft_html(task: dict, result: str, *, category: str, post_title: str) -> str:
    """E-E-A-T 구조 HTML 초안."""
    tid = task.get("id") or "?"
    intro = (
        f"<p>젬마24 에이전트 사무실에서 수집·취합한 <strong>작업 #{tid}</strong> 결과를 "
        f"블로그 초안으로 정리했습니다. 투자·세무 권유가 아닌 정보 정리 목적이며, "
        f"발행 전 대표님 검토·수정이 필요합니다.</p>"
    )
    blocks: list[str] = [
        f"[카테고리] {category}",
        intro,
    ]

    current_title = ""
    current_lines: list[str] = []
    for line in (result or "").splitlines():
        if line.startswith("■ "):
            if current_title:
                blocks.append(_section_html(current_title, "\n".join(current_lines)))
            current_title = line[2:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_title:
        blocks.append(_section_html(current_title, "\n".join(current_lines)))
    elif result.strip():
        blocks.append(_section_html("취합 내용", result[:3500]))

    blocks.append(
        "<h3>자주 묻는 질문 (FAQ)</h3>"
        "<p><strong>Q.</strong> 이 글은 자동으로 올라간 건가요?</p>"
        "<p><strong>A.</strong> 사무실 작업 완료 시 생성된 <em>초안</em>입니다. "
        "사무실에서 「발행」하거나 수정 화면에서 내용을 다듬은 뒤 공개하세요.</p>"
        "<p><strong>Q.</strong> 데이터는 어디서 왔나요?</p>"
        "<p><strong>A.</strong> coupax 블로그·월배당 ETF 시트·에이전트 점검 로그를 바탕으로 "
        f"작성되었습니다. 수치는 <a href=\"/etf/monthly-sheet\">월배당 ETF 시트</a>에서 최신본을 확인하세요.</p>"
    )
    blocks.append(
        "<p class=\"post-disclaimer\"><strong>면책</strong> "
        "본 글은 일반적인 금융 정보 제공 목적이며, 투자 권유 또는 세무·법률 자문이 아닙니다.</p>"
    )
    blocks.append(
        f"<p><small>초안 메타: task_id={tid} · 생성 {datetime.now().strftime('%Y-%m-%d %H:%M')}</small></p>"
    )
    return "\n\n".join(blocks)


def create_draft_from_task(
    task: dict,
    result: str,
    *,
    primary_id: str = "",
) -> int | None:
    """초안 글 INSERT. post_id 또는 None."""
    if not _enabled():
        return None
    if task.get("blog_draft_id"):
        return int(task["blog_draft_id"])
    if not result or len(result.strip()) < 80:
        return None
    if not DB_PATH.is_file():
        return None

    ensure_posts_schema()
    category = _pick_category(task, result)
    post_title = _pick_title(task)
    content = build_draft_html(task, result, category=category, post_title=post_title)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    author = os.getenv("AGENT_OFFICE_BLOG_AUTHOR", "머니인사이트").strip() or "머니인사이트"

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            """
            INSERT INTO posts (title, author, content, password, created, views, is_draft)
            VALUES (?,?,?,?,?,0,1)
            """,
            (post_title, author, content, security_utils.hash_password(_draft_password()), now),
        )
        conn.commit()
        return int(cur.lastrowid)
