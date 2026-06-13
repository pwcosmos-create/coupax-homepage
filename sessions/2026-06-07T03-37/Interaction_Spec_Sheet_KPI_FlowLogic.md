# 📈 MVP 대시보드: 핵심 KPI 변화 인터랙션 상세 명세서 (Flow Logic)

**[목표]** 시스템적 통제권 확보의 시각화: 사용자가 데이터를 통해 '왜' 이 수치가 변했는지 논리적인 경로를 인지하도록 설계한다.
**[참고 원칙]**
1.  **컬러 우선순위:** 변화 흐름은 반드시 **Accent Color (Clear Sky Blue, `#ADD8E6`)**로 시작하고, 최종 결과물(KPI 수치)는 **Secondary Color (Deep Copper, `#B8860B`)**로 마무리한다.
2.  **인지 부하 최소화:** 애니메이션은 과장되어서는 안 되며, 변화의 '방향성'과 '속도'에 집중해야 한다.

---

## 1. 핵심 인터랙션 상태 정의 (Interaction States)

| 상태 명칭 | 발생 시점 | 목표 경험 (UX Goal) | 사용 컬러 팔레트 |
| :--- | :--- | :--- | :--- |
| **Initial Load** | 대시보드 진입 직후, 데이터 로딩 완료 전. | 시스템의 존재감(권위)과 구조적 안정성 인지. | Primary (Midnight Blue) $\rightarrow$ Accent (Clear Sky Blue) |
| **Positive Flow (상승)** | KPI가 이전 대비 증가했을 때. | 긍정적인 흐름, 데이터 기반 성공 경험 시각화. | Clear Sky Blue $\rightarrow$ Deep Copper |
| **Negative/Anomaly Flow** | KPI가 급격히 하락하거나 비정상적인 패턴을 보일 때 (경고). | 즉각적인 주의 환기, 문제의 원인 파악 유도. | Accent (Clear Sky Blue) $\rightarrow$ Secondary (Deep Copper) + Alert Color (Red 계열) |

## 2. 상태별 애니메이션 및 시각 효과 명세 (Animation & Visual Specs)

### A. Initial Load: 시스템 권위 부여
*   **대상:** 모든 KPI 카드 제목과 레이블.
*   **트리거:** 컴포넌트 마운트 완료(Mount Complete).
*   **효과:** 1단계로, 데이터가 '채워지는' 느낌을 준다.
    *   **모션:** `Opacity` (0% $\rightarrow$ 100%)와 함께 `Y-axis Translate` (아래에서 위로)를 사용한다.
    *   **지연 시간:** 각 카드별 300ms 간격으로 순차적으로 나타나야 한다 (Staggered Effect).
    *   **시각 요소:** 데이터 수치 자체는 Placeholder 값으로 로딩되며, 배경 흐름 연결선(Accent Color)이 먼저 그려지면서 '시스템 활성화' 느낌을 준다.

### B. Positive Flow: 상승 추세 시각화
*   **대상:** 실시간 변화가 감지된 KPI 수치 영역 (숫자 자체).
*   **트리거:** 데이터 업데이트 발생 및 증감 폭 계산 완료.
*   **단계별 모션 (필수):** 3단계로 구성하여 인지 부하를 분산시킨다.
    1.  **(Flow Line - Accent Blue):** 기존 값과 새 값을 연결하는 가상의 흐름선이 **좌측에서 우측으로** 그려진다(Drawing Effect). 이 선은 `Clear Sky Blue`이다. (Duration: 400ms)
    2.  **(Value Transition - Scale/Color):** 수치 숫자(`Deep Copper`)가 변화할 때, 이전 값 $\rightarrow$ 새 값을 나타내며 **Scale Up & Down** 모션을 짧게 보여준다. 이때 `Ease-out`을 적용하여 부드러움을 유지한다. (Duration: 200ms)
    3.  **(Final State - Deep Copper):** 최종 수치에만 `Deep Copper`를 확실하게 고정하고, 아래에 작은 상승 아이콘 $\triangle$과 함께 변화율(%)을 표시한다.

### C. Negative/Anomaly Flow: 이상 감지 경고 (Critical Alert)
*   **대상:** KPI 카드 전체 및 해당 지표의 알림 영역.
*   **트리거:** 데이터가 정의된 임계값(Threshold) 이하로 급락했을 때.
*   **모션:** 시스템이 '경보'를 울리는 느낌을 준다.
    1.  **(Visual Alert):** KPI 카드 배경에 미세하고 빠른 `Red/Orange` 깜빡임 효과(`Pulse Animation`)를 줍니다. (Frequency: 800ms 주기).
    2.  **(Text Highlight):** 수치와 함께 경고 메시지("Anomaly Detected", "Alert!")가 `Deep Copper` 위로 오버레이되어 강렬하게 노출된다.
    3.  **(Action Prompt):** CTA 영역에 '상세 분석 보기' 버튼이 활성화되며, 이 버튼은 가장 높은 우선순위의 **Deep Copper**를 사용한다.

---

## 📝 코다리 개발팀 참고 사항 (Technical Implementation Notes)

1.  **API 연동 포인트:** KPI 업데이트는 클라이언트 측에서 실시간 스트림(WebSockets 등)으로 수신되는 것을 가정하고, 이 데이터가 들어올 때마다 위의 애니메이션 로직을 트리거해야 합니다.
2.  **프론트엔드 컴포넌트 분리:** `KPI_Card` 컴포넌트는 상태(`State`)에 따라 렌더링하는 로직이 복잡하므로, **애니메이션 관련 코드를 별도의 Hook 또는 Utility 클래스로 분리하여 관리**해야 합니다.
3.  **성능 최적화:** 애니메이션은 부드러움(Smoothness)을 유지하되, 과부하를 일으키지 않도록 `requestAnimationFrame` 기반의 동기화된 렌더링 처리가 필수입니다.