"""홈페이지 디자인 플레이북 — 재사용 가능한 학습 카드 단일 출처.

coupax.co.kr 및 이후 신규 사이트 제작 시 토큰·레이아웃·컴포넌트·핸드오프 기준.
"""
from __future__ import annotations

# 위원회 토론 주제 (catalog_seed → 제목)
DEBATE_TOPICS: list[dict] = [
    {
        "catalog_seed": "debate_hero_density",
        "title": "토론·히어로 밀도 vs 여백",
        "category": "debate",
        "priority": 90,
        "body": (
            "【주제】 첫 화면 히어로: 정보 밀도를 높일지, 여백·단일 메시지를 유지할지.\n"
            "【토큰】 Midnight #0A1931 배경 + Copper CTA는 브랜드 고정.\n"
            "【레이아웃】 데스크톱 2열(카피+비주얼), 모바일 1열·최소 24px 패딩.\n"
            "【결론 가이드】 B2C 랜딩은 여백 우선, 사무실·데이터 허브는 밀도 허용."
        ),
    },
    {
        "catalog_seed": "debate_nav_tabs_mobile",
        "title": "토론·모바일 탭 2열 vs 가로 스크롤",
        "category": "debate",
        "priority": 89,
        "body": (
            "【주제】 Agent Office·홈 다단 탭: 375px에서 2열 그리드 vs 스크롤 칩.\n"
            "【접근성】 터치 타깃 44px, focus 링 유지.\n"
            "【결론 가이드】 탭 5개 이상이면 스크롤+sticky, 4개 이하면 2열 그리드."
        ),
    },
    {
        "catalog_seed": "debate_cta_copper_vs_accent",
        "title": "토론·CTA Deep Copper vs UI Accent",
        "category": "debate",
        "priority": 88,
        "body": (
            "【주제】 주요 CTA 색: #B8860B(Deep Copper) vs #4f6ef7(Accent).\n"
            "【브랜드】 Copper=프리미엄·금융, Accent=기능·링크.\n"
            "【결론 가이드】 단일 Primary CTA는 Copper, 보조·인라인 링크는 Accent."
        ),
    },
    {
        "catalog_seed": "debate_card_border_vs_shadow",
        "title": "토론·카드 테두리 vs 그림자",
        "category": "debate",
        "priority": 87,
        "body": (
            "【주제】 블로그·지식 카드: 1px border vs soft shadow.\n"
            "【다크 배경】 Midnight 위에서는 border+낮은 shadow 혼용.\n"
            "【결론 가이드】 다크 테마는 border 1px rgba(255,255,255,.08), 라이트는 shadow md."
        ),
    },
    {
        "catalog_seed": "debate_typography_scale",
        "title": "토론·본문 15px vs 16px",
        "category": "debate",
        "priority": 86,
        "body": (
            "【주제】 모바일 본문 기준 크기와 line-height(1.55~1.65).\n"
            "【가독성】 16px는 WCAG 권장에 가깝, 15px는 밀도↑.\n"
            "【결론 가이드】 공개 블로그·장문은 16px, 대시보드 메타·캡션은 14–15px."
        ),
    },
    {
        "catalog_seed": "debate_dark_vs_light_sections",
        "title": "토론·섹션 다크 베이스 vs 라이트 혼합",
        "category": "debate",
        "priority": 85,
        "body": (
            "【주제】 전 페이지 다크 vs 히어로만 다크·본문 라이트.\n"
            "【일관성】 style.css 변수로 section 테마 스위치.\n"
            "【결론 가이드】 coupax 공개 홈은 히어로 다크+본문 라이트 혼합이 기본."
        ),
    },
]

PLAYBOOK_CARDS: list[dict] = [
    {
        "title": "coupax.co.kr 홈페이지 디자인 종합",
        "catalog_seed": "design_coupax_site_overview",
        "category": "playbook",
        "priority": 101,
        "body": (
            "【개요】 coupax.co.kr 공개 홈·블로그·지식 네트워크와 비공개 Agent Office를 하나의 디자인 시스템으로 운영한다. "
            "브랜드 토큰은 Midnight Blue #0A1931, Deep Copper #B8860B, Clear Sky Blue #ADD8E6, UI Accent #4f6ef7을 "
            ":root CSS 변수로 고정하고, 섹션마다 임의 hex를 쓰지 않는다.\n"
            "【작업 범위】 헤더·네비·푸터, 홈·블로그 카드 타일, 질문창·대화 UI, 모바일 375px~ 반응형, "
            "style.css 핸드오프, Agent Office 3열(roster|center|feed) 레이아웃, 원키스 US HTS UI 연동.\n"
            "【플레이북】 토큰 → 레이아웃 8px 그리드 → 컴포넌트(버튼·카드·폼) → 접근성(WCAG 대비·focus) → "
            "확정 카드는 homepage_design_knowledge_pack·Wiki(domain=homepage-design)에 동기화.\n"
            "【UX 톤】 신뢰·간결·과장 금지. Primary CTA는 Copper·페이지당 1개. "
            "디자인 위원회가 45분마다 토론 주제를 생성·합의해 재사용 플레이북을 확장한다."
        ),
    },
    {
        "title": "플레이북·홈페이지 제작 재사용 원칙",
        "catalog_seed": "design_playbook_intro",
        "category": "playbook",
        "priority": 100,
        "body": (
            "이 카드 묶음은 특정 도메인(coupax)뿐 아니라 **다음 홈페이지 제작**에 그대로 가져갈 수 있는 "
            "디자인·핸드오프 규칙이다. 토큰(JSON/CSS 변수) → 레이아웃 그리드 → 컴포넌트 → 접근성 → "
            "style.css 반영 순으로 적용한다. 브랜드 색만 바꾸고 구조·간격·CTA 계층은 유지한다."
        ),
    },
    {
        "title": "디자인 토큰·색상 팔레트",
        "catalog_seed": "design_tokens_palette",
        "category": "tokens",
        "priority": 99,
        "body": (
            "기준 팔레트: Midnight Blue #0A1931(배경·헤더), Deep Copper #B8860B(Primary CTA·강조), "
            "Clear Sky Blue #ADD8E6(보조·배지), UI Accent #4f6ef7(링크·포커스). "
            "CSS: --color-midnight, --color-copper, --color-sky, --color-accent. "
            "대비: 본문 on 다크는 #e8ecf4 이상, Copper 버튼 텍스트는 #0A1931 또는 #fff(대비 검증)."
        ),
    },
    {
        "title": "타이포그래피 스케일",
        "catalog_seed": "design_tokens_typography",
        "category": "tokens",
        "priority": 98,
        "body": (
            "제목: clamp(1.5rem, 4vw, 2.25rem) · 소제목 1.125–1.25rem · 본문 1rem(16px) · 캡션 .875rem. "
            "font-family: system-ui, 'Pretendard', 'Noto Sans KR', sans-serif. "
            "letter-spacing: 제목 -0.02em, 본문 normal. 장문 line-height 1.6, UI 라벨 1.4."
        ),
    },
    {
        "title": "레이아웃·그리드·간격",
        "catalog_seed": "design_layout_grid",
        "category": "layout",
        "priority": 97,
        "body": (
            "컨테이너 max-width 1120–1200px, 좌우 padding 16px(모바일)~32px(데스크톱). "
            "8px 베이스 스페이싱(8·16·24·32·48). 카드 그리드: repeat(auto-fill, minmax(280px, 1fr)). "
            "Agent Office: roster | center | feed 3열, <900px에서 feed 하단 스택."
        ),
    },
    {
        "title": "반응형·브레이크포인트",
        "catalog_seed": "design_layout_responsive",
        "category": "layout",
        "priority": 96,
        "body": (
            "최소 뷰포트 375px. 브레이크포인트: 480 / 768 / 900 / 1024. "
            "모바일: 탭·네비 줄바꿈, 표는 가로 스크롤 래퍼, 터치 44px. "
            "이미지 max-width 100%, hero 비율 16:9 또는 3:2 object-fit cover."
        ),
    },
    {
        "title": "컴포넌트·헤더·네비·푸터",
        "catalog_seed": "design_component_header_nav",
        "category": "component",
        "priority": 95,
        "body": (
            "헤더 sticky optional, 로고+주요 링크+사무실(비공개). 활성 탭 .is-active + 밑줄 Copper. "
            "푸터: 저작권·문의·개인정보. 공개 nav에 내부 전용(원히어로 등) 노출 금지 — 사무실 탭만."
        ),
    },
    {
        "title": "컴포넌트·카드·타일·블로그",
        "catalog_seed": "design_component_cards",
        "category": "component",
        "priority": 94,
        "body": (
            "카드: radius 12px, padding 16–20px, hover translateY(-2px) 또는 border 밝기↑. "
            "블로그 타일: 썸네일 16:9, 제목 2줄 clamp, 메타 날짜·태그. "
            "학습 카드 리스트: id·상태·summary·details 본문."
        ),
    },
    {
        "title": "컴포넌트·폼·질문창·대화 UI",
        "catalog_seed": "design_component_forms",
        "category": "component",
        "priority": 93,
        "body": (
            "textarea min-height 96px, focus ring accent. CSRF hidden 필드. "
            "홈 질문창·Agent feed: 메시지 카드 avatar+from→to+kind+time. "
            "에러는 .hint 빨강, 성공 초록 — 동일 패턴 재사용."
        ),
    },
    {
        "title": "CTA·버튼 계층",
        "catalog_seed": "design_component_cta",
        "category": "component",
        "priority": 92,
        "body": (
            "Primary: .btn-primary Copper 배경. Secondary: .btn-gray. "
            "페이지당 Primary 1개 원칙. 위험 작업은 별도 .btn-danger. "
            "disabled opacity .55, pointer-events none."
        ),
    },
    {
        "title": "Agent Office·비공개 레이아웃",
        "catalog_seed": "design_office_layout",
        "category": "office",
        "priority": 91,
        "body": (
            "division 탭: 금융·사주·차수·시황·홈페이지디자인. unit별 roster+instruct+feed. "
            "mode_on 스위치, 주기 표시. 지시 division hidden 필드 필수. "
            "디자인 unit: 토큰 스와치·체크리스트·학습 카드 패널."
        ),
    },
    {
        "title": "핸드오프·style.css·변수",
        "catalog_seed": "design_handoff_css",
        "category": "handoff",
        "priority": 90,
        "body": (
            "디자인 결정은 Design_System_Spec / style.css에 반영. "
            "새 색은 :root 변수 추가 후 컴포넌트에서 var() 참조. "
            "인라인 style 최소화. agent_office.css·knowledge_network.css는 도메인별 분리 유지."
        ),
    },
    {
        "title": "접근성·WCAG 기본",
        "catalog_seed": "design_a11y_basics",
        "category": "a11y",
        "priority": 89,
        "body": (
            "시맨틱 header/nav/main, aria-label on icon-only 버튼. "
            "색 대비 4.5:1(본문), 3:1(대형 텍스트). keyboard focus visible. "
            "이미지 alt, 폼 label 연결. motion reduce 미디어쿼리 고려."
        ),
    },
    {
        "title": "성능·에셋·폰트",
        "catalog_seed": "design_perf_assets",
        "category": "perf",
        "priority": 88,
        "body": (
            "favicon.svg, logo.png web 최적화. defer script. "
            "썸네일 lazy loading. CSS 버전 쿼리 ?v= 배포 캐시 무효화. "
            "불필요한 대형 PNG 지양 — SVG 아이콘 우선."
        ),
    },
    {
        "title": "UX 카피·톤·마이크로카피",
        "catalog_seed": "design_content_voice",
        "category": "content",
        "priority": 87,
        "body": (
            "톤: 신뢰·간결·과장 금지(금융·사주 동일). CTA 동사형: '지시 전달', '확정', '미리보기'. "
            "placeholder는 예시 한 줄. 에러 메시지는 원인+다음 행동."
        ),
    },
]

# stock.coupax.co.kr/workisus — 원키스 US 해외 HTS형 UI (스크린 기준)
WORKISUS_CARDS: list[dict] = [
    {
        "title": "원키스 US·제품 정의",
        "catalog_seed": "workisus_def",
        "category": "workisus",
        "priority": 84,
        "body": (
            "원키스 US(OneKiss US)는 stock.coupax.co.kr/workisus 해외(미국) 주식용 "
            "웹 HTS형 대시보드이다. 상단 us·원키스 us·해외 브랜딩, 계좌번호(단일 해외 계좌)·"
            "국내주식 바로가기·화면잠금·로그아웃이 있다. "
            "차수매매는 한 계좌·슬롯 메모·수동 주문(매매 방법은 원히어로 자동봇과 다름). "
            "원히어로 multi·cascade_accounts 다계좌 체인·ATR 자동 gap과 무관. "
            "본 화면은 수동 HTS·잔고·주문·미체결·차트 다창 조작이 중심이다. "
            "학습 카드·디자인 플레이북은 UI·운용 분리를 유지한다."
        ),
    },
    {
        "title": "원키스 US·다창 레이아웃 3001~3005",
        "catalog_seed": "workisus_panel_layout",
        "category": "workisus",
        "priority": 83,
        "body": (
            "기본 2×2 다창: [3001] 실시간 잔고(탭: 잔고·차수매매·체결·미체결·과거거래), "
            "[3003] 매매내역 산정(기간·CSV), [3005] 미체결 목록, [3002] 일반주문(매수/매도/정정취소), "
            "[3004] 종합차트(일·주·월·분·매수라인·이평). 다크 테마·고정 헤더 메뉴 "
            "(대시보드·잔고평가·주문미체결·매매설정·통계·로그차트·보기·고객지원). "
            "리사이즈·창 배치는 HTS 습관 사용자를 전제한다."
        ),
    },
    {
        "title": "원키스 US·일반주문 3002",
        "catalog_seed": "workisus_order_form",
        "category": "workisus",
        "priority": 82,
        "body": (
            "종목 선택(JOBY 등)·매수(빨강)·매도(파랑)·정정/취소 탭. 차수(자동)·구분(시장가)·"
            "가격·수량·25/50/전액·현금·실시간결제 체크. 매수주문·초기화 CTA는 크고 색으로 구분. "
            "미체결 3005와 연동해 취소 버튼 제공. 계좌·API키·비밀번호는 카드·로그에 넣지 않는다."
        ),
    },
    {
        "title": "원키스 US·잔고·매매내역 3001·3003",
        "catalog_seed": "workisus_balance_history",
        "category": "workisus",
        "priority": 81,
        "body": (
            "3001 상단 요약: 예수금·미수금 D+2·총매입·총평가·평가손익·수익률·추정자산. "
            "그리드: 종목명·등락·수량·매입가·현재가·평가손익·수익률·매입/평가금액·목표비·현재비·차이. "
            "잔고 탭 우측 차수 칸(차수·날짜·수량·수익률 뷰)은 동일 계좌 슬롯 메타를 표시한다. "
            "차수매매 서브탭: 종목별 1·2·3차 매수가·수량·일자·현재가·손익 — 한 계좌 기준. "
            "3003: 날짜 범위·오늘/이번주/이번달/3개월·설정 저장·불러오기·CSV. "
            "갱신 시 표 레이아웃은 유지하고 숫자만 in-place 패치(깜빡임 방지)."
        ),
    },
    {
        "title": "원키스 US·한 계좌 차수매매",
        "catalog_seed": "workisus_single_account_cascade",
        "category": "workisus",
        "priority": 84,
        "body": (
            "원키스 US 세븐 스플릿: 해외 증권 계좌 1개·종목별 슬롯 1(앵커 999%)·2(15초)·3~N(buy_gaps). "
            "슬롯 DB(/api/slots?market=US)·3001 차수 칸·3002 슬롯 번호로 추적. "
            "합산 평단≤0%면 개별 익절 보류. 원히어로 멀티 cascade·다계좌 이체와 무관. "
            "no_slot_trading=false일 때 auto_bot US 격자 자동이 정본."
        ),
    },
    {
        "title": "토론·원키스 US 다창 vs 단일 페이지",
        "catalog_seed": "debate_workisus_multi_window",
        "category": "debate",
        "priority": 80,
        "body": (
            "【주제】 해외 HTS: Kiwoom식 다창(3001~3005) vs 모바일 단일 스크롤 페이지.\n"
            "【사용자】 데스크톱·듀얼모니터 트레이더는 다창, 375px 모바일은 탭·스택.\n"
            "【결론 가이드】 workisus 데스크톱은 다창 유지, 좁은 뷰포트만 반응형 단일 플로우 제공."
        ),
    },
]


def all_design_specs() -> list[dict]:
    """카탈로그 전체(플레이북 + 원키스 US + 토론), priority 내림차순."""
    merged = PLAYBOOK_CARDS + WORKISUS_CARDS + DEBATE_TOPICS
    return sorted(merged, key=lambda s: -(s.get("priority") or 0))


def debate_specs() -> list[dict]:
    return list(DEBATE_TOPICS)
