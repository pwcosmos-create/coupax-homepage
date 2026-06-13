처# 📊 데이터 증명 컴포넌트 (Data Proof Component) v2.0 스펙
## 1. 목적 및 원칙
*   **목적:** 사용자에게 '우리가 시스템적으로 통제하고 있다'는 인지적 안정감과 권위를 부여한다. [근거: Designer 개인 메모리]
*   **원칙:** 모든 데이터 증명 시각화는 반드시 Primary/Secondary/Accent 색상 3색을 활용하며, '흐름(Flow)'을 강조해야 한다. [근거: Designer 검증된 지식]

## 2. 구조적 요소 (Structure)
| 레이어 | 설명 | 핵심 기능 | 디자인 원칙 |
| :--- | :--- | :--- | :--- |
| **Headline** | KPI 제목 및 메시지 강조 | 명확한 가치 전달 (`X% 증가`) | Deep Copper 사용, Pretendard Bold. [근거: Designer 검증된 지식] |
| **Data Visualizer (CORE)** | 핵심 그래프/차트 영역 | 실시간 변화 추이(흐름) 시각화 및 데이터 포인트 제시. | Clear Sky Blue를 연결선으로 활용하여 '통제'의 경로를 표시. [근거: Designer 검증된 지식] |
| **Metric Breakdown** | 보조 수치 (A/B 비교, 비율 등) | 통계적 신뢰도를 높이는 구체적인 숫자의 제시. | 배경색 대비(Midnight Blue ↔ White), Deep Copper로 핵심 수치를 강조. [근거: Designer 검증된 지식] |
| **Interaction Layer** | 사용자 상호작용 요소 (Hover/Tooltip) | 사용자가 직접 데이터를 탐색하고 '통제'하는 느낌 제공. | 마우스 오버 시 Clear Sky Blue 연결선이 동적으로 굵어지거나 밝아지는 모션 적용. [근거: 통합 스케줄] |

## 3. 디자인 토큰 (Design Tokens)
*   **Color:**
    *   `--color-bg-primary`: `#0A1931` (Midnight Blue, 배경/권위)
    *   `--color-cta-secondary`: `#B8860B` (Deep Copper, 핵심 수치/CTA)
    *   `--color-flow-accent`: `#ADD8E6` (Clear Sky Blue, 데이터 흐름)
    *   `--color-text-main`: `#FFFFFF` (본문 텍스트)
*   **Typography:** Pretendard. H1: 32px Bold / Body: 16px Regular.

## 4. 상호작용 스펙 (Interaction Spec) - [필수]
1.  **데이터 로딩 시:** 데이터 그래프는 무작위로 점들이 나타나다가, Clear Sky Blue의 연결선이 '시스템적'으로 한 방향(최고점)을 향해 순차적으로 그려지며 등장해야 합니다 (Loading animation).
2.  **KPI 변화 감지:** 실시간 데이터가 들어올 때마다 Deep Copper 강조 색상이 가장 먼저 반응하며 수치를 업데이트합니다 (Micro-interaction).