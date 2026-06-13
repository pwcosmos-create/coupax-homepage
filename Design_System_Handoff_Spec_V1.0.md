# 🎨 디자인 시스템 핸드오프 명세서 (Phase 1 티저 영상 에셋) V1.0
## 🎯 목적 및 범위
본 문서는 Phase 1 티저 콘텐츠에 사용될 모든 핵심 시각 에셋(썸네일, 인포그래픽, CTA 등)을 개발팀이 즉시 구현할 수 있도록 기술적 스펙과 컴포넌트 구조를 정의합니다.

**[근거: 자율 사이클 원칙 - 반복 금지/새로운 각도 진전]**
*   Mockup 제작 완료 $\rightarrow$ **개발 핸드오프 명세서 작성 (다음 단계)**

## 🎨 디자인 시스템 개요 (Design System Overview)
*   **Primary Color:** Midnight Blue (`#0A1931`) - 배경, 권위적 섹션 구분선.
*   **Secondary Color:** Deep Copper (`#B8860B`) - CTA 버튼, 핵심 수치(KPI), 최종 결론 강조. (가장 중요)
*   **Accent Color:** Clear Sky Blue (`#ADD8E6`) - 데이터 흐름, 그래프의 상승 추세, 시스템 연결선(Flow).

## 🖼️ 컴포넌트별 상세 스펙 정의 (Component Specification)

### 1. 메인 썸네일 컴포넌트 (Thumbnail Core Component)
*   **용도:** 유튜브 영상의 첫 인상 결정. 시청자의 '불안감'과 '통제력 회복'을 동시에 자극해야 함.
*   **크기 스펙:** 1280px (W) x 720px (H).
*   **레이어 구조 (Layering):**
    1.  **Background Layer (Midnight Blue):** 전체 배경색 및 권위적 분위기 조성.
    2.  **Hook Text Layer (Pretendard Bold, White/Clear Sky Blue):** 가장 큰 폰트 크기로 배치. 시청자의 문제점(Pain Point)을 직설적으로 언급.
    3.  **Proof Element Layer (Deep Copper):** 핵심 KPI 수치 또는 '증명된 데이터'를 강조하는 박스형 컴포넌트. 이 레이어는 반드시 Deep Copper로 처리되어야 함.
    4.  **CTA/Branding Layer:** 하단에 작게 배치되는 로고 및 채널 이름.

### 2. 인포그래픽 그래프 컴포넌트 (Data Visualization Component)
*   **용도:** '데이터 기반 증명'을 시각화하는 핵심 요소. 단순한 차트가 아닌, 시스템적 흐름을 보여줘야 함.
*   **크기 스펙:** 가로 100% 기준 유연하게 조정 가능. (최대 폭: 1280px)
*   **핵심 구조:** **'Before $\rightarrow$ System Flow $\rightarrow$ After'**의 3단계 흐름을 반드시 포함해야 함.
    *   **Before State:** 낮은 신뢰도의 데이터(흐릿한 회색/빨간 계열).
    *   **System Flow (Accent Color):** Clear Sky Blue를 사용하여 '데이터가 시스템을 통해 정제되고 연결되는' 애니메이션 경로를 구현. 이 경로는 단순 선이 아닌, **노드(Node)와 연결선(Connection Line)**의 조합으로 표현되어야 함.
    *   **After State:** 명확하고 상승하는 그래프 (Deep Copper 강조).

### 3. CTA 버튼 컴포넌트 (Call to Action Button Component)
*   **용도:** 시청자의 다음 행동을 유도하는 가장 중요한 요소.
*   **스펙:**
    *   **기본 상태 (Default):** Deep Copper 배경, 흰색 텍스트. 모서리 라운딩(Radius: 8px).
    *   **호버/클릭 상태 (Hover/Active):** Deep Copper 색상을 유지하되, 미세한 그림자 효과(Box-shadow)를 추가하여 '눌리는' 느낌을 부여해야 함.
    *   **텍스트:** 간결하고 행동 지향적이어야 함. ("지금 바로 시스템 접근하기", "무료 리포트 다운로드").

## ⚙️ 개발팀 참고 사항 (Developer Notes)
1.  **애니메이션 원칙:** 모든 시각화는 '점진적 노출(Progressive Reveal)' 원칙을 따릅니다. 한 번에 모든 정보가 나타나지 않도록, 데이터 포인트와 연결선이 순차적으로 활성화되는 애니메이션 스펙을 적용해야 합니다.
2.  **폰트 처리:** Pretendard 폰트는 웹 환경에서 최적화된 로딩 속도를 유지하도록 구현하고, 제목(H1)과 핵심 수치에만 Bold 처리를 집중합니다.