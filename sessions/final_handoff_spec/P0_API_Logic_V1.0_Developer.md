# 💻 P0 기능 최종 핸드오프 스펙 (기술 및 로직)

## 💡 목표: 개발 가능한 API 명세서와 클라이언트 로직 정의
**[근거: 코다리 안정화 보고서, CEO 지시사항]**

### 1. 데이터 모델 확정 및 Schema Mapping
(F01, F02에서 사용되는 핵심 데이터 필드 목록을 최종적으로 정리)
*   `user_id`: String (필수, Primary Key)
*   `revenue_data`: JSON Array (반드시 유효성 검사 필요 - 숫자형/날짜 형식 확인)
*   `error_code`: Integer (Fallback 처리 시 필수 로깅 대상)

### 2. 핵심 API Endpoint 명세서 (API Contract)
| 기능 | Endpoint | Method | 요청 본문 (Request Body Schema) | 예상 응답 (Success Response) | 비고 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| F01: 데이터 수집 | `/api/v1/data/collect` | POST | `{user_id: str, start_date: date}` | `{status: 'SUCCESS', data: {...}}` | **[근거: DPSR 99.9% 기준]** |
| F02: 분석 실행 | `/api/v1/analyze` | POST | `{data_set_id: str, param: float}` | `{analysis_result: dict, confidence: float}` | 결과 필드에 `confidence` 추가를 요청합니다. |

### 3. 클라이언트 로직 및 에러 처리 루프 (Pseudo Code)
**[근거: 코다리 Fallback Plan 문서화]**

```pseudo
FUNCTION fetchData(endpoint, payload):
    TRY:
        response = CALL_API(endpoint, payload)
        IF response.status == 'SUCCESS':
            RETURN processData(response.data)
        ELSE IF response.status == 'WARNING':
            LOG_TO_DB("Warning:", response.message) # 데이터 수집 지연 처리 (Self-Healing Log)
            VISUAL_FEEDBACK(SystemMessage, "일부 데이터가 누락되었으나 분석을 계속합니다.")
            RETURN processData(response.data)
        ELSE: # Critical Failure Case
            CALL_ERROR_HANDLER("Critical API Error")
    CATCH Exception e:
        // 최종 방어 로직 (Fallback Plan) 실행
        CALL_ERROR_HANDLER(e, "Network/Authentication Failed.")

FUNCTION CALL_ERROR_HANDLER(error, reason):
    LOG_TO_DB("FATAL:", error, reason)
    SET_GLOBAL_STATE('API_STATUS', 'FAILED') 
    // Designer가 정의한 에러 UI를 호출합니다.
    TRIGGER_DESIGNER_UI_ELEMENT("Network Error Card", message=reason) 
```

---