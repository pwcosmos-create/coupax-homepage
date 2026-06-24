"""젬마24 로컬 추론 — Ollama + 주입 지식망(인터넷 불필요)."""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

BOARD = Path(__file__).resolve().parent
_SCRIPTS = BOARD / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import agent_office_wiki_store as wiki_store  # noqa: E402

_QUERY_TOKEN_RE = re.compile(
    r"[가-힣]{2,}|etf|irp|연금|배당|절세|청약|예적금|금리|퇴직|관상|관相|인상|삼정|오관|길상",
    re.I,
)
_GWANSANG_TOPIC_RE = re.compile(
    r"관상|관相|얼굴.?관|이마.?관|눈.?관|눈꼬리|눈매|코.?관|콧|입술.?관|인중|턱.?관|"
    r"삼정|오관|길상|인상.?분석|관자|광대|볼.?관|필러|대칭.?관",
    re.I,
)
_SAJU_TOPIC_RE = re.compile(
    r"사주|명리|오행|십신|대운|세운|용신|일주|격국|사주팔자",
    re.I,
)
# 사무실 작업 로그·내부 Wiki — 블로그 질문 답변에 노출 금지
_OFFICE_MARKERS = (
    "wiki_office_",
    "사무실",
    "에이전트",
    "동기화 전문",
    "메타 카드",
    "글 발행 초안",
    "작업 #",
    "사서 젬마",
    "창조 젬마",
    "대조했습니다",
    "마지막 수정",
    "■ 지시",
    "■ 연구",
)
_OPERATIONAL_RE = re.compile(
    r"(동기화|메타\s*카드|작업\s*#|사서\s*젬마|창조\s*젬마|대조했|마지막\s*수정|초안\s*→)",
    re.I,
)
_EMOJI_SYMBOL_RE = re.compile(r"[⚙️✓🗂️☸️🔧📋→·•▪▫■□]")


def _ollama_enabled() -> bool:
    return os.environ.get("GEMMA_OLLAMA_ENABLED", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def _use_openai() -> bool:
    return os.environ.get("HOME_QA_USE_OPENAI", "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def is_public_wiki_card(card: dict | None) -> bool:
    """블로그·홈 질문 답변에 쓸 수 있는 카드인지 (사무실 작업 로그 제외)."""
    if not isinstance(card, dict):
        return False
    wid = str(card.get("id") or "")
    if wid.startswith(("wiki_office_", "wiki_pulse_")):
        return False
    if (card.get("source") or "").strip() in (
        "office",
        "office_paste",
        "reserved",
        "coupax-agent-office",
    ):
        return False
    blob = " ".join(
        [
            wid,
            str(card.get("title") or ""),
            str(card.get("summary") or "")[:200],
        ]
    )
    if any(m in blob for m in _OFFICE_MARKERS):
        return False
    return True


def sanitize_display_text(text: str, *, max_len: int = 320) -> str:
    """Wiki 원문을 읽기 좋은 짧은 문장으로 정리."""
    if not text:
        return ""
    t = str(text).replace("\r\n", "\n")
    # 작업 보고서 본문이면 '취합 결론' 구간만 추출
    m = re.search(r"■\s*취합\s*결론\s*\n(.*?)(?:\n■|\Z)", t, re.S)
    if m:
        t = m.group(1)
    t = _EMOJI_SYMBOL_RE.sub(" ", t)
    t = re.sub(r"\s*→\s*", ". ", t)
    t = re.sub(r"\s+", " ", t).strip()
    # 불릿 나열을 문장으로
    parts = [p.strip(" .") for p in re.split(r"\s*[·•]\s*", t) if p.strip()]
    seen: set[str] = set()
    sentences: list[str] = []
    for p in parts:
        if _OPERATIONAL_RE.search(p):
            continue
        key = p[:48].lower()
        if key in seen or len(p) < 8:
            continue
        seen.add(key)
        if not p.endswith((".", "!", "?", "…", "요", "다", "니다")):
            p += "."
        sentences.append(p)
        if len(sentences) >= 3:
            break
    out = " ".join(sentences)
    if len(out) > max_len:
        out = out[: max_len - 1].rstrip() + "…"
    return out


def infer_rag_domain(content: str, topic: str = "") -> str:
    """질문 텍스트로 Wiki domain 라우팅."""
    blob = f"{topic}\n{content}"
    if _GWANSANG_TOPIC_RE.search(blob):
        return wiki_store.DOMAIN_GWANSANG
    if _SAJU_TOPIC_RE.search(blob):
        return wiki_store.DOMAIN_SAJU
    return wiki_store.DOMAIN_FINANCE


def _rag_disclaimer(domain: str) -> str:
    if domain == wiki_store.DOMAIN_GWANSANG:
        return "본 내용은 관상 해석 참고용이며 의학·법률·투자 자문이 아닙니다."
    if domain == wiki_store.DOMAIN_SAJU:
        return "본 내용은 명리 참고용이며 확정 예언·의학·법률·투자 자문이 아닙니다."
    return "투자·세무·법률 자문이 아닙니다."


def search_injected_knowledge(
    content: str,
    topic: str = "",
    *,
    domain: str | None = None,
    limit: int = 3,
    public_only: bool = True,
) -> list[dict]:
    """gemma_knowledge.json 에서 질문과 관련된 Wiki 카드 검색."""
    if domain is None:
        domain = infer_rag_domain(content, topic)
    try:
        data = wiki_store.load_knowledge()
    except Exception:
        return []

    blob = f"{topic} {content}".lower()
    tokens = {t.lower() for t in _QUERY_TOKEN_RE.findall(blob)}
    if topic:
        tokens.add(topic.lower())

    scored: list[tuple[int, dict]] = []
    for w in data.get("wiki") or []:
        if not isinstance(w, dict):
            continue
        if wiki_store.wiki_domain(w) != domain:
            continue
        if public_only and not is_public_wiki_card(w):
            continue
        if domain == wiki_store.DOMAIN_SAJU:
            if (w.get("council_tier") or "") == "excluded":
                continue
            if w.get("council_status") == "fail":
                continue
        text = " ".join(
            [
                str(w.get("title") or ""),
                str(w.get("summary") or ""),
                " ".join(w.get("tags") or []),
            ]
        ).lower()
        score = sum(2 if t in str(w.get("title") or "").lower() else 1 for t in tokens if t in text)
        if domain == wiki_store.DOMAIN_SAJU and w.get("council_pass"):
            score += 5
        elif domain == wiki_store.DOMAIN_SAJU and (w.get("council_tier") or "") == "certified":
            score += 5
        if score > 0:
            scored.append((score, w))

    scored.sort(key=lambda x: (-x[0], str(x[1].get("ts") or "")))
    hits = [w for _, w in scored[:limit]]
    if hits or domain != wiki_store.DOMAIN_FINANCE:
        return hits
    # 금융 도메인 카드가 비어 있으면 토큰 매칭되는 다른 공개 Wiki도 참고
    fallback: list[tuple[int, dict]] = []
    for w in data.get("wiki") or []:
        if not isinstance(w, dict) or not public_only or not is_public_wiki_card(w):
            continue
        if wiki_store.wiki_domain(w) == wiki_store.DOMAIN_SAJU:
            if (w.get("council_tier") or "") == "excluded" or w.get("council_status") == "fail":
                continue
        text = " ".join(
            [
                str(w.get("title") or ""),
                str(w.get("summary") or ""),
                " ".join(w.get("tags") or []),
            ]
        ).lower()
        score = sum(2 if t in str(w.get("title") or "").lower() else 1 for t in tokens if t in text)
        if score > 0:
            fallback.append((score, w))
    fallback.sort(key=lambda x: (-x[0], str(x[1].get("ts") or "")))
    return [w for _, w in fallback[:limit]]


def format_knowledge_sources(cards: list[dict], *, max_titles: int = 3) -> str:
    """RAG 출처 — 답변 하단에 표시."""
    titles: list[str] = []
    for w in cards[:max_titles]:
        t = (w.get("title") or "").strip()
        if t and t not in titles:
            titles.append(t[:60])
    if not titles:
        return ""
    return "참고 지식: " + " · ".join(titles)


def format_knowledge_context(cards: list[dict], *, domain: str = wiki_store.DOMAIN_FINANCE) -> str:
    if not cards:
        hint = "일반 참고 상식 범위에서 답변하세요."
        if domain == wiki_store.DOMAIN_GWANSANG:
            hint = "관상 참고 톤(경향·가능성)으로 답하고 단정·불길 표현은 피하세요."
        elif domain == wiki_store.DOMAIN_SAJU:
            hint = "명리 참고 톤으로 답하고 단정 예언은 피하세요."
        return f"(주입된 젬마 지식망에서 직접 매칭된 항목이 없습니다. {hint})"
    lines = ["[주입 지식 — 페쇄망 내부 자료, 외부 검색 금지]"]
    for w in cards:
        title = (w.get("title") or "지식").strip()
        summary = (w.get("summary") or "").strip()[:500]
        tags = ", ".join(w.get("tags") or [])[:80]
        lines.append(f"- {title}: {summary}")
        if tags:
            lines.append(f"  태그: {tags}")
    return "\n".join(lines)


def gemma_local_reply(
    author: str,
    content: str,
    post_title: str,
    topic: str = "",
) -> str | None:
    """
    서버 로컬 Ollama(etf_gemma 등) + gemma_knowledge 주입 컨텍스트.
    외부 API·인터넷 검색 없음.
    """
    if not _ollama_enabled():
        return None

    url = os.environ.get(
        "GEMMA_OLLAMA_URL", "http://127.0.0.1:11434/api/generate"
    ).strip()
    model = os.environ.get("GEMMA_OLLAMA_MODEL", "gemma4:e2b-16k").strip()
    if not url or not model:
        return None

    rag_domain = infer_rag_domain(content, topic)
    cards = search_injected_knowledge(content, topic, domain=rag_domain)
    ctx = format_knowledge_context(cards, domain=rag_domain)
    topic = (topic or "").strip() or "기타"
    disclaimer = _rag_disclaimer(rag_domain)

    prompt = f"""<start_of_turn>user
[운영 원칙 — 페쇄망]
- 당신은 coupax 머니인사이트의 AI '젬마24'입니다.
- 아래 [주입 지식]과 질문만 사용하세요. 인터넷·실시간 검색·외부 API는 사용하지 마세요.
- 개인정보는 저장·반복하지 마세요.
- 특정 종목 매수·매도 권유, 수익 약속 금지.
- 반드시 @{author} 님으로 시작해 3~6문장으로 직접 답하세요.
- 마지막에 한 문장 면책({disclaimer})을 넣으세요.

{ctx}

[질문]
주제: {topic}
글 제목: {post_title}
질문:
{content.strip()}
<end_of_turn>
<start_of_turn>model
"""

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": float(os.environ.get("GEMMA_OLLAMA_TEMPERATURE", "0.35")),
            "top_p": 0.9,
        },
    }
    timeout = int(os.environ.get("GEMMA_OLLAMA_TIMEOUT_SEC", "45") or "45")

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = (data.get("response") or "").strip()
        if len(text) < 20:
            return None
        src = format_knowledge_sources(cards)
        if src and src not in text:
            text = text.rstrip() + "\n\n" + src
        return text
    except (
        urllib.error.URLError,
        TimeoutError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
        ValueError,
    ):
        return None


def knowledge_snippet_reply(
    author: str,
    content: str,
    topic: str = "",
    *,
    head: str,
) -> str | None:
    """주입 지식으로 짧고 읽기 쉬운 참고 답변 (사무실 로그·원문 덤프 금지)."""
    rag_domain = infer_rag_domain(content, topic)
    cards = search_injected_knowledge(
        content, topic, domain=rag_domain, public_only=True, limit=2
    )
    if not cards:
        return None
    topic = (topic or "").strip() or "기타"
    paras: list[str] = [
        head + f"「{topic}」 질문에 대해 참고할 수 있는 내용을 짧게 정리했습니다."
    ]
    for w in cards[:1]:
        raw = (w.get("summary") or w.get("body") or "").strip()
        clean = sanitize_display_text(raw, max_len=360)
        if len(clean) < 24 or _OPERATIONAL_RE.search(clean):
            continue
        title = (w.get("title") or "").strip()
        if title and title not in clean:
            paras.append(f"{title}: {clean}")
        else:
            paras.append(clean)
    if len(paras) < 2:
        return None
    if rag_domain == wiki_store.DOMAIN_GWANSANG:
        paras.append(
            f"관상은 개인차가 크며 {_rag_disclaimer(rag_domain)} "
            "궁금한 부위(이마·눈·코 등)를 알려 주시면 댓글로 이어서 설명드리겠습니다."
        )
    elif rag_domain == wiki_store.DOMAIN_SAJU:
        paras.append(
            f"{_rag_disclaimer(rag_domain)} "
            "생년월일시는 넣지 않아도 되며, 궁금한 키워드를 댓글로 알려 주세요."
        )
    else:
        paras.append(
            "더 구체적인 금액·기간·상품명을 알려 주시면 댓글로 이어서 설명드리겠습니다."
        )
    src = format_knowledge_sources(cards)
    if src:
        paras.append(src)
    return "\n\n".join(paras)
