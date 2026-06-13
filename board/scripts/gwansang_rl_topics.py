"""관상 학습 RL 확장 토픽 — 카탈로그 시드 소진 후 Gemini 제작 대상."""
from __future__ import annotations

EXPANSION_TOPICS: list[dict] = [
    {
        "title": "관상·눈썹·눈썹살 해석",
        "catalog_seed": "rl_gwansang_eyebrow",
        "category": "feature",
        "priority": 78,
        "hint": "눈썹 두께·아치·눈썹살 — 집중·감정 표현 참고. 단정 금지.",
    },
    {
        "title": "관상·광대·볼 윤곽",
        "catalog_seed": "rl_gwansang_cheek",
        "category": "feature",
        "priority": 77,
        "hint": "광대·볼 돌출·꺼짐 — 사교·에너지 이미지 참고. 골격 vs 지방 구분.",
    },
    {
        "title": "관상·관자놀이·측면 윤곽",
        "catalog_seed": "rl_gwansang_temple",
        "category": "feature",
        "priority": 76,
        "hint": "관자·측면 실루엣 — 계획·완충 이미지. 촬영 각도 왜곡 언급.",
    },
    {
        "title": "관상·점·모반 참고",
        "catalog_seed": "rl_gwansang_mole",
        "category": "feature",
        "priority": 75,
        "hint": "점 위치 전통 설명을 현대적으로 완화. 의학·암 단정 금지.",
    },
    {
        "title": "관상·수염·턱수염 이미지",
        "catalog_seed": "rl_gwansang_facial_hair",
        "category": "feature",
        "priority": 74,
        "hint": "수염 밀도·형태 — 성숙·신뢰 이미지 참고. 성별·문화 차이 명시.",
    },
    {
        "title": "관상·좌우 비대칭 읽기",
        "catalog_seed": "rl_gwansang_asymmetry",
        "category": "science",
        "priority": 73,
        "hint": "대칭·비대칭은 지각·습관 참고. 불길·궁합 단정 금지.",
    },
    {
        "title": "관상·미간·이마 주름 습관",
        "catalog_seed": "rl_gwansang_glabella",
        "category": "science",
        "priority": 72,
        "hint": "미간 주름 — 표정 습관·피로. 우울·질병 단정 금지.",
    },
    {
        "title": "관상·입꼬리·웃음 습관",
        "catalog_seed": "rl_gwansang_mouth_corner",
        "category": "feature",
        "priority": 71,
        "hint": "입꼬리 방향 — 표정·사교 에너지 참고.",
    },
    {
        "title": "관상·목선·하악 각도",
        "catalog_seed": "rl_gwansang_neck_jaw",
        "category": "feature",
        "priority": 70,
        "hint": "목·턱선 — 자세·체중·골격. 의지 단정 완화.",
    },
    {
        "title": "관상·다크서클·눈밑",
        "catalog_seed": "rl_gwansang_undereye",
        "category": "health",
        "priority": 69,
        "hint": "눈밑 그늘 — 수면·수분·알레르기. 대운·흉상 전환 금지.",
    },
    {
        "title": "관상·셀피·렌즈 왜곡 보정",
        "catalog_seed": "rl_gwansang_selfie",
        "category": "science",
        "priority": 68,
        "hint": "광각·거리·조명이 비율을 바꿈. 측정 전 보정 안내.",
    },
    {
        "title": "관상·피부톤·홍조 패턴",
        "catalog_seed": "rl_gwansang_complexion",
        "category": "health",
        "priority": 67,
        "hint": "혈색·홍조 — 생활·실내조명. 질병·운세 단정 금지.",
    },
]


def all_expansion_topics() -> list[dict]:
    return sorted(EXPANSION_TOPICS, key=lambda x: -(int(x.get("priority") or 0)))
