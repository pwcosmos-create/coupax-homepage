# MVP Dashboard API Specification

## 1. Endpoint Definitions (RESTful)

### 1.1. /api/v1/dashboard/status
**Description:** 시스템의 전반적인 안정성 및 데이터 파이프라인 상태를 확인합니다. (시스템적 통제권 시각화 기반)
**Method:** GET
**Response:** JSON
**Purpose:** $DPSR$ 99.9% 달성 여부 및 실시간 데이터 흐름 상태 보고.

### 1.2. /api/v1/dashboard/kpi_summary
**Description:** 핵심 KPI 요약 정보를 제공합니다. (정보 분할 및 단계별 노출 반영)
**Method:** GET
**Response:** JSON
**Purpose:** $ROI_{basic}, ROI_{standard}, ROI_{premium}$ 등 주요 수익화 지표를 집계하여 반환.

### 1.3. /api/v1/data/realtime_metrics
**Description:** 실시간 매출 및 트래픽 데이터를 제공합니다. (Self-Healing 루프를 통해 안정화된 데이터)
**Method:** GET
**Response:** JSON
**Purpose:** PayPal 연동 등에서 수집된 최신 실시간 $ROI$ 관련 데이터.

### 1.4. /api/v1/pipeline/health_check
**Description:** 데이터 파이프라인의 안정성 검증을 위한 엔드포인트입니다.
**Method:** GET
**Response:** JSON
**Purpose:** `paypal_revenue.py` 스크립트의 최종 안정성 상태 및 오류 로그를 반환하여 $DPSR$ 검증에 활용.

## 2. Data Model Definition (JSON Schema Draft)

### 2.1. KPI Summary Model
```json
{
  "status": "OK",
  "dpsr_stability": "99.9%",
  "roi_basic": 10,
  "roi_standard": 75,
  "roi_premium": "Maximized",
  "realtime_revenue": {
    "metric": "RevenueUSD",
    "value": 12345.67,
    "timestamp": "2026-06-07T10:00:00Z"
  },
  "pipeline_status": {
    "source_stability": "Stable",
    "last_check": "2026-06-07T12:30:00Z"
  }
}
```

### 2.2. Realtime Metrics Model (예시)
```json
{
  "metric": "RevenueUSD",
  "value": 12345.67,
  "timestamp": "2026-06-07T10:00:00Z"
}
```