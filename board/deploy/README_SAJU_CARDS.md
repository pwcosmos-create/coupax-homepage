# 사주 학습 카드 배포 — 위원회 검증 유지

## 금지

- `cards.json`을 서버에 **통째로 scp 덮어쓰기** → `council_*` 검증 기록이 사라짐

## 권장

1. **서버에서만** 카드 추가 (사무실 UI, cron `saju_auto_add_cards.py`, seed 스크립트 SSH 실행)
2. 로컬에서 만든 카드를 올릴 때:

```powershell
cd board\deploy
.\merge_saju_cards_to_server.ps1
```

3. 서버에서 직접 병합:

```bash
cd /home/ubuntu/coupax-homepage/board
.venv/bin/python scripts/agent_office_saju_learn.py import-merge /path/to/incoming.json --add-new-only
```

## 동작

- `merge_stores()` / `preserve_council_fields()` — `council_at`이 있는 카드는 검증 필드 보존
- `save_store()` — 상한(500장) 초과 시 **검증된 카드는 먼저 보존**
- 새 카드(`add_card`, seed, auto_pool)는 **append만** — 기존 카드 수정 없음

## 위원회 검증 (자동)

- **확정 즉시**: `confirm_card()` → `trigger_council_verify(mode=realtime)`
- **지속 검증**: cron `tick-cycle` (3분마다) + worker 매 사이클 1장
  1. 미검증 확정 카드 (id 오름차순)
  2. 없으면 **PASS 카드만** 순차 재검증·강화 (`pass_reverify_index`)
- **PASS 일괄 강화**: `batch-reverify-pass --reset --count 100 --sleep 1`
- **FAIL 자동 수정·재인증**: `batch-fix-recert --count 80` (본문·태그·면책 보정 후 재검증)
- **문구 최적화**: `saju_card_copy_optimize.py --all` (제목·본문 문장·요약·태그 → pack·Wiki·재인증)
- **재검증 구체화**: `batch-enrich-reverify --count 161` (개요·절차·키워드·주의 본문 → 재검증)
- **작성 시 구체화**: `add_card` / `confirm_card` 시 `compose_new_card()` 자동 (SAJU_CARD_COMPOSE_ON_CREATE=1)
  - **변수형** (`변수·` 제목): 【개요】【풀이 절차】【활용 키워드】…
  - **해석형** (`해석·` 제목·일반 가이드): 【인사·성향】【명식·구조】【오행·십신 해석】【테마 풀이】【실천 조언】【풀이 예문】…
- **자동 추가 (cron)**: **분당 10장** (`--per-minute 10`, `--sleep 5`)
  - 환경변수: `SAJU_CARDS_PER_MINUTE=10`, `SAJU_CARDS_SLEEP_SEC=5`
  - **Gemini 해설 cron**: 분당 10장 (`install_saju_auto_cards_cron.sh`에 포함)
- **심층 풀이 카드 장수 가이드**: `docs/SAJU-DEEP-READING-CARD-GUIDE.md`
  - pack은 배치마다 1회만 export (부하 완화)
- **본문 품질 (하이브리드)**  
  1. 추가 시 `compose_new_card()` — 템플릿 초안 (빠름)  
  2. 위원회 **PASS** 후 **`Gemini 2.5`** (`SAJU_CARD_GEMINI_MODEL=gemini-2.5-flash`)로 해설 **1회** 작성  
  3. `GEMINI_API_KEY` + `SAJU_CARD_LLM_PROVIDER=gemini` + `SAJU_CARD_LLM_ALLOW_OLLAMA_FALLBACK=0` (Gemini 전용, Groq 없음)  
  4. 성공 시 카드에 `llm_composed_at` 저장 → **이후 Gemini/Ollama 재호출 없음** (아래 참고)  
  - 수동: `python scripts/saju_card_llm_compose.py batch --count 3 --sleep 15`
  - cron: `install_saju_gemini_compose_cron.sh` — `llm_composed_at` 없는 PASS 카드만 분당 N건
- **위원회 검증 (cron)**: **5분마다** 4장 (`SAJU_COUNCIL_PER_TICK=4`)
  - `deploy/install_saju_card_council_cron.sh`
- **검증 주체**: `agent_office_saju_card_council.py`의 **명리 위원회 패널** (결계·명리·이기·독해·전장·품질·**재점검** 젬마). **재점검 젬마**(`saju_reinspector`)는 PASS·FAIL 재시도·수정 재인증 시 면책·인증 이력·강화 기준 담당. 규칙·체크리스트 기반 — **LLM API 없음**. 확정 시 `confirm_card` → 즉시 1회 검증, cron은 미검증·FAIL·PASS 재검증 순.

## Gemini 해설 1회 작성 — `llm_composed_at` (저장본 재사용)

위원회 **PASS** 이후 `saju_card_llm_compose.py`가 템플릿 초안(`body`)을 Gemini 2.5로 다듬으면, 성공한 카드에 다음 필드가 기록됩니다.

| 필드 | 의미 |
|------|------|
| `llm_composed_at` | Gemini 다듬기 완료 시각 (`YYYY-MM-DD HH:MM`). **이 값이 있으면 LLM을 다시 부르지 않음** |
| `llm_compose_model` | 사용 모델 (예. `gemini:gemini-2.5-flash`) |
| `llm_compose_provider` | `gemini` (기본, Ollama 폴백 꺼짐) |

### 재호출하지 않는 이유

- **비용·부하**: 분당 자동 추가·cron batch가 같은 카드를 반복 호출하지 않도록 함  
- **본문 보호**: PASS 후 확정된 해설이 매번 덮어쓰이지 않음  
- **멱등성**: 위원회가 PASS를 다시 찍거나(`reverify_pass`) cron이 돌아도, `llm_composed_at`이 있으면 **저장된 `body`·제목·요약·태그를 그대로 사용**

### 어디서 막는지

1. **`eligible()`** — `llm_composed_at`이 비어 있지 않으면 `False`  
2. **`polish_card_after_pass()`** — 위 필드가 있으면 API 호출 없이 `skipped`, `reason=already_llm_composed`  
3. **`batch_polish(only_missing=True)`** — 대기 목록에서 `llm_composed_at` 있는 카드 제외 (cron 기본)  
4. **`status`** — `gemini_pending` = PASS이면서 `llm_composed_at` 없고 `eligible`인 건수만 집계

### 흐름 요약

```
추가(템플릿) → confirm → 위원회 PASS
  → llm_composed_at 없음? → Gemini 1회 → body 저장 + llm_composed_at 기록
  → llm_composed_at 있음? → 스킵 (저장본 재사용, API 없음)
```

### 다시 LLM을 돌리고 싶을 때 (수동·비권장)

`data/saju_learning/cards.json`에서 해당 카드의 `llm_composed_at`(및 `llm_compose_model`, `llm_compose_provider`)를 **삭제**한 뒤:

```bash
.venv/bin/python scripts/saju_card_llm_compose.py run --card-id N
```

배포 zip으로 `cards.json` 전체를 덮어쓰지 말 것 — 서버 병합 스크립트(`merge_saju_cards_to_server.ps1`)만 사용.
