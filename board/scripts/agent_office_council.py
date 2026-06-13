"""
금융·사주 위원회 — 조사(전원 보고서) → 토론 → 검증 1작업.

  python scripts/agent_office_council.py run saju-learn
  python scripts/agent_office_council.py run finance

환경 변수:
  AGENT_OFFICE_USE_COUNCIL=1   예약 큐를 위원회 1건으로 유지 (기본 1)
  AGENT_OFFICE_COUNCIL_SAJU_QUEUE=1
  AGENT_OFFICE_COUNCIL_FINANCE_QUEUE=1
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import agent_registry

DIVISION_SAJU = agent_registry.DIVISION_SAJU
DIVISION_FINANCE = agent_registry.DIVISION_FINANCE

SOURCE_COUNCIL_SAJU = "council_saju"
SOURCE_COUNCIL_FINANCE = "council_finance"

SAJU_COUNCIL_BODY = (
    "학습 카드·pack·PII·태그·확정·오류를 전 에이전트가 조사하고, "
    "토론·검증 후 PASS 시 pack·CURSOR 문서를 갱신합니다."
)
FINANCE_COUNCIL_BODY = (
    "블로그·댓글·PII·ETF·피드·사이트 상태를 전 에이전트가 조사하고, "
    "토론·검증 후 PASS 시 결론만 기록합니다."
)

# (agent_id, job name in agent_office_jobs.JOB_HANDLERS)
SAJU_PANEL: list[tuple[str, str]] = [
    ("saju_privacy", "saju_pii_scan"),
    ("saju_reader", "saju_card_pulse"),
    ("saju_scholar", "saju_review_hint"),
    ("saju_structurer", "saju_tag_digest"),
    ("saju_curator", "saju_pack_sync"),
    ("saju_rl", "saju_gap_autofill"),
    ("saju_error_fix", "saju_error_resolve"),
]

FINANCE_PANEL: list[tuple[str, str]] = [
    ("privacy", "pii_scan"),
    ("researcher", "fact_pulse"),
    ("structurer", "meta_digest"),
    ("creator", "draft_check"),
    ("observer", "site_watch"),
    ("listener", "comment_scan"),
    ("rl", "daily_conclusion"),
]


@dataclass
class PanelReport:
    agent_id: str
    job: str
    ok: bool
    summary: str


@dataclass
class CouncilResult:
    division: str
    passed: bool
    report: str
    panel: list[PanelReport] = field(default_factory=list)
    debate_issues: list[str] = field(default_factory=list)
    verify_issues: list[str] = field(default_factory=list)
    wiki_id: str = ""


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def use_council() -> bool:
    return os.getenv("AGENT_OFFICE_USE_COUNCIL", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def council_queue_target(division: str) -> int:
    if division == DIVISION_SAJU:
        return max(0, int(os.getenv("AGENT_OFFICE_COUNCIL_SAJU_QUEUE", "1") or "1"))
    return max(0, int(os.getenv("AGENT_OFFICE_COUNCIL_FINANCE_QUEUE", "1") or "1"))


def queue_status(division: str) -> dict:
    """UI·API용 자동 큐 표시 (위원회 1건 또는 예약 3건)."""
    if use_council() and division == DIVISION_SAJU:
        try:
            import agent_office_saju_card_council as card_council

            if card_council.use_card_council():
                return card_council.queue_status()
        except Exception:
            pass
    if use_council():
        return {
            "mode": "council",
            "active": count_council_active(division),
            "target": council_queue_target(division),
            "label": "위원회",
        }
    if division == DIVISION_SAJU:
        import agent_office_saju_reserved_tasks as saju_reserved

        return {
            "mode": "reserved",
            "active": saju_reserved.count_reserved_active(),
            "target": max(1, int(os.getenv("AGENT_OFFICE_SAJU_RESERVED_QUEUE", "3") or "3")),
            "label": "명리 예약",
        }
    import agent_office_reserved_tasks as finance_reserved

    return {
        "mode": "reserved",
        "active": finance_reserved.count_reserved_active(),
        "target": max(1, int(os.getenv("AGENT_OFFICE_RESERVED_QUEUE", "3") or "3")),
        "label": "예약",
    }


def council_source(division: str) -> str:
    return SOURCE_COUNCIL_SAJU if division == DIVISION_SAJU else SOURCE_COUNCIL_FINANCE


def council_wiki_id(division: str) -> str:
    return "wiki_pulse_council_saju" if division == DIVISION_SAJU else "wiki_pulse_council_finance"


def council_title(division: str) -> str:
    return "명리 위원회" if division == DIVISION_SAJU else "금융 위원회"


def _panel_for(division: str) -> list[tuple[str, str]]:
    if division == DIVISION_SAJU:
        return list(SAJU_PANEL)
    panel = list(FINANCE_PANEL)
    try:
        import etf_ops_policy

        if etf_ops_policy.etf_ops_enabled():
            panel.append(("etf_sync", "etf_sync"))
    except Exception:
        pass
    return panel


def _run_panel_jobs(division: str) -> list[PanelReport]:
    import agent_office_jobs

    registry = agent_registry.load_registry()
    agents_by_id = {
        a.get("id"): a
        for a in registry.get("agents") or []
        if isinstance(a, dict) and a.get("id")
    }
    out: list[PanelReport] = []
    for aid, job in _panel_for(division):
        agent = agents_by_id.get(aid) or {"id": aid, "job": job}
        agent = {**agent, "job": job}
        try:
            ok, msg = agent_office_jobs.run_job(agent)
            out.append(PanelReport(aid, job, ok, (msg or "")[:1200]))
        except Exception as e:
            out.append(PanelReport(aid, job, False, f"실행 오류: {e!s}"[:400]))
    return out


def _debate(panel: list[PanelReport], division: str) -> list[str]:
    """보고서 간 모순·주의점."""
    issues: list[str] = []
    by_id = {p.agent_id: p for p in panel}

    if division == DIVISION_SAJU:
        err = by_id.get("saju_error_fix")
        if err and not err.ok:
            issues.append(f"오류해결: {err.summary[:200]}")
        pii = by_id.get("saju_privacy")
        if pii and not pii.ok:
            issues.append(f"PII: {pii.summary[:200]}")
        scholar = by_id.get("saju_scholar")
        struct = by_id.get("saju_structurer")
        if scholar and struct:
            if "대기" in scholar.summary and "검수 대기" in scholar.summary:
                if "태그" in struct.summary and "없음" not in struct.summary:
                    issues.append("명리: 대기 카드가 있는데 태그 분포는 존재 — 검수 우선")
        curator = by_id.get("saju_curator")
        reader = by_id.get("saju_reader")
        if curator and reader:
            if "0" in reader.summary and "pack" in curator.summary.lower():
                if re.search(r"pack\s*0", curator.summary, re.I):
                    issues.append("독해·전장: 확정 카드 수와 pack 건수 불일치 가능")
    else:
        pii = by_id.get("privacy")
        if pii and not pii.ok:
            issues.append(f"PII: {pii.summary[:200]}")
        rl = by_id.get("rl")
        if rl and "대기" in (rl.summary or ""):
            m = re.search(r"대기\s*(\d+)", rl.summary)
            if m and int(m.group(1)) > 5:
                issues.append(f"RL: 대기 지시 {m.group(1)}건 — 우선순위 정리 필요")

    failed = [p for p in panel if not p.ok]
    if len(failed) >= 3:
        issues.append(f"조사 실패 {len(failed)}건 — 위원회 전원 재실행 권장")

    return issues


def _verify_saju(panel: list[PanelReport]) -> list[str]:
    issues: list[str] = []
    try:
        import agent_office_saju_learn

        st = agent_office_saju_learn.stats()
        if int(st.get("pending") or 0) > 30:
            issues.append(f"학습 대기 카드 {st['pending']}건 과다 (상한 30)")
        pack_path = BOARD / "data" / "saju_learning" / "saju_knowledge_pack.json"
        if int(st.get("confirmed") or 0) > 0 and not pack_path.is_file():
            issues.append("확정 카드 있으나 saju_knowledge_pack.json 없음")
    except Exception as e:
        issues.append(f"학습부 통계: {e!s}"[:120])

    for p in panel:
        if p.agent_id in ("saju_privacy", "saju_error_fix") and not p.ok:
            issues.append(f"{p.agent_id} 미통과")

    return issues


def _verify_finance(panel: list[PanelReport]) -> list[str]:
    issues: list[str] = []
    try:
        import agent_office_health

        for c in agent_office_health.run_checks().get("checks") or []:
            if isinstance(c, dict) and not c.get("ok"):
                issues.append(f"{c.get('name')}: {str(c.get('detail') or '')[:80]}")
    except Exception as e:
        issues.append(f"health: {e!s}"[:120])

    for p in panel:
        if p.agent_id == "privacy" and not p.ok:
            issues.append("privacy PII 미통과")

    return issues


def run_council(division: str) -> CouncilResult:
    division = (division or DIVISION_FINANCE).strip()
    if division not in (DIVISION_FINANCE, DIVISION_SAJU):
        division = DIVISION_FINANCE

    panel = _run_panel_jobs(division)
    debate = _debate(panel, division)
    verify = _verify_saju(panel) if division == DIVISION_SAJU else _verify_finance(panel)

    passed = not verify and len([p for p in panel if not p.ok]) <= 2

    title = council_title(division)
    lines = [
        f"【{title} · {_now()}】",
        f"단계: 조사({len(panel)}통) → 토론 → 검증",
        f"검증: {'PASS' if passed else 'FAIL'}",
        "",
        "■ 1. 조사 보고서",
    ]
    for i, p in enumerate(panel, 1):
        flag = "OK" if p.ok else "NG"
        lines.append(f"  {i}. [{flag}] {p.agent_id} ({p.job})")
        for part in (p.summary or "").split("\n"):
            part = part.strip()
            if part:
                lines.append(f"     {part[:220]}")

    lines.extend(["", "■ 2. 토론 (쟁점)"])
    if debate:
        for d in debate:
            lines.append(f"  · {d}")
    else:
        lines.append("  · 보고서 간 중대한 모순 없음")

    lines.extend(["", "■ 3. 검증"])
    if verify:
        for v in verify:
            lines.append(f"  · NG {v}")
    else:
        lines.append("  · 자동 체크리스트 통과")

    lines.extend(["", "■ 4. 결론"])
    if passed:
        if division == DIVISION_SAJU:
            lines.append("  · PASS — pack·CURSOR_SAJU_LEARN.md 갱신 권장")
            lines.append("  · 확정 카드는 사무실 「확정」 버튼으로 반영")
        else:
            lines.append("  · PASS — 금융 피드·블로그·댓글 상태 기록 완료")
    else:
        lines.append("  · FAIL — 위 검증·조사 실패 해결 후 재실행")

    report = "\n".join(lines)[:8000]
    return CouncilResult(
        division=division,
        passed=passed,
        report=report,
        panel=panel,
        debate_issues=debate,
        verify_issues=verify,
        wiki_id=council_wiki_id(division),
    )


def apply_pass_actions(result: CouncilResult) -> list[str]:
    """PASS 후 부수 작업."""
    actions: list[str] = []
    if not result.passed:
        return actions
    if result.division == DIVISION_SAJU:
        try:
            import agent_office_saju_learn

            pack = agent_office_saju_learn.export_pack()
            agent_office_saju_learn.render_cursor_md()
            actions.append(f"pack {pack.get('card_count', 0)}건 export")
        except Exception as e:
            actions.append(f"pack export 실패: {e!s}"[:80])
    return actions


def push_council_wiki(task: dict, result: CouncilResult) -> bool:
    try:
        import agent_office_wiki_store
        import agent_office_swiki_sync

        wid = result.wiki_id or council_wiki_id(result.division)
        card = {
            "id": wid,
            "domain": result.division,
            "layer": "10_Wiki",
            "title": council_title(result.division),
            "summary": (
                f"{'PASS' if result.passed else 'FAIL'} · "
                f"조사 {len(result.panel)}건 · 검증 이슈 {len(result.verify_issues)}건"
            )[:500],
            "body": result.report[:8000],
            "task_id": task.get("id"),
            "source": council_source(result.division),
            "storage_tier": "github_archive",
            "agent_primary": "structurer" if result.division == DIVISION_FINANCE else "saju_structurer",
            "agent_synth": "rl" if result.division == DIVISION_FINANCE else "saju_rl",
            "ts": _now(),
            "tags": ["위원회", "검증", result.division],
            "council_pass": result.passed,
        }
        agent_office_swiki_sync.push_wiki_card(card, force=True)
        return True
    except Exception:
        return False


def process_council_task(task: dict, registry: dict) -> tuple[bool, str]:
    """task_runner 에서 council 작업 1건 처리."""
    import agent_office_log
    import agent_office_tasks

    tid = task.get("id")
    division = (task.get("division") or DIVISION_FINANCE).strip()
    if division not in (DIVISION_FINANCE, DIVISION_SAJU):
        division = DIVISION_SAJU if task.get("source") == SOURCE_COUNCIL_SAJU else DIVISION_FINANCE

    agent_office_tasks.update_task(
        tid,
        status="in_progress",
        started_at=_now(),
        handled_by="saju_structurer" if division == DIVISION_SAJU else "structurer",
    )
    agent_office_log.append_message(
        from_id="ceo",
        to_id="saju_structurer" if division == DIVISION_SAJU else "structurer",
        kind="task",
        text=f"[위원회 #{tid}] {council_title(division)} 조사·토론·검증 시작",
        division=division,
    )

    result = run_council(division)
    extra = apply_pass_actions(result) if result.passed else []
    if extra:
        result.report += "\n\n■ 적용\n  · " + "\n  · ".join(extra)

    push_council_wiki(task, result)

    agent_office_tasks.update_task(
        tid,
        status="done",
        finished_at=_now(),
        result=result.report[:4000],
        wiki_id=result.wiki_id,
        council_pass=result.passed,
    )

    kind = "conclusion" if result.passed else "system"
    agent_office_log.append_message(
        from_id="saju_rl" if division == DIVISION_SAJU else "rl",
        to_id="ceo",
        kind=kind,
        text=result.report[:1500],
        division=division,
    )

    summary = (
        f"{'PASS' if result.passed else 'FAIL'} · "
        f"{council_title(division)} · 조사 {len(result.panel)} · "
        f"검증 {len(result.verify_issues)} · 토론 {len(result.debate_issues)}"
    )
    return result.passed, summary


def _is_council_task(t: dict) -> bool:
    return (t.get("source") or "") in (SOURCE_COUNCIL_SAJU, SOURCE_COUNCIL_FINANCE)


def count_council_active(division: str) -> int:
    import agent_office_tasks

    src = council_source(division)
    n = 0
    for t in agent_office_tasks.load_tasks().get("tasks") or []:
        if not isinstance(t, dict):
            continue
        if t.get("source") != src:
            continue
        if (t.get("status") or "queued") in ("queued", "in_progress"):
            n += 1
    return n


def ensure_council_queue(division: str) -> int:
    """위원회 대기 1건 유지. 추가한 수."""
    import agent_office_tasks

    if not use_council():
        return 0
    target = council_queue_target(division)
    if target <= 0:
        return 0
    added = 0
    while count_council_active(division) < target:
        body = SAJU_COUNCIL_BODY if division == DIVISION_SAJU else FINANCE_COUNCIL_BODY
        agent_office_tasks.add_task(
            body=body,
            assign_to="saju_structurer" if division == DIVISION_SAJU else "structurer",
            title=council_title(division),
            priority="normal",
            created_by="위원회",
            source=council_source(division),
            division=division,
            quiet=True,
        )
        added += 1
        if added > target + 1:
            break
    return added


def main() -> int:
    import board_env

    board_env.load_board_env()
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["run"])
    p.add_argument("division", choices=["finance", "saju-learn"])
    args = p.parse_args()
    div = DIVISION_SAJU if args.division == "saju-learn" else DIVISION_FINANCE
    r = run_council(div)
    print(r.report)
    print("---")
    print("PASS" if r.passed else "FAIL", r.wiki_id)
    if r.passed:
        print(apply_pass_actions(r))
    return 0 if r.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
