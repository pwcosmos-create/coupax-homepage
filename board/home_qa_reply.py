"""홈 질문창 즉시 답변 — 젬마24."""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parent
_SCRIPTS = BOARD / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
if str(BOARD) not in sys.path:
    sys.path.insert(0, str(BOARD))

import comment_reply_bot as bot  # noqa: E402
import gemma24_local  # noqa: E402
import security_utils  # noqa: E402

BOT_TABLE_SQL = bot.BOT_TABLE_SQL
GEMMA24_AUTHOR = os.environ.get("HOME_QA_REPLY_AUTHOR", "젬마24").strip() or "젬마24"
_HOME_QA_FOOTER = " (참고용이며 투자·세무·법률 자문이 아닙니다.)"


def ensure_bot_table(db) -> None:
    db.execute(BOT_TABLE_SQL)
    db.commit()


def _head(author: str) -> str:
    return f"@{author} 님, 젬마24입니다. "


def _wants_explain(text: str) -> bool:
    t = text.strip()
    return any(
        k in t
        for k in (
            "알려",
            "설명",
            "대해",
            "뭐",
            "무엇",
            "어떻",
            "방법",
            "궁금",
            "란",
            "차이",
            "?",
            "까요",
        )
    )


def _topic_reply(author: str, content: str, topic: str) -> str | None:
    """주제·키워드별 구체적 참고 답변."""
    t = content.strip()
    low = t.lower()
    head = _head(author)

    if "연금저축" in t or re.search(r"연금\s*저축", t):
        return head + (
            "연금저축은 노후를 위해 스스로 납입하는 개인연금 상품입니다. "
            "매년 납입 한도(예: 600만 원) 안에서 넣으면 연말정산·종합소득세 신고 시 "
            "세액공제(최대 16.5% 수준)를 받을 수 있습니다.\n\n"
            "만 55세 이후 연금·일시금으로 받으며, IRP·DC형 퇴직연금과 합쳐 "
            "연간 1,800만 원 한도로 운용할 수 있습니다. "
            "중도 해지 시 세액 환수 등 불이익이 있어 5년 이상 장기 여유 자금으로 가입하는 것이 일반적입니다."
        )

    if "irp" in low and (_wants_explain(t) or "퇴직" in t):
        return head + (
            "IRP(개인형 퇴직연금)는 퇴직금·개인 추가 납입을 모아 운용하는 계좌입니다.\n\n"
            "연금저축과 합산해 연간 900만 원까지 세액공제(연금저축 600만·IRP 300만)를 받을 수 있고, "
            "주식형 ETF는 IRP에서 최대 70%, 연금저축은 100%까지 담을 수 있습니다.\n\n"
            "IRP에는 안전자산 30% 의무가 있어, 한도 채우기 순서는 보통 "
            "연금저축 600만 원 → IRP 300만 원 순입니다."
        )

    if "etf" in low and ("뭐" in t or "무엇" in t or "란" in t):
        return head + (
            "ETF(상장지수펀드)는 지수·섹터 등을 추종하는 펀드를 주식처럼 사고팔 수 있는 상품입니다. "
            "개별 주식보다 분산이 쉽고, 보수·거래비용이 액티브 펀드보다 낮은 경우가 많습니다. "
            "국내·해외, 배당·성장 등 테마별로 고르고, 적립식으로 매수 단가를 나누는 방식이 흔합니다. "
            "투자 전 간이투자설명서·총보수·괴리율을 확인해 주세요."
        )

    if "월배당" in t or ("배당" in t and "etf" in low):
        return head + (
            "월배당 ETF는 분배금을 월 단위로 지급하도록 설계된 상품입니다. "
            "분배율(%)만 보면 매력적일 수 있으나, 분배금이 원금 일부 환원인 경우도 있어 "
            "최근 1년·3년 총수익률(가격+분배)을 함께 보는 것이 좋습니다. "
            "과세·보수·추종 지수 리스크도 간이투자설명서에서 확인하세요."
        )

    if "연금" in t or "irp" in low or "퇴직연금" in t:
        return head + (
            "연금·IRP·퇴직연금은 목적(노후·세액공제)과 납입 한도, 운용 규칙이 다릅니다. "
            "연금저축·IRP 세액공제 한도, 주식 비중 제한( IRP 70% )을 먼저 정리한 뒤 "
            "본인 소득·퇴직 시점에 맞는 계좌를 선택하세요. 최신 한도는 국세청·금융사 안내를 확인하세요."
        )

    if "청약" in t or "주택" in t:
        return head + (
            "주택 청약은 청약통장 가입 기간·무주택 기간·가점 등으로 순위가 정해집니다. "
            "특별·일반공급 유형별 소득·자산 기준이 다르니 청약홈에서 본인 해당 유형을 확인하세요. "
            "예치금·가입 지역이 분양 지역과 맞는지도 체크리스트에 넣으면 좋습니다."
        )

    if "?" in t or "까요" in t or "어떻게" in t or "방법" in t:
        return head + (
            f"「{topic}」 주제로 질문 주셨네요. "
            f"질문하신 내용(「{t[:40]}{'…' if len(t) > 40 else ''}」)에 대해 "
            "일반적인 기준만 말씀드릴 수 있습니다. "
            "구체적 금액·기간·상품명을 알려 주시면 댓글로 더 짚어 드리겠습니다. "
            "공식 확인은 금융감독원·국세청·운용사 공시를 참고해 주세요."
        )

    return None


def _openai_reply(author: str, content: str, post_title: str, topic: str = "") -> str | None:
    if not gemma24_local._use_openai():
        return None
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    system = (
        "너는 coupax.co.kr 머니인사이트의 AI '젬마24'다. "
        "사용자 질문에 반드시 3~6문장으로 직접 답한 뒤, 한 문장 면책(자문 아님)으로 끝낸다. "
        "'@닉네임 님'으로 시작한다. 특정 종목 매수·매도 권유, 수익 약속 금지. "
        "질문을 피하거나 '공식 사이트 확인만 하세요'만 말하지 말 것."
    )
    user = (
        f"주제: {topic or '기타'}\n"
        f"글 제목: {post_title}\n"
        f"질문자: {author}\n"
        f"질문:\n{content}\n"
    )
    body = json.dumps(
        {
            "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": 700,
            "temperature": 0.45,
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
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"].strip()
        return text if text else None
    except (urllib.error.URLError, KeyError, IndexError, TypeError, json.JSONDecodeError):
        return None


def _use_ollama_on_sync() -> bool:
    """웹 댓글·홈 질문은 기본적으로 Ollama 생략(느려 gunicorn 타임아웃 유발)."""
    return os.environ.get("HOME_QA_USE_OLLAMA", "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _optimize_reply_text(text: str) -> str:
    """중복·불릿 덤프·과도한 공백 정리."""
    text = re.sub(r"\r\n", "\n", text).strip()
    text = re.sub(r"[⚙️✓🗂️☸️🔧📋]{1,}", "", text)
    # 연속 불릿 줄 → 한 줄로
    text = re.sub(r"(?:^[·•]\s*.+\n){2,}", lambda m: " ".join(
        re.sub(r"^[·•]\s*", "", ln).strip()
        for ln in m.group(0).splitlines()
        if ln.strip()
    ) + "\n", text, flags=re.M)
    parts = re.split(r"\n{2,}|\n", text)
    seen: set[str] = set()
    blocks: list[str] = []
    for block in parts:
        block = re.sub(r"\s+", " ", block).strip()
        if not block:
            continue
        key = block[:56].lower()
        if key in seen:
            continue
        seen.add(key)
        blocks.append(block)
    text = "\n\n".join(blocks)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return _split_dense_paragraphs(text.strip())


def _split_dense_paragraphs(text: str) -> str:
    """한 덩어리로 이어진 긴 답변을 2~3문장 단위로 나눔."""
    blocks = text.split("\n\n")
    out: list[str] = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if len(block) < 200 or block.count(".") + block.count("!") + block.count("?") < 3:
            out.append(block)
            continue
        sents = re.split(r"(?<=[.!?…])\s+", block)
        chunk: list[str] = []
        buf: list[str] = []
        for s in sents:
            s = s.strip()
            if not s:
                continue
            buf.append(s)
            if len(buf) >= 2:
                chunk.append(" ".join(buf))
                buf = []
        if buf:
            chunk.append(" ".join(buf))
        out.extend(chunk if chunk else [block])
    return "\n\n".join(out)


def _finalize_reply(author: str, body: str) -> str:
    if not body.strip().startswith("@"):
        body = _head(author) + body.lstrip()
    text = _optimize_reply_text(body)
    if _HOME_QA_FOOTER not in text:
        text += _HOME_QA_FOOTER
    if len(text) > 2000:
        cut = text[:1990].rstrip()
        if cut and cut[-1] not in ".!?…":
            cut += "…"
        text = cut + _HOME_QA_FOOTER if _HOME_QA_FOOTER not in cut else cut
    return text


def build_reply_fallback(
    author: str, content: str, post_title: str, topic: str = ""
) -> str:
    """Ollama·API 실패 시 즉시 쓰는 템플릿/지식 답변."""
    topic = (topic or "").strip() or "기타"
    head = _head(author)
    body = (
        _topic_reply(author, content, topic)
        or gemma24_local.knowledge_snippet_reply(
            author, content, topic, head=head
        )
        or (
            head
            + f"「{topic}」 관련 질문 감사합니다. "
            "일반적인 기준만 안내드릴 수 있으며, 구체적 금액·기간·상품명을 알려 주시면 "
            "댓글로 이어서 설명드리겠습니다."
        )
    )
    return _finalize_reply(author, body)


def build_reply(
    author: str, content: str, post_title: str, topic: str = ""
) -> str:
    topic = (topic or "").strip() or "기타"
    head = _head(author)
    # 빠른 경로 우선 — Ollama는 마지막(기본 비활성)으로 gunicorn 타임아웃 방지
    body = (
        _topic_reply(author, content, topic)
        or gemma24_local.knowledge_snippet_reply(
            author, content, topic, head=head
        )
        or _openai_reply(author, content, post_title, topic)
    )
    if not body and _use_ollama_on_sync():
        body = gemma24_local.gemma_local_reply(author, content, post_title, topic)
    if not body:
        body = (
            head
            + f"「{topic}」 관련 질문 감사합니다. 질문 내용을 바탕으로 참고 답변을 남깁니다. "
            "더 구체적인 상황(금액·기간·상품)을 댓글로 알려 주시면 이어서 설명드리겠습니다."
        )
    return _finalize_reply(author, body)


def _comment_as_reply_dict(row) -> dict:
    return {
        "id": int(row[0]),
        "author": row[1],
        "content": row[2],
        "created": row[3],
    }


def _existing_reply_for_source(db, source_comment_id: int) -> dict | None:
    """bot_comment_replies에 등록된 기존 답변."""
    ensure_bot_table(db)
    row = db.execute(
        "SELECT reply_comment_id FROM bot_comment_replies WHERE source_comment_id=? LIMIT 1",
        (source_comment_id,),
    ).fetchone()
    if not row:
        return None
    c = db.execute(
        "SELECT id, author, content, created FROM comments WHERE id=?",
        (int(row[0]),),
    ).fetchone()
    if not c or c[1] != GEMMA24_AUTHOR:
        return None
    return _comment_as_reply_dict(c)


def _gemma_reply_after_source(db, post_id: int, source_comment_id: int) -> dict | None:
    """바로 다음 댓글이 젬마24면 그걸 답변으로 간주 (레거시 매핑 보강)."""
    c = db.execute(
        "SELECT id, author, content, created FROM comments "
        "WHERE post_id=? AND id > ? ORDER BY id LIMIT 1",
        (post_id, source_comment_id),
    ).fetchone()
    if not c or c[1] != GEMMA24_AUTHOR:
        return None
    ensure_bot_table(db)
    exists = db.execute(
        "SELECT 1 FROM bot_comment_replies WHERE source_comment_id=? LIMIT 1",
        (source_comment_id,),
    ).fetchone()
    if not exists:
        created = c[3] or datetime.now().strftime("%Y-%m-%d %H:%M")
        db.execute(
            "INSERT OR IGNORE INTO bot_comment_replies "
            "(source_comment_id, reply_comment_id, created_at) VALUES (?,?,?)",
            (source_comment_id, int(c[0]), created),
        )
        db.commit()
    return _comment_as_reply_dict(c)


def user_comment_needs_reply(db, post_id: int, source_comment_id: int) -> bool:
    """사용자 댓글에 젬마24 답변이 아직 없으면 True."""
    if _existing_reply_for_source(db, source_comment_id):
        return False
    if _gemma_reply_after_source(db, post_id, source_comment_id):
        return False
    row = db.execute(
        "SELECT author FROM comments WHERE id=? AND post_id=?",
        (source_comment_id, post_id),
    ).fetchone()
    return bool(row and row[0] != GEMMA24_AUTHOR)


def attach_reply(
    db,
    post_id: int,
    source_comment_id: int | None,
    author: str,
    content: str,
    post_title: str,
    topic: str = "",
) -> dict:
    """댓글 질문에 젬마24 답변을 붙임. 실패해도 템플릿 답변은 반드시 시도."""
    if source_comment_id:
        sid = int(source_comment_id)
        existing = _existing_reply_for_source(db, sid)
        if existing:
            return existing
        legacy = _gemma_reply_after_source(db, post_id, sid)
        if legacy:
            return legacy
    try:
        reply_body = build_reply(author, content, post_title, topic)
    except Exception:
        reply_body = build_reply_fallback(author, content, post_title, topic)
    return insert_reply(db, post_id, source_comment_id, reply_body)


def insert_reply(
    db,
    post_id: int,
    source_comment_id: int | None,
    reply_body: str,
) -> dict:
    ensure_bot_table(db)
    if source_comment_id:
        existing = _existing_reply_for_source(db, int(source_comment_id))
        if existing:
            return existing
    pw = os.environ.get("COMMENT_BOT_PASSWORD", "").strip() or "home-qa-bot"
    created = datetime.now().strftime("%Y-%m-%d %H:%M")
    cur = db.execute(
        "INSERT INTO comments (post_id, author, content, password, created) VALUES (?,?,?,?,?)",
        (
            post_id,
            GEMMA24_AUTHOR,
            reply_body,
            security_utils.hash_password(pw),
            created,
        ),
    )
    reply_id = int(cur.lastrowid)
    if source_comment_id:
        exists = db.execute(
            "SELECT 1 FROM bot_comment_replies WHERE source_comment_id=? LIMIT 1",
            (source_comment_id,),
        ).fetchone()
        if not exists:
            db.execute(
                "INSERT OR IGNORE INTO bot_comment_replies "
                "(source_comment_id, reply_comment_id, created_at) VALUES (?,?,?)",
                (source_comment_id, reply_id, created),
            )
    db.commit()
    return {
        "id": reply_id,
        "author": GEMMA24_AUTHOR,
        "content": reply_body,
        "created": created,
    }
