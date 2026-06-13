"""
수석 개발자실 예약 큐 — queued 예약 작업을 항상 TARGET개 유지.
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

SOURCE_RESERVED_CHIEF_DEV = "reserved_chief_dev"
DIVISION_CHIEF_DEV = agent_registry.DIVISION_CHIEF_DEV
DEFAULT_TARGET = int(os.getenv("AGENT_OFFICE_CHIEF_DEV_RESERVED_QUEUE", "3") or "3")

# 수석 개발자실 자율 학습 로테이션
CHIEF_DEV_RESERVED_TEMPLATES: list[dict] = [
    {
        "assign_to": "chief-arch",
        "title": "코드 구조 리뷰",
        "body": "최근 변경된 백엔드 로직의 결합도 및 응집도를 평가하고, 중장기적으로 유지보수성을 높이기 위한 리팩토링 전략을 수립하세요.",
    },
    {
        "assign_to": "chief-rag",
        "title": "사내 RAG 품질 개선",
        "body": "수집된 개발 문서 벡터 DB의 검색 정확도(Retrieval Accuracy)를 평가하고, 검색 결과의 톤앤매너 개선안을 제안하세요.",
    },
    {
        "assign_to": "chief-ops",
        "title": "리소스 병목 모니터링",
        "body": "Flask 서버 및 gunicorn 워커들의 CPU/메모리 점유율 임계치 초과 여부를 시뮬레이션하고 무중단 배포 안정성을 평가하세요.",
    },
    {
        "assign_to": "chief-arch",
        "title": "API 보안 취약점 점검",
        "body": "사내 API 엔드포인트의 입력값 검증 로직과 인증 메커니즘을 검토하여 OWASP 10대 취약점 관점에서의 안전성을 분석하세요.",
    },
    {
        "assign_to": "chief-rag",
        "title": "신규 프레임워크 동향 스크랩",
        "body": "React, Vue 등 프론트엔드 최신 릴리즈 노트를 크롤링하여 당사 기술 스택에 적용 가능한 최적화 기법을 발췌하세요.",
    },
    {
        "assign_to": "chief-ops",
        "title": "장애 대응 런북 업데이트",
        "body": "과거 서버 재시작 실패 사례를 기반으로 장애 복구 소요 시간을 최소화하기 위한 DevOps 장애 대응 런북(Runbook) 초안을 작성하세요.",
    },
    {
        "assign_to": "chief-web-search",
        "title": "React/Vite 공식 문서 크롤링",
        "body": "React 19 버전의 최신 기능이나 Vite 플러그인 생태계의 주요 변경사항을 웹 서치로 검색하여 요약하고 Vector DB에 추가해 주세요.",
    },
    {
        "assign_to": "chief-web-search",
        "title": "GitHub Trending / Tech Radar 스크랩",
        "body": "최근 1주일간 GitHub Trending 상위권에 랭크된 프론트엔드 도구 및 아키텍처 라이브러리 목록을 스크랩하여 기술 부채 절감 방안을 도출하세요.",
    },
]

def _load_meta(data: dict) -> int:
    try:
        return int(data.get("chief_dev_reserved_rotation") or 0)
    except (TypeError, ValueError):
        return 0

def _save_meta(data: dict, rotation: int) -> None:
    data["chief_dev_reserved_rotation"] = rotation % max(len(CHIEF_DEV_RESERVED_TEMPLATES), 1)
    data["chief_dev_reserved_target"] = DEFAULT_TARGET

def _is_chief_dev_reserved(t: dict) -> bool:
    if not isinstance(t, dict):
        return False
    if t.get("source") == SOURCE_RESERVED_CHIEF_DEV:
        return True
    return (
        t.get("source") == "reserved"
        and (t.get("division") or "").strip() == DIVISION_CHIEF_DEV
    )

def count_reserved_queued() -> int:
    n = 0
    for t in agent_office_tasks.load_tasks().get("tasks") or []:
        if _is_chief_dev_reserved(t) and (t.get("status") or "queued") == "queued":
            n += 1
    return n

def count_reserved_in_progress() -> int:
    n = 0
    for t in agent_office_tasks.load_tasks().get("tasks") or []:
        if _is_chief_dev_reserved(t) and t.get("status") == "in_progress":
            n += 1
    return n

def count_reserved_active() -> int:
    return count_reserved_queued() + count_reserved_in_progress()

def _recent_reserved_bodies(limit: int = 12) -> set[str]:
    bodies: set[str] = set()
    for t in reversed(agent_office_tasks.load_tasks().get("tasks") or []):
        if not _is_chief_dev_reserved(t):
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

    for offset in range(len(CHIEF_DEV_RESERVED_TEMPLATES)):
        idx = (rotation + offset) % len(CHIEF_DEV_RESERVED_TEMPLATES)
        tpl = dict(CHIEF_DEV_RESERVED_TEMPLATES[idx])
        if tpl.get("body") not in recent:
            _save_meta(data, idx + 1)
            agent_office_tasks.save_tasks(data)
            return tpl

    tpl = dict(CHIEF_DEV_RESERVED_TEMPLATES[rotation % len(CHIEF_DEV_RESERVED_TEMPLATES)])
    _save_meta(data, rotation + 1)
    agent_office_tasks.save_tasks(data)
    return tpl

def add_reserved_task(*, quiet: bool = True) -> dict:
    tpl = pick_next_template()
    return agent_office_tasks.add_task(
        body=tpl["body"],
        assign_to=tpl.get("assign_to") or "all",
        title=tpl.get("title") or "수석 개발자실 자동 학습",
        priority="normal",
        created_by="자동 예약",
        source=SOURCE_RESERVED_CHIEF_DEV,
        division=DIVISION_CHIEF_DEV,
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
        f"chief_dev_reserved_queued={count_reserved_queued()} "
        f"active={count_reserved_active()} added={n}"
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
