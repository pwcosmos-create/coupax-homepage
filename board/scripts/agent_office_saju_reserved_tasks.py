"""
사주·명리 학습부 예약 큐 — queued 예약 작업을 항상 TARGET개 유지 (자율 학습).

  python scripts/agent_office_saju_reserved_tasks.py ensure
  python scripts/agent_office_saju_reserved_tasks.py ensure --target 3

환경 변수: AGENT_OFFICE_SAJU_RESERVED_QUEUE (기본 3)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_tasks
import agent_registry

SOURCE_RESERVED_SAJU = "reserved_saju"
DIVISION_SAJU = agent_registry.DIVISION_SAJU
DEFAULT_TARGET = int(os.getenv("AGENT_OFFICE_SAJU_RESERVED_QUEUE", "3") or "3")

# 명리학 자율 학습 로테이션 (담당 에이전트·주제)
SAJU_RESERVED_TEMPLATES: list[dict] = [
    {
        "assign_to": "saju_reader",
        "title": "풀이 카드 학습",
        "body": "검수 대기·확정된 사주 풀이 카드를 조사해 핵심 격국·톤을 요약하고 명리 학습 포인트를 정리해 주세요.",
    },
    {
        "assign_to": "saju_scholar",
        "title": "오행·십신 점검",
        "body": "학습 카드 본문에서 오행·십신·일주·대운 관련 서술을 조사해 태그 누락·모순 힌트를 명리 관점으로 정리해 주세요.",
    },
    {
        "assign_to": "saju_structurer",
        "title": "태그·pack 구조",
        "body": "확정 카드의 태그 분포와 saju_knowledge_pack.json 구조를 조사해 10_Wiki(saju-learn) 반영 방향을 제안해 주세요.",
    },
    {
        "assign_to": "saju_privacy",
        "title": "PII·민감정보 스캔",
        "body": "대기 중인 풀이 카드에 이름·생년월일·연락처 패턴이 있는지 조사해 보고해 주세요.",
    },
    {
        "assign_to": "saju_curator",
        "title": "확정·export 점검",
        "body": "확정 대기 큐와 pack·CURSOR_SAJU_LEARN.md 갱신 상태를 조사해 학습 반영이 빠진 카드가 있는지 정리해 주세요.",
    },
    {
        "assign_to": "saju_rl",
        "title": "명리 학습 우선순위",
        "body": "사주 학습부 대기·확정 건수와 최근 작업을 조사해 다음에 검수·학습할 우선 항목 3가지를 정리해 주세요.",
    },
    {
        "assign_to": "saju_reinspector",
        "title": "위원회 인증 재점검",
        "body": "PASS 확정 카드의 council_*·강화 이력·면책 문구를 조사해 재점검 우선순위와 품질 리스크 3건을 정리해 주세요.",
    },
    {
        "assign_to": "saju_scholar",
        "title": "용신·격국 패턴",
        "body": "확정 풀이에서 용신·격국·기신 언급 패턴을 조사해 반복되는 명리 해석 스타일을 요약해 주세요.",
    },
    {
        "assign_to": "saju_reader",
        "title": "신살·세운 키워드",
        "body": "학습 카드에서 신살·세운·월운 관련 키워드를 조사해 태그 사전 보완안을 제안해 주세요.",
    },
    {
        "assign_to": "saju_structurer",
        "title": "확정분 교차 취합",
        "body": "확정된 카드 2건 이상을 비교 조사해 공통 명리 프레임(오행 균형·십신 강약)을 Wiki 메모 형태로 취합해 주세요.",
    },
]


def _load_meta(data: dict) -> int:
    try:
        return int(data.get("saju_reserved_rotation") or 0)
    except (TypeError, ValueError):
        return 0


def _save_meta(data: dict, rotation: int) -> None:
    data["saju_reserved_rotation"] = rotation % max(len(SAJU_RESERVED_TEMPLATES), 1)
    data["saju_reserved_target"] = DEFAULT_TARGET


def _is_saju_reserved(t: dict) -> bool:
    if not isinstance(t, dict):
        return False
    if t.get("source") == SOURCE_RESERVED_SAJU:
        return True
    return (
        t.get("source") == "reserved"
        and (t.get("division") or "").strip() == DIVISION_SAJU
    )


def count_reserved_queued() -> int:
    n = 0
    for t in agent_office_tasks.load_tasks().get("tasks") or []:
        if _is_saju_reserved(t) and (t.get("status") or "queued") == "queued":
            n += 1
    return n


def count_reserved_in_progress() -> int:
    n = 0
    for t in agent_office_tasks.load_tasks().get("tasks") or []:
        if _is_saju_reserved(t) and t.get("status") == "in_progress":
            n += 1
    return n


def count_reserved_active() -> int:
    return count_reserved_queued() + count_reserved_in_progress()


def _recent_reserved_bodies(limit: int = 12) -> set[str]:
    bodies: set[str] = set()
    for t in reversed(agent_office_tasks.load_tasks().get("tasks") or []):
        if not _is_saju_reserved(t):
            continue
        b = (t.get("body") or "").strip()
        if b:
            bodies.add(b)
        if len(bodies) >= limit:
            break
    return bodies


def pick_next_template() -> dict:
    data = agent_office_tasks.load_tasks()
    rotation = _load_meta(data)
    recent = _recent_reserved_bodies()

    for offset in range(len(SAJU_RESERVED_TEMPLATES)):
        idx = (rotation + offset) % len(SAJU_RESERVED_TEMPLATES)
        tpl = dict(SAJU_RESERVED_TEMPLATES[idx])
        if tpl.get("body") not in recent:
            _save_meta(data, idx + 1)
            agent_office_tasks.save_tasks(data)
            return tpl

    tpl = dict(SAJU_RESERVED_TEMPLATES[rotation % len(SAJU_RESERVED_TEMPLATES)])
    _save_meta(data, rotation + 1)
    agent_office_tasks.save_tasks(data)
    return tpl


def add_reserved_task(*, quiet: bool = True) -> dict:
    tpl = pick_next_template()
    return agent_office_tasks.add_task(
        body=tpl["body"],
        assign_to=tpl.get("assign_to") or "all",
        title=tpl.get("title") or "명리 예약 학습",
        priority="normal",
        created_by="명리예약",
        source=SOURCE_RESERVED_SAJU,
        division=DIVISION_SAJU,
        quiet=quiet,
    )


def ensure_reserved_queue(target: int | None = None) -> int:
    try:
        import agent_office_council

        if agent_office_council.use_council():
            try:
                import agent_office_saju_card_council as card_council

                if card_council.use_card_council():
                    return card_council.ensure_card_council_queue()
            except Exception:
                pass
            return agent_office_council.ensure_council_queue(DIVISION_SAJU)
    except Exception:
        pass
    target = max(1, int(target or DEFAULT_TARGET))
    added = 0
    while count_reserved_active() < target:
        add_reserved_task(quiet=True)
        added += 1
        if added > target + 2:
            break
    return added


def main() -> int:
    import argparse

    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    ens = sub.add_parser("ensure")
    ens.add_argument("--target", type=int, default=DEFAULT_TARGET)
    args = p.parse_args()
    if args.cmd != "ensure":
        p.print_help()
        return 1
    n = ensure_reserved_queue(args.target)
    print(
        f"saju_reserved_queued={count_reserved_queued()} "
        f"active={count_reserved_active()} added={n}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
