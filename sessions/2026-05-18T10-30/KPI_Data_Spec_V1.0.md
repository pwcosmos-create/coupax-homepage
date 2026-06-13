# 📊 KPI 데이터 요구사항 명세서 (Minimum Data Requirements Specification) V1.0
## 🎯 목적 및 범위
본 문서는 '보배시즌'의 핵심 가치인 **시스템적 통제권(SSI)**을 객관적으로 증명하기 위해 필요한 최소한의 데이터 수집, 계산 로직, 그리고 출력 포맷을 정의합니다. 이 명세서는 개발팀(코다리)이 $DPSR$ 99.9%를 목표로 Mocking Layer를 구축하는 기준점이 됩니다.

## 🔑 핵심 KPI 목록 (3가지)
1. **전환율 (Conversion Rate, CR):** A 단계(정보 탐색)에서 B 단계(유료 서비스 고려)로 넘어가는 효율성 측정.
2. **투자 대비 수익률 (Return on Investment, ROI):** 시스템 접근 권한 구매가 실제 투자에 미치는 재무적 효과 증명.
3. **시스템 안정성 지수 (System Stability Index, SSI):** 데이터 기반의 예측 가능성과 신뢰도를 수치화하여 심리적 통제권을 판매하는 핵심 지표.

---

## ⚙️ KPI별 상세 요구사항 명세

### 1. 전환율 (Conversion Rate, CR)
*   **KPI 정의:** 잠재 고객이 '무료 체험/정보 탐색' 단계에서 '유료 서비스 가입 고려' 단계로 넘어가는 비율.
*   **비즈니스 목표:** A $\rightarrow$ B Funnel의 효율성 증명.
*   **필수 데이터 입력 (Source):**
    1.  `User_Interaction_Log`: 웹사이트/랜딩 페이지 방문 기록 (세션 수, 체류 시간).
    2.  `CTA_Click_Data`: 특정 CTA(Call-to-Action) 클릭 여부 및 시점.
*   **계산 로직:** $CR = \frac{\text{B 단계 진입 사용자 수}}{\text{A 단계 총 방문자 수}} \times 100$
*   **Mocking Layer 요구사항:**
    *   **Input Mock:** 가상의 `User_Interaction_Log`를 시간대별로 생성 (예: 주중/주말 패턴 반영).
    *   **Output Format:** 백분율(%) 형태로 출력.
    *   **Expected Range:** 1% ~ 5% 사이의 현실적인 범위에서 변동성을 테스트할 수 있어야 함.

### 2. 투자 대비 수익률 (Return on Investment, ROI)
*   **KPI 정의:** 시스템 접근 권한 구매 비용 대비 예상되는 포트폴리오 리스크 감소액을 측정하여 재무적 가치를 증명.
*   **비즈니스 목표:** '돈을 아껴준다'는 객관적인 근거 제시. (가장 강력한 설득 요소)
*   **필수 데이터 입력 (Source):**
    1.  `Initial_Portfolio_Value`: 고객의 초기 포트폴리오 가치 (Mocking 시뮬레이션 필요).
    2.  `Risk_Reduction_Factor`: 시스템 도입으로 예상되는 리스크 감소율 (%) (핵심 변수).
*   **계산 로직:** $ROI = \frac{(\text{Initial Value} \times \text{Risk Reduction Factor}) - \text{Cost}}{\text{Cost}} \times 100$
*   **Mocking Layer 요구사항:**
    *   **Input Mock:** 가상의 초기 포트폴리오 값과 리스크 감소율을 입력받아 계산.
    *   **Output Format:** 백분율(%) 형태로 출력하며, **반드시 '긍정적 수치'가 나오도록 설계되어야 함.** (구매의 당위성 확보)
    *   **Expected Range:** 최소 100% 이상이 나오는 시나리오를 기본으로 설정.

### 3. 시스템 안정성 지수 (System Stability Index, SSI)
*   **KPI 정의:** 데이터 수집 및 분석 파이프라인 자체의 신뢰도와 예측 가능성을 측정하는 종합 지표. 이는 '보배시즌' 서비스가 **24시간 작동한다**는 개념을 증명합니다.
*   **비즈니스 목표:** 경쟁사 대비 압도적인 시스템적 통제권(SSI) 확보를 통한 브랜드 신뢰 구축.
*   **필수 데이터 입력 (Source):**
    1.  `Data_Uptime`: 실시간 데이터 파이프라인의 가동 시간 및 성공률 (%).
    2.  `Error_Rate`: 시스템 오류 발생 빈도 (Mocking 시뮬레이션 필요).
*   **계산 로직:** $SSI = \text{Weight}_1(\text{Data Uptime}) - \text{Weight}_2(\text{Error Rate})$
*   **Mocking Layer 요구사항:**
    *   **Input Mock:** 99.9% 이상의 높은 가동 시간과 극히 낮은 오류율을 기본값으로 설정하여, **'절대적인 안정성'** 이미지를 구축해야 함.
    *   **Output Format:** 점수(Score) 형태로 출력 (예: 99.9%).

---
## 🚀 코다리에게 전달하는 실행 지침
1.  위 명세서(`KPI_Data_Spec_V1.0.md`)를 기반으로 Mocking Layer의 모든 로직을 재구축하십시오.
2.  특히, **ROI**와 **SSI**는 단순한 데이터 출력을 넘어, 고객에게 '개인화된 증명 결과물'처럼 보이도록 시각적 출력 포맷까지 고려하여 설계해야 합니다.