#!/usr/bin/env python3
"""
사주 학습 카드 문구 최적화 — 제목·본문·요약·태그 정리 후 pack·Wiki·재인증.

  python scripts/saju_card_copy_optimize.py --dry-run
  python scripts/saju_card_copy_optimize.py --all
  python scripts/saju_card_copy_optimize.py --card-id 3
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

try:
    from saju_structure_audit import _extract_tags_enhanced
except ImportError:
    _extract_tags_enhanced = None  # type: ignore

FOOTER_MARK = "본 내용은 명리 참고용"
STANDARD_FOOTER = (
    " 본 내용은 명리 참고용이며 확정 예언·의학·법률·투자 자문이 아닙니다. "
    "가능성·경향으로 해석하며, 학파·환경에 따라 달라질 수 있습니다."
)

_RE_SPACES = re.compile(r"[ \t]+")
_RE_MULTI_PERIOD = re.compile(r"[.。]{2,}")
_RE_BEFORE_HOOK = re.compile(
    r"([가-힣])(?<![.!?。])(\s+)(?=[①②③④⑤⑥⑦⑧⑨【「])"
)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _strip_footers(text: str) -> str:
    out = text
    while FOOTER_MARK in out:
        idx = out.find(FOOTER_MARK)
        out = out[:idx].rstrip()
    return out.strip()


def _ensure_punctuation(body: str) -> str:
    if not body:
        return body
    if "." not in body and "。" not in body and "!" not in body:
        body = re.sub(
            r"(다|요|음|임|한다|됩니다|합니다)(\s+)(?=[가-힣①②③【])",
            r"\1. ",
            body,
        )
    body = _RE_MULTI_PERIOD.sub("。", body)
    if body and body[-1] not in ".!?。":
        body += "。"
    return body


def _split_dense_clauses(body: str) -> str:
    """쉼표·접속 과다 구간에 문장 경계 보강."""
    body = re.sub(
        r",\s*(?=[가-힣])",
        ". ",
        body,
    )
    body = _RE_BEFORE_HOOK.sub(r"\1. ", body)
    return body


def optimize_title(card: dict) -> str:
    title = learn._redact_pii((card.get("title") or "").strip())[:120]
    if re.match(r"^test\s*$", title, re.I):
        body = (card.get("body") or "").strip()
        title = learn._summary(_strip_footers(body), 48) or "명리 학습·일주 참고"
    title = _RE_SPACES.sub(" ", title)
    if title.startswith("변수") and not title.startswith("변수·"):
        title = title.replace("변수", "변수·", 1)
    if len(title) > 60:
        if "일주" in title and "병화" in title:
            title = "일주·병화 명리 참고"
        elif title.startswith("변수·"):
            title = title[:60].rstrip("· ").strip()
        else:
            title = learn._summary(title, 52)
    return title


def optimize_body(card: dict, title: str) -> str:
    body = learn._redact_pii(_strip_footers(card.get("body") or ""))
    body = _RE_SPACES.sub(" ", body).strip()

    if title.startswith("변수·") and not body.startswith("【"):
        key = title.replace("변수·", "", 1).strip()
        if key and key[:12] not in body[:40]:
            body = f"【{key}】 {body}"

    if title.startswith("심층·") and "【심층" not in body[:20]:
        body = f"【{title}】 {body}"

    body = _split_dense_clauses(body)
    body = _ensure_punctuation(body)

    if FOOTER_MARK not in body:
        body = body.rstrip("。. ") + STANDARD_FOOTER

    return body[:24000]


def optimize_summary(title: str, body: str) -> str:
    core = _strip_footers(body)
    sentences = re.split(r"(?<=[.!?。])\s+", core)
    sentences = [s.strip() for s in sentences if len(s.strip()) >= 12]
    if not sentences:
        hook = learn._summary(core, 120)
    elif len(sentences) == 1:
        hook = sentences[0]
    else:
        hook = sentences[0]
        if len(sentences[0]) < 80 and len(sentences) > 1:
            hook = f"{sentences[0]} {sentences[1]}"
    hook = _RE_SPACES.sub(" ", hook).strip()
    if title and title[:20] not in hook:
        line = f"「{title}」 {hook}"
    else:
        line = hook
    return learn._summary(line, 158)


def optimize_tags(body: str, title: str, existing: list | None) -> list[str]:
    old = [str(t).strip() for t in (existing or []) if str(t).strip()]
    blob = f"{title}\n{body}"
    if _extract_tags_enhanced:
        tags = _extract_tags_enhanced(blob, old)
    else:
        tags = list(old)
        for t in learn._extract_tags(blob):
            if t not in tags:
                tags.append(t)
    for fallback in ("명리", "사주"):
        if len(tags) >= 2:
            break
        if fallback not in tags:
            tags.append(fallback)
    return tags[:16]


def optimize_card(card: dict) -> tuple[dict, list[str]]:
    patches: list[str] = []
    title = optimize_title(card)
    if title != (card.get("title") or "").strip():
        patches.append("제목")

    body = optimize_body(card, title)
    try:
        import saju_card_reverify_enrich as enrich

        enriched, ep = enrich.enrich_card_fields(
            {**card, "title": title, "body": body}
        )
        if ep and enriched.get("body"):
            body = enriched["body"]
            patches.append("구체화")
    except Exception:
        pass
    if body != (card.get("body") or "").strip():
        patches.append("본문")

    summary = optimize_summary(title, body)
    old_sum = (card.get("summary") or "").strip()
    if summary != old_sum and old_sum[:80] == (card.get("body") or "")[:80]:
        patches.append("요약(본문복붙 해소)")
    elif summary != old_sum:
        patches.append("요약")

    tags = optimize_tags(body, title, card.get("tags"))
    if tags != (card.get("tags") or []):
        patches.append("태그")

    if not patches:
        patches.append("미세")

    return {
        "title": title,
        "body": body,
        "summary": summary,
        "tags": tags,
    }, patches


def apply_optimize(card_id: int, *, dry_run: bool = False) -> dict:
    card = learn.get_card(card_id)
    if not card or (card.get("status") or "") != "confirmed":
        return {"ok": False, "card_id": card_id, "error": "not_confirmed"}

    optimized, patches = optimize_card(card)
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "card_id": card_id,
            "patches": patches,
            "title": optimized["title"][:60],
            "summary_preview": optimized["summary"][:100],
        }

    prev_note = (card.get("note") or "").strip()
    note = f"{prev_note}\n[문구최적화 {_now()}] {', '.join(patches)}".strip()[:500]
    updated = learn.update_confirmed_card(
        card_id,
        title=optimized["title"],
        body=optimized["body"],
        summary=optimized["summary"],
        tags=optimized["tags"],
        note=note,
        copy_optimized_at=_now(),
    )
    if not updated:
        return {"ok": False, "card_id": card_id, "error": "save_failed"}

    import agent_office_saju_card_council as council

    verify = council.verify_card_by_id(card_id, mode="copy_optimize")
    return {
        "ok": True,
        "card_id": card_id,
        "patches": patches,
        "passed": bool(verify and verify.get("passed")),
        "title": optimized["title"][:60],
    }


def batch_optimize(
    *,
    limit: int = 500,
    dry_run: bool = False,
    sleep_sec: float = 0,
    recert: bool = True,
) -> dict:
    cards = [
        c
        for c in learn.load_store().get("cards") or []
        if isinstance(c, dict) and c.get("status") == "confirmed"
    ]
    cards.sort(key=lambda c: int(c.get("id") or 0))
    changed = 0
    passed = 0
    done: list[dict] = []
    for c in cards[:limit]:
        cid = int(c["id"])
        before = {
            "title": c.get("title"),
            "body": (c.get("body") or "")[:200],
            "summary": (c.get("summary") or "")[:100],
        }
        opt, patches = optimize_card(c)
        if (
            opt["title"] == (c.get("title") or "").strip()
            and opt["body"] == (c.get("body") or "").strip()
            and opt["summary"] == (c.get("summary") or "").strip()
            and opt["tags"] == (c.get("tags") or [])
        ):
            continue
        if dry_run:
            done.append({"card_id": cid, "patches": patches, "dry_run": True})
            changed += 1
            continue
        row = apply_optimize(cid, dry_run=False)
        if row.get("ok"):
            changed += 1
            if row.get("passed"):
                passed += 1
            done.append(row)
        if sleep_sec > 0:
            import time

            time.sleep(sleep_sec)

    if not dry_run and changed:
        learn.export_pack()

    import agent_office_saju_card_council as council

    return {
        "dry_run": dry_run,
        "scanned": min(limit, len(cards)),
        "changed": changed,
        "recert_pass": passed,
        "samples": done[:5],
        **council.council_stats(),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="학습 카드 문구 최적화")
    p.add_argument("--all", action="store_true", help="확정 카드 전체")
    p.add_argument("--card-id", type=int, default=0)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int, default=500)
    p.add_argument("--sleep", type=float, default=0)
    args = p.parse_args()

    if args.card_id:
        print(apply_optimize(args.card_id, dry_run=args.dry_run))
        return 0
    if args.all or not args.card_id:
        print(
            batch_optimize(
                limit=args.limit,
                dry_run=args.dry_run,
                sleep_sec=args.sleep,
            )
        )
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
