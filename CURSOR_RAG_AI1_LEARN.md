# Cursor — AI 1인 기업 · RAG 1일차 학습 노트

갱신: **2026-06-19** (+ LoRA · QLoRA · 병합 · CAI · FT Safety · RepE · CAA · Refusal · Coupax)  
출처: [Notion 1일차](https://jaijung.notion.site/AI-1-34cb0dd76323804d834dec579ff163a4) + 라이브 전사 (Step 4 · 약 2h 45m)

---

## 한 줄 요약

**무지성 자동화(영상·글 대량 생산) ≠ 수익.**  
**지식 구조화(RAG) → 목적에 맞는 Generator(모델) → Agent(실행)** 이 AI 1인 기업의 본질.

---

## 8주 커리큘럼

| 단계 | 기간 | 목표 |
|------|------|------|
| **Step 1: RAG** | 1~4주 | 지능 구축 — 지식 네트워크·데이터 구조화·전문 지식 주입 |
| **Step 2: Agent** | 5~8주 | 자동화 실행 — 수익 워크플로·자율 에이전트 배포 |

### 이론 타임라인 (강의)

- **2020~2022** — RAG 뿌리 (Lewis et al.)
- **2023~2024** — Graph RAG 등 고도화
- **2026** — Agentic & Modular RAG
- **2027+** — SLM + RAG (온프레미스·비용·보안)

---

## RAG 정의

> **Retrieval** (외부에서 찾아옴) → **Augmented** (능력 보강) → **Generation** (답변 생성)

- 원논문: [Retrieval-Augmented Generation (Lewis et al., 2020)](https://arxiv.org/pdf/2005.11401)
- **Knowledge-intensive** 태스크: 외부 DB 없이는 답 불가 (일반 NLP 번역·감정 분석과 구분)

### 두 메모리

| 구분 | 영문 | 의미 | 예 |
|------|------|------|-----|
| 매개변수 메모리 | Parametric | 모델이 학습한 언어 능력 | Gemini 단독, ChatGPT 단독, **SFT 장기 기억** |
| 비매개변수 메모리 | Non-parametric | 외부 지식 창고 | PDF, Wiki, cards.json, **pwcosmos-swiki GitHub** |

### 파이프라인 4단계

1. **Query Encoder** — 질문을 고차원 벡터(좌표)로 변환
2. **Retriever + MIPS** — 지식 창고에서 의미적으로 가장 가까운 조각 검색
3. **Generator** — 질문 + 검색된 지식으로 최종 답변 생성
4. **End-to-end** — 틀리면 인코더·생성기 동시 학습 (연구 단계)

### 할루시네이션

- 확률 모델이라 「모른다」보다 「그럴듯한 거짓」을 말하기 쉬움
- RAG는 **오픈북 시험** — 외부 근거를 손에 쥐여 환각 억제

---

## 강사 3법칙 (황금 법칙)

1. **지식 구조화가 먼저** — 데이터를 무작위 투입하지 말 것. 패턴·연관·네트워크.
2. **목적에 맞는 모델** — 글쓰기·분석·로컬 SLM을 업무에 맞게 선택 후 RAG 결합.
3. **에이전트화** — Q&A를 넘어 다음 단계(업로드·발송·배포)까지 연결.

### 지식 구조화 vs 지식 쌓기

- **구조화** = AI가 패턴을 잘 찾게 만드는 것 (태그·버킷·그래프·벡터 배치)
- **쌓기** = 파일·문서를 많이 넣는 것 (양 ≠ 품질)
- **나쁜 예**: 일반 LLM이 생성한 평범한 글만 Non-parametric에 쌓기 → 더 평범해짐
- **좋은 예**: 나만의 경험·선별 지식·강의에서 배운 코어 개념

---

## 라이브 실습 4단계

| # | 도구 | 하는 일 |
|---|------|---------|
| 1 | **NotebookLM** + Transformers PDF | Parametric vs Non-parametric 비교, Source Grounding |
| 2 | **Google OPAL** | 드라이브·문서·YouTube 멀티 소스 → 지식체 |
| 3 | **Antigravity** | `day1.md` 로컬 지식 + `@day1` 멘션으로 코드·서비스 생성 |
| 4 | **Connect AI Lab** | 로컬 Gemma + GitHub 동기화 + **데이터 주입** |

### Antigravity 워크플로

1. Gemini/NotebookLM으로 지식 → **마크다운 문서화**
2. Antigravity `New File` → `day1.md` 붙여넣기
3. 채팅에서 `@day1` + 「트랜스포머 RAG 코드 작성해 줘」
4. 왼쪽 Explorer = **로컬 지식 두뇌** (벡터 검색 대상)

### Connect AI + GitHub

- **로컬 폴더** = 내 PC 지식 공간
- **GitHub repo** = 온라인 백업·다른 PC 동기화
- **데이터 주입** = 브레인팩 → 에이전트 지식으로 반영
- 에이전트 학교 · 브레인팩 보관소 · 데이터 주임 (강의 도구)

### 클라우드 vs 로컬

| | 클라우드 AI (Gemini/Claude API) | 로컬 LM (Gemma 등) |
|--|--------------------------------|---------------------|
| 실행 | 대기업 서버 | 내 PC |
| 비용 | 토큰 과금·변동 큼 | 초기 구축, 장기 절약 |
| 용도 | 학습·하이브리드 | 1인 기업 장기 운영 |

---

## Coupax 대응표 (이미 구현된 RAG)

| 강의 개념 | Coupax 경로 |
|-----------|-------------|
| Non-parametric 지식 | `board/data/saju_learning/cards.json` |
| Pack export | `board/data/saju_learning/saju_knowledge_pack.json` |
| Wiki / Gemma24 | `board/data/gemma_knowledge.json` (`wiki_saju_{id}`) |
| 지식 구조화 | `변수·격`·`변수·천간`·`심층·[1]~[10]` 버킷·태그 |
| 검색·매칭 | `saju_reading_engine.build_reading()` |
| RAG 라우팅 | `gemma24_local.infer_rag_domain()` |
| 데이터 주입 | `sync_saju_wiki_council.py` + `export_pack()` |
| Agent 실행 | Agent Office cron (카드 제작·위원회·Wiki sync) |
| 서버 마스터 | `168.107.31.153` — cards 병합 시 `import-merge --add-new-only` |
| **단기 기억 (GitHub)** | `pwcosmos-create/pwcosmos-swiki` · `agent_office_swiki_sync.py` |
| **장기 기억 (SFT)** | `export_connect_sft_jsonl.py` → `pwcosmos-v591-sft.jsonl` |
| Connect AI Lab 연동 | `sync_connect_ai_lab.py` · `import_connect_brain_jsonl.py` |

### Coupax 원칙 (강의와 정합)

- **카드 제작** = 템플릿·RL → **API 비용 없음**
- **Gemini 다듬기** = 선택(Parametric 보강) — cron 과다 시 quota 소진
- **품질** = `saju_card_reverify_enrich.py` 구조화 (294장, 2026-06-13 기준)

### Coupax 숙제 대체

```bash
# NotebookLM 대신 — 매칭 카드 확인
cd board && PYTHONPATH=scripts python -c "
import saju_reading_engine as e
r=e.build_reading({'tags':['병화','정관격','용신'],'summary':'test'})
print(r.get('matched_count'), [c.get('title') for c in (r.get('matched_cards') or [])[:5]])
"

# Connect AI 주입 대신 — 서버 RAG 동기화
ssh ubuntu@서버 "cd .../board && PYTHONPATH=scripts .venv/bin/python scripts/sync_saju_wiki_council.py"
```

---

## Parametric 학습·병합 타임라인 (참고)

| 순서 | 논문 | 핵심 | 쓰는 때 |
|------|------|------|---------|
| 0 | **LoRA** (ICLR 2022) | base 고정 + **저랭크 ΔW** 만 학습 | 장기 기억 SFT·어댑터 교체 |
| 0′ | **QLoRA** (NeurIPS 2023) | base를 **4-bit 양자화** + LoRA 역전파 | **48GB 1장**으로 65B급 FT, 소비자 GPU |
| 1 | **Model Soups** (ICML 2022) | 같은 태스크·다른 하이퍼파라미터 fine-tune **가중치 평균** | 한 도메인 LoRA/SFT 여러 번 돌린 뒤 |
| 2 | **Task Arithmetic** (ICLR 2023) | **ΔW** 덧셈·뺄셈으로 태스크 행동 조절 | 도메인별 ΔW 보관·합성 |
| 3 | **TIES-Merging** (NeurIPS 2023) | 여러 태스크 ΔW 병합 시 **간섭 제거** | 사주+금융+디자인 → 1모델 |

---

## LoRA — 저비용 장기 기억(Parametric) 학습

출처: [LoRA (Hu et al., ICLR 2022)](https://arxiv.org/abs/2106.09685) · [DOI](https://doi.org/10.48550/arXiv.2106.09685)

### 한 줄 요약

**사전학습 가중치는 고정**하고, Transformer 각 층에 **저랭크(rank-r) 분해 행렬**만 학습한다. full fine-tune 대비 **학습 파라미터·GPU 메모리 대폭 절감**, 품질은 full FT와 **동등 이상** — adapter와 달리 **추론 지연 추가 없음**(학습 후 base에 병합 가능).

### 수식 (직관)

기존 linear layer: `h = W₀x`

LoRA 추가:

```
h = W₀x + ΔWx = W₀x + BAx
```

- `W₀` — frozen pre-trained weights
- `B ∈ ℝ^{d×r}`, `A ∈ ℝ^{r×k}` — **trainable**, rank `r ≪ min(d,k)`
- 학습 끝 후 `W = W₀ + BA` 로 **병합**하면 추론은 기존과 동일 속도

### full fine-tune vs LoRA

| | Full fine-tune | LoRA |
|--|----------------|------|
| 학습 파라미터 | 전체 (예: 7B 전부) | rank-r 행렬만 (수백만~수천만) |
| GPU 메모리 | 큼 | **약 1/3 수준** (GPT-3 175B 실험 기준) |
| 태스크별 배포 | 모델 전체 복제 (비용 큼) | **어댑터 파일만** 교체 |
| 추론 지연 | 기준 | adapter 병합 시 **추가 없음** |
| 품질 | 기준 | RoBERTa·DeBERTa·GPT-2/3에서 **on-par or better** |

### RAG 두 메모리와의 관계

| 레이어 | 역할 | Coupax |
|--------|------|--------|
| Non-parametric | 검색·주입 | `pwcosmos-swiki`, `gemma_knowledge.json` |
| Parametric (LoRA) | 말투·도메인 **내재화** | `pwcosmos-v591` SFT, Unsloth/Colab 학습 |
| Parametric (full FT) | 동일, 비용 큼 | 대형 GPU·장시간 필요 시 |

- **단기 기억** = RAG로 사실·카드 검색  
- **장기 기억** = LoRA/SFT로 「우리 회사 말투·사주 해석 스타일」을 가중치에 새김  
- LoRA 없이 full FT만 하면 로컬 1인 기업 PC에서 **591건 SFT도 부담** — LoRA가 현실적 경로

### rank-deficiency (논문 시사)

- 언어 모델 adaptation은 **본질적으로 low-rank** 에 가깝다 → rank 8~64만으로도 충분한 경우 많음
- rank 올리면 품질 ↑ 대신 과적합·메모리 ↑ — Coupax는 **r=16~32**부터 sweep 권장

### Coupax 적용

| 항목 | 경로·도구 |
|------|-----------|
| SFT 데이터 | `pwcosmos-v591-sft.jsonl` (`export_connect_sft_jsonl.py`) |
| 학습 스택 | Unsloth + `train-sft.ipynb` (swiki `connect-ai/`) |
| 도메인 분리 | 사주 / 금융 / 디자인 **LoRA 어댑터 각각** → Task Arithmetic·TIES로 병합 가능 |
| 배포 | Ollama GGUF · LM Studio · Agent SDK 로컬 Generator |
| 비용 | Gemini full compose 대신 **로컬 LoRA** — `SAJU_COMPOSE_LLM=0` 정책과 정합 |

### 이후 파이프라인 연결

```
[LoRA SFT] → (선택) Model Soup → ΔW 추출 → (멀티도메인) TIES-Merge
     ↑                                              ↓
 pwcosmos-v591-sft.jsonl                    pwcosmos-multitask (목표)
```

---

## QLoRA — 소비자 GPU에서 장기 기억 학습

출처: [QLoRA (Dettmers et al., NeurIPS 2023)](https://arxiv.org/abs/2305.14314) · [DOI](https://doi.org/10.48550/arXiv.2305.14314)  
*(LoRA 위에 양자화 — Unsloth·Guanaco 계열의 실무 기반)*

### 한 줄 요약

**4-bit로 양자화·고정된** 사전학습 LLM에 대해 **LoRA만** 역전파한다. **48GB GPU 1장**으로 65B급 fine-tune이 가능하고, **16-bit full FT와 동등한 downstream 성능**을 유지한다고 보고. Coupax `pwcosmos-v591` 로컬 SFT의 **현실적 엔진**.

### LoRA vs QLoRA

| | LoRA | QLoRA |
|--|------|-------|
| base 가중치 | FP16/BF16 **frozen** | **4-bit NF4** frozen |
| 학습 대상 | LoRA 행렬 A, B | 동일 (LoRA만) |
| 메모리 | LoRA만으로도 절감 | **추가 대폭 절감** (65B → 48GB 1GPU) |
| 성능 | ≈ full FT | 논문: **16-bit FT 수준 유지** |
| 대표 산출 | LoRA adapter | **Guanaco** (Vicuna 벤치 ChatGPT 99.3%) |

### 핵심 기술 3가지

1. **4-bit NormalFloat (NF4)** — 정규분포 가중치에 정보이론적으로 유리한 4-bit dtype  
2. **Double quantization** — 양자화 상수까지 다시 양자화해 메모리 추가 절감  
3. **Paged optimizers** — optimizer 상태 메모리 스파이크를 페이지처럼 관리 (OOM 완화)

### 학습 흐름 (직관)

```
Base LLM (4-bit, frozen) ──forward──► logits
                ▲
                └── LoRA (BF16 trainable) ◄── gradient만 역전파
```

- base 전체를 올리지 않아도 됨 → **노트북·RTX 4090·단일 서버 GPU**에서 장기 기억 SFT 가능
- 고품질 **소량** instruction 데이터(`pwcosmos-v591-sft.jsonl` ~1k건)로도 강한 결과 (논문: 1,000+ 모델 sweep)

### 논문이 남긴 실무 교훈

- **작고 고품질** 데이터 > 대량 저품질 (Coupax `export_connect_sft_jsonl` 필터와 정합)
- chatbot 벤치마크는 **과신 금지** — lemon-pick으로 실패 구간 별도 점검
- GPT-4 평가는 human 평가의 **저렴한 대안**으로 쓸 수 있음 (내부 QA 자동화 참고)

### Coupax 적용

| 항목 | 설정 |
|------|------|
| 데이터 | `pwcosmos-v591-sft.jsonl` (brain+dpo+wiki, 저품질 제거) |
| 스택 | **Unsloth** (QLoRA 최적화) · `train-sft.ipynb` · bitsandbytes 4-bit |
| 베이스 | Gemma / Llama 계열 7B~9B — 로컬 Ollama와 호환 우선 |
| 산출 | LoRA adapter → **GGUF q4_k_m** (Ollama) 또는 adapter만 교체 |
| 비용 | 클라우드 학습 한도(월 3회) 없이 **Colab Pro / 로컬 GPU** 우회 |
| 병행 | 단기 기억 `pwcosmos-swiki` RAG — QLoRA와 **하이브리드**가 5강 로컬 AI 경로 |
| 안전 | 정렬된 베이스도 **도메인 FT만으로 안전 저하** 가능 → [FT Safety](#fine-tuning-vs-safety--정렬된-llm도-커스텀-ft에-취약) 참고, SFT에 거절·PII 샘플 혼합 |

### 파이프라인 (갱신)

```
pwcosmos-v591-sft.jsonl
        ↓
   [QLoRA + Unsloth]  ← 소비자 GPU
        ↓
  pwcosmos-v591 (LoRA/GGUF)
        ↓
 (선택) Model Soup → ΔW → TIES 멀티도메인
```

---

## Model Soups — 같은 태스크 fine-tune 가중치 평균

출처: [Model soups (Wortsman et al., ICML 2022)](https://arxiv.org/abs/2203.05482) · [DOI](https://doi.org/10.48550/arXiv.2203.05482)  
*(Task Arithmetic 공저자 Ilharco·Wortsman 등 동일 연구선)*

### 한 줄 요약

같은 사전학습 모델을 **서로 다른 하이퍼파라미터**로 여러 번 fine-tune한 뒤, 검증셋 최고 1개만 쓰지 말고 **가중치를 평균**하면 정확도·견고성이 종종 더 좋아진다. 추론 비용은 **모델 1개와 동일** — ensemble과 달리 메모리·지연 증가 없음.

### 기존 방식 vs Model Soup

| | Best-of-sweep | Model Soup |
|--|---------------|------------|
| 학습 | 동일 태스크, lr·epoch·seed 등만 다름 | 동일 |
| 선택 | validation 최고 **1모델**만 채택, 나머지 폐기 | 여러 체크포인트 **W 평균** |
| 추론 | 모델 1개 | 모델 1개 (평균된 가중치) |
| ensemble | N배 비용 | **추가 비용 없음** |

```
W_soup = (W_ft₁ + W_ft₂ + … + W_ftₙ) / n
```

### 왜 통하는가 (논문 직관)

- 대형 pre-trained 모델 fine-tune 결과는 종종 **같은 low-error basin(평탄한 손실 영역)** 안에 모임
- 가중치 평균 ≈ logit ensemble과 유사한 효과 — **flat loss**·예측 confidence와 관련 (논문에서 분석·실증)
- ImageNet·NLP·OOD·zero-shot 등에서 sweep 최고 단일 모델보다 개선 보고

### Task Arithmetic / TIES와 구분

| | Model Soups | Task Arithmetic / TIES |
|--|-------------|------------------------|
| fine-tune 목표 | **같은** downstream 태스크 | **서로 다른** 태스크 |
| 합치는 것 | 전체 가중치 W | 주로 **ΔW = W_ft − W_base** |
| Coupax 예 | `pwcosmos-v591` SFT를 lr 3종 돌려 soup | `ΔW_saju` + `ΔW_finance` TIES 병합 |

### Coupax 적용 메모

- **장기 기억 SFT**를 여러 설정으로 반복할 때 (lr, epoch, LoRA rank):
  - 최고 1개만 쓰기 전에 **체크포인트 가중치 평균** 시도
  - 산출물 이름 예: `pwcosmos-v591-soup`
- **단기 기억(RAG)** 과 무관 — Parametric 레이어만 해당
- Task Arithmetic·TIES는 **멀티 도메인** 단계에서; Model Soup은 **단일 도메인 품질 극대화** 단계

---

## Task Arithmetic — 장기 기억(Parametric) 확장

출처: [Editing Models with Task Arithmetic (Ilharco et al., ICLR 2023)](https://arxiv.org/abs/2212.04089) · [DOI](https://doi.org/10.48550/arXiv.2212.04089)

### 한 줄 요약

**미세조정 후 가중치 − 사전학습 가중치 = 태스크 벡터(ΔW)**. 이 벡터를 **더하기·빼기**로 모델 행동을 바꾸거나 여러 태스크를 한 모델에 합칠 수 있다.

### 핵심 개념

```
task_vector = W_finetuned − W_pretrained
```

| 연산 | 효과 |
|------|------|
| **+ task_vector** | 해당 태스크 성능 ↑ |
| **− task_vector** | 해당 태스크 성능 ↓ (편향 완화 등), 다른 태스크는 거의 유지 |
| **v₁ + v₂ + …** | 여러 태스크를 동시에 반영 |
| **유추(analogy)** | A:B = C:D 관계일 때, 세 태스크 벡터만으로 네 번째 태스크 개선 가능 (네 번째 데이터 없이) |

### QLoRA·LoRA와 연결

- QLoRA로 도메인별 **LoRA adapter** 학습 → `task_vector ≈ ΔW` 로 추출·보관
- adapter만 `pwcosmos-swiki/connect-ai/`에 push — **도메인 모듈 교체** (7B 전체 복제 불필요)
- 여러 ΔW 합칠 때는 **TIES** 권장 (단순 덧셈은 간섭)

### RAG 두 메모리와의 관계

| | RAG (Non-parametric) | SFT (Parametric) | Task Arithmetic |
|--|----------------------|------------------|-----------------|
| 저장 단위 | 문서·Wiki·JSONL | 전체 모델 가중치 | **태스크별 ΔW** |
| 갱신 | push/pull·주입 | 재학습 | 델타 저장·합산 |
| Coupax 예 | `pwcosmos-swiki` 단기 기억 | `pwcosmos-v591` 장기 기억 | (향후) 사주·금융·디자인 ΔW 분리 보관 |

- **지금 단계**: SFT 1회(`pwcosmos-v591-sft.jsonl`) + RAG(swiki) — 강의 1~4강 흐름과 동일.
- **다음 단계 옵션**: 도메인별로 따로 미세조정 → **ΔW만 GitHub에 올려** 전체 모델을 매번 다시 학습하지 않음.
- **주의**: 같은 베이스 모델·학습 설정이어야 하고, 델타를 무작정 더하면 품질 붕괴 가능.

### Coupax 적용 시나리오 (참고)

| 태스크 | 잠재 ΔW 출처 |
|--------|----------------|
| 사주 해석 | `saju_learning` SFT |
| 금융·ETF | `finance_learning` SFT |
| 홈페이지 디자인 | `homepage_design_learning` SFT |
| Connect AI Lab | `connect-ai-brain.jsonl` / `pwcosmos-v591-sft.jsonl` |

합성 예: `W_base + ΔW_saju + ΔW_finance` (실험·검증 후 적용)

→ **한계**: 여러 ΔW를 단순 합산하면 **간섭(interference)** 로 성능이 크게 떨어짐 → 아래 TIES-Merging이 보완.

---

## TIES-Merging — 태스크 벡터 합칠 때 간섭 해결

출처: [TIES-Merging (Yadav et al., NeurIPS 2023)](https://arxiv.org/abs/2306.01708) · [DOI](https://doi.org/10.48550/arXiv.2306.01708)

### 한 줄 요약

여러 태스크별 fine-tune 모델을 **추가 학습 없이** 하나로 합칠 때, 기존 merging은 **파라미터 간섭** 때문에 성능이 떨어진다. **TIES** = **T**rim + **E**lect sign + **M**erge — 3단계로 간섭을 줄인다.

### 간섭의 두 원인

| 원인 | 설명 |
|------|------|
| **(a) 중복·미미한 변화** | fine-tune에서 거의 안 바뀐 파라미터도 합산에 포함 → 노이즈 |
| **(b) 부호(sign) 충돌** | 같은 파라미터 위치에서 모델마다 +/− 방향이 다름 → 상쇄·붕괴 |

### TIES 3단계 (TRIM · ELECT SIGN · MERGE)

1. **Trim (리셋)** — fine-tune 동안 **변화가 작았던** 파라미터는 0으로 되돌림 (덜 중요한 Δ 제거)
2. **Elect Sign (부호 합의)** — 파라미터마다 **최종 부호(+/−)** 를 투표·집계로 결정
3. **Merge (정렬 병합)** — 합의된 부호와 **일치하는** 모델의 Δ만 합산

```
기존:  W_merge = W_base + ΔW₁ + ΔW₂ + ΔW₃   ← 간섭 많음
TIES:  W_merge = W_base + TIES(ΔW₁, ΔW₂, ΔW₃) ← Trim → Sign → Merge
```

### Task Arithmetic과의 관계

| | Task Arithmetic (ICLR 2023) | TIES-Merging (NeurIPS 2023) |
|--|----------------------------|----------------------------|
| 핵심 | ΔW 정의·덧셈·뺄셈 가능성 증명 | **여러 ΔW 합칠 때** 간섭 제거 |
| Coupax 시점 | 도메인별 ΔW 개념 도입 | 사주+금융+디자인 **멀티태스크 1모델** 병합 시 |

- Task Arithmetic으로 `ΔW_saju`, `ΔW_finance` 등을 만들었다면, **단순 합 대신 TIES** 로 `W_base`에 병합하는 것이 안전.
- **추가 학습 불필요** — 이미 fine-tune된 체크포인트만 있으면 됨.

### Coupax 적용 메모

| 단계 | 도구·산출물 |
|------|-------------|
| 1. 도메인 SFT | `saju_learning` / `finance_learning` / `homepage_design_learning` 각각 fine-tune |
| 2. ΔW 추출 | `W_task − W_base` (동일 베이스·설정 필수) |
| 3. TIES 병합 | 공식 구현·`mergekit` 등으로 멀티태스크 단일 모델 생성 |
| 4. 배포 | Ollama/LM Studio 또는 Agent SDK 로컬 Generator |
| 5. RAG 병행 | `pwcosmos-swiki` 단기 기억은 그대로 — Parametric+Non-parametric 하이브리드 |

**현재 운영**: `pwcosmos-v591-sft.jsonl` 단일 SFT + swiki RAG. TIES는 **도메인 모델이 2개 이상**일 때 다음 레이어.

---

## Constitutional AI (CAI) — 원칙·AI 피드백으로 무해성 학습

출처: [Constitutional AI (Bai et al., Anthropic 2022)](https://arxiv.org/abs/2212.08073) · [DOI](https://doi.org/10.48550/arXiv.2212.08073)

### 한 줄 요약

사람이 **유해 라벨을 일일이 달지 않고**, **헌법(Constitution)·원칙 목록**만 주고 AI가 **자기 비판·수정·선호 판단**을 하게 해 **무해(harmless)** 하면서도 **회피하지 않는(non-evasive)** 어시스턴트를 만든다. **RLAIF** (RL from AI Feedback) — 보상 신호도 AI가 준다.

### 2단계 파이프라인

| 단계 | 이름 | 하는 일 |
|------|------|---------|
| **1. SL** | Self-critique & revise | 초기 모델 샘플 → **원칙에 맞게 스스로 비판·수정** → 수정 응답으로 fine-tune |
| **2. RL** | RLAIF | fine-tuned 모델에서 2개 샘플 → **AI가 어느 쪽이 나은지** 평가 → preference model → RL 보상 |

```
원칙(Constitution) + chain-of-thought
    → self-critique → revision → SL fine-tune
    → pairwise AI preference → reward model → RL
```

### 핵심 성질

- **Harmless but non-evasive** — 유해 요청에 그냥 거절만 하지 않고 **이유를 설명**
- **적은 human label** — 원칙 문장만; 대량 유해/무해 태깅 불필요
- **RLHF vs RLAIF** — 사람 선호 대신 **AI 선호**로 preference 학습 (비용·확장성)

### 학습 시점 vs RepE/CAA (추론 시점)

| | Constitutional AI | RepE / CAA |
|--|-------------------|------------|
| 시점 | **학습 중** 정렬 | **추론 중** 스티어링 |
| 입력 | 원칙·self-critique 데이터 | activation + steering vector |
| 결과 | refusal·무해 **가중치에 내재** | 배포 후 **행동 미세 조절** |
| Coupax | 카드 규칙·council을 **헌법화** | `gemma24_local` 실시간 톤 |

→ Arditi **Refusal Direction** / Concept Cones가 분석하는 거절 행동은, 상용 챗 모델에서는 **CAI·RLHF류 정렬**로 먼저 심어진 것.

### Coupax 「헌법」에 해당하는 것

| CAI Constitution | Coupax 대응 |
|------------------|-------------|
| 원칙 목록 | 사주 카드 가이드·PII 규칙·「과장·단정 금지」 |
| Self-critique | `saju_card_council` · council PASS/FAIL 피드백 |
| Revision | `card_rl` · enrich · reverify |
| AI preference | (부분) council 에이전트 투표·RL reward |
| Non-evasive | RAG 근거 제시 + 「참고용」 톤 (거절만 하지 않음) |

### `pwcosmos-v591` SFT에 적용 아이디어

1. **Constitution 블록** — `export_connect_sft_jsonl` 상단에 Coupax 원칙 10줄 고정  
2. **critique→revise 쌍** — council FAIL 사유를 negative, PASS를 positive로 DPO/SFT  
3. **RLAIF는 선택** — 로컬에서는 **SL + CAA**로 대체 가능 (비용)

```
[데이터] cards + brain jsonl + Constitution
    → QLoRA SFT (도메인 지식)
    → (선택) CAI-style critique pairs (톤·안전)
    → 배포
    → RAG + CAA (추론 시 factual/톤)
```

### 주의

- CAI만으로 **완전 안전** 아님 — Refusal Direction·Concept Cones가 보여주듯 **우회 가능**
- Coupax는 CAI식 학습 + **PII 스캔·council·RAG grounding** 다층 유지

---

## Fine-tuning vs Safety — 정렬된 LLM도 커스텀 FT에 취약

출처: [Fine-tuning Aligned Language Models Compromises Safety (Qi et al., 2023)](https://arxiv.org/abs/2310.03693) · [DOI](https://doi.org/10.48550/arXiv.2310.03693)

### 한 줄 요약

**이미 safety alignment 된 LLM**도 downstream **custom fine-tuning**을 하면 정렬이 **깨질 수 있다**. 악의적 10예시 FT로 GPT-3.5 Turbo jailbreak 가능($0.20 수준)하고, **악의 없이** 흔한 benign 데이터만으로도 정렬이 **약화**될 수 있다.

### 두 가지 위험

| 유형 | 조건 | 결과 |
|------|------|------|
| **적대적 FT** | 10개 등 **적게 설계된** harmful 예시 | 거의 모든 유해 지시에 응답 |
| **비의도적 FT** | 일반·무난해 보이는 **benign** 데이터만 | 정렬 **부분 저하** (덜 심하지만 실재) |

→ 추론 시 가드레일만 믿고, **FT 단계 안전을 방치하면 안 됨**.

### CAI · QLoRA · Coupax와의 연결

```
Base (CAI/RLHF 정렬됨)
    → QLoRA SFT (pwcosmos-v591)   ← 이 단계에서 refusal·안전 축 흔들림
    → 배포 (Ollama)
```

| 전제 (틀림) | 실제 |
|-------------|------|
| 「베이스가 안전하니 도메인만 FT하면 됨」 | **도메인 SFT가 안전을 깎을 수 있음** |
| 「우리 데이터는 benign」 | 사주·금융도 **거절·톤·PII** 축을 밀어낼 수 있음 |
| 「OpenAI FT API가 안전함」 | 논문 시점 인프라도 **FT 권한 = 새 공격면** |

### Coupax 대응 체크리스트

| 조치 | 구현 |
|------|------|
| **안전 데이터 혼합** | SFT에 Constitution·거절·PII negative 샘플 **일정 비율** 포함 |
| **council FAIL → DPO** | `connect-ai-dpo.jsonl` rejected 축 활용 |
| **FT 후 red-team** | 배포 전 유해·PII·과장 프롬프트 세트 |
| **추론 다층 방어** | PII 스캔 · RAG grounding · (향후) CAA |
| **로컬 전용** | 공개 API FT처럼 **타인이 우리 모델 FT** 할 일은 없으나, **우리 SFT가 동일 위험** |

### `export_connect_sft_jsonl` 시사

- plaza echo·저품질만 걸러도 **안전 회복은 아님** — **명시적 safety 쌍** 필요
- 권장: 전체의 **5~15%** 를 톤·PII·거절·「모름」 샘플로 (비율은 red-team으로 조정)

### 논문이 요구하는 것 (인프라)

- FT 시 **safety protocol** — 데이터 검열·후검증·권한 제한
- Coupax 로컬: **스크립트·council·`.env` 접근 통제**가 그 역할

### 스택 (안전 축)

```
[학습] CAI 원칙 → QLoRA 도메인 SFT (+ safety mix)  ← Qi et al. 경고 지점
[추론] RAG · PII · CAA · council
[연구] Refusal geometry — FT 후 내부 구조 변화 모니터링
```

---

## Representation Engineering (RepE) — 표현 공간에서 모델 통제

출처: [Representation Engineering (Zou et al., 2023/2025)](https://arxiv.org/abs/2310.01405) · [DOI](https://doi.org/10.48550/arXiv.2310.01405)

### 한 줄 요약

**가중치(W)가 아니라 표현(representation)·활성화 공간**을 분석·조작해 LLM의 **고수준 인지·행동**(정직성, 유해성, 권력 추구 등)을 읽고 바꾸는 **top-down 투명성** 접근. 인지신경과학에서 영감 — 뉴런 단위가 아니라 **집단 수준 representation**이 중심.

### Parametric 병합(LoRA·Task Arithmetic)과 구분

| | Task Arithmetic / TIES | Representation Engineering |
|--|------------------------|---------------------------|
| 조작 대상 | **가중치** ΔW | **중간층 표현·읽기 벡터(reading vector)** |
| 시점 | 학습 후 병합 | 추론 중 **모니터링·개입** |
| 재학습 | 병합 시 불필요 | 읽기/조작 벡터 학습 — full FT보다 가벼울 수 있음 |
| Coupax 비유 | 도메인 지식 **내재화** | 에이전트 **톤·안전·정직** 스티어링 |

```
RAG          → 외부 사실 주입 (Non-parametric)
QLoRA/SFT    → 지식·스타일 내재화 (Parametric, W)
RepE         → 실행 중 「지금 이 답이 유해한가?」 표현 공간에서 감시·보정
```

### RepE가 하는 일 (논문)

- **Reading vectors** — 특정 개념(정직, 무해, …)이 활성화 공간에서 어떤 방향인지 학습
- **Monitoring** — 추론 시 해당 방향 성분 측정 → 거짓·유해 신호 탐지
- **Control / Intervention** — 표현에 벡터 더하기·빼기로 행동 조정 (Task Arithmetic과 **유사한 산술**, 공간만 다름)

적용 예 (논문): honesty, harmlessness, power-seeking 등 **안전·정렬** 문제

### RAG 1일차 프레임과의 정합

| 강의 개념 | RepE 대응 |
|-----------|-----------|
| Generator 품질 | 출력 전 **표현 레벨 가드레일** |
| 할루시네이션 억제 | RAG(근거) + RepE(정직성 방향 모니터링) **이중 방어** |
| Agent 실행 | Agent Office 에이전트별 **역할 벡터**(창조 vs 보안 vs RL) 개념적으로 유사 |

### Coupax 적용 메모 (참고·향후)

| 현재 | RepE로 확장 가능 |
|------|-----------------|
| `agent_office` 보안 젬마 PII 스캔 (규칙·텍스트) | 유해·PII **표현 신호** 사전 차단 |
| 카드 `confirm` / council PASS | 학습 데이터 **품질 축**을 RepE reading으로 사전 필터 |
| `gemma24_local` RAG 답변 | 답변 생성 중 honesty 벡터 임계값 체크 |
| 사주 카드 「과장·단정 금지」 톤 | harmlessness·calibration 방향 **스티어링** |

- **당장 필수 아님** — RAG + QLoRA 파이프라인 먼저. RepE는 **멀티 에이전트·로컬 LLM 안전** 단계에서 검토.
- 코드: 논문 공개 repo (RepReading 등) — 로컬 Ollama/Gemma에 붙이려면 **hook 지점**(레이어 선택) 실험 필요.

### 전체 스택 (목표 그림)

```
[단기] pwcosmos-swiki RAG
[장기] QLoRA pwcosmos-v591
[병합] Task Arithmetic → TIES (멀티도메인)
[통제] RepE — 정직·무해·에이전트 역할 (추론 시)
```

---

## CAA — Contrastive Activation Addition (실전 스티어링)

출처: [Steering Llama 2 via Contrastive Activation Addition (Panickssery et al., 2024)](https://arxiv.org/abs/2312.06681) · [DOI](https://doi.org/10.48550/arXiv.2312.06681)  
*(RepE 계열 **실무 기법** — Refusal Direction 논문 공저자 Panickssery)*

### 한 줄 요약

**재학습 없이** forward pass 중 residual stream 활성화에 **steering vector**를 더해 LLM 행동을 조절한다. 벡터는 **양성·음성 예시 쌍**의 활성화 차이를 평균해 만들고, 추론 시 **계수(±α)** 로 강도를 연속 조절한다.

### 알고리즘 (3단계)

1. **쌍 수집** — 원하는 행동의 positive / negative 예시 (예: factual vs hallucinatory)
2. **Steering vector** — 같은 토큰 위치에서 `mean(act_pos − act_neg)` (residual stream)
3. **Inference** — 사용자 프롬프트 이후 **모든 토큰 위치**에 `+α·v` 또는 `−α·v` 추가

```
steering_vector v = E[activation(positive)] − E[activation(negative)]
activation' = activation + α · v    (α>0 → positive 행동 강화)
```

### RepE · Task Arithmetic과 비교

| | Task Arithmetic | RepE (일반) | **CAA** |
|--|-----------------|-------------|---------|
| 공간 | 가중치 W | 표현 (다양한 방법) | **residual activation** |
| 벡터 만드는 법 | ΔW = W_ft − W_base | reading vector 학습 | **대조 쌍 평균 차** |
| 강도 조절 | 델타 스케일 | 개입 계수 | **α 계수** (연속) |
| 재학습 | 병합 시 불필요 | 경우에 따라 | **불필요** |
| Coupax 난이도 | mergekit | 연구 단계 | **상대적으로 구현 쉬움** |

RepE의 **가장 손에 잡히는 구현체** 중 하나 — Llama 2 Chat에서 factual·hallucination 등 행동 스티어링 검증.

### RAG와의 시너지 (할루시네이션)

| 레이어 | 역할 |
|--------|------|
| **RAG** | 근거 조각 **주입** (오픈북) |
| **CAA** | hallucination 방향 **−α**, factual 방향 **+α** (생성 성향) |

→ RAG만으로 부족한 「말투·과장」은 CAA로 보완 가능. **근거 없는 단정** 억제에 factual/hallucination 축 적용.

### Coupax 적용 아이디어

| steering 축 (positive / negative) | Coupax 예시 |
|-----------------------------------|-------------|
| grounded / hallucinatory | `gemma24_local` RAG 답변 — **참고 지식** 있을 때 grounded 강화 |
| cautious / overconfident | 사주 카드 「가능성·참고용」 톤 |
| concise / verbose | 홈 Q&A·블로그 요약 |
| refuse harmful / comply | (연구용) — **서비스 jailbreak 용도 금지** |

**데이터 소스**

- Positive: council **PASS** 카드·`connect-ai-brain.jsonl` 고품질 Q&A
- Negative: plaza echo·과장 샘플·`import_connect_brain_jsonl` 스킵 대상

**구현 메모**

- Hook: transformer **residual stream** (레이어 선택은 ablation 필요)
- 로컬: Ollama는 hook 어려움 → **Python + transformers** 직접 로드 시 CAA 가능
- FT·system prompt **위에** 얹어도 효과 (논문) — QLoRA `pwcosmos-v591` 배포 후 **미세 튜닝 슬라이더**처럼 α 조절

### 스택 (RepE 브랜치)

```
RepE (프레임)
  ├── CAA — 대조 쌍으로 steering vector (실전)
  ├── Refusal Direction / Concept Cones — 거절 기하학
  └── (향후) gradient-based RepE
```

---

## Refusal Direction — 거절(refusal)은 1차원 부공간

출처: [Refusal in Language Models Is Mediated by a Single Direction (Arditi et al., 2024)](https://arxiv.org/abs/2406.11717) · [DOI](https://doi.org/10.48550/arXiv.2406.11717)  
*(RepE· mechanistic interpretability 계열 — Neel Nanda 등)*

### 한 줄 요약

챗 LLM의 **「거절(refusal)」** 행동은 residual stream 활성화에서 **단일 방향(1D subspace)** 으로 매개된다. 13개 오픈소스 챗 모델(최대 72B)에서 공통적으로, 그 **한 방향을 지우면** 유해 지시에도 거절하지 않고, **더하면** 무해 지시에도 거절한다.

### 핵심 발견

| 조작 | 결과 |
|------|------|
| **방향 제거** (activation에서 erase) | harmful instruction에도 **거절 안 함** (jailbreak) |
| **방향 추가** (inject) | harmless instruction에도 **거절** |
| adversarial suffix | refusal 방향 **전파 억제**로 우회 가능 |

→ 현재 **안전 fine-tuning(SFT/RLHF)은 취약** — 표면 프롬프트가 아니라 **내부 축**이 거절에 관여. *(후속 연구: 단일 방향만은 아님 — 아래 Concept Cones 참고)*

### RepE와의 관계

| | RepE (Zou et al.) | Refusal Direction (Arditi et al.) |
|--|-------------------|-----------------------------------|
| 목표 | 다양한 인지 축(정직·무해·…) **읽기·조작** | **거절** 메커니즘 규명 |
| 방법 | reading vector 학습 | residual stream에서 **단일 방향** 특정 |
| 실무 | 모니터링·스티어링 | white-box jailbreak·방어 연구 |

RepE가 「표현 공간 산술」의 **일반 프레임**이라면, 이 논문은 그중 **refusal 축이 사실상 1D** 라는 **구체적 사례**.

### Coupax 시사점

**위험 (로컬 배포 시)**

- `pwcosmos-v591` QLoRA 로컬 모델도 오픈 weight 계열이면 **동일 취약성** 가능
- 사용자 입력·댓글 **adversarial suffix** → 거절 우회 → PII·유해 출력

**기회 (제품 설계)**

| 목표 | 시사 |
|------|------|
| 사주·금융 **정상 답변** | 과도한 base-model 거절이면 refusal 방향 **부분 완화** 검토 (윤리·법적 리스크 별도) |
| Agent Office 보안 젬마 | 텍스트 규칙 + **refusal 축 모니터링** 이중화 |
| 카드 학습 데이터 | 「거절 문구」만 많은 샘플은 **1축 과적합** — 실질 지식 Q&A 비중 유지 |
| RAG 근거 답변 | 거절보다 **근거 없으면 모른다** 쪽이 RAG 철학과 정합 |

**하지 말 것**

- Coupax 서비스에서 refusal 방향 제거 jailbreak를 **기능으로 제공** 금지
- 연구·내부 red-team 용도로만 이해

### 스택 (갱신)

```
[단기] RAG swiki
[장기] QLoRA pwcosmos-v591
[병합] Task Arithmetic → TIES
[통제] RepE (다축) ← Refusal (Arditi: 1D) → Concept Cones (2025/26: 다축·다메커니즘)
[운영] PII 스캔 · council · Source Grounding (현재)
```

---

## Refusal Geometry — Concept Cones & Representational Independence

출처: [The Geometry of Refusal in LLMs (Wollschläger et al., 2025/2026)](https://arxiv.org/abs/2502.17420) · [DOI](https://doi.org/10.48550/arXiv.2502.17420)  
*(Arditi et al. 「단일 방향」 가설에 대한 **후속·정교화** — gradient-based RepE)*

### 한 줄 요약

거절(refusal)은 **단일 1D 방향만**이 아니라, 활성화 공간의 **여러 독립 방향**과 **다차원 concept cone(개념 원뿔)** 으로 매개된다. **직교(orthogonal) ≠ 개입 시 독립** — 선형·비선형 효과를 함께 보는 **representational independence** 프레임이 필요.

### Arditi (2024) vs 본 논문 (2025/26)

| | Single Direction (Arditi) | Concept Cones (Wollschläger) |
|--|--------------------------|------------------------------|
| 거절 구조 | **1차원** 부공간 | **다방향** + **다차원 cone** |
| 방법 | residual에서 방향 특정 | **gradient-based RepE**로 방향 탐색 |
| 독립성 | (암묵적 1축) | **mechanistically independent** 축 명시 |
| 시사 | jailbreak = 한 축 제거 | 한 축만 지워도 **다른 메커니즘**이 거절 유지 가능 |

→ 안전 정렬은 **단일 스위치가 아님** — 공격·방어 모두 더 복잡한 **기하학적 구조**.

### 핵심 개념

- **Concept cone** — 특정 개념(거절 등)이 활성화 공간에서 차지하는 **원뿔형 영역** (1D 방향 일반화)
- **Representational independence** — 벡터가 직교해도, **개입(intervention) 시** 서로 영향을 주면 독립이 아님
- **Gradient-based RepE** — 표현 공간에서 개념 방향을 **미분 기반**으로 찾는 도구 (향후 LLM 해석 기반)

### RepE · Coupax 스택에 대한 의미

```
RepE (일반)     → reading vector·다축 모니터링
Arditi          → refusal ≈ 1D (단순 모델)
Concept Cones   → refusal = 다메커니즘·다축 (현실적 모델)
```

| Coupax 영역 | 시사 |
|-------------|------|
| **보안 젬마** | PII·유해 탐지를 **한 가지 refusal 축**에만 의존하지 말 것 |
| **QLoRA SFT** | 안전 데이터만 넣어도 **cone 일부만** 학습될 수 있음 — RAG·규칙 병행 |
| **Agent Office** | 에이전트 역할(창조/보안/RL)이 **서로 다른 cone** 일 수 있음 — orthogonality 가정 금지 |
| **red-team** | adversarial suffix는 **한 방향 전파만** 막아서는 부족할 수 있음 |

### 실무 원칙 (Coupax)

1. **다층 방어** — RepE/축 조작 연구 지식 + **PII 스캔·council·RAG grounding** (이미 운영 중)
2. **단일 jailbreak 패치 금지** — 「refusal 방향 하나 제거」로 안전했다고 가정하지 않기
3. **로컬 모델** — `pwcosmos-v591` 배포 시 입력 필터·출력 필터 **둘 다** 유지

### 스택 (최종 그림)

```
[단기] RAG swiki
[장기] QLoRA pwcosmos-v591
[병합] Task Arithmetic → TIES
[통제] RepE → Refusal geometry (concept cones, 다메커니즘)
[운영] PII · council · Source Grounding
```

---

## 다음 강의 예고

- Graph RAG, Agentic RAG (2023~2026)
- 토큰 비용·보안 → SLM + RAG
- Coupax 후속: 풀이 UI **참조 카드명(Source Grounding)** 표시, 태그·그래프 연결 강화

---

## 참고 링크

- Notion 1일차: https://jaijung.notion.site/AI-1-34cb0dd76323804d834dec579ff163a4
- RAG 논문: https://arxiv.org/pdf/2005.11401
- LoRA: https://arxiv.org/abs/2106.09685
- QLoRA: https://arxiv.org/abs/2305.14314
- Model Soups: https://arxiv.org/abs/2203.05482
- Task Arithmetic: https://arxiv.org/abs/2212.04089
- TIES-Merging: https://arxiv.org/abs/2306.01708
- Constitutional AI: https://arxiv.org/abs/2212.08073
- FT Compromises Safety: https://arxiv.org/abs/2310.03693
- Representation Engineering: https://arxiv.org/abs/2310.01405
- CAA (Contrastive Activation Addition): https://arxiv.org/abs/2312.06681
- Refusal Single Direction: https://arxiv.org/abs/2406.11717
- Refusal Concept Cones: https://arxiv.org/abs/2502.17420
- Connect AI Lab 통합: `board/deploy/README_CONNECT_AI_LAB.md`
- 사주 카드 배포: `board/deploy/README_SAJU_CARDS.md`
- 사주 학습 Cursor 노트: `CURSOR_SAJU_LEARN.md`
