"""
사무실 예약 작업 큐 — 대기(queued) 예약 작업을 항상 TARGET개 유지.

  python scripts/agent_office_reserved_tasks.py ensure
  python scripts/agent_office_reserved_tasks.py ensure --target 3
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_tasks

SOURCE_RESERVED = "reserved"
DEFAULT_TARGET = int(os.getenv("AGENT_OFFICE_RESERVED_QUEUE", "3") or "3")

# 예약 작업 제목 → wiki_pulse_* 고정 id (③ 한 카드 갱신)
RESERVED_TITLE_PULSE_SLUG: dict[str, str] = {
    "팩트 펄스": "fact_pulse",
    "월배당 ETF 점검": "etf_check",
    "댓글·FAQ 스캔": "faq_scan",
    "사이트·시트 관측": "site_observe",
    "지식 메타 취합": "meta_digest",
    "블로그 글감": "blog_idea",
    "PII 스캔": "pii_scan",
    "우선순위 브리핑": "priority_brief",
    "금리·매크로 체크": "macro_check",
}


def pulse_slug_for_title(title: str) -> str:
    t = (title or "").strip()
    if t in RESERVED_TITLE_PULSE_SLUG:
        return RESERVED_TITLE_PULSE_SLUG[t]
    import re

    s = re.sub(r"[^\w가-힣]+", "_", t).strip("_")[:40]
    return s or "reserved"


def pulse_wiki_id_for_title(title: str) -> str:
    return f"wiki_pulse_{pulse_slug_for_title(title)}"

# 로테이션 예약 작업 풀 (담당·주제 다양화)
RESERVED_TEMPLATES: list[dict] = [
    {
        "assign_to": "researcher",
        "title": "팩트 펄스",
        "body": "블로그·사이트 최신 글과 조회·댓글 현황을 조사해 오늘 이슈 요약을 정리해 주세요.",
    },
    {
        "assign_to": "etf_sync",
        "title": "월배당 ETF 점검",
        "body": "월배당 ETF 시트 종목 수·데이터 신선도를 조사하고 갱신이 필요한지 정리해 주세요.",
    },
    {
        "assign_to": "listener",
        "title": "댓글·FAQ 스캔",
        "body": "최근 블로그 댓글 톤과 FAQ 후보 질문을 조사해 요약해 주세요.",
    },
    {
        "assign_to": "observer",
        "title": "사이트·시트 관측",
        "body": "ETF 허브·시트 데이터와 화면 상태를 점검해 이상 여부를 보고해 주세요.",
    },
    {
        "assign_to": "structurer",
        "title": "지식 메타 취합",
        "body": "최근 사무실 피드·작업 로그를 구조화해 Wiki/메타 카드 초안 방향을 제안해 주세요.",
    },
    {
        "assign_to": "creator",
        "title": "블로그 글감",
        "body": (
            "웹 검색으로 최근 금융·재테크 이슈를 조사해 E-E-A-T 장문 글감 후보 3건을 선정·제안해 주세요. "
            "사이트 기존 글·댓글과 겹치지 않는 주제를 우선합니다."
        ),
    },
    {
        "assign_to": "privacy",
        "title": "PII 스캔",
        "body": "최근 댓글·작업지시에 개인정보 패턴이 있는지 조사해 보고해 주세요.",
    },
    {
        "assign_to": "rl",
        "title": "우선순위 브리핑",
        "body": "대기 지시·피드 현황을 조사해 내일 우선 처리 항목을 정리해 주세요.",
    },
    {
        "assign_to": "researcher",
        "title": "금리·매크로 체크",
        "body": "금리·환율·매크로 관련 최근 블로그·댓글 키워드를 조사해 이슈 카드를 정리해 주세요.",
    },
]


def _active_reserved_templates() -> list[dict]:
    import etf_ops_policy

    if etf_ops_policy.etf_ops_enabled():
        return RESERVED_TEMPLATES
    blocked_assign = {"etf_sync"}
    blocked_body_keys = ("ETF 허브", "월배당 ETF 시트")
    out: list[dict] = []
    for tpl in RESERVED_TEMPLATES:
        if tpl.get("assign_to") in blocked_assign:
            continue
        body = tpl.get("body") or ""
        if any(k in body for k in blocked_body_keys):
            continue
        out.append(tpl)
    return out or RESERVED_TEMPLATES[:1]


def _load_meta(data: dict) -> int:
    try:
        return int(data.get("reserved_rotation") or 0)
    except (TypeError, ValueError):
        return 0


def _save_meta(data: dict, rotation: int) -> None:
    data["reserved_rotation"] = rotation % max(len(_active_reserved_templates()), 1)
    data["reserved_target"] = DEFAULT_TARGET


def _is_finance_reserved(t: dict) -> bool:
    if not isinstance(t, dict) or t.get("source") != SOURCE_RESERVED:
        return False
    div = (t.get("division") or "finance").strip()
    return div != "saju-learn"


def count_reserved_queued() -> int:
    n = 0
    for t in agent_office_tasks.load_tasks().get("tasks") or []:
        if not isinstance(t, dict):
            continue
        if (t.get("status") or "queued") != "queued":
            continue
        if _is_finance_reserved(t):
            n += 1
    return n


def count_reserved_in_progress() -> int:
    n = 0
    for t in agent_office_tasks.load_tasks().get("tasks") or []:
        if not isinstance(t, dict):
            continue
        if t.get("status") != "in_progress":
            continue
        if _is_finance_reserved(t):
            n += 1
    return n


def _recent_reserved_bodies(limit: int = 12) -> set[str]:
    bodies: set[str] = set()
    for t in reversed(agent_office_tasks.load_tasks().get("tasks") or []):
        if not isinstance(t, dict) or not _is_finance_reserved(t):
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

    pool = _active_reserved_templates()
    for offset in range(len(pool)):
        idx = (rotation + offset) % len(pool)
        tpl = dict(pool[idx])
        if tpl.get("body") not in recent:
            _save_meta(data, idx + 1)
            agent_office_tasks.save_tasks(data)
            return tpl

    tpl = dict(pool[rotation % len(pool)])
    _save_meta(data, rotation + 1)
    agent_office_tasks.save_tasks(data)
    return tpl


def add_reserved_task(*, quiet: bool = True) -> dict:
    tpl = pick_next_template()
    return agent_office_tasks.add_task(
        body=tpl["body"],
        assign_to=tpl.get("assign_to") or "all",
        title=tpl.get("title") or "예약 작업",
        priority="normal",
        created_by="예약",
        source=SOURCE_RESERVED,
        division="finance",
        quiet=quiet,
    )


def count_reserved_active() -> int:
    """대기 + 진행 중 예약 작업 수 (중복 생성 방지)."""
    return count_reserved_queued() + count_reserved_in_progress()


def ensure_reserved_queue(target: int | None = None) -> int:
    """대기 중인 예약 작업이 target개가 되도록 추가. 추가한 개수 반환."""
    try:
        import agent_office_council
        import agent_registry

        if agent_office_council.use_council():
            return agent_office_council.ensure_council_queue(
                agent_registry.DIVISION_FINANCE
            )
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
    p.add_argument("--target", type=int, default=DEFAULT_TARGET)
    args = p.parse_args()
    n = ensure_reserved_queue(args.target)
    print(f"reserved_queued={count_reserved_queued()} added={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
