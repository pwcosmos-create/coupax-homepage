"""agent_registry.json — 관상 학습부 젬마 (전원 ON)."""
from __future__ import annotations

import json
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
REGISTRY_PATH = BOARD / "data" / "agent_registry.json"

GWANSANG_AGENTS: list[dict] = [
    {
        "id": "gwansang_watch",
        "name": "워치젬마",
        "emoji": "👁️",
        "role": "전체·SEO·갭",
        "division": "gwansang-learn",
        "mode_on": True,
        "interval_minutes": 30,
        "interval_label": "30분",
        "job": "gwansang_watch_pulse",
        "skills": [{"id": "watch", "title": "점검", "summary": "카드·갭·확정 현황."}],
    },
    {
        "id": "gwansang_curator",
        "name": "큐레이터",
        "emoji": "✦",
        "role": "확정·pack·Wiki",
        "division": "gwansang-learn",
        "mode_on": True,
        "interval_minutes": 45,
        "interval_label": "45분",
        "job": "gwansang_pack_sync",
        "skills": [{"id": "pack", "title": "pack", "summary": "gwansang_knowledge_pack.json."}],
    },
    {
        "id": "gwansang_compose",
        "name": "제작젬마",
        "emoji": "✍️",
        "role": "갭 카드 제작",
        "division": "gwansang-learn",
        "mode_on": True,
        "interval_minutes": 40,
        "interval_label": "40분",
        "job": "gwansang_card_compose",
        "skills": [{"id": "compose", "title": "갭 1장", "summary": "SEO 200자+ 확정."}],
    },
    {
        "id": "gwansang_catalog",
        "name": "카탈로그젬마",
        "emoji": "📚",
        "role": "시드·동기화",
        "division": "gwansang-learn",
        "mode_on": True,
        "interval_minutes": 90,
        "interval_label": "90분",
        "job": "gwansang_catalog_maintain",
        "skills": [{"id": "seed", "title": "카탈로그", "summary": "12종 관상 시드."}],
    },
    {
        "id": "gwansang_seo",
        "name": "SEO젬마",
        "emoji": "🔍",
        "role": "200자+·키워드",
        "division": "gwansang-learn",
        "mode_on": True,
        "interval_minutes": 50,
        "interval_label": "50분",
        "job": "gwansang_seo_pulse",
        "skills": [{"id": "seo", "title": "SEO", "summary": "관상·얼굴 키워드 보강."}],
    },
    {
        "id": "gwansang_scholar",
        "name": "학자젬마",
        "emoji": "📜",
        "role": "전통 관상 이론",
        "division": "gwansang-learn",
        "mode_on": True,
        "interval_minutes": 70,
        "interval_label": "70분",
        "job": "gwansang_scholar_pulse",
        "skills": [{"id": "theory", "title": "오관·삼정", "summary": "이론 카드 담당."}],
    },
    {
        "id": "gwansang_features",
        "name": "오관젬마",
        "emoji": "👤",
        "role": "이마·눈·코·입",
        "division": "gwansang-learn",
        "mode_on": True,
        "interval_minutes": 65,
        "interval_label": "65분",
        "job": "gwansang_features_pulse",
        "skills": [{"id": "features", "title": "오관", "summary": "부위별 해석 카드."}],
    },
    {
        "id": "gwansang_fortune",
        "name": "운세젬마",
        "emoji": "🌟",
        "role": "길상·재물·연애",
        "division": "gwansang-learn",
        "mode_on": True,
        "interval_minutes": 75,
        "interval_label": "75분",
        "job": "gwansang_fortune_pulse",
        "skills": [{"id": "fortune", "title": "경향", "summary": "단정 예언 없음."}],
    },
    {
        "id": "gwansang_reader",
        "name": "리더젬마",
        "emoji": "📖",
        "role": "수집·요약",
        "division": "gwansang-learn",
        "mode_on": True,
        "interval_minutes": 80,
        "interval_label": "80분",
        "job": "gwansang_reader_pulse",
        "skills": [{"id": "read", "title": "수집", "summary": "본문·요약 초안."}],
    },
    {
        "id": "gwansang_structurer",
        "name": "구조젬마",
        "emoji": "🗂️",
        "role": "분류·태그",
        "division": "gwansang-learn",
        "mode_on": True,
        "interval_minutes": 85,
        "interval_label": "85분",
        "job": "gwansang_structurer_pulse",
        "skills": [{"id": "struct", "title": "구조", "summary": "【】블록·카테고리."}],
    },
    {
        "id": "gwansang_privacy",
        "name": "프라이버시젬마",
        "emoji": "🔒",
        "role": "PII 차단",
        "division": "gwansang-learn",
        "mode_on": True,
        "interval_minutes": 120,
        "interval_label": "2시간",
        "job": "gwansang_pii_scan",
        "skills": [{"id": "pii", "title": "PII", "summary": "연락처·실명 금지."}],
    },
    {
        "id": "gwansang_gap_autofill",
        "name": "갭젬마",
        "emoji": "🧩",
        "role": "갭 자동 제작",
        "division": "gwansang-learn",
        "mode_on": True,
        "interval_minutes": 55,
        "interval_label": "55분",
        "job": "gwansang_gap_autofill",
        "skills": [{"id": "gap", "title": "갭 RL", "summary": "카탈로그 누락 자동 확정."}],
    },
    {
        "id": "gwansang_wiki_sync",
        "name": "Wiki젬마",
        "emoji": "📡",
        "role": "Wiki 동기화",
        "division": "gwansang-learn",
        "mode_on": True,
        "interval_minutes": 60,
        "interval_label": "1시간",
        "job": "gwansang_wiki_sync",
        "skills": [{"id": "wiki", "title": "10_Wiki", "summary": "확정 카드 Wiki 반영."}],
    },
    {
        "id": "gwansang_error_fix",
        "name": "오류점검젬마",
        "emoji": "🛠️",
        "role": "품질·200자",
        "division": "gwansang-learn",
        "mode_on": True,
        "interval_minutes": 100,
        "interval_label": "100분",
        "job": "gwansang_error_fix",
        "skills": [{"id": "qa", "title": "품질", "summary": "본문·태그·PII 점검."}],
    },
    {
        "id": "gwansang_daily_conclusion",
        "name": "일일결론젬마",
        "emoji": "📋",
        "role": "일일 요약",
        "division": "gwansang-learn",
        "mode_on": True,
        "interval_minutes": 1440,
        "interval_label": "1일",
        "job": "gwansang_daily_conclusion",
        "skills": [{"id": "daily", "title": "결론", "summary": "확정·대기·다음 작업."}],
    },
    {
        "id": "gwansang_review",
        "name": "검수젬마",
        "emoji": "✅",
        "role": "대기 카드 검수",
        "division": "gwansang-learn",
        "mode_on": True,
        "interval_minutes": 95,
        "interval_label": "95분",
        "job": "gwansang_review_hint",
        "skills": [{"id": "review", "title": "검수", "summary": "pending 카드 안내."}],
    },
    {
        "id": "gwansang_tag_digest",
        "name": "태그젬마",
        "emoji": "🏷️",
        "role": "키워드·태그",
        "division": "gwansang-learn",
        "mode_on": True,
        "interval_minutes": 110,
        "interval_label": "110분",
        "job": "gwansang_tag_digest",
        "skills": [{"id": "tags", "title": "태그", "summary": "SEO 키워드 빈도."}],
    },
]


def _upsert_agent(agents: list, row: dict) -> str:
    aid = row.get("id")
    mode_on = bool(row.get("mode_on", True))
    for i, a in enumerate(agents):
        if isinstance(a, dict) and a.get("id") == aid:
            agents[i] = {**a, **row, "mode_on": mode_on, "division": "gwansang-learn"}
            return "updated"
    agents.append({**row, "mode_on": mode_on, "division": "gwansang-learn"})
    return "added"


def main() -> int:
    if not REGISTRY_PATH.is_file():
        print("registry missing:", REGISTRY_PATH)
        return 1
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    agents = data.get("agents") or []
    counts = {"added": 0, "updated": 0}
    for row in GWANSANG_AGENTS:
        action = _upsert_agent(agents, row)
        counts[action] = counts.get(action, 0) + 1
    data["agents"] = agents
    REGISTRY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"gwansang-learn agents: {counts} · active={len(GWANSANG_AGENTS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
