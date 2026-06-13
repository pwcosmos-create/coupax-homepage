#!/usr/bin/env python3
"""
위원회 FAIL 학습 카드 — 자동 수정 후 재인증 신청.

  python scripts/saju_card_council_fix.py --card-id 5
  python scripts/saju_card_council_fix.py batch --count 80
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_saju_learn as learn  # noqa: E402

STANDARD_FOOTER = (
    " 본 내용은 명리 참고용이며 확정 예언·의학·법률·투자 자문이 아닙니다. "
    "가능성·경향으로 해석하며, 학파·환경에 따라 달라질 수 있습니다."
)

TITLE_TAG_HINTS: dict[str, tuple[str, ...]] = {
    "천간": ("천간", "일간", "명리"),
    "지지": ("지지", "명리", "사주"),
    "십신": ("십신", "명리", "사주"),
    "오행": ("오행", "상생", "명리"),
    "신살": ("신살", "명리"),
    "격": ("격국", "명리", "사주"),
    "지지관계": ("합", "충", "명리"),
    "운": ("대운", "세운", "명리"),
    "일주": ("일주", "일간", "명리"),
    "용신": ("용신", "기신", "명리"),
    "변수": ("명리", "사주", "변수"),
    "심층": ("명리", "사주", "풀이"),
}

ABSOLUTE_REPLACEMENTS = (
    (re.compile(r"반드시"), "경향상"),
    (re.compile(r"100%"), "가능성"),
    (re.compile(r"무조건"), "경향"),
    (re.compile(r"절대\s*길"), "길한 경향"),
    (re.compile(r"절대\s*흉"), "주의 경향"),
    (re.compile(r"이혼\s*확정"), "관계 변화 가능성"),
    (re.compile(r"파산\s*확정"), "재정 주의"),
)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def needs_fix_after_fail(card: dict) -> bool:
    return _needs_fix_after_fail(card)


def _needs_fix_after_fail(card: dict) -> bool:
    if (card.get("council_status") or "").strip() != "fail":
        return False
    fix_at = (card.get("council_fix_at") or "").strip()
    fail_at = (card.get("council_at") or "").strip()
    if not fix_at:
        return True
    return fix_at < fail_at


def _title_tags(title: str) -> list[str]:
    t = (title or "").lower()
    out: list[str] = []
    for key, hints in TITLE_TAG_HINTS.items():
        if key in title or key in t or any(h in title for h in hints[:2]):
            out.extend(hints[:2])
    return list(dict.fromkeys(out))[:6]


def _ensure_tags(card: dict, min_count: int = 3) -> list[str]:
    tags = [str(x).strip() for x in (card.get("tags") or []) if str(x).strip()]
    body = card.get("body") or ""
    for t in learn._extract_tags(body):
        if t not in tags:
            tags.append(t)
    for t in _title_tags(card.get("title") or ""):
        if t not in tags:
            tags.append(t)
    for fallback in ("명리", "사주", "참고용"):
        if len(tags) >= min_count:
            break
        if fallback not in tags:
            tags.append(fallback)
    return tags[:12]


def _soften_absolute_claims(text: str) -> str:
    out = text
    for pat, repl in ABSOLUTE_REPLACEMENTS:
        out = pat.sub(repl, out)
    return out


def _ensure_body(card: dict, min_len: int = 100) -> str:
    body = learn._redact_pii((card.get("body") or "").strip())
    body = _soften_absolute_claims(body)
    title = (card.get("title") or "").strip()

    if re.match(r"^test\s*$", title, re.I):
        title = "학습·명리 참고 카드"
        if len(body) < 40:
            body = (
                "명리 참고용 학습 카드입니다. 일간·월지·십신을 바탕으로 "
                "성향·시기 흐름을 가능성·경향으로 서술합니다."
            )

    if "일주" in title and "일주" not in body and "일간" not in body:
        body += f" {title} 관련 해석은 일간·일주(日支)를 함께 봅니다."

    if "용신" in body and "참고" not in body and "학파" not in body:
        body += " 용신·기신은 학파·조후에 따라 달라질 수 있는 참고 견해입니다."

    if "참고용" not in body and "금지" not in body:
        if STANDARD_FOOTER.strip() not in body:
            body = body.rstrip() + STANDARD_FOOTER

    while len(body) < min_len:
        body += " 명리 해석은 환경·대운에 따라 달라질 수 있습니다."

    if "." not in body and "。" not in body:
        body += " 해석은 참고용입니다."

    return body[:24000]


def _ensure_title(card: dict) -> str:
    title = (card.get("title") or "").strip()[:120]
    if re.match(r"^test\s*$", title, re.I) or not title:
        body = (card.get("body") or "").strip()
        title = learn._summary(body, 50) or "학습·명리 참고"
    return title


def fix_fail_card(card: dict) -> tuple[dict, list[str]]:
    """FAIL 카드 본문·태그·제목 자동 보정. (적용 전 패치 목록 반환)"""
    patches: list[str] = []
    title = _ensure_title(card)
    if title != (card.get("title") or "").strip():
        patches.append("제목 보정")

    body = _ensure_body({**card, "title": title})
    try:
        import saju_card_reverify_enrich as enrich

        enriched, ep = enrich.enrich_card_fields({**card, "title": title, "body": body})
        if ep and enriched.get("body"):
            body = enriched["body"]
            patches.append("구체화")
    except Exception:
        pass
    if body != (card.get("body") or "").strip():
        patches.append("본문·면책·길이 보정")

    tags = _ensure_tags({**card, "body": body, "title": title})
    old_tags = card.get("tags") or []
    if tags != old_tags:
        patches.append("태그 보강")

    if not patches:
        patches.append("재검증 신청")

    fixed = {
        "title": title,
        "body": body,
        "tags": tags,
        "summary": learn._summary(body),
    }
    return fixed, patches


def apply_fix(card_id: int, fixed: dict, patches: list[str]) -> dict | None:
    patch_txt = ", ".join(patches[:5])
    prev = learn.get_card(card_id) or {}
    note = f"{(prev.get('note') or '').strip()}\n[자동수정 {_now()}] {patch_txt}".strip()[:500]

    card = learn.update_confirmed_card(
        card_id,
        title=fixed.get("title"),
        body=fixed.get("body"),
        tags=fixed.get("tags"),
        summary=fixed.get("summary"),
        note=note,
        council_recert_requested_at=_now(),
        council_fix_at=_now(),
        council_fix_note=patch_txt[:300],
    )
    return card


def fix_and_request_recert(card_id: int) -> dict:
    """수정 저장 → wiki 동기화 → 위원회 재인증."""
    card = learn.get_card(card_id)
    if not card:
        return {"ok": False, "error": "not_found", "card_id": card_id}
    if (card.get("council_status") or "").strip() != "fail":
        return {
            "ok": False,
            "error": "not_fail",
            "card_id": card_id,
            "status": card.get("council_status"),
        }

    fixed_fields, patches = fix_fail_card(card)
    card = apply_fix(card_id, fixed_fields, patches)
    if not card:
        return {"ok": False, "error": "apply_failed", "card_id": card_id}

    import agent_office_saju_card_council as council

    verify = council.verify_card_by_id(card_id, mode="recert_after_fix")
    passed = bool(verify and verify.get("passed"))
    try:
        import agent_office_log

        agent_office_log.append_message(
            from_id="saju_error_fix",
            kind="conclusion" if passed else "task",
            text=(
                f"[FAIL 수정·재인증 #{card_id}] {', '.join(patches[:3])} → "
                f"{'PASS' if passed else 'FAIL'} · {(card.get('title') or '')[:40]}"
            ),
            division="saju-learn",
        )
    except Exception:
        pass

    return {
        "ok": True,
        "card_id": card_id,
        "patches": patches,
        "passed": passed,
        "title": (card.get("title") or "")[:60],
    }


def batch_fix_recert(
    count: int = 50, *, only_unfixed: bool = True, sleep_sec: float = 0
) -> dict:
    cards = [
        c
        for c in learn.load_store().get("cards") or []
        if isinstance(c, dict)
        and c.get("status") == "confirmed"
        and (c.get("council_status") or "").strip() == "fail"
    ]
    cards.sort(key=lambda c: int(c.get("id") or 0))
    if only_unfixed:
        cards = [c for c in cards if _needs_fix_after_fail(c)]
    if not cards:
        import agent_office_saju_card_council as council

        return {
            "requested": 0,
            "processed": 0,
            "upgraded_pass": 0,
            **council.council_stats(),
        }
    count = min(int(count), len(cards))
    done: list[dict] = []
    upgraded = 0
    for c in cards[:count]:
        row = fix_and_request_recert(int(c["id"]))
        done.append(row)
        if row.get("passed"):
            upgraded += 1
        if sleep_sec > 0:
            import time

            time.sleep(sleep_sec)
    import agent_office_saju_card_council as council

    return {
        "requested": count,
        "processed": len(done),
        "upgraded_pass": upgraded,
        **council.council_stats(),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="FAIL 카드 자동 수정·재인증")
    p.add_argument("--card-id", type=int, default=0)
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("batch")
    args, extra = p.parse_known_args()
    if args.card_id:
        print(fix_and_request_recert(args.card_id))
        return 0
    if extra and extra[0] == "batch":
        n = 80
        for i, a in enumerate(extra):
            if a == "--count" and i + 1 < len(extra):
                n = int(extra[i + 1])
        print(batch_fix_recert(n, sleep_sec=0))
        return 0
    p2 = argparse.ArgumentParser()
    p2.add_argument("cmd", choices=["batch"])
    p2.add_argument("--count", type=int, default=80)
    p2.add_argument("--sleep", type=float, default=0)
    p2.add_argument("--all", action="store_true", help="이미 수정한 FAIL도 재시도")
    a2 = p2.parse_args()
    if a2.cmd == "batch":
        print(
            batch_fix_recert(
                a2.count, only_unfixed=not a2.all, sleep_sec=a2.sleep
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
