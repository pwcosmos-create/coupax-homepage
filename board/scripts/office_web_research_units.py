"""사업부별 웹 검색 토론 축·위원회 패널 설정."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class UnitWebResearchConfig:
    unit_id: str
    division: str
    learn_module: str
    env_prefix: str
    apply_note: str
    log_from_id: str
    debate_panel: list[tuple[str, str]]
    role_stances: dict[str, str] = field(default_factory=dict)
    query_axes: list[tuple[str, str, str, str, str]] = field(default_factory=list)


def _axes(*rows: tuple[str, str, str, str, str]) -> list[tuple[str, str, str, str, str]]:
    return list(rows)


UNIT_CONFIGS: dict[str, UnitWebResearchConfig] = {
    "finance": UnitWebResearchConfig(
        unit_id="finance",
        division="finance",
        learn_module="agent_office_finance_learn",
        env_prefix="FINANCE",
        apply_note="금융 블로그 E-E-A-T·출처 표기·과장 표현 금지.",
        log_from_id="finance_council",
        debate_panel=[
            ("finance_editor", "편집"),
            ("finance_fact", "팩트체크"),
            ("finance_seo", "SEO"),
            ("finance_eeat", "E-E-A-T"),
            ("finance_macro", "매크로"),
        ],
        role_stances={
            "finance_editor": "독자 가독성·짧은 문단·소제목 계층 우선.",
            "finance_fact": "수치·날짜·기관명은 출처 2곳 이상 교차.",
            "finance_seo": "제목 60자·메타 200자·키워드 자연 배치.",
            "finance_eeat": "저자·경험·전문성 문구, 투자 권유 문구 금지.",
            "finance_macro": "금리·환율·지수 맥락을 먼저, 종목 추천은 배제.",
        },
        query_axes=_axes(
            (
                "personal finance blog E-E-A-T trust design 2025",
                "블로그 신뢰",
                "출처·각주 강조",
                "스토리·경험 중심",
                "수치·기관명 각주 필수, 체험담은 사실과 분리.",
            ),
            (
                "ETF dividend blog article structure readability",
                "ETF 글 구조",
                "표·수치 상단",
                "서술형 도입",
                "국내 ETF는 표+배당일, 서두 200자 요약.",
            ),
            (
                "financial content disclaimer investment advice Korea",
                "면책 문구",
                "상단 고정 배너",
                "하단 짧은 문구",
                "투자 권유 아님 문구 상단+하단 병행.",
            ),
            (
                "blog table of contents sticky sidebar long form",
                "장문 목차",
                "우측 sticky TOC",
                "인라인 앵커만",
                "3000자 이상 장문만 sticky TOC.",
            ),
        ),
    ),
    "saju-learn": UnitWebResearchConfig(
        unit_id="saju-learn",
        division="saju-learn",
        learn_module="agent_office_saju_learn",
        env_prefix="SAJU",
        apply_note="사주 앱 변수명·격국·용신 규칙과 충돌 시 앱 정본 우선.",
        log_from_id="saju_council",
        debate_panel=[
            ("saju_scholar", "학자"),
            ("saju_reader", "해석"),
            ("saju_structure", "구조"),
            ("saju_fortune", "운세"),
            ("saju_seo", "SEO"),
        ],
        role_stances={
            "saju_scholar": "명리 전통 용어·격국 정의를 앱 카탈로그와 일치.",
            "saju_reader": "일주·십성 해석은 비유 과다 금지, 조건부 서술.",
            "saju_structure": "변수·격·운·심층 제목 규칙 준수.",
            "saju_fortune": "대운·세운은 시점·한계 명시.",
            "saju_seo": "200자 요약·질문형 제목, PII·실명 금지.",
        },
        query_axes=_axes(
            (
                "four pillars of destiny day master interpretation guide",
                "일주 해석",
                "전통 명리 강조",
                "현대 심리 비유",
                "앱 일주 카드는 전통+현대 균형, 단정 금지.",
            ),
            (
                "yongsin useful god bazi selection methods",
                "용신",
                "강약·조후 중심",
                "통변·격국 중심",
                "변수·운 용신 목 형식, 구형 희신 단독 제목 금지.",
            ),
            (
                "saju palja ten gods personality meaning",
                "십성",
                "표·관계도",
                "서술형 사례",
                "십성은 표+한 줄 정의 후 사례.",
            ),
            (
                "korean fortune telling app UX reading card design",
                "앱 카드 UX",
                "짧은 카드 슬라이드",
                "장문 스크롤",
                "무료 풀이는 카드형, 심층은 장문.",
            ),
        ),
    ),
    "gwansang-learn": UnitWebResearchConfig(
        unit_id="gwansang-learn",
        division="gwansang-learn",
        learn_module="agent_office_gwansang_learn",
        env_prefix="GWANSANG",
        apply_note="전통 관상·과학 관찰 층 분리. SEO 200자+, 의학·물리 단정·진단 금지.",
        log_from_id="gwansang_council",
        debate_panel=[
            ("gwansang_scholar", "학자"),
            ("gwansang_science", "과학·관찰"),
            ("gwansang_feature", "오관"),
            ("gwansang_fortune", "운세"),
            ("gwansang_health", "건강"),
            ("gwansang_seo", "SEO"),
        ],
        role_stances={
            "gwansang_scholar": "전통 관상 용어·삼정·오관 정의 일관.",
            "gwansang_science": "해부·생리·지각은 「왜 그렇게 보이는지」만. 운명·질병 단정 금지.",
            "gwansang_feature": "눈·코·입·귀·이마는 관찰 포인트 중심.",
            "gwansang_fortune": "재물·연애·직업은 경향만, 단정 금지.",
            "gwansang_health": "건강은 생활 습관 권고만, 질병 진단 금지.",
            "gwansang_seo": "본문 200자+, 제목에 관상·부위 키워드.",
        },
        query_axes=_axes(
            (
                "physiognomy face reading eye shape meaning",
                "눈 관상",
                "전통 형태 분류",
                "인상·인성 비유",
                "눈꼬리·눈매 관찰 후 성향 경향 서술.",
            ),
            (
                "nose shape face reading wealth career",
                "코 관상",
                "재물·직업 강조",
                "건강·균형 강조",
                "코는 재물 경향+균형 인상 병기.",
            ),
            (
                "face reading forehead three zones sanqing",
                "삼정",
                "상·중·하정 구분",
                "통합 인상만",
                "삼정은 구역별 연령·주제 매핑 표.",
            ),
            (
                "physiognomy content SEO long form article",
                "관상 SEO",
                "질문형 H2",
                "키워드 리스트",
                "H2 질문형+200자 요약 필수.",
            ),
            (
                "facial anatomy bone soft tissue forehead jaw morphology",
                "얼굴 해부",
                "골격·연부조직 설명",
                "전통 오관 상징만",
                "이마·광대·턱은 골격+지방+근육 층을 분리 서술.",
            ),
            (
                "facial expression psychology first impression trust",
                "표정·지각",
                "심리·첫인상 연구",
                "오관 길흉 해석",
                "인상 형성 메커니즘만, 성격 단정 금지.",
            ),
            (
                "facial symmetry perception attractiveness psychology",
                "대칭·인상",
                "지각 심리·평균성",
                "전통 길상 대칭",
                "대칭은 인상 참고만, 운명·궁합 단정 금지.",
            ),
            (
                "skin physiology complexion dark circles fatigue",
                "피부 생리",
                "생리·생활 습관",
                "색·윤택 길흉",
                "혈색·다크서클은 습관 신호, 진단 대체 금지.",
            ),
            (
                "portrait photography lighting angle facial distortion optics",
                "촬영·광학",
                "조명·각도 보정",
                "사진 그대로 관상",
                "셀카·측면·광원 왜곡을 먼저 안내.",
            ),
            (
                "facial aging muscle skin wrinkles expression habits",
                "노화·주름",
                "근육·표정 습관",
                "주름 길흉만",
                "주름은 표정·자외선·수면, 불길 단정 금지.",
            ),
        ),
    ),
    "kiwoom-chasu": UnitWebResearchConfig(
        unit_id="kiwoom-chasu",
        division="kiwoom-chasu",
        learn_module="agent_office_kiwoom_learn",
        env_prefix="KIWOM",
        apply_note="원히어로 차수·슬롯·ATR 규칙 정본 우선, API 키·계좌번호 금지.",
        log_from_id="kiwoom_council",
        debate_panel=[
            ("kiwoom_slot", "슬롯"),
            ("kiwoom_risk", "리스크"),
            ("kiwoom_atr", "ATR"),
            ("kiwoom_chasu", "차수"),
            ("kiwoom_ui", "UI"),
        ],
        role_stances={
            "kiwoom_slot": "분할·슬롯 수·간격은 위키 정본과 동일.",
            "kiwoom_risk": "손절·익절·무손실 리밸런싱 우선.",
            "kiwoom_atr": "ATR 배수·변동성 구간 명시.",
            "kiwoom_chasu": "차수 증가 조건·최대 차수 한도.",
            "kiwoom_ui": "HTS 탭·손익 표시·알림 UX.",
        },
        query_axes=_axes(
            (
                "grid trading strategy slot sizing risk management",
                "그리드 슬롯",
                "고정 간격",
                "ATR 가변 간격",
                "ATR 가변+최대 슬롯 상한 병기.",
            ),
            (
                "averaging down vs scaling in trading rules",
                "물타기",
                "차수 제한 물타기",
                "무손실 리밸런싱",
                "원히어로는 무손실 리밸런싱 우선.",
            ),
            (
                "trading dashboard UI order panel design",
                "매매 UI",
                "밀집 주문 패널",
                "여백·단계 강조",
                "차수·슬롯 상태는 한 눈에, 주문은 보조.",
            ),
            (
                "ATR volatility position sizing retail trading",
                "ATR 사이징",
                "고정 수량",
                "ATR 비례",
                "변동성 큰 종목은 ATR 비례 축소.",
            ),
        ),
    ),
    "stock-watch": UnitWebResearchConfig(
        unit_id="stock-watch",
        division="stock-watch",
        learn_module="agent_office_stock_learn",
        env_prefix="STOCK",
        apply_note="투자 권유·매수매도 신호 금지. 공시·시세·출처 교차.",
        log_from_id="stock_council",
        debate_panel=[
            ("stock_macro", "매크로"),
            ("stock_listener", "여론"),
            ("stock_fact", "팩트"),
            ("stock_risk", "리스크"),
            ("stock_youtube", "영상"),
        ],
        role_stances={
            "stock_macro": "금리·환율·지수 맥락, 인과 단정 금지.",
            "stock_listener": "댓글·커뮤니티는 참고만, 사실 검증 필요.",
            "stock_fact": "공시·언론 2곳 이상, 날짜·수치 명시.",
            "stock_risk": "변동성·유동성·지정학 리스크 병기.",
            "stock_youtube": "크리에이터 의견≠사실, 제목 자극 주의.",
        },
        query_axes=_axes(
            (
                "stock market macro interest rate impact analysis",
                "금리 영향",
                "채권·금리 먼저",
                "종목 픽 먼저",
                "매크로→섹터→종목 순, 종목 추천 금지.",
            ),
            (
                "KOSPI market sentiment retail investor behavior",
                "국내 심리",
                "수급·외국인",
                "뉴스 헤드라인",
                "수급 데이터+헤드라인 교차.",
            ),
            (
                "earnings season CEO remarks stock interpretation caution",
                "CEO 발언",
                "실적 가이던스 중심",
                "인터뷰 인상 중심",
                "가이던스·공시 수치 우선.",
            ),
            (
                "oil price geopolitical risk equity market",
                "유가·지정학",
                "에너지 섹터",
                "전체 시장",
                "유가 쇼크는 섹터→지수 순서.",
            ),
        ),
    ),
    "homepage-design": UnitWebResearchConfig(
        unit_id="homepage-design",
        division="homepage-design",
        learn_module="agent_office_homepage_design_learn",
        env_prefix="HOMEPAGE_DESIGN",
        apply_note="Midnight/Copper/Accent 토큰·8px 그리드·WCAG 유지.",
        log_from_id="design_council",
        debate_panel=[
            ("design_token", "토큰·색"),
            ("design_typography", "타이포"),
            ("design_layout", "레이아웃"),
            ("design_component", "컴포넌트"),
            ("design_a11y", "접근성"),
            ("design_researcher", "레퍼런스"),
        ],
        role_stances={
            "design_token": "브랜드 토큰 일관, 임의 hex 금지.",
            "design_typography": "제목 clamp, 본문 16px.",
            "design_layout": "8px 그리드, 모바일 375px.",
            "design_component": "Primary CTA 페이지당 1개.",
            "design_a11y": "대비 4.5:1, focus ring.",
            "design_researcher": "외부 레퍼런스는 토큰에 맞게 축소.",
        },
        query_axes=_axes(
            (
                "AI agent dashboard office UI design multi panel",
                "에이전트 사무실",
                "3열 패널 고정",
                "단일 피드 집중",
                "Agent Office 3열 유지.",
            ),
            (
                "design system CSS variables tokens documentation",
                "디자인 토큰",
                "JSON 토큰",
                ":root CSS",
                ":root+스펙 문서 병행.",
            ),
            (
                "web design color contrast WCAG accessibility CTA",
                "접근성 CTA",
                "고대비 버튼",
                "아웃라인 CTA",
                "Primary Copper, 대비 검증.",
            ),
        ),
    ),
    "workisus-chasu": UnitWebResearchConfig(
        unit_id="workisus-chasu",
        division="workisus-chasu",
        learn_module="agent_office_workisus_learn",
        env_prefix="WORKISUS",
        apply_note="wonkisus 10분할·무손실 Wiki 정본 우선.",
        log_from_id="workisus_council",
        debate_panel=[
            ("workisus_grid", "그리드"),
            ("workisus_us", "US시장"),
            ("workisus_risk", "리스크"),
            ("workisus_ui", "UI"),
            ("workisus_slot", "슬롯"),
        ],
        role_stances={
            "workisus_grid": "10분할·간격·재진입 Wiki와 일치.",
            "workisus_us": "미국 장 시간·환율·종목 유동성.",
            "workisus_risk": "무손실 리밸런싱·최대 차수.",
            "workisus_ui": "workisus HTS 탭·손익 갱신.",
            "workisus_slot": "슬롯별 수량·ATR 연동.",
        },
        query_axes=_axes(
            (
                "US stock grid trading ten split lossless rebalancing",
                "10분할",
                "고정 10슬롯",
                "ATR 가변 슬롯",
                "wonkisus 10분할 정본, ATR은 보조.",
            ),
            (
                "US market premarket after hours trading UI",
                "미국 장외",
                "프리마켓 표시",
                "정규장만",
                "프리/애프터는 배지로 구분.",
            ),
            (
                "overseas stock trading dashboard mobile UX",
                "모바일 US",
                "하단 탭",
                "햄버거",
                "차수·손익은 하단 고정.",
            ),
        ),
    ),
}


def get_config(unit_id: str) -> UnitWebResearchConfig | None:
    return UNIT_CONFIGS.get((unit_id or "").strip())


def all_unit_ids() -> list[str]:
    return list(UNIT_CONFIGS.keys())
