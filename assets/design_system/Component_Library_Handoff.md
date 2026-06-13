# 🎨 보배시즌 - 최종 컴포넌트 라이브러리 (Design System Handoff)

## 🎯 목표: 개발팀의 즉각적인 구현을 위한 재사용 가능한 요소 정의
이 문서는 Mockup에 사용된 모든 UI 요소를 분해하여, 일관성과 확장성을 확보하는 것을 목표로 합니다.

### 1. 컬러 팔레트 (Color Palette)
| 역할 | 이름 | HEX 코드 | 용도 및 근거 |
| :--- | :--- | :--- | :--- |
| **Primary** | Midnight Blue | `#0A1931` | 배경, 주요 섹션 구분선. 깊은 신뢰감과 권위 부여. (근거: 시스템적 안정성) |
| **Secondary** | Deep Copper | `#B8860B` | CTA 버튼, 핵심 강조 요소(KPI 수치), 로고 포인트. 프리미엄 가치와 희소성 상징. (근거: 높은 전환율 유도) |
| **Accent** | Clear Sky Blue | `#ADD8E6` | 데이터 흐름, 그래프의 상승 추세, 시스템 연결선(Flow). '명확한 통제' 시각화. (근거: 데이터 기반 강조) |
| **Neutral** | Off-White | `#F9FAFB` | 기본 배경색. 가독성 극대화. |

### 2. 타이포그래피 스케일 (Typography Scale)
*   **폰트:** Pretendard (가장 높은 가독성과 현대적 느낌을 제공합니다.) [근거: 높은 가독성 및 현대적 느낌]
*   **H1 (헤드라인):** 48px / Bold / Midnight Blue. (페이지의 핵심 메시지 전달)
*   **H2 (섹션 제목):** 32px / SemiBold / Midnight Blue. (주요 기능/장점 섹션 구분)
*   **Body Large:** 18px / Regular / #333333. (핵심 설명 문구, 가독성 최우선)
*   **Body Small:** 14px / Regular / #666666. (보조 정보, 법적 고지 등)

### 3. 핵심 컴포넌트 정의 (Core Components)

#### A. CTA 버튼 (Call-to-Action Button)
*   **기본 상태 (Default):** 배경: Deep Copper (`#B8860B`), 텍스트: Off-White, 패딩: 14px 32px, 모서리: 8px Radius.
*   **호버 상태 (Hover):** 배경: #D4A95C (Deep Copper보다 밝은 톤), 그림자: Subtle Shadow.
*   **비활성화 상태 (Disabled):** 배경: #AAAAAA, 텍스트: #666666.

#### B. 데이터 카드 (KPI/Data Card)
*   **레이아웃:** Midnight Blue 배경의 직사각형 박스.
*   **구조:** 상단에 Clear Sky Blue로 강조된 아이콘 + KPI 수치(Deep Copper). 하단에 설명 텍스트(Body Small).
*   **목적:** 데이터 기반 증명 (Systemic Proof)을 시각적으로 분리하여 보여줍니다.

#### C. 기능 목록 섹션 (Feature List Section)
*   **레이아웃:** 아이콘 + 제목(H3) + 상세 설명(Body Large).
*   **강조 원칙:** 각 기능을 '통제력'이라는 관점에서 재해석하고, 해당 기능이 사용자에게 주는 **심리적 이점**을 강조하는 문구로 작성합니다.

---