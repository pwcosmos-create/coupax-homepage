# 🎨 P0 기능 최종 핸드오프 스펙 (디자인 & 인터랙션)

## 💡 목표: 사용자 경험의 완결성 확보 및 개발팀 전달 준비
**[근거: CEO 지시사항, Designer 개인 메모리]**

### 1. 디자인 시스템 컴포넌트 업데이트 및 확장 원칙
*   **핵심:** 기존 정의된 Deep Copper, Midnight Blue, Clear Sky Blue를 유지하되, 다음 상태(State)에 대한 컴포넌트를 추가합니다.
    *   `Button State`: `Disabled (API Error)`, `Loading (Skeleton)`
    *   `Input Field State`: `Validation Error`, `Network Error`
    *   `Data Display State`: `Empty Data Placeholder (권위적 톤 유지)`

### 2. 핵심 시퀀스: 데이터 로딩 및 에러 핸들링 (가장 중요)
**[근거: 코다리 Fallback Plan, Designer 검증된 지식]**

| 시나리오 | 사용자 경험(UX) 가이드라인 | 애니메이션/인터랙션 스펙 | 비주얼 컴포넌트 |
| :--- | :--- | :--- | :--- |
| **성공 (Success)** | 데이터가 즉시, 그리고 부드럽게 나타남. 성공 시점은 Deep Copper 강조색 사용. | Clear Sky Blue의 흐름선이 목표 지점에 도달하며 데이터 블록이 '팝'처럼 등장합니다. | KPI 수치: `Deep Copper`로 최종 고정. |
| **네트워크 에러** | "데이터 연결에 실패했습니다." (추상적 메시지 X) | 1. 로딩 스피너가 회색으로 느려짐. 2. Deep Copper와 Clear Sky Blue 경계선이 깜빡이며 불안정함을 표현합니다. | `Network Error Card`: Midnight Blue 배경, 흰색 글씨에 주황빛 (Deep Copper의 변형) 액센트 사용. **[구체 메시지 예시: "연결 점검 필요: 현재 서버 연결이 불안정합니다. 인터넷 연결을 확인하거나 잠시 후 다시 시도해 주세요." ]** |
| **API 인증 에러** | 시스템 오류임을 명확히 안내하고, 해결 방안 제시 (사용자 조치 요구). | 버튼 클릭 무효화 처리. Clear Sky Blue의 흐름선이 끊어지며 'X' 표시와 함께 진동 효과를 줍니다. | `Auth Error Card`: 경고 아이콘과 함께 "관리자 문의 필요" 문구 명시. **[근거: 코다리 API 인증 실패 Fallback Plan]** |

### 3. P0 기능별 인터랙션 스펙 (F01 & F02)
*   **(예시: F01 핵심 버튼)** : 사용자가 '분석 실행' 버튼(Deep Copper) 클릭 → 즉시 `Loading` 상태로 전환. 로딩 중에는 Clear Sky Blue의 흐름선이 데이터 처리 과정을 시각적으로 보여주며 (전환 속도 800ms), 성공/실패 메시지 창을 통해 결과를 전달합니다.

---