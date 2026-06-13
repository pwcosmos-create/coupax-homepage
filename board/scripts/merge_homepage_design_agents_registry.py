"""agent_registry.json — 홈페이지 디자인부 젬마 전원 추가·활성화."""
from __future__ import annotations

import json
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
REGISTRY_PATH = BOARD / "data" / "agent_registry.json"

DESIGN_AGENTS: list[dict] = [
    {
        "id": "design_curator",
        "name": "디자인 큐레이터",
        "emoji": "🎨",
        "role": "플레이북·pack·확정",
        "division": "homepage-design",
        "mode_on": True,
        "interval_minutes": 60,
        "interval_label": "1시간",
        "job": "homepage_design_pack_sync",
        "skills": [
            {
                "id": "design-pack-sync",
                "title": "재사용 플레이북 pack",
                "summary": "확정 카드→pack·CURSOR_HOMEPAGE_DESIGN_LEARN.md·Wiki.",
            }
        ],
    },
    {
        "id": "design_token",
        "name": "토큰젬마",
        "emoji": "🎯",
        "role": "색·CSS 변수",
        "division": "homepage-design",
        "mode_on": True,
        "interval_minutes": 90,
        "interval_label": "90분",
        "job": "homepage_design_token_pulse",
        "skills": [{"id": "palette", "title": "Midnight·Copper·Accent", "summary": "브랜드 팔레트 :root 고정."}],
    },
    {
        "id": "design_typography",
        "name": "타이포젬마",
        "emoji": "🔤",
        "role": "글꼴·스케일",
        "division": "homepage-design",
        "mode_on": True,
        "interval_minutes": 120,
        "interval_label": "2시간",
        "job": "homepage_design_typography_pulse",
        "skills": [{"id": "type-scale", "title": "타이포 스케일", "summary": "clamp·16px 본문·캡션."}],
    },
    {
        "id": "design_layout",
        "name": "레이아웃젬마",
        "emoji": "📐",
        "role": "그리드·반응형",
        "division": "homepage-design",
        "mode_on": True,
        "interval_minutes": 75,
        "interval_label": "75분",
        "job": "homepage_design_layout_pulse",
        "skills": [{"id": "responsive", "title": "375px+", "summary": "브레이크포인트·Office 3열."}],
    },
    {
        "id": "design_component",
        "name": "컴포넌트젬마",
        "emoji": "🧩",
        "role": "버튼·카드·폼",
        "division": "homepage-design",
        "mode_on": True,
        "interval_minutes": 80,
        "interval_label": "80분",
        "job": "homepage_design_component_pulse",
        "skills": [{"id": "ui-patterns", "title": "UI 패턴", "summary": "헤더·블로그 타일·질문창."}],
    },
    {
        "id": "design_a11y",
        "name": "접근성젬마",
        "emoji": "♿",
        "role": "WCAG·대비",
        "division": "homepage-design",
        "mode_on": True,
        "interval_minutes": 180,
        "interval_label": "3시간",
        "job": "homepage_design_a11y_pulse",
        "skills": [{"id": "a11y", "title": "접근성", "summary": "대비·키보드·aria."}],
    },
    {
        "id": "design_handoff",
        "name": "핸드오프젬마",
        "emoji": "📦",
        "role": "style.css 반영",
        "division": "homepage-design",
        "mode_on": True,
        "interval_minutes": 100,
        "interval_label": "100분",
        "job": "homepage_design_handoff_pulse",
        "skills": [{"id": "css-handoff", "title": "CSS 핸드오프", "summary": "변수·컴포넌트 클래스 동기."}],
    },
    {
        "id": "design_ux_writer",
        "name": "UX카피젬마",
        "emoji": "✍️",
        "role": "CTA·마이크로카피",
        "division": "homepage-design",
        "mode_on": True,
        "interval_minutes": 150,
        "interval_label": "2.5시간",
        "job": "homepage_design_ux_pulse",
        "skills": [{"id": "microcopy", "title": "카피 톤", "summary": "신뢰·간결·동사 CTA."}],
    },
    {
        "id": "design_council",
        "name": "디자인 위원회",
        "emoji": "⚖️",
        "role": "토론·합의 카드",
        "division": "homepage-design",
        "mode_on": True,
        "interval_minutes": 45,
        "interval_label": "45분",
        "job": "homepage_design_council_debate",
        "skills": [{"id": "design-debate", "title": "8인 토론", "summary": "토큰·레이아웃·CTA 등 주제별 합의 카드."}],
    },
    {
        "id": "design_researcher",
        "name": "리서치젬마",
        "emoji": "🔍",
        "role": "레퍼런스·벤치마크",
        "division": "homepage-design",
        "mode_on": True,
        "interval_minutes": 200,
        "interval_label": "3.3시간",
        "job": "homepage_design_research_pulse",
        "skills": [{"id": "bench", "title": "벤치마크", "summary": "동종 UI→coupax 토큰 축소."}],
    },
    {
        "id": "design_catalog",
        "name": "카탈로그젬마",
        "emoji": "📚",
        "role": "플레이북 카드 sync",
        "division": "homepage-design",
        "mode_on": True,
        "interval_minutes": 120,
        "interval_label": "2시간",
        "job": "homepage_design_catalog_maintain",
        "skills": [{"id": "catalog-sync", "title": "카탈로그 유지", "summary": "시드·갱신·누락 보완."}],
    },
    {
        "id": "design_privacy",
        "name": "프라이버시젬마",
        "emoji": "🔒",
        "role": "목업 PII 차단",
        "division": "homepage-design",
        "mode_on": True,
        "interval_minutes": 240,
        "interval_label": "4시간",
        "job": "homepage_design_pii_scan",
        "skills": [{"id": "pii", "title": "PII 검사", "summary": "학습 카드·지시에 연락처 금지."}],
    },
]


def _upsert_agent(agents: list, row: dict) -> str:
    aid = row["id"]
    for i, a in enumerate(agents):
        if isinstance(a, dict) and (a.get("id") or "").strip() == aid:
            merged = dict(a)
            merged.update(row)
            agents[i] = merged
            return "updated"
    agents.append(row)
    return "added"


def main() -> int:
    if not REGISTRY_PATH.is_file():
        print("registry missing:", REGISTRY_PATH)
        return 1
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    agents = data.get("agents") or []
    counts = {"added": 0, "updated": 0}
    for row in DESIGN_AGENTS:
        action = _upsert_agent(agents, row)
        counts[action] = counts.get(action, 0) + 1
    data["agents"] = agents
    REGISTRY_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"homepage-design agents: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
