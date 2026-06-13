# AI 심층 풀이 — 지식 카드 장수 가이드

> **용도:** saju-v2 심층 풀이·카드 조합·LLM 보충 설계 시 기준 문서.  
> **LLM 정책 (board):** **Gemini 2.5만** — Groq·Ollama 미사용 (`SAJU_CARD_LLM_ALLOW_OLLAMA_FALLBACK=0`).  
> **코드:** `scripts/saju_reading_engine.py`, `scripts/seed_saju_deep_sections.py`, `app.py` `/api/saju/reading/compose`

---

## 현재 서버 현황 (갱신: `python scripts/saju_reading_engine.py inventory`)

| 항목 | 장수 (예시 2026-05-23) |
|------|------------------------|
| **PASS(사주위원회 인증) 전체** | **341장+** |
| 일주·천간 (`stem-day`) | 16 |
| 띠·천간 (`stem-chen`) | 10 |
| 격국 (`gyeok`) | 10 |
| 지지 (`branch`) | 7 |
| 용신 (`yongsin`) | 6 |
| 기신 (`gisin`) | 6 |
| 심층·기타 (`other`) | 286 |

**결론:** 총량은 **이미 충분**합니다. 한 번 풀이할 때는 그중 **10~20장**만 골라 10개 섹션에 넣습니다.

---

## 코드가 요구하는 것

| 구분 | 조건 | 이 저장소 구현 |
|------|------|----------------|
| **조합 시작 최소** | PASS 카드 **1장** 이상 (전부 PASS) | saju-v2: 1장+. **board API:** `SAJU_READING_MIN_PASS_CARDS` 기본 **2** (`saju_reading_engine.py`) |
| **섹션 수** | 화면 **10개** (1. 인사 성향 ~ 10. 실천 주의) | `SECTION_HINTS` 10절 (`saju_reading_engine.py`) |
| **섹션당 카드** | 최대 **3장**까지 합침 | saju-v2 클라이언트. board 조합은 섹션당 **1장** excerpt |
| **LLM 보충** | 섹션 비었거나 본문 **220자 미만** | saju-v2 → **Gemini** (Groq 사용 안 함). Wiki `summary` **220자** |
| **풀이당 매칭** | — | `match_pass_cards` 상한 **12장**, 조합 시 섹션별 1장 |
| **채팅 응답** | `text_chat` / `text_full` | v2 API — saju-v2 연동: `docs/SAJU-V2-COMPOSE-INTEGRATION.md` |
| **질문 추론** | `user_query` → kind | `scripts/saju_reading_intent.py` |

---

## 목표별 필요 장수

### ① 최소 — “돌아가기만”

- **PASS 1장+**
- 본문이 매우 짧아 **Gemini 보충**이 자주 붙음 → 비추천

### ② 권장 — “10섹션을 카드 위주로”

| 카드 종류 | 최소 장수 | 담당 섹션 |
|-----------|-----------|-----------|
| 심층·[1]~[10] | **10** | 1~10 전체 뼈대 (`seed_saju_deep_sections.py`) |
| 변수·격 (10격 + 칠살격) | **11** | 4. 십신·격국 |
| 일주(10천간) | **10** | 1. 인사·성향 |
| 용신·기신 (오행 5×2) | **10** | 5. 용신·기신 |
| 지지 | **7** (권장) | 8. 연애·관계 |
| 희신 (선택) | **5** | 5번 보강 |

- **합계:** 약 **40~50장** (최소) · **60~80장** (여유)
- 이 정도면 LLM 없이도 대부분 섹션이 채워짐

### ③ 운영 — “지금처럼 풀 운영”

- **PASS 200~350장** (현재 **341장+** ✅)
- 매칭이 약하면 **Gemini가 빈·짧은 섹션만** 맞춤 보축

---

## 한 줄 요약

| 목표 | 필요 장수 |
|------|-----------|
| 인증 풀이만 실행 | 1장+ |
| 10섹션 카드 위주 | **약 50~80장** |
| 안정 운영 (현재) | **200~350장** ← **OK** |

---

## 부족할 때 생기는 현상

- 격국·용신·심층이 **검색에 안 걸리면** → 해당 섹션만 짧거나 비음 → **Gemini 보축**
- 칠살격 / 희신 / 심층 **summary** 부족 → P0 보강 대상 (제작 요청서 기준)

---

## 화면 표시 (saju-v2 참고)

- 읽는 순서: **1. 인사 성향 → 2. 사주팔자 → … → 10. 실천 주의**
- **「AI 풀이 받기」** 클릭 시에만 분석 시작
- 초안 완료 후 **5초** 뒤 본문 공개

---

## 운영 명령

```bash
# PASS·버킷별 장수 (서버 board 디렉터리)
.venv/bin/python scripts/saju_reading_engine.py inventory

# P0 카드 일괄 (띠12·칠살·희신5·조후·원진) + 심층 10섹션
.venv/bin/python scripts/seed_saju_deep_sections.py
.venv/bin/python scripts/saju_auto_add_cards.py --ingest-p0 --sleep 1

# 조합 데모
.venv/bin/python scripts/saju_reading_engine.py demo --tags 일주,병화,정관,용신,오행
```

### P0 자동 풀 (`AUTO_CARD_POOL_P0`)

cron `ingest_pool` 시 **P0가 먼저** 소진됩니다: `변수·띠` 12 · `변수·격` 칠살/종격/잡격 · `변수·희신` 5 · 조후 · 원진.

---

## 카드 버킷 분류 규칙 (`inventory`)

| 버킷 | 판별 (제목·태그) |
|------|------------------|
| `stem-day` | `일주`, `일간`, `천간` + 일주 계열 |
| `stem-chen` | `띠`, `생肖`, `천간` (일주 제외) |
| `gyeok` | `격`, `격국`, `칠살` |
| `branch` | `지지`, `변수·지지` |
| `yongsin` | `용신`, `희신` |
| `gisin` | `기신` |
| `other` | `심층·`, `해석·`, 그 외 변수·해석 |

PASS만 집계. FAIL·미확정 제외.
