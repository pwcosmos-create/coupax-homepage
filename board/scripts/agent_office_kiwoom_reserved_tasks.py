"""
키움 차수거래 예약 큐 — 대기 작업 TARGET개 유지 (로테이션 학습).

  python scripts/agent_office_kiwoom_reserved_tasks.py ensure
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

SOURCE_RESERVED_KIWOM = "reserved_kiwoom"
DIVISION = agent_registry.DIVISION_KIWOM
DEFAULT_TARGET = int(os.getenv("AGENT_OFFICE_KIWOM_RESERVED_QUEUE", "3") or "3")

KIWOM_RESERVED_TEMPLATES: list[dict] = [
    {
        "assign_to": "kiwoom_reader",
        "title": "차수 전략 수집",
        "body": "확정·대기 학습 카드에서 1·2·3차 진입·청산 조건을 조사해 차수거래 패턴을 요약해 주세요.",
    },
    {
        "assign_to": "kiwoom_risk",
        "title": "손절·익절 점검",
        "body": "대기 카드의 손절·익절·분할 규칙을 조사해 누락·모순 힌트를 정리해 주세요.",
    },
    {
        "assign_to": "kiwoom_structurer",
        "title": "태그·pack 구조",
        "body": "학습 카드 태그 분포와 kiwoom_knowledge_pack.json 구조를 조사해 Wiki 반영 방향을 제안해 주세요.",
    },
    {
        "assign_to": "kiwoom_order",
        "title": "주문·체결 점검",
        "body": "최근 학습 카드·블로그에서 주문·미체결·체결·호가 관련 기록을 조사해 요약해 주세요.",
    },
    {
        "assign_to": "kiwoom_account",
        "title": "계좌·예수금 점검",
        "body": "학습 카드에서 예수금·주문가능금액·잔고·평가금 관련 메모를 조사해 HTS 대조 체크리스트를 요약해 주세요. 계좌번호는 기록하지 마세요.",
    },
    {
        "assign_to": "kiwoom_account",
        "title": "계좌 이동·차수 연계",
        "body": "확정 카드에서 계좌 이체·대체·계좌 차수거래 시나리오를 조사해 이체 전후 점검 항목을 요약해 주세요.",
    },
    {
        "assign_to": "kiwoom_reader",
        "title": "계좌별 차수 패턴",
        "body": "학습 카드에서 위탁·CMA·연금 등 계좌별 차수 배분 사례를 조사해 공통 패턴 3가지를 정리해 주세요.",
    },
    {
        "assign_to": "kiwoom_account",
        "title": "계좌간 이동 차수 운용",
        "body": "「계좌간 이동으로 하는 차수거래」 확정 카드를 조사해 1→2→3차 이체 체크리스트 요약과 스킵 규칙을 정리해 주세요.",
    },
    {
        "assign_to": "kiwoom_privacy",
        "title": "계좌·PII 스캔",
        "body": "학습 카드에 계좌번호·비밀번호·API키 패턴이 있는지 조사해 보고해 주세요.",
    },
    {
        "assign_to": "kiwoom_curator",
        "title": "확정·export",
        "body": "확정 대기 큐와 pack·CURSOR_KIWOM_LEARN.md 갱신 상태를 조사해 빠진 카드가 있는지 정리해 주세요.",
    },
    {
        "assign_to": "kiwoom_rl",
        "title": "차수거래 우선순위",
        "body": "학습부 대기·확정 건수와 최근 작업을 조사해 다음 검수·학습 우선 3가지를 정리해 주세요.",
    },
    {
        "assign_to": "kiwoom_reader",
        "title": "종목·티커 패턴",
        "body": "확정 카드에서 종목·티커·섹터 언급 패턴을 조사해 반복 전략 스타일을 요약해 주세요.",
    },
    {
        "assign_to": "kiwoom_structurer",
        "title": "차수별 교차 취합",
        "body": "확정 카드 2건 이상을 비교해 공통 차수 프레임(진입·추가·청산)을 Wiki 메모로 취합해 주세요.",
    },
    {
        "assign_to": "kiwoom_reader",
        "title": "월배당 ETF 차수",
        "body": "확정 카드에서 월배당 ETF·배당락·분배금과 차수(1·2·3차) 연계 규칙을 조사해 요약해 주세요.",
    },
    {
        "assign_to": "kiwoom_risk",
        "title": "VI·급락 차수 중단",
        "body": "확정 카드에서 VI·급락·거래정지 시 2·3차 중단·손절 우선 규칙을 조사해 체크리스트로 정리해 주세요.",
    },
    {
        "assign_to": "kiwoom_rl",
        "title": "체결·카드 대조",
        "body": "「학습 카드·체결 로그 대조」 확정 카드를 조사해 피드백 우선순위 3가지를 정리해 주세요.",
    },
]


def _load_meta(data: dict) -> int:
    try:
        return int(data.get("kiwoom_reserved_rotation") or 0)
    except (TypeError, ValueError):
        return 0


def _save_meta(data: dict, rotation: int) -> None:
    data["kiwoom_reserved_rotation"] = rotation % max(len(KIWOM_RESERVED_TEMPLATES), 1)
    data["kiwoom_reserved_target"] = DEFAULT_TARGET


def _is_kiwoom_reserved(t: dict) -> bool:
    if not isinstance(t, dict):
        return False
    if t.get("source") == SOURCE_RESERVED_KIWOM:
        return True
    return t.get("source") == "reserved" and (t.get("division") or "").strip() == DIVISION


def count_reserved_queued() -> int:
    n = 0
    for t in agent_office_tasks.load_tasks().get("tasks") or []:
        if _is_kiwoom_reserved(t) and (t.get("status") or "queued") == "queued":
            n += 1
    return n


def count_reserved_in_progress() -> int:
    n = 0
    for t in agent_office_tasks.load_tasks().get("tasks") or []:
        if _is_kiwoom_reserved(t) and t.get("status") == "in_progress":
            n += 1
    return n


def count_reserved_active() -> int:
    return count_reserved_queued() + count_reserved_in_progress()


def _recent_reserved_bodies(limit: int = 12) -> set[str]:
    bodies: set[str] = set()
    for t in reversed(agent_office_tasks.load_tasks().get("tasks") or []):
        if not _is_kiwoom_reserved(t):
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
    for offset in range(len(KIWOM_RESERVED_TEMPLATES)):
        idx = (rotation + offset) % len(KIWOM_RESERVED_TEMPLATES)
        tpl = dict(KIWOM_RESERVED_TEMPLATES[idx])
        if tpl.get("body") not in recent:
            _save_meta(data, idx + 1)
            agent_office_tasks.save_tasks(data)
            return tpl
    tpl = dict(KIWOM_RESERVED_TEMPLATES[rotation % len(KIWOM_RESERVED_TEMPLATES)])
    _save_meta(data, rotation + 1)
    agent_office_tasks.save_tasks(data)
    return tpl


def add_reserved_task(*, quiet: bool = True) -> dict:
    tpl = pick_next_template()
    return agent_office_tasks.add_task(
        body=tpl["body"],
        assign_to=tpl.get("assign_to") or "all",
        title=tpl.get("title") or "차수거래 예약",
        priority="normal",
        created_by="차수예약",
        source=SOURCE_RESERVED_KIWOM,
        division=DIVISION,
        quiet=quiet,
    )


def ensure_reserved_queue(target: int | None = None) -> int:
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
        f"kiwoom_reserved_queued={count_reserved_queued()} "
        f"active={count_reserved_active()} added={n}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
