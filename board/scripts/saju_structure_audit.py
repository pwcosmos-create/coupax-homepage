#!/usr/bin/env python3
"""사주 학습부 구조화 — 태그·pack·10_Wiki 반영 (지시 #538·#539)."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
_SCRIPTS = BOARD / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
if str(BOARD) not in sys.path:
    sys.path.insert(0, str(BOARD))

import agent_office_saju_learn as saju_learn  # noqa: E402
import agent_office_wiki_store as wiki_store  # noqa: E402

# 명리 태그 사전 (본문 키워드 → 표준 태그)
_TAG_RULES: list[tuple[str, str]] = [
    ("오행", "오행"),
    ("목(木)|목기|甲乙|寅卯", "목"),
    ("화(火)|화기|丙丁|巳午", "화"),
    ("토(土)|土|戊己|辰戌丑未", "토"),
    ("금(金)|金|庚辛|申酉", "금"),
    ("수(水)|水|壬癸|亥子", "수"),
    ("십신", "십신"),
    ("비겁|比肩|劫財|겁재", "비겁"),
    ("식상|食神|傷官", "식상"),
    ("재성|正財|偏財|편재|정재", "재성"),
    ("관성|正官|偏官|편관|정관|七杀", "관성"),
    ("인성|正印|偏印|편인|정인", "인성"),
    ("일주", "일주"),
    ("월주|년주|시주", "사주팔자"),
    ("대운", "대운"),
    ("세운|流年", "세운"),
    ("월운", "월운"),
    ("용신", "용신"),
    ("기신|忌神", "기신"),
    ("격국|格局", "격국"),
    ("신살", "신살"),
    ("명리|四柱", "명리"),
    ("병화|갑목|정화", "천간지지"),
]

_CONTRADICTION_HINTS = [
    ("용신.*기신|기신.*용신", "용신·기신 동시 강조 — 맥락(시기·계층) 구분 필요"),
    ("대운.*세운.*상충|충.*대운", "대운·세운 충돌 언급 — 시기별 해석 분리 권장"),
    ("오행.*균형.*과다|과다.*균형", "균형 vs 과다 표현 — 강약 수치화 권장"),
]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _extract_tags_enhanced(text: str, existing: list[str] | None = None) -> list[str]:
    tags = list(existing or [])
    blob = text or ""
    for pattern, tag in _TAG_RULES:
        if re.search(pattern, blob, re.I):
            if tag not in tags:
                tags.append(tag)
    # 기존 extract_tags 보완
    for t in saju_learn._extract_tags(blob):
        if t not in tags:
            tags.append(t)
    return tags[:16]


def _find_contradictions(text: str) -> list[str]:
    hints: list[str] = []
    for pat, msg in _CONTRADICTION_HINTS:
        if re.search(pat, text, re.I):
            hints.append(msg)
    return hints


def audit_cards() -> dict:
    store = saju_learn.load_store()
    cards = [c for c in store.get("cards") or [] if isinstance(c, dict)]
    confirmed = [c for c in cards if c.get("status") == "confirmed"]
    pending = [c for c in cards if c.get("status") != "confirmed"]

    tag_counter: Counter[str] = Counter()
    missing_by_card: list[dict] = []
    contradictions: list[dict] = []

    for c in cards:
        body = c.get("body") or ""
        old_tags = list(c.get("tags") or [])
        suggested = _extract_tags_enhanced(body, old_tags)
        missing = [t for t in suggested if t not in old_tags]
        for t in old_tags:
            tag_counter[t] += 1
        for t in missing:
            tag_counter[t] += 1

        if missing:
            missing_by_card.append(
                {
                    "id": c.get("id"),
                    "title": c.get("title"),
                    "missing_tags": missing,
                    "current_tags": old_tags,
                }
            )

        hints = _find_contradictions(body)
        if hints:
            contradictions.append(
                {"id": c.get("id"), "title": c.get("title"), "hints": hints}
            )

    pack = saju_learn.export_pack()
    knowledge = wiki_store.load_knowledge()
    saju_wiki = [
        w
        for w in knowledge.get("wiki") or []
        if isinstance(w, dict) and wiki_store.wiki_domain(w) == wiki_store.DOMAIN_SAJU
    ]

    return {
        "audited_at": _now(),
        "card_total": len(cards),
        "confirmed_count": len(confirmed),
        "pending_count": len(pending),
        "tag_distribution": dict(tag_counter.most_common()),
        "pack": {
            "version": pack.get("version"),
            "card_count": pack.get("card_count"),
            "exported_at": pack.get("exported_at"),
            "fields": ["id", "title", "body", "tags", "summary"],
        },
        "wiki_saju_count": len(saju_wiki),
        "wiki_ids": [w.get("id") for w in saju_wiki[:20]],
        "missing_tags": missing_by_card,
        "contradictions": contradictions,
    }


def apply_tag_fixes(dry_run: bool = False) -> int:
    store = saju_learn.load_store()
    updated = 0
    for c in store.get("cards") or []:
        if not isinstance(c, dict):
            continue
        body = c.get("body") or ""
        new_tags = _extract_tags_enhanced(body, c.get("tags") or [])
        if new_tags != (c.get("tags") or []):
            if not dry_run:
                c["tags"] = new_tags
            updated += 1
    if not dry_run and updated:
        saju_learn.save_store(store)
        saju_learn.export_pack()
        for c in store.get("cards") or []:
            if c.get("status") == "confirmed" and isinstance(c.get("id"), int):
                try:
                    import agent_office_wiki_store

                    agent_office_wiki_store.save_saju_card_to_knowledge(c)
                except Exception:
                    pass
    return updated


def build_wiki_structure_memo(audit: dict) -> str:
    lines = [
        "■ 사주 학습부 구조화 취합 (젬마24 · saju_structurer)",
        "",
        f"■ 조사 시각: {audit['audited_at']}",
        f"■ 카드: 전체 {audit['card_total']} · 확정 {audit['confirmed_count']} · 대기 {audit['pending_count']}",
        "",
        "■ 태그 분포 (확정+전체)",
    ]
    if audit["tag_distribution"]:
        for tag, n in sorted(audit["tag_distribution"].items(), key=lambda x: -x[1]):
            lines.append(f"  · {tag}: {n}건")
    else:
        lines.append("  · (아직 태그 없음)")

    lines.extend(
        [
            "",
            "■ saju_knowledge_pack.json 구조",
            f"  · version={audit['pack'].get('version')} purpose=offline_saju_interpretation",
            f"  · card_count={audit['pack'].get('card_count')} exported_at={audit['pack'].get('exported_at')}",
            f"  · 필드: {', '.join(audit['pack'].get('fields') or [])}",
            "",
            "■ 10_Wiki(saju-learn) 반영 방향",
            f"  · 현재 Wiki(saju-learn) 카드: {audit['wiki_saju_count']}건",
        ]
    )
    if audit["wiki_ids"]:
        lines.append(f"  · 예: {', '.join(str(x) for x in audit['wiki_ids'][:5])}")

    lines.extend(
        [
            "  1) 확정 카드 1건 → wiki_saju_{id} 1:1 매핑 (save_saju_card_to_knowledge)",
            "  2) pack은 오프라인 추론용 스냅샷, Wiki는 검색·주입용 요약(summary 220자)",
            "  3) 태그는 20_Meta에 kind=tag로 중복 저장 → 키워드 검색 강화",
            "  4) 공통 프레임 카드(오행·십신·대운)는 별도 wiki_saju_frame_* 로 취합 권장",
            "",
            "■ 태그 누락 보완 (오행·십신·일주·대운 점검)",
        ]
    )
    if audit["missing_tags"]:
        for m in audit["missing_tags"]:
            lines.append(
                f"  · #{m['id']} {m['title']}: 추가 권장 → {', '.join(m['missing_tags'])}"
            )
    else:
        lines.append("  · 누락 태그 없음 (또는 본문에 키워드 부족)")

    lines.append("")
    lines.append("■ 명리 관점 모순·주의 힌트")
    if audit["contradictions"]:
        for c in audit["contradictions"]:
            lines.append(f"  · #{c['id']} {c['title']}: " + "; ".join(c["hints"]))
    else:
        lines.append("  · 자동 탐지된 모순 없음")

    lines.append("")
    lines.append("■ 취합 결론")
    lines.append(
        "확정 풀이는 pack+Wiki 이중 저장을 유지하고, "
        "태그 사전(오행·십신·일주·대운·용신·격국)을 카드별로 보강한 뒤 "
        "공통 명리 프레임 Wiki 1건을 추가하면 젬마24 주입 품질이 올라갑니다."
    )
    return "\n".join(lines)


def save_frame_wiki(audit: dict) -> dict | None:
    """공통 명리 프레임 → 10_Wiki 카드 1건."""
    dist = audit.get("tag_distribution") or {}
    top = ", ".join(f"{k}({v})" for k, v in list(dist.items())[:8]) or "데이터 수집 중"
    body = (
        f"사주 학습부 구조화 스냅샷 ({audit['audited_at']}). "
        f"확정 {audit['confirmed_count']}건 · 대기 {audit['pending_count']}건. "
        f"주요 태그: {top}. "
        "오행·십신·일주·대운·용신·격국을 카드별 태그와 Wiki summary로 이중 인덱싱합니다. "
        "pack.json은 오프라인, gemma_knowledge Wiki는 RAG 주입용입니다."
    )
    card = {
        "id": 90001,
        "title": "명리 학습 프레임 (구조화)",
        "body": body,
        "summary": body[:220],
        "tags": ["명리", "오행", "십신", "구조화", "Wiki"],
        "source": "structure_audit",
        "status": "confirmed",
        "confirmed_at": _now(),
    }
    return wiki_store.save_saju_card_to_knowledge(card)


def complete_tasks(result_text: str) -> list[int]:
    """queued reserved_saju 중 구조화 관련 작업 완료 처리."""
    import agent_office_log
    import agent_office_tasks

    done_ids: list[int] = []
    keywords = ("태그·pack", "오행·십신", "pack 구조", "10_Wiki")
    for t in agent_office_tasks.load_tasks().get("tasks") or []:
        if not isinstance(t, dict):
            continue
        if t.get("status") not in ("queued", "in_progress"):
            continue
        if t.get("source") != "reserved_saju":
            continue
        title = (t.get("title") or "") + (t.get("body") or "")
        if not any(k in title for k in keywords):
            continue
        tid = t.get("id")
        if not isinstance(tid, int):
            continue
        agent_office_tasks.update_task(
            tid,
            status="done",
            finished_at=_now(),
            handled_by="saju_structurer",
            resolved_to="saju_structurer",
            synthesized_by="saju_structurer",
            result=result_text[:4000],
        )
        try:
            agent_office_log.append_message(
                from_id="saju_structurer",
                to_id="ceo",
                kind="conclusion",
                text=f"[작업 #{tid} 구조화 완료]\n{result_text[:1200]}",
                division="saju-learn",
            )
        except Exception:
            pass
        done_ids.append(tid)
    return done_ids


def main() -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-tasks", action="store_true", help="지시 완료 처리 생략")
    args = p.parse_args()

    audit = audit_cards()
    memo = build_wiki_structure_memo(audit)
    out_dir = BOARD / "data" / "saju_learning"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "structure_audit.json"
    report_path.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    memo_path = out_dir / "structure_memo.txt"
    memo_path.write_text(memo, encoding="utf-8")

    tag_updates = apply_tag_fixes(dry_run=args.dry_run)
    wiki = None if args.dry_run else save_frame_wiki(audit)

    print(memo)
    print()
    print(f"report: {report_path}")
    print(f"tag_cards_updated: {tag_updates}")
    if wiki:
        print(f"wiki: {wiki.get('id')}")

    if not args.no_tasks and not args.dry_run:
        done = complete_tasks(memo)
        if done:
            print(f"tasks_completed: {done}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
