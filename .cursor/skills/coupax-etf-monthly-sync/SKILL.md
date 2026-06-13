---
name: coupax-etf-monthly-sync
description: >-
  coupax ETF 파이프라인·공개 페이지 — 2026-05 전면 중단(COUPAX_ETF_ENABLED=0).
  search-etf 호출 금지. 이 스킬은 재개 전까지 사용하지 않음.
---

# coupax ETF — 전면 중단 (2026-05)

**COUPAX_ETF_ENABLED=0** (기본값) 상태:

| 항목 | 상태 |
|------|------|
| `/etf`, `/etf/monthly-sheet`, CSV, 데이터 상품 페이지 | 503 중단 안내 |
| `sync_daily_monthly_etfs.py` 및 merge·fill_* | 실행 시 즉시 SKIP |
| search-etf.com API | `SEARCH_ETF_CALLS_ALLOWED=0` — 호출 금지 |
| 서버 cron | 제거 (`deploy/uninstall_monthly_etf_cron.sh`) |
| 에이전트 `etf_sync` | `mode_on: false` |
| 예약 작업 | ETF·시트 관련 템플릿 제외 |

정책 모듈:

- `board/scripts/etf_ops_policy.py` — 전역 on/off
- `board/scripts/search_etf_policy.py` — search-etf 전용

**재개하지 말 것** — 외부 허가·1차 출처 파이프라인 구축 후에만 `COUPAX_ETF_ENABLED=1` 검토.
