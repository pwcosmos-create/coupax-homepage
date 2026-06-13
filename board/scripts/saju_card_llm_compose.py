#!/usr/bin/env python3
"""
PASS 확정 학습 카드 — 템플릿 초안을 Gemini 2.5로 **1회만** 다듬어 저장.

재호출 방지 (저장본 재사용)
  카드에 ``llm_composed_at``(ISO 시각 문자열)이 있으면 Gemini/Ollama를 **다시 호출하지 않습니다**.
  ``eligible()``·``batch_polish(only_missing=True)``·위원회 PASS 후 ``polish_card_after_pass()`` 모두
  이 필드를 먼저 확인합니다. 이미 다듬어진 ``body``·``title``·``summary``·``tags``를 그대로 쓰며,
  API 비용·중복 작업·본문 덮어쓰기를 막습니다.

  다시 LLM을 돌리려면 (수동·비권장): ``llm_composed_at``·``llm_compose_model``·
  ``llm_compose_provider`` 필드를 카드 JSON에서 지운 뒤 ``run``/``batch`` 실행.

환경 변수
  SAJU_COMPOSE_LLM=1
  SAJU_CARD_LLM_PROVIDER=gemini   (기본 gemini 전용, Groq·Ollama 미사용)
  SAJU_CARD_LLM_ALLOW_OLLAMA_FALLBACK=0
  GEMINI_API_KEY=...              Google AI Studio
  SAJU_CARD_GEMINI_MODEL=gemini-2.5-flash

명령
  python scripts/saju_card_llm_compose.py status
  python scripts/saju_card_llm_compose.py run --card-id 12
  python scripts/saju_card_llm_compose.py batch --count 3 --sleep 15
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_saju_learn as learn  # noqa: E402

try:
    import board_env

    board_env.load_board_env()
except ImportError:
    pass

FOOTER_MARK = "본 내용은 명리 참고용"
STANDARD_FOOTER = (
    " 본 내용은 명리 참고용이며 확정 예언·의학·법률·투자 자문이 아닙니다. "
    "가능성·경향으로 해석하며, 학파·환경에 따라 달라질 수 있습니다."
)

_LLM_MODES = frozenset(
    {"realtime", "initial", "recert_after_fix", "copy_optimize"}
)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def llm_enabled() -> bool:
    return os.getenv("SAJU_COMPOSE_LLM", "1").strip().lower() in ("1", "true", "yes")


def llm_scope() -> str:
    return (os.getenv("SAJU_COMPOSE_LLM_SCOPE", "interpretive") or "interpretive").strip().lower()


def gemini_api_key() -> str:
    """board/.env 전용 — coupax_app·GOOGLE_API_KEY 와 분리."""
    return (os.getenv("GEMINI_API_KEY") or "").strip()


def gemini_enabled() -> bool:
    return bool(gemini_api_key())


def ollama_enabled() -> bool:
    return os.getenv("GEMMA_OLLAMA_ENABLED", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def allow_ollama_fallback() -> bool:
    return os.getenv("SAJU_CARD_LLM_ALLOW_OLLAMA_FALLBACK", "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def llm_provider() -> str:
    """사주 카드 해설 — 기본 Gemini 2.5만 (Groq·Ollama 폴백 없음)."""
    pref = (os.getenv("SAJU_CARD_LLM_PROVIDER") or "gemini").strip().lower()
    if pref not in ("", "gemini"):
        pref = "gemini"
    if gemini_enabled():
        return "gemini"
    if allow_ollama_fallback() and pref == "ollama" and ollama_enabled():
        return "ollama"
    return ""


def gemini_model() -> str:
    return (os.getenv("SAJU_CARD_GEMINI_MODEL") or "gemini-2.5-flash").strip()


def llm_available() -> bool:
    return bool(llm_provider())


def _is_pass(card: dict) -> bool:
    return (card.get("council_status") or "").strip() == "pass" or card.get(
        "council_pass"
    ) is True


def eligible(card: dict | None, *, mode: str = "") -> bool:
    """LLM 다듬기 대상 여부. ``llm_composed_at``이 있으면 False(저장본 재사용)."""
    if not llm_enabled() or not llm_available():
        return False
    if not isinstance(card, dict) or (card.get("status") or "") != "confirmed":
        return False
    if not _is_pass(card):
        return False
    if (card.get("llm_composed_at") or "").strip():
        return False
    if mode and mode not in _LLM_MODES:
        return False
    style = (card.get("card_style") or "").strip()
    title = (card.get("title") or "").strip()
    if llm_scope() == "all":
        return True
    if style == "interpretive" or title.startswith("해석·") or title.startswith("심층·"):
        return True
    return False


def _strip_footer(text: str) -> str:
    out = (text or "").strip()
    while FOOTER_MARK in out:
        out = out[: out.find(FOOTER_MARK)].rstrip()
    return out


def _gemini_generate(prompt: str) -> tuple[str | None, str]:
    """Google AI Gemini 2.5 generateContent."""
    api_key = gemini_api_key()
    model = gemini_model()
    if not api_key:
        return None, ""
    url = f"{GEMINI_API_BASE}/models/{model}:generateContent?key={api_key}"
    temp = float(os.getenv("SAJU_CARD_GEMINI_TEMPERATURE", "0.5"))
    max_tokens = int(os.getenv("SAJU_CARD_GEMINI_MAX_TOKENS", "12000") or "12000")
    timeout = int(os.getenv("SAJU_CARD_GEMINI_TIMEOUT_SEC", "120") or "120")

    payload = {
        "systemInstruction": {
            "parts": [
                {
                    "text": (
                        "당신은 한국어 사주 명리 상담 카드 전문 작가입니다. "
                        "따뜻하고 읽기 쉬운 상담 문체로, 규칙을 정확히 지킵니다."
                    )
                }
            ]
        },
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temp,
            "maxOutputTokens": max_tokens,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        candidates = data.get("candidates") or []
        if not candidates:
            return None, model
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(
            (p.get("text") or "") for p in parts if isinstance(p, dict)
        ).strip()
        return (text if len(text) >= 200 else None), model
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            err_body = str(e)
        return None, f"{model}:{e.code}:{err_body[:80]}"
    except Exception:
        return None, model


def _ollama_generate(prompt: str) -> tuple[str | None, str]:
    model = (
        os.environ.get("SAJU_CARD_LLM_MODEL")
        or os.environ.get("GEMMA_OLLAMA_MODEL")
        or "gemma:2b"
    ).strip()
    if not model or not ollama_enabled():
        return None, ""
    timeout = int(os.environ.get("SAJU_CARD_LLM_TIMEOUT_SEC", "120") or "120")
    temp = float(os.environ.get("SAJU_CARD_LLM_TEMPERATURE", "0.45"))
    base = os.environ.get(
        "GEMMA_OLLAMA_URL", "http://127.0.0.1:11434/api/generate"
    ).strip()
    host = base.rsplit("/api/", 1)[0] if "/api/" in base else "http://127.0.0.1:11434"
    chat_url = f"{host}/api/chat"
    payload = {
        "model": model,
        "stream": False,
        "messages": [{"role": "user", "content": prompt}],
        "options": {"temperature": temp, "num_predict": 1800},
    }
    try:
        req = urllib.request.Request(
            chat_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = ((data.get("message") or {}).get("content") or "").strip()
        return (text if len(text) >= 200 else None), model
    except Exception:
        return None, model


def generate_polish_text(prompt: str) -> tuple[str | None, str, str]:
    """(text, model_label, provider) — Gemini만."""
    provider = llm_provider()
    if provider == "gemini":
        text, label = _gemini_generate(prompt)
        if text:
            return text, label or gemini_model(), "gemini"
    if allow_ollama_fallback() and ollama_enabled():
        text, label = _ollama_generate(prompt)
        if text:
            return text, label, "ollama"
    return None, "", provider or "none"


def _build_prompt(card: dict) -> str:
    title = (card.get("title") or "").strip()
    draft = _strip_footer(card.get("body") or "")[:4000]
    return f"""아래 [초안]을 바탕으로 **풍부한 사주 명리 상담 카드 본문**을 한국어로 작성하세요.
전체 분량은 **최소 3,000자 이상**이 되도록 매우 깊이 있고 방대하게 작성하세요. 각 절(【】)마다 최소 400자~600자 이상의 분량을 꽉 채우세요.

[규칙]
- 메타 설명(「~로 씁니다」「절차는」「작성하세요」) 절대 금지. 실제 상담 풀이 문장만.
- 아래 7개 절 제목을 **한 줄에 그대로** 쓴 뒤 본문을 이어 쓰세요(제목 생략·변형 금지).
  【인사·성향】
  【명식·구조】
  【오행·십신 해석】
  【시기·운세】
  【테마 풀이】
  【실천 조언】
  【주의】
- [가독성 강제 규칙]: 스마트폰에서 읽기 편하도록 **반드시 3~4문장마다 줄바꿈(엔터 2번)**을 하세요. 
- [디자인 규칙]: 문단에서 가장 중요한 1~2개의 핵심 키워드나 문장은 반드시 **굵은 글씨(**텍스트**)**로 강조하세요.
- [전문성+대중성 규칙]: 각 단락의 시작이나 중요 설명에서는 먼저 **전문 명리학 용어(예: 재생관, 괴강살 등)**를 언급하여 신뢰도를 높인 뒤, 바로 이어서 **누구나 이해하기 쉬운 찰떡같은 비유(예: 폭풍우 속의 바위)**를 덧붙여 설명하세요.
- 「안녕하세요」「귀하」「~하신 분」「~경향이 있습니다」「~보이기 쉽습니다」 따뜻한 상담 톤.
- 오행·십신·대운·세운을 자연스럽게 엮고, 초안의 핵심 키워드를 빠뜨리지 마세요.
- 확정 예언·질병명·투자 종목·이혼·사망·합격·승진 **시기** 단정 금지.
- 【주의】에 참고용·면책 3문장 이상.
- 제목 주제: {title}

[초안]
{draft}
"""


_SECTION_LABELS = (
    "【인사·성향】",
    "【명식·구조】",
    "【오행·십신 해석】",
    "【시기·운세】",
    "【테마 풀이】",
    "【실천 조언】",
    "【주의】",
)
_REQUIRED_MARKERS = _SECTION_LABELS


def _structure_fallback(body: str) -> str:
    """모델이 절 제목을 빼먹었을 때 문단·문장 단위로 7절 구조를 붙입니다."""
    text = re.sub(r"\n{3,}", "\n\n", (body or "").strip())
    if not text:
        return ""
    paras = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
    n = len(_SECTION_LABELS)
    if len(paras) >= n:
        return "\n\n".join(
            f"{_SECTION_LABELS[i]}\n{paras[i]}" for i in range(n)
        )
    sents = [
        s.strip()
        for s in re.split(r"(?<=[.。!?])\s+", text)
        if s.strip()
    ]
    if len(sents) < n:
        return f"{_SECTION_LABELS[0]}\n{text}"
    per = max(1, len(sents) // n)
    chunks: list[str] = []
    idx = 0
    for si in range(n):
        take = per if si < n - 1 else len(sents) - idx
        part = " ".join(sents[idx : idx + take])
        idx += take
        chunks.append(f"{_SECTION_LABELS[si]}\n{part}")
    return "\n\n".join(chunks)


def _normalize_body(text: str) -> str:
    try:
        from saju_card_reverify_enrich import format_readable_body

        text = format_readable_body(text or "")
    except ImportError:
        text = (text or "").strip()
    body = re.sub(r"\n{3,}", "\n\n", text)
    body = _strip_footer(body)
    if not all(m in body for m in _REQUIRED_MARKERS):
        if len(body) >= 400:
            body = _structure_fallback(body)
        else:
            return ""
    if not all(m in body for m in _REQUIRED_MARKERS):
        return ""
    if len(body) < 400:
        return ""
    if FOOTER_MARK not in body:
        body = body.rstrip("。. ") + STANDARD_FOOTER
    return body[:24000]


def polish_card_after_pass(card_id: int, *, mode: str = "realtime") -> dict:
    """PASS 카드 1건 — Gemini 2.5(기본) 1회 다듬기.

    ``llm_composed_at``이 이미 있으면 API를 호출하지 않고 ``skipped``·
    ``reason=already_llm_composed``로 반환합니다(저장본 재사용).
    실패 시 기존 초안·이전 본문은 유지합니다.
    """
    card = learn.get_card(card_id)
    if not card:
        return {"ok": False, "card_id": card_id, "error": "not_found"}
    if (card.get("llm_composed_at") or "").strip():
        return {
            "ok": True,
            "card_id": card_id,
            "skipped": True,
            "reason": "already_llm_composed",
            "llm_composed_at": (card.get("llm_composed_at") or "").strip(),
        }
    if not eligible(card, mode=mode):
        return {
            "ok": True,
            "card_id": card_id,
            "skipped": True,
            "reason": "not_eligible",
        }

    prompt = _build_prompt(card)
    raw, model_label, provider = generate_polish_text(prompt)
    if not raw:
        return {
            "ok": False,
            "card_id": card_id,
            "error": f"{provider}_failed",
            "provider": provider,
        }

    body = _normalize_body(raw)
    if not body:
        return {
            "ok": False,
            "card_id": card_id,
            "error": "normalize_failed",
            "provider": provider,
        }

    try:
        from saju_card_copy_optimize import optimize_summary, optimize_tags, optimize_title

        title = optimize_title({"title": card.get("title"), "body": body})
        summary = optimize_summary(title, body)
        tags = optimize_tags(body, title, card.get("tags"))
    except ImportError:
        title = card.get("title")
        summary = learn._summary(body, 160)
        tags = card.get("tags")

    model_note = f"gemini:{model_label}" if provider == "gemini" else model_label
    note = (
        f"{(card.get('note') or '').strip()}\n[Gemini 다듬기 {_now()}] {model_note}"
    ).strip()[:500]

    updated = learn.update_confirmed_card(
        card_id,
        title=title,
        body=body,
        summary=summary,
        tags=tags,
        note=note,
        llm_composed_at=_now(),
        llm_compose_model=model_note[:60],
        llm_compose_provider=provider,
    )
    if not updated:
        return {"ok": False, "card_id": card_id, "error": "update_failed"}

    try:
        import agent_office_log

        agent_office_log.append_message(
            from_id="saju_reader",
            kind="conclusion",
            text=(
                f"[Gemini 카드 #{card_id}] {(title or '')[:50]} "
                f"— {model_label} 저장"
            ),
            division="saju-learn",
        )
    except Exception:
        pass

    return {
        "ok": True,
        "card_id": card_id,
        "title": (title or "")[:60],
        "body_len": len(body),
        "model": model_label,
        "provider": provider,
    }


def batch_polish(
    count: int = 5, *, sleep_sec: float = 15, only_missing: bool = True
) -> dict:
    """PASS 카드 일괄 다듬기.

    ``only_missing=True``(기본)이면 ``llm_composed_at`` 없는 카드만 대상 —
    cron·수동 batch가 이미 Gemini 처리된 카드를 다시 부르지 않습니다.
    """
    cards = [
        c
        for c in learn.load_store().get("cards") or []
        if isinstance(c, dict) and c.get("status") == "confirmed" and _is_pass(c)
    ]
    if only_missing:
        cards = [c for c in cards if not (c.get("llm_composed_at") or "").strip()]
    cards = [c for c in cards if eligible(c, mode="initial")]
    cards.sort(key=lambda c: int(c.get("id") or 0))
    count = min(int(count), len(cards), 30)
    done: list[dict] = []
    for c in cards[:count]:
        cid = int(c["id"])
        row = polish_card_after_pass(cid, mode="initial")
        done.append(row)
        if sleep_sec > 0:
            time.sleep(sleep_sec)
    ok = sum(1 for r in done if r.get("ok") and not r.get("skipped"))
    return {"requested": count, "polished": ok, "provider": llm_provider(), "rows": done}


def main() -> int:
    p = argparse.ArgumentParser(description="PASS 카드 Gemini 2.5 본문 다듬기")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("status", help="설정·대기 건수")
    one = sub.add_parser("run", help="카드 1건")
    one.add_argument("--card-id", type=int, required=True)
    bat = sub.add_parser("batch", help="PASS 카드 일괄")
    bat.add_argument("--count", type=int, default=3)
    bat.add_argument("--sleep", type=float, default=15)
    args = p.parse_args()

    if args.cmd == "status":
        cards = learn.load_store().get("cards") or []
        passed = [c for c in cards if isinstance(c, dict) and _is_pass(c)]
        missing = [
            c
            for c in passed
            if not (c.get("llm_composed_at") or "").strip()
            and eligible(c, mode="initial")
        ]
        print(
            {
                "llm_enabled": llm_enabled(),
                "provider": llm_provider(),
                "gemini_only": not allow_ollama_fallback(),
                "gemini_model": gemini_model(),
                "gemini_key": bool(gemini_api_key()),
                "scope": llm_scope(),
                "pass_total": len(passed),
                "gemini_pending": len(missing),
            }
        )
        return 0
    if args.cmd == "run":
        print(polish_card_after_pass(args.card_id, mode="initial"))
        return 0
    if args.cmd == "batch":
        print(batch_polish(args.count, sleep_sec=args.sleep))
        return 0
    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
