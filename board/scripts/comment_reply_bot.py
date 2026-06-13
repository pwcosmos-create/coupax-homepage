#!/usr/bin/env python3
"""
블로그 댓글에 자동 답글을 다는 봇. SQLite board DB에 직접 INSERT (add_comment와 동일).

환경 변수
  BOARD_DB_PATH          DB 경로 (기본: board/board.db)
  COMMENT_BOT_ENABLED    1이 아니면 종료 (기본: 0 — 실수 실행 방지)
  COMMENT_BOT_DRY_RUN    1이면 INSERT 없이 로그만
  COMMENT_BOT_AUTHOR     답글 작성자 표시명 (기본: 머니인사이트)
  COMMENT_BOT_PASSWORD   답글 삭제용 비밀번호 (운영에서는 필수)
  COMMENT_BOT_MAX_PER_RUN 한 번에 최대 답글 수 (기본: 5)
  COMMENT_BOT_MIN_COMMENT_ID  이 id 미만 댓글은 무시 (배포 시 현재 max(id)로 두면 과거 댓글 스킵)
  COMMENT_BOT_MAX_AGE_DAYS    댓글 생성 시각이 N일보다 오래되면 스킵 (기본: 14)
  COMMENT_BOT_MIN_AGE_SEC    방금 단 댓글에 바로 달리지 않도록 최소 대기 초 (기본: 120)
  COMMENT_BOT_SKIP_AUTHORS   쉼표로 구분한 닉네임 — 답글 대상에서 제외 (봇·운영자)
  COMMENT_BOT_POST_IDS       처리할 post_id만 제한 (쉼표, 비우면 전체)
  OPENAI_API_KEY           있으면 짧은 한국어 답변 생성 (없으면 규칙 기반 템플릿)
  COMMENT_BOT_LEGAL_FOOTER   답글 말미에 붙일 면책 문구 (비우면 생략). 애드센스 대비 기본값 있음.

cron 예: board/deploy/install_comment_bot_cron.sh 참고
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

# ── 기본 경로 ───────────────────────────────────────────────────────────────
_BOARD_DIR = Path(__file__).resolve().parent.parent
if str(_BOARD_DIR) not in sys.path:
    sys.path.insert(0, str(_BOARD_DIR))
import security_utils  # noqa: E402

DB_PATH = os.environ.get(
    "BOARD_DB_PATH",
    str(_BOARD_DIR / "board.db"),
)

BOT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS bot_comment_replies (
  source_comment_id INTEGER PRIMARY KEY,
  reply_comment_id INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
"""

DEFAULT_SKIP = "머니인사이트,젬마24,코드노트,관리자"


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name, "").strip().lower()
    if v in ("1", "true", "yes", "y"):
        return True
    if v in ("0", "false", "no", "n"):
        return False
    return default


def _parse_created(created: str | None) -> datetime | None:
    if not created:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(created.strip(), fmt)
        except ValueError:
            continue
    return None


def _simple_reply(author: str, content: str, post_title: str) -> str:
    t = content.strip()
    low = t.lower()
    head = f"@{author} 님, "
    if "감사" in t or "고마" in t:
        return head + (
            "따뜻한 말씀 감사합니다. 더 궁금한 점이 있으시면 댓글로 남겨 주세요."
        )
    if "?" in t or "까요" in t or "인가요" in t or "되나요" in t or "어떻게" in t:
        return head + (
            "질문 주셔서 감사합니다. 본 글과 답변은 일반 정보 안내이며 투자·세무 자문이 아닙니다. "
            "최종 판단은 운용사 공시·간이투자설명서 등 공식 자료를 함께 확인해 주세요. "
            "자주 묻는 주제는 새 글로 정리할 수 있습니다."
        )
    if "etf" in low or "배당" in t or "월배당" in t or "티커" in low:
        return head + (
            "ETF·배당 관련 질문 감사합니다. 글 내용은 참고용 설명이며, "
            "투자 결정 전 반드시 최신 공시·운용사 자료를 확인해 주세요. "
            "종목·상황을 조금 더 구체적으로 적어 주시면 답변에 도움이 됩니다."
        )
    if "오류" in t or "틀" in t or "안 맞" in t or "수정" in t:
        return head + (
            "알려 주셔서 감사합니다. 가능한 범위에서 데이터를 바로잡겠습니다. "
            "어느 글·어느 항목인지 조금만 더 구체적으로 적어 주시면 큰 도움이 됩니다."
        )
    return head + (
        f"「{post_title[:40]}{'…' if len(post_title) > 40 else ''}」 글에 남겨 주셔서 감사합니다. "
        "추가로 궁금한 점이 있으면 댓글로 이어 주세요."
    )


def _openai_reply(author: str, content: str, post_title: str) -> str | None:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    system = (
        "너는 한국어 금융·재테크 블로그 운영자다. 글 하단 질문(댓글)에 짧고 정중하게 답한다. "
        "일반적인 설명·안내만 하고, 특정 금융상품 매수·매도를 권유하거나 수익·손실을 약속하지 않는다. "
        "법적·세무·투자 자문처럼 들리게 단정하지 말 것. 320자 이내."
    )
    user = (
        f"글 제목: {post_title}\n"
        f"댓글 작성자: {author}\n"
        f"댓글 내용:\n{content}\n\n"
        "위 댓글에 대한 답글 본문만 출력한다. '@이름 님'으로 시작해도 된다."
    )
    body = json.dumps(
        {
            "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": 500,
            "temperature": 0.5,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"].strip()
        return text if text else None
    except (urllib.error.URLError, KeyError, IndexError, TypeError, json.JSONDecodeError):
        return None


def _clamp_reply(text: str, max_len: int = 4000) -> str:
    text = re.sub(r"\r\n", "\n", text).strip()
    if len(text) > max_len:
        return text[: max_len - 1] + "…"
    return text


_DEFAULT_LEGAL_FOOTER = (
    " (참고용 안내이며 투자·세무 자문이 아니며 특정 상품 매매를 권유하지 않습니다.)"
)


def _finalize_reply_body(body: str) -> str:
    """애드센스·면책에 맞게 말미 문구를 붙이고 길이 제한을 적용한다."""
    raw = os.environ.get("COMMENT_BOT_LEGAL_FOOTER")
    if raw is None:
        footer = _DEFAULT_LEGAL_FOOTER
    else:
        footer = raw.strip()
    text = re.sub(r"\r\n", "\n", body).strip()
    if footer and footer not in text:
        text = text + footer
    return _clamp_reply(text)


def _spammy(content: str) -> bool:
    if len(content) > 2000:
        return True
    if len(re.findall(r"https?://", content, re.I)) >= 3:
        return True
    if re.search(r"(http://|\.(ru|cn)/)", content, re.I):
        return True
    return False


def main() -> int:
    if not _env_bool("COMMENT_BOT_ENABLED", False):
        print("COMMENT_BOT_ENABLED!=1 — exit")
        return 0

    dry = _env_bool("COMMENT_BOT_DRY_RUN", False)
    author_bot = os.environ.get("COMMENT_BOT_AUTHOR", "머니인사이트").strip() or "머니인사이트"
    password = os.environ.get("COMMENT_BOT_PASSWORD", "").strip()
    if not password and not dry:
        print("COMMENT_BOT_PASSWORD is required (or set COMMENT_BOT_DRY_RUN=1)", file=sys.stderr)
        return 2

    max_per = int(os.environ.get("COMMENT_BOT_MAX_PER_RUN", "5"))
    min_cid = int(os.environ.get("COMMENT_BOT_MIN_COMMENT_ID", "0"))
    max_age_days = int(os.environ.get("COMMENT_BOT_MAX_AGE_DAYS", "14"))
    min_age_sec = int(os.environ.get("COMMENT_BOT_MIN_AGE_SEC", "120"))

    skip_raw = os.environ.get("COMMENT_BOT_SKIP_AUTHORS", DEFAULT_SKIP)
    skip_authors = {a.strip() for a in skip_raw.split(",") if a.strip()}
    skip_authors.add(author_bot)

    post_filter = os.environ.get("COMMENT_BOT_POST_IDS", "").strip()
    post_ids: set[int] | None = None
    if post_filter:
        post_ids = set()
        for p in post_filter.split(","):
            p = p.strip()
            if p.isdigit():
                post_ids.add(int(p))

    now = datetime.now()
    age_limit = now - timedelta(days=max_age_days)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(BOT_TABLE_SQL)
    conn.commit()

    sql = """
    SELECT c.id, c.post_id, c.author, c.content, c.created, p.title
    FROM comments c
    JOIN posts p ON p.id = c.post_id
    WHERE c.id NOT IN (SELECT source_comment_id FROM bot_comment_replies)
      AND c.id >= ?
    ORDER BY c.id ASC
    """
    rows = cur.execute(sql, (min_cid,)).fetchall()
    done = 0

    for row in rows:
        if done >= max_per:
            break
        cid = row["id"]
        pid = row["post_id"]
        auth = (row["author"] or "").strip()
        content = (row["content"] or "").strip()

        if post_ids is not None and pid not in post_ids:
            continue
        if auth in skip_authors:
            continue
        if len(content) < 2:
            continue
        if _spammy(content):
            continue

        ct = _parse_created(row["created"])
        if ct is not None:
            if ct < age_limit:
                continue
            if (now - ct).total_seconds() < min_age_sec:
                continue

        title = row["title"] or ""
        reply_body = _openai_reply(auth, content, title) or _simple_reply(auth, content, title)
        reply_body = _finalize_reply_body(reply_body)

        created = now.strftime("%Y-%m-%d %H:%M")
        print(f"candidate id={cid} post={pid} author={auth!r} -> reply_len={len(reply_body)}")

        if dry:
            print(f"  [dry-run] {reply_body[:200]}{'…' if len(reply_body) > 200 else ''}")
            done += 1
            continue

        cur.execute(
            "INSERT INTO comments (post_id, author, content, password, created) VALUES (?,?,?,?,?)",
            (pid, author_bot, reply_body, security_utils.hash_password(password), created),
        )
        rid = cur.lastrowid
        cur.execute(
            "INSERT INTO bot_comment_replies (source_comment_id, reply_comment_id, created_at) VALUES (?,?,?)",
            (cid, rid, created),
        )
        conn.commit()
        print(f"  inserted reply comment id={rid}")
        done += 1

    conn.close()
    print(f"finished, processed={done} dry_run={dry}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
