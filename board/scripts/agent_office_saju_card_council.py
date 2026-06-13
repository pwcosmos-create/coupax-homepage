"""
명리 위원회 — 학습 카드 1장씩 조사·토론·검증 (지속 로테이션).

  python scripts/agent_office_saju_card_council.py tick-cycle  # 미검증 우선 + 순차 재검증
  python scripts/agent_office_saju_card_council.py run --card-id 5
  python scripts/agent_office_saju_card_council.py status

동작:
  - 확정(confirm) 시 즉시 검증 (mode=realtime)
  - cron/worker tick-cycle: 미검증 우선 → PASS 카드만 순차 재검증(강화·엄격)
  - batch-reverify-pass: PASS 카드 일괄 재검증 (강화)
  - 검증 기록(council_*)은 import-merge 시 서버 기준 보존

환경 변수:
  AGENT_OFFICE_SAJU_CARD_COUNCIL=1   (기본 1) 카드 단위 위원회 사용
  AGENT_OFFICE_SAJU_CARD_COUNCIL_QUEUE=1  동시 대기 작업 수
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import json_store

import agent_registry

ROTATION_PATH = BOARD / "data" / "saju_learning" / "council_rotation.json"

DIVISION_SAJU = agent_registry.DIVISION_SAJU
SOURCE_COUNCIL_SAJU_CARD = "council_saju_card"

PII_PATTERNS = [
    re.compile(r"\d{3}-\d{3,4}-\d{4}"),
    re.compile(r"\d{10,11}"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
]

ABSOLUTE_CLAIMS = re.compile(
    r"(반드시|100%|확정|무조건|절대\s*길|절대\s*흉|재벌|파산|이혼\s*확정)"
)

DISCLAIMER_HINTS = ("참고", "금지", "단정", "가능성", "경향", "면책", "주의")

REINSPECTOR_AGENT = "saju_reinspector"

REVERIFY_MODES = frozenset(
    {
        "reverify_pass",
        "retry_fail",
        "recert_after_fix",
        "reverify",
        "copy_optimize",
    }
)

VARIABLE_TAG_HINTS = {
    "천간": ("천간", "일간", "갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"),
    "지지": ("지지", "자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"),
    "십신": ("십신", "비견", "겁재", "식신", "상관", "편재", "정재", "편관", "정관", "편인", "정인"),
    "오행": ("오행", "목", "화", "토", "금", "수", "상생", "상극"),
    "신살": ("신살", "도화", "역마", "화개", "백호", "괴강"),
    "격": ("격", "격국", "정관격", "편관격"),
    "지지관계": ("합", "충", "형", "파", "해", "삼합"),
    "운": ("대운", "세운", "월운", "일운"),
}


@dataclass
class PanelReport:
    agent_id: str
    job: str
    ok: bool
    summary: str


@dataclass
class CardCouncilResult:
    card_id: int
    passed: bool
    report: str
    panel: list[PanelReport] = field(default_factory=list)
    debate_issues: list[str] = field(default_factory=list)
    verify_issues: list[str] = field(default_factory=list)
    wiki_id: str = ""


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def use_card_council() -> bool:
    return os.getenv("AGENT_OFFICE_SAJU_CARD_COUNCIL", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def card_council_queue_target() -> int:
    return max(0, int(os.getenv("AGENT_OFFICE_SAJU_CARD_COUNCIL_QUEUE", "1") or "1"))


def council_per_tick() -> int:
    """cron/worker 1회당 연속 검증 장수."""
    return max(1, min(30, int(os.getenv("SAJU_COUNCIL_PER_TICK", "10") or "10")))


def council_fast_mode() -> bool:
    """1이면 PASS 재검증·강화도 일반 기준(속도 우선)."""
    return os.getenv("SAJU_COUNCIL_FAST", "1").strip().lower() in ("1", "true", "yes")


def _strict_for_mode(mode: str) -> bool:
    if mode in ("retry_fail", "recert_after_fix", "copy_optimize"):
        return False
    if mode == "reverify_pass":
        return not council_fast_mode()
    return mode in ("reverify",)


def _load_confirmed_cards() -> list[dict]:
    import agent_office_saju_learn

    cards = [
        c
        for c in agent_office_saju_learn.load_store().get("cards") or []
        if isinstance(c, dict) and c.get("status") == "confirmed"
    ]
    cards.sort(key=lambda c: int(c.get("id") or 0))
    return cards


def _is_council_pass(card: dict) -> bool:
    return (card.get("council_status") or "").strip() == "pass" or card.get(
        "council_pass"
    ) is True


def council_stats() -> dict:
    cards = _load_confirmed_cards()
    verified = sum(1 for c in cards if (c.get("council_at") or "").strip())
    passed = sum(1 for c in cards if _is_council_pass(c))
    failed = sum(1 for c in cards if (c.get("council_status") or "") == "fail")
    pending = len(cards) - verified
    strengthened = sum(
        1 for c in cards if (c.get("council_strengthened_at") or "").strip()
    )
    return {
        "total_confirmed": len(cards),
        "council_pass": passed,
        "council_fail": failed,
        "council_pending": max(0, pending),
        "council_strengthened": strengthened,
    }


def queue_status() -> dict:
    st = council_stats()
    return {
        "mode": "council_card",
        "active": count_card_council_active(),
        "target": card_council_queue_target(),
        "label": "위원회·카드",
        "verified": st["council_pass"],
        "total": st["total_confirmed"],
        "pending_verify": st["council_pending"],
    }


def _load_rotation() -> dict:
    try:
        data = json_store.load_json(ROTATION_PATH, default={})
        return data if isinstance(data, dict) else {}
    except json_store.JsonStoreError:
        return {}


def _save_rotation(data: dict) -> None:
    ROTATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _now()
    json_store.save_json(ROTATION_PATH, data)


def next_card_to_verify() -> dict | None:
    """아직 위원회 검증을 받지 않은 확정 카드 1장 (id 오름차순)."""
    for c in _load_confirmed_cards():
        if not (c.get("council_at") or "").strip():
            return c
    return None


def _pass_cards_ordered() -> list[dict]:
    """위원회 PASS 카드만 (id 오름차순) — 재검증·강화 대상."""
    return [c for c in _load_confirmed_cards() if _is_council_pass(c)]


def pick_next_pass_reverify() -> tuple[dict | None, str]:
    """PASS 카드 1장 순차 재검증 (pass_reverify_index 커서)."""
    passed = _pass_cards_ordered()
    if not passed:
        return None, ""

    rot = _load_rotation()
    cursor = int(rot.get("pass_reverify_index") or 0)
    if cursor >= len(passed):
        cursor = 0
    card = passed[cursor]
    rot["pass_reverify_index"] = (cursor + 1) % len(passed)
    rot["last_pass_reverify_card_id"] = card.get("id")
    rot["pass_reverify_total"] = len(passed)
    _save_rotation(rot)
    return card, "reverify_pass"


def _fail_cards_ordered() -> list[dict]:
    return [
        c
        for c in _load_confirmed_cards()
        if (c.get("council_status") or "").strip() == "fail"
    ]


def pick_next_fail_retry() -> tuple[dict | None, str]:
    """FAIL 카드 1장 재검증 (일반 기준·속도 우선)."""
    failed = _fail_cards_ordered()
    if not failed:
        return None, ""
    rot = _load_rotation()
    cursor = int(rot.get("fail_retry_index") or 0)
    if cursor >= len(failed):
        cursor = 0
    card = failed[cursor]
    rot["fail_retry_index"] = (cursor + 1) % len(failed)
    rot["last_fail_retry_card_id"] = card.get("id")
    _save_rotation(rot)
    return card, "retry_fail"


def pick_next_card() -> tuple[dict | None, str]:
    """
    다음 검증 대상 1장.
    1) 미검증 확정 카드
    2) FAIL 재시도 (일반 기준)
    3) PASS 순차 재검증
    """
    unverified = next_card_to_verify()
    if unverified:
        return unverified, "initial"
    card, mode = pick_next_fail_retry()
    if card:
        return card, mode
    return pick_next_pass_reverify()


def parse_card_id_from_task(task: dict) -> int | None:
    raw = f"{task.get('title') or ''}\n{task.get('body') or ''}"
    m = re.search(r"card[_\s#]*id\s*[=:]?\s*(\d+)", raw, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"카드\s*#?\s*(\d+)", raw)
    if m:
        return int(m.group(1))
    m = re.search(r"#(\d+)\s*검증", raw)
    if m:
        return int(m.group(1))
    return None


def _check_pii(card: dict) -> PanelReport:
    text = f"{card.get('title') or ''}\n{card.get('body') or ''}"
    hits = []
    for pat in PII_PATTERNS:
        if pat.search(text):
            hits.append(pat.pattern[:24])
    ok = not hits
    return PanelReport(
        "saju_privacy",
        "card_pii",
        ok,
        "PII 없음" if ok else f"PII 의심 패턴: {', '.join(hits[:3])}",
    )


def _check_tags(card: dict, *, strict: bool = False) -> PanelReport:
    tags = [str(t).strip() for t in (card.get("tags") or []) if str(t).strip()]
    body = (card.get("body") or "").strip()
    min_tags = 3 if strict else 2
    min_body = 100 if strict else 80
    issues = []
    if len(tags) < min_tags:
        issues.append(f"태그 {min_tags}개 미만")
    title = (card.get("title") or "").lower()
    for key, hints in VARIABLE_TAG_HINTS.items():
        if key in title or any(h in title for h in hints[:3]):
            if not any(any(h in tg for h in hints) for tg in tags):
                issues.append(f"제목·{key} 관련 태그 부족")
    if len(body) < min_body:
        issues.append(f"본문 짧음 ({len(body)}자, 최소 {min_body})")
    ok = not issues
    return PanelReport(
        "saju_structurer",
        "card_tags",
        ok,
        "태그·구조 OK" if ok else "; ".join(issues[:4]),
    )


def _check_myeongri(card: dict) -> PanelReport:
    body = (card.get("body") or "").strip()
    title = (card.get("title") or "").strip()
    issues = []
    if re.match(r"^test\s*$", title, re.I):
        issues.append("테스트 제목 — 삭제·재작성 권장")
    if ABSOLUTE_CLAIMS.search(body):
        issues.append("확정적 예언·절대 길흉 표현")
    if "용신" in body and "참고" not in body and "학파" not in body:
        if len(body) < 200 and body.count("용신") >= 2:
            issues.append("용신 단정 — 학파·참고용 문구 보강 필요")
    if "일주" in title and "일주" not in body and "일간" not in body:
        issues.append("제목 일주·본문 키워드 불일치")
    ok = len(issues) <= 1
    return PanelReport(
        "saju_scholar",
        "card_myeongri",
        ok,
        "명리 서술 OK" if ok else "; ".join(issues[:5]),
    )


def _check_readability(card: dict, *, strict: bool = False) -> PanelReport:
    body = (card.get("body") or "").strip()
    min_len = 80 if strict else 60
    ok = len(body) >= min_len and len(body.split(".")) + len(body.split("。")) >= 1
    return PanelReport(
        "saju_reader",
        "card_read",
        ok,
        f"독해 {len(body)}자" if ok else f"본문 부족 ({len(body)}자)",
    )


def _check_curator(card: dict) -> PanelReport:
    ok = (card.get("status") or "") == "confirmed"
    wiki = bool((card.get("wiki_id") or "").strip())
    msg = f"확정·wiki={'Y' if wiki else 'N'}"
    if not wiki and ok:
        msg += " (wiki 동기화 권장)"
    return PanelReport("saju_curator", "card_pack", ok, msg)


def _check_quality(card: dict, *, strict: bool = False) -> PanelReport:
    title = (card.get("title") or "").strip()
    body = (card.get("body") or "").strip()
    min_body = 80 if strict else 40
    issues = []
    if not title:
        issues.append("제목 없음")
    if len(body) < min_body:
        issues.append(f"본문 {min_body}자 미만")
    if body == (card.get("summary") or "")[: len(body)] and len(body) < 100:
        issues.append("요약=본문 단편 — 학습 가치 낮음")
    ok = not issues
    return PanelReport(
        "saju_error_fix",
        "card_quality",
        ok,
        "품질 OK" if ok else "; ".join(issues),
    )


def _strengthen_issues(card: dict) -> list[str]:
    """엄격 재점검 — 면책·구조 강화 항목."""
    body = (card.get("body") or "").strip()
    issues: list[str] = []
    if len(body) < 80:
        issues.append("강화: 본문 80자 미만")
    tags = [str(t).strip() for t in (card.get("tags") or []) if str(t).strip()]
    if len(tags) < 2:
        issues.append("강화: 태그 2개 미만")
    if ABSOLUTE_CLAIMS.search(body) and not any(h in body for h in DISCLAIMER_HINTS):
        issues.append("강화: 단정 표현·완화 문구 부족")
    risky = ("투자", "의학", "이혼", "사망", "파산", "합격", "승진")
    if any(k in body for k in risky) and not any(h in body for h in DISCLAIMER_HINTS):
        issues.append("강화: 민감 주제·면책 문구 부족")
    return issues


def _check_reinspector(card: dict, *, mode: str = "initial", strict: bool = False) -> PanelReport:
    """재점검 젬마 — PASS·FAIL 재시도·수정 재인증 시 인증·면책·강화."""
    if mode not in REVERIFY_MODES and not strict:
        return PanelReport(
            REINSPECTOR_AGENT,
            "saju_cert_reverify",
            True,
            "최초 인증 — 재점검 전담 생략",
        )

    body = (card.get("body") or "").strip()
    issues: list[str] = []

    if mode == "reverify_pass" and not _is_council_pass(card):
        issues.append("재점검: PASS 이력 없음")
    if not (card.get("council_at") or "").strip() and mode in REVERIFY_MODES:
        issues.append("재점검: council_at 없음")

    footer_mark = "본 내용은 명리 참고용"
    if len(body) >= 120 and footer_mark not in body:
        issues.append("재점검: 참고용 면책 문단 부족")

    composed = (card.get("composed_at") or "").strip()
    if mode in ("recert_after_fix", "copy_optimize") and not composed and len(body) < 150:
        issues.append("재점검: 구체화·면책 보강 필요")

    if strict or mode == "reverify_pass":
        issues.extend(_strengthen_issues(card))

    ok = not issues
    summary = "인증 재점검 OK" if ok else "; ".join(issues[:5])
    if ok and strict:
        summary += " · 강화 기준 통과"
    return PanelReport(REINSPECTOR_AGENT, "saju_cert_reverify", ok, summary)


def _run_card_panel(
    card: dict, *, strict: bool = False, mode: str = "initial"
) -> list[PanelReport]:
    panel = [
        _check_pii(card),
        _check_tags(card, strict=strict),
        _check_myeongri(card),
        _check_readability(card, strict=strict),
        _check_curator(card),
        _check_quality(card, strict=strict),
    ]
    if mode in REVERIFY_MODES or strict:
        panel.append(_check_reinspector(card, mode=mode, strict=strict))
    return panel


def _debate_card(panel: list[PanelReport]) -> list[str]:
    issues: list[str] = []
    scholar = next((p for p in panel if p.agent_id == "saju_scholar"), None)
    quality = next((p for p in panel if p.agent_id == "saju_error_fix"), None)
    reinspect = next((p for p in panel if p.agent_id == REINSPECTOR_AGENT), None)
    if reinspect and not reinspect.ok:
        issues.append(f"재점검: {reinspect.summary[:100]}")
    if scholar and not scholar.ok and quality and not quality.ok:
        issues.append("명리·품질 동시 NG — 우선 수정 후 재검증")
    pii = next((p for p in panel if p.agent_id == "saju_privacy"), None)
    if pii and not pii.ok:
        issues.append(f"PII: {pii.summary[:120]}")
    failed = [p for p in panel if not p.ok]
    if len(failed) >= 3:
        issues.append(f"조사 실패 {len(failed)}건 — 전원 재검토")
    return issues


def _verify_card(
    card: dict, panel: list[PanelReport], *, mode: str = "initial"
) -> list[str]:
    issues: list[str] = []
    block_ids = ("saju_privacy", "saju_error_fix")
    if mode in REVERIFY_MODES:
        block_ids = block_ids + (REINSPECTOR_AGENT,)
    for p in panel:
        if p.agent_id in block_ids and not p.ok:
            issues.append(f"{p.agent_id}: {p.summary[:100]}")
    if (card.get("title") or "").strip().lower() == "test":
        issues.append("테스트 카드 — 위원회 FAIL 권장")
    return issues


def run_card_council(
    card: dict, *, strict: bool = False, mode: str = "initial"
) -> CardCouncilResult:
    cid = int(card.get("id") or 0)
    panel = _run_card_panel(card, strict=strict, mode=mode)
    debate = _debate_card(panel)
    verify = _verify_card(card, panel, mode=mode)
    failed = [p for p in panel if not p.ok]
    max_fail = 1 if strict else 2
    passed = not verify and len(failed) <= max_fail

    lines = [
        f"【명리 위원회 · 카드 #{cid} · {_now()}】",
        f"제목: {(card.get('title') or '')[:80]}",
        f"단계: 조사({len(panel)}통) → 토론 → 검증"
        + (" · 재점검·강화(엄격)" if strict else "")
        + (" · 재점검" if mode in REVERIFY_MODES and not strict else ""),
        f"검증: {'PASS' if passed else 'FAIL'}",
        "",
        "■ 1. 조사",
    ]
    for i, p in enumerate(panel, 1):
        flag = "OK" if p.ok else "NG"
        lines.append(f"  {i}. [{flag}] {p.agent_id} — {p.summary[:200]}")
    lines.extend(["", "■ 2. 토론"])
    if debate:
        for d in debate:
            lines.append(f"  · {d}")
    else:
        lines.append("  · 중대 모순 없음")
    lines.extend(["", "■ 3. 검증"])
    if verify:
        for v in verify:
            lines.append(f"  · NG {v}")
    else:
        lines.append("  · 카드 체크리스트 통과")
    lines.extend(
        [
            "",
            "■ 4. 결론",
            "  · PASS — pack·Wiki 유지" if passed else "  · FAIL — 수정 후 재검증",
        ]
    )

    return CardCouncilResult(
        card_id=cid,
        passed=passed,
        report="\n".join(lines)[:8000],
        panel=panel,
        debate_issues=debate,
        verify_issues=verify,
        wiki_id=f"wiki_saju_card_council_{cid}",
    )


def apply_card_result(
    card_id: int,
    result: CardCouncilResult,
    *,
    mode: str = "initial",
) -> bool:
    import agent_office_saju_learn

    status = "pass" if result.passed else "fail"
    note_bits = []
    if result.verify_issues:
        note_bits.append("검증: " + "; ".join(result.verify_issues[:3])[:200])
    if result.debate_issues:
        note_bits.append("토론: " + "; ".join(result.debate_issues[:2])[:120])

    fields: dict = {
        "council_status": status,
        "council_at": _now(),
        "council_pass": result.passed,
        "council_report": result.report[:2000],
        "council_note": " · ".join(note_bits)[:400],
        "council_mode": mode,
    }
    if mode in ("reverify", "reverify_pass"):
        prev = agent_office_saju_learn.get_card(card_id) or {}
        fields["council_reverified_at"] = _now()
        fields["council_reverify_count"] = int(prev.get("council_reverify_count") or 0) + 1
        if (
            mode == "reverify_pass"
            and result.passed
            and _strict_for_mode("reverify_pass")
        ):
            fields["council_strengthened_at"] = _now()
            fields["council_strength_level"] = int(
                prev.get("council_strength_level") or 0
            ) + 1
        elif mode in ("retry_fail", "recert_after_fix") and result.passed:
            fields["council_fast_recert_at"] = _now()
        if mode == "recert_after_fix":
            fields["council_recert_at"] = _now()
    elif mode == "realtime":
        fields["council_realtime_at"] = _now()
    elif mode == "copy_optimize":
        fields["council_copy_optimized_at"] = _now()

    ok = agent_office_saju_learn.set_card_council(card_id, **fields)
    if ok:
        try:
            card = agent_office_saju_learn.get_card(card_id)
            if card and card.get("status") == "confirmed":
                import agent_office_wiki_store

                agent_office_wiki_store.save_saju_card_to_knowledge(card)
        except Exception:
            pass
        if result.passed:
            try:
                import saju_card_llm_compose as llm_compose

                llm_row = llm_compose.polish_card_after_pass(card_id, mode=mode)
                if llm_row.get("ok") and not llm_row.get("skipped"):
                    card = agent_office_saju_learn.get_card(card_id)
                    if card:
                        import agent_office_wiki_store

                        agent_office_wiki_store.save_saju_card_to_knowledge(card)
            except Exception:
                pass
    return ok


def push_card_council_wiki(task: dict, card: dict, result: CardCouncilResult) -> bool:
    try:
        import agent_office_swiki_sync

        cid = result.card_id
        card_wiki = {
            "id": result.wiki_id,
            "domain": DIVISION_SAJU,
            "layer": "10_Wiki",
            "title": f"명리위원회 카드 #{cid} 검증",
            "summary": (
                f"{'PASS' if result.passed else 'FAIL'} · "
                f"{(card.get('title') or '')[:60]} · "
                f"검증 {len(result.verify_issues)} · 토론 {len(result.debate_issues)}"
            )[:500],
            "body": result.report[:8000],
            "task_id": task.get("id"),
            "source": SOURCE_COUNCIL_SAJU_CARD,
            "storage_tier": "github_archive",
            "agent_primary": "saju_structurer",
            "agent_synth": REINSPECTOR_AGENT,
            "ts": _now(),
            "tags": ["위원회", "카드검증", DIVISION_SAJU, f"card_{cid}"],
            "council_pass": result.passed,
            "card_id": cid,
        }
        agent_office_swiki_sync.push_wiki_card(card_wiki, force=True)
        return True
    except Exception:
        return False


def count_card_council_active() -> int:
    import agent_office_tasks

    n = 0
    for t in agent_office_tasks.load_tasks().get("tasks") or []:
        if not isinstance(t, dict):
            continue
        if t.get("source") != SOURCE_COUNCIL_SAJU_CARD:
            continue
        if (t.get("status") or "queued") in ("queued", "in_progress"):
            n += 1
    return n


def ensure_card_council_queue() -> int:
    """미검증 카드 1장에 대한 위원회 작업 1건 유지."""
    import agent_office_tasks

    if not use_card_council():
        return 0
    target = card_council_queue_target()
    if target <= 0:
        return 0
    added = 0
    while count_card_council_active() < target:
        card = next_card_to_verify()
        if not card:
            break
        cid = int(card.get("id") or 0)
        title = (card.get("title") or "")[:60]
        assign = (
            REINSPECTOR_AGENT
            if (card.get("council_at") or "").strip()
            else "saju_structurer"
        )
        agent_office_tasks.add_task(
            body=(
                f"학습카드 #{cid} 「{title}」 명리 위원회 1장 검증\n"
                f"card_id={cid}\n"
                "조사(PII·태그·명리·독해·pack·품질·재점검) → 토론 → 검증 후 "
                "council_status 기록."
            ),
            assign_to=assign,
            title=f"명리위원회 카드 #{cid} 검증",
            priority="normal",
            created_by="명리위원회",
            source=SOURCE_COUNCIL_SAJU_CARD,
            division=DIVISION_SAJU,
            quiet=True,
        )
        added += 1
        if added > target + 2:
            break
    return added


def process_card_council_task(task: dict, registry: dict) -> tuple[bool, str]:
    import agent_office_log
    import agent_office_saju_learn
    import agent_office_tasks

    tid = task.get("id")
    cid = parse_card_id_from_task(task)
    if not cid:
        card = next_card_to_verify()
        cid = int(card.get("id") or 0) if card else 0
    if not cid:
        agent_office_tasks.update_task(
            tid, status="done", finished_at=_now(), result="검증 대상 카드 없음"
        )
        return True, "no cards"

    card = agent_office_saju_learn.get_card(cid)
    if not card:
        agent_office_tasks.update_task(
            tid,
            status="done",
            finished_at=_now(),
            result=f"카드 #{cid} 없음",
        )
        return False, f"missing card {cid}"

    agent_office_tasks.update_task(
        tid,
        status="in_progress",
        started_at=_now(),
        handled_by="saju_structurer",
    )
    agent_office_log.append_message(
        from_id="ceo",
        to_id="saju_structurer",
        kind="task",
        text=f"[위원회·카드 #{cid}] 검증 시작",
        division=DIVISION_SAJU,
    )

    result = run_card_council(card)
    apply_card_result(cid, result)
    push_card_council_wiki(task, card, result)

    agent_office_tasks.update_task(
        tid,
        status="done",
        finished_at=_now(),
        result=result.report[:4000],
        wiki_id=result.wiki_id,
        council_pass=result.passed,
    )
    agent_office_log.append_message(
        from_id="saju_rl",
        to_id="ceo",
        kind="conclusion" if result.passed else "system",
        text=result.report[:1500],
        division=DIVISION_SAJU,
    )

    ensure_card_council_queue()

    summary = (
        f"{'PASS' if result.passed else 'FAIL'} · 카드 #{cid} · "
        f"조사 {len(result.panel)} · 검증 {len(result.verify_issues)}"
    )
    # 작업 완료 여부(True)와 카드 검증 결과(PASS/FAIL)는 분리
    return True, summary


def verify_card_by_id(card_id: int, *, mode: str = "realtime") -> dict | None:
    """지정 카드 즉시 검증 (신규 확정·실시간)."""
    import agent_office_saju_learn

    card = agent_office_saju_learn.get_card(card_id)
    if not card or (card.get("status") or "") != "confirmed":
        return None
    try:
        import saju_card_reverify_enrich as enrich

        if enrich.enrich_before_verify(card_id, mode):
            card = agent_office_saju_learn.get_card(card_id) or card
    except Exception:
        pass
    result = run_card_council(card, strict=_strict_for_mode(mode), mode=mode)
    apply_card_result(card_id, result, mode=mode)
    push_card_council_wiki(
        {"id": 0, "title": f"{mode} #{card_id}"},
        card,
        result,
    )
    try:
        import agent_office_log

        log_from = (
            REINSPECTOR_AGENT if mode in REVERIFY_MODES else "saju_rl"
        )
        agent_office_log.append_message(
            from_id=log_from,
            to_id="ceo",
            kind="conclusion" if result.passed else "system",
            text=(
                f"[위원회·{mode} · 카드 #{card_id}] "
                f"{'PASS' if result.passed else 'FAIL'} · {(card.get('title') or '')[:50]}"
            ),
            division=DIVISION_SAJU,
        )
    except Exception:
        pass
    return {
        "card_id": card_id,
        "title": (card.get("title") or "")[:60],
        "passed": result.passed,
        "mode": mode,
    }


def verify_one_card_cycle() -> dict | None:
    """미검증 우선 → 검증 완료 카드 순차 재검증 1장."""
    card, mode = pick_next_card()
    if not card:
        return None
    cid = int(card.get("id") or 0)
    import agent_office_saju_learn

    fresh = agent_office_saju_learn.get_card(cid) or card
    if mode == "retry_fail":
        try:
            import saju_card_council_fix as fix

            if fix.needs_fix_after_fail(fresh):
                fixed_fields, patches = fix.fix_fail_card(fresh)
                fix.apply_fix(cid, fixed_fields, patches)
                fresh = agent_office_saju_learn.get_card(cid) or fresh
                mode = "recert_after_fix"
        except Exception:
            pass
    try:
        import saju_card_reverify_enrich as enrich

        if enrich.enrich_before_verify(cid, mode):
            fresh = agent_office_saju_learn.get_card(cid) or fresh
    except Exception:
        pass
    result = run_card_council(fresh, strict=_strict_for_mode(mode), mode=mode)
    apply_card_result(cid, result, mode=mode)
    push_card_council_wiki({"id": 0, "title": f"{mode} #{cid}"}, fresh, result)
    if mode in REVERIFY_MODES:
        try:
            import agent_registry

            agent_registry.update_agent_run(
                REINSPECTOR_AGENT, f"card#{cid}·{'PASS' if result.passed else 'FAIL'}"
            )
        except Exception:
            pass
    return {
        "card_id": cid,
        "title": (fresh.get("title") or "")[:60],
        "passed": result.passed,
        "mode": mode,
    }


def verify_one_card_inline() -> dict | None:
    """하위 호환 — cycle과 동일."""
    return verify_one_card_cycle()


def run_batch(count: int = 20) -> dict:
    """미검증 카드를 연속 검증 (서버 일괄 실행용)."""
    count = max(1, min(int(count), 200))
    done: list[dict] = []
    for _ in range(count):
        row = verify_one_card_inline()
        if not row:
            break
        done.append(row)
    st = council_stats()
    passed = sum(1 for r in done if r.get("passed"))
    failed = len(done) - passed
    return {
        "requested": count,
        "processed": len(done),
        "batch_pass": passed,
        "batch_fail": failed,
        **st,
    }


def tick() -> dict:
    """cron·worker: 큐 보충 + 카드 위원회 작업 1건 처리."""
    import agent_office_task_runner

    added = ensure_card_council_queue()
    done = agent_office_task_runner.process_queued_tasks(max_tasks=1)
    st = council_stats()
    return {"queue_added": added, "tasks_processed": done, **st}


def tick_cycle(per_tick: int | None = None) -> dict:
    """미검증 → FAIL재시도 → PASS재검증, 1회에 여러 장 처리."""
    n = per_tick if per_tick is not None else council_per_tick()
    n = max(1, min(int(n), 30))
    done: list[dict] = []
    for _ in range(n):
        row = verify_one_card_cycle()
        if not row:
            break
        done.append(row)
    st = council_stats()
    rot = _load_rotation()
    passed = sum(1 for r in done if r.get("passed"))
    return {
        "per_tick": n,
        "processed": len(done),
        "tick_pass": passed,
        "tick_fail": len(done) - passed,
        "verified_cards": done[-3:],
        "pass_reverify_index": rot.get("pass_reverify_index"),
        "fail_retry_index": rot.get("fail_retry_index"),
        "fast_mode": council_fast_mode(),
        **st,
    }


def reset_pass_reverify_cursor() -> dict:
    rot = _load_rotation()
    rot["pass_reverify_index"] = 0
    _save_rotation(rot)
    return {"pass_reverify_index": 0, "pass_total": len(_pass_cards_ordered())}


def run_batch_reverify_pass(
    count: int = 30, *, sleep_sec: float = 0, reset: bool = False
) -> dict:
    """PASS 카드만 연속 재검증·강화 (서버 일괄 실행용)."""
    if reset:
        reset_pass_reverify_cursor()
    count = max(1, min(int(count), 300))
    done: list[dict] = []
    still_pass = 0
    downgraded = 0
    for _ in range(count):
        card, mode = pick_next_pass_reverify()
        if not card or mode != "reverify_pass":
            break
        cid = int(card.get("id") or 0)
        import agent_office_saju_learn

        fresh = agent_office_saju_learn.get_card(cid) or card
        result = run_card_council(
            fresh, strict=_strict_for_mode(mode), mode=mode
        )
        apply_card_result(cid, result, mode=mode)
        push_card_council_wiki({"id": 0, "title": f"{mode} #{cid}"}, fresh, result)
        row = {
            "card_id": cid,
            "title": (fresh.get("title") or "")[:60],
            "passed": result.passed,
            "strengthened": result.passed and _strict_for_mode(mode),
        }
        done.append(row)
        if result.passed:
            still_pass += 1
        else:
            downgraded += 1
        if sleep_sec > 0:
            import time

            time.sleep(sleep_sec)
    st = council_stats()
    return {
        "requested": count,
        "processed": len(done),
        "batch_still_pass": still_pass,
        "batch_downgraded": downgraded,
        "fast_mode": council_fast_mode(),
        **st,
    }


def reset_fail_retry_cursor() -> dict:
    rot = _load_rotation()
    rot["fail_retry_index"] = 0
    _save_rotation(rot)
    return {"fail_retry_index": 0, "fail_total": len(_fail_cards_ordered())}


def run_batch_fail_retry(
    count: int = 50, *, sleep_sec: float = 0, reset: bool = False
) -> dict:
    """FAIL 카드 일반 기준 재검증 (빠른 인증 복구)."""
    if reset:
        reset_fail_retry_cursor()
    count = max(1, min(int(count), 500))
    done: list[dict] = []
    upgraded = 0
    for _ in range(count):
        card, mode = pick_next_fail_retry()
        if not card or mode != "retry_fail":
            break
        cid = int(card.get("id") or 0)
        import agent_office_saju_learn

        fresh = agent_office_saju_learn.get_card(cid) or card
        result = run_card_council(fresh, strict=False, mode=mode)
        apply_card_result(cid, result, mode=mode)
        push_card_council_wiki({"id": 0, "title": f"{mode} #{cid}"}, fresh, result)
        row = {
            "card_id": cid,
            "title": (fresh.get("title") or "")[:60],
            "passed": result.passed,
        }
        done.append(row)
        if result.passed:
            upgraded += 1
        if sleep_sec > 0:
            import time

            time.sleep(sleep_sec)
    st = council_stats()
    return {
        "requested": count,
        "processed": len(done),
        "batch_upgraded": upgraded,
        "fast_mode": True,
        **st,
    }


def fast_cert(*, max_cards: int = 300, sleep_sec: float = 0) -> dict:
    """미검증 → FAIL재시도 → PASS재검증 일괄 (대기 없음)."""
    max_cards = max(1, min(int(max_cards), 500))
    out: dict = {"steps": []}
    st0 = council_stats()
    if st0.get("council_fail"):
        try:
            import saju_card_council_fix as fix

            n = min(st0["council_fail"], max_cards)
            out["steps"].append(
                ("fix_recert", fix.batch_fix_recert(n, sleep_sec=sleep_sec))
            )
            max_cards = max(0, max_cards - n)
        except Exception as e:
            out["steps"].append(("fix_recert", {"error": str(e)[:120]}))
    st0 = council_stats()
    if st0.get("council_pending"):
        n = min(st0["council_pending"], max_cards)
        out["steps"].append(("pending", run_batch(n)))
        max_cards -= n
    st1 = council_stats()
    if max_cards > 0 and st1.get("council_fail"):
        n = min(st1["council_fail"], max_cards)
        out["steps"].append(
            ("fail_retry", run_batch_fail_retry(n, sleep_sec=sleep_sec, reset=True))
        )
        max_cards -= n
    if max_cards > 0:
        out["steps"].append(
            (
                "pass_cycle",
                run_batch_reverify_pass(
                    min(max_cards, 100), sleep_sec=sleep_sec, reset=False
                ),
            )
        )
    out["stats"] = council_stats()
    out["fast_mode"] = council_fast_mode()
    return out


def main() -> int:
    import board_env

    board_env.load_board_env()
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("tick")
    tc = sub.add_parser("tick-cycle", help="미검증→FAIL→PASS 연속 검증")
    tc.add_argument(
        "--per-tick",
        type=int,
        default=None,
        help="1회 처리 장수 (기본 SAJU_COUNCIL_PER_TICK=10)",
    )
    sub.add_parser("ensure")
    sub.add_parser(
        "reset-pass-reverify", help="PASS 재검증 커서 0으로 (일괄 강화 전)"
    )
    bat = sub.add_parser("batch")
    bat.add_argument("--count", type=int, default=30, help="연속 검증 장수 (최대 200)")
    brp = sub.add_parser("batch-reverify-pass", help="PASS 카드 재검증·강화")
    brp.add_argument("--count", type=int, default=30, help="최대 300")
    brp.add_argument("--sleep", type=float, default=0, help="장 간 대기(초)")
    bfr = sub.add_parser("batch-fail-retry", help="FAIL 카드 빠른 재인증")
    bfr.add_argument("--count", type=int, default=100, help="최대 500")
    bfr.add_argument("--sleep", type=float, default=0)
    bfr.add_argument("--reset", action="store_true")
    fc = sub.add_parser("fast-cert", help="미검증+FAIL+PASS 일괄 빠른 인증")
    fc.add_argument("--max", type=int, default=300, dest="max_cards")
    fc.add_argument("--sleep", type=float, default=0)
    bfx = sub.add_parser("batch-fix-recert", help="FAIL 수정 후 재인증")
    bfx.add_argument("--count", type=int, default=80)
    bfx.add_argument("--sleep", type=float, default=0)
    bfx.add_argument("--all", action="store_true", help="이미 수정한 FAIL 포함")
    ber = sub.add_parser("batch-enrich-reverify", help="본문 구체화 후 재검증")
    ber.add_argument("--count", type=int, default=200)
    ber.add_argument("--sleep", type=float, default=0)
    ber.add_argument("--force", action="store_true", help="이미 구체화된 카드도 재작성")
    brp.add_argument(
        "--reset", action="store_true", help="커서 0부터 (전체 1바퀴)"
    )
    run_p = sub.add_parser("run")
    run_p.add_argument("--card-id", type=int, required=True)
    args = p.parse_args()

    if args.cmd == "status":
        print(queue_status())
        print(council_stats())
        return 0
    if args.cmd == "ensure":
        print("added", ensure_card_council_queue())
        return 0
    if args.cmd == "tick":
        print(tick())
        return 0
    if args.cmd == "tick-cycle":
        print(tick_cycle(per_tick=args.per_tick))
        return 0
    if args.cmd == "batch-fail-retry":
        print(
            run_batch_fail_retry(
                args.count, sleep_sec=args.sleep, reset=bool(args.reset)
            )
        )
        return 0
    if args.cmd == "fast-cert":
        print(fast_cert(max_cards=args.max_cards, sleep_sec=args.sleep))
        return 0
    if args.cmd == "batch-enrich-reverify":
        import saju_card_reverify_enrich as enrich

        e = enrich.batch_enrich(
            args.count, force=bool(args.force), sleep_sec=args.sleep
        )
        r = run_batch_reverify_pass(
            args.count, sleep_sec=args.sleep, reset=True
        )
        print({"enrich": e, "reverify": r})
        return 0
    if args.cmd == "batch-fix-recert":
        import saju_card_council_fix as fix

        print(
            fix.batch_fix_recert(
                args.count,
                only_unfixed=not args.all,
                sleep_sec=args.sleep,
            )
        )
        return 0
    if args.cmd == "batch":
        print(run_batch(args.count))
        return 0
    if args.cmd == "reset-pass-reverify":
        print(reset_pass_reverify_cursor())
        return 0
    if args.cmd == "batch-reverify-pass":
        print(
            run_batch_reverify_pass(
                args.count, sleep_sec=args.sleep, reset=bool(args.reset)
            )
        )
        return 0
    if args.cmd == "run":
        import agent_office_saju_learn

        card = agent_office_saju_learn.get_card(args.card_id)
        if not card:
            print("card not found")
            return 1
        r = run_card_council(card)
        apply_card_result(args.card_id, r, mode="manual")
        print(r.report)
        print("PASS" if r.passed else "FAIL")
        return 0 if r.passed else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
