#!/usr/bin/env python3
"""관상 학습 카드 — Gemini로 RL 확장 토픽 본문 제작 (SEO 200자+).

  GWANSANG_COMPOSE_LLM=1
  GEMINI_API_KEY=...
  GWANSANG_CARD_GEMINI_MODEL=gemini-2.5-flash

  python scripts/gwansang_card_llm_compose.py status
  python scripts/gwansang_card_llm_compose.py compose --seed rl_gwansang_eyebrow
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

try:
    import board_env

    board_env.load_board_env()
except ImportError:
    pass

import agent_office_gwansang_learn as learn  # noqa: E402
from gwansang_card_catalog import MIN_BODY_CHARS  # noqa: E402

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
FOOTER = (
    " 본 내용은 관상 해석 참고용이며 확정 예언·의학·법률·투자 자문이 아닙니다. "
    "경향·가능성으로 해석하며 개인차가 있습니다."
)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def llm_enabled() -> bool:
    return os.getenv("GWANSANG_COMPOSE_LLM", "1").strip().lower() in ("1", "true", "yes")


def gemini_api_key() -> str:
    return (os.getenv("GEMINI_API_KEY") or "").strip()


def gemini_model() -> str:
    return (os.getenv("GWANSANG_CARD_GEMINI_MODEL") or "gemini-2.5-flash").strip()


def llm_available() -> bool:
    return llm_enabled() and bool(gemini_api_key())


def _gemini_generate(prompt: str) -> tuple[str | None, str]:
    api_key = gemini_api_key()
    model = gemini_model()
    if not api_key:
        return None, ""
    url = f"{GEMINI_API_BASE}/models/{model}:generateContent?key={api_key}"
    temp = float(os.getenv("GWANSANG_CARD_GEMINI_TEMPERATURE", "0.45"))
    max_tokens = int(os.getenv("GWANSANG_CARD_GEMINI_MAX_TOKENS", "4096") or "4096")
    timeout = int(os.getenv("GWANSANG_CARD_GEMINI_TIMEOUT_SEC", "90") or "90")
    payload = {
        "systemInstruction": {
            "parts": [
                {
                    "text": (
                        "당신은 한국어 관상(관相) 학습 카드 작가입니다. "
                        "SEO 200자 이상, 【부위】 소제목, 경향·참고 톤을 지킵니다."
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
        parts = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
        text = "".join((p.get("text") or "") for p in parts if isinstance(p, dict)).strip()
        return (text if len(text) >= MIN_BODY_CHARS else None), model
    except Exception:
        return None, model


def _build_prompt(topic: dict) -> str:
    title = (topic.get("title") or "").strip()
    hint = (topic.get("hint") or "").strip()
    category = (topic.get("category") or "feature").strip()
    return f"""관상 학습 카드 본문을 작성하세요.

[제목] {title}
[분류] {category}
[작성 힌트] {hint}

[규칙]
- 본문 **{MIN_BODY_CHARS}자 이상** 한국어
- 첫 줄에 【부위명】 형태 소제목 1개 이상
- 전통 관상 + 현대 참고(습관·커뮤니케이션) 균형
- 불길·질병·투자·궁합 단정 금지, '경향·가능성·참고' 톤
- 실명·연락처·사진 식별 정보 금지
- 마지막에 SEO 키워드(관상, 얼굴, 해당 부위)를 자연스럽게 1문장 포함
- 제목·본문만 출력 (메타 설명 없음)
"""


def compose_topic(
    topic: dict,
    *,
    agent_id: str = "gwansang_compose",
    confirm: bool = True,
) -> dict | None:
    """RL 토픽 1건 → 카드 추가(+확정)."""
    if not llm_available():
        return None
    seed = (topic.get("catalog_seed") or "").strip()
    title = (topic.get("title") or "").strip()
    if seed and learn.find_card_by_seed(seed):
        return {"skipped": True, "catalog_seed": seed, "reason": "exists"}
    if title and learn.title_taken(title):
        return {"skipped": True, "title": title, "reason": "title_taken"}

    body, model = _gemini_generate(_build_prompt(topic))
    if not body:
        return None
    if FOOTER.strip() not in body:
        body = body.rstrip() + FOOTER

    card = learn.add_card(
        body=body,
        title=title,
        source="rl_gemini",
        catalog_seed=seed,
        category=topic.get("category") or "",
        agent_id=agent_id,
        revise_if_seed_exists=False,
    )
    cid = card.get("id")
    if confirm and isinstance(cid, int):
        learn.confirm_card(int(cid))
        card = learn.find_card_by_seed(seed) if seed else card
    return {
        "card_id": cid,
        "title": card.get("title") if card else title,
        "catalog_seed": seed,
        "status": card.get("status") if card else "pending",
        "llm_model": model,
        "agent_id": agent_id,
    }


def status() -> dict:
    return {
        "llm_enabled": llm_enabled(),
        "llm_available": llm_available(),
        "model": gemini_model(),
        "min_body": MIN_BODY_CHARS,
        "cards": learn.stats(),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("status")
    c = sub.add_parser("compose")
    c.add_argument("--seed", required=True)
    args = p.parse_args()
    if args.cmd == "status":
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "compose":
        from gwansang_rl_topics import all_expansion_topics

        row = next(
            (t for t in all_expansion_topics() if t.get("catalog_seed") == args.seed),
            None,
        )
        if not row:
            print(json.dumps({"error": "unknown seed"}, ensure_ascii=False))
            return 1
        out = compose_topic(row)
        print(json.dumps(out or {"error": "compose failed"}, ensure_ascii=False, indent=2))
        return 0 if out and not out.get("skipped") else 1
    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
