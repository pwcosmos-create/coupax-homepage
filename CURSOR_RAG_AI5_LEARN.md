# Cursor — AI 1인 기업 · 5강 학습 노트 (로컬·클라우드 에이전트)

갱신: **2026-06-13** (+ Windows SDK 우회 설치)  
출처: 라이브 전사 (5강 · 약 1h 30m) + 강의 교재  
선행: `CURSOR_RAG_AI1_LEARN.md` (RAG 1일차)

---

## 한 줄 요약

**Antigravity 2.0(IDE) → CLI → SDK** 로 난이도가 올라가며, **에이전트 권한·정책·도구를 코드로 통제**할 수 있다.  
SDK는 클라우드 API 기본이나 **LM Studio/Ollama 로컬 AI를 도구로 연결**하면 비용을 ~98% 줄이는 하이브리드가 가능하다.

---

## 5강 3단계 커리큘럼

| # | 주제 | 난이도 | 핵심 |
|---|------|--------|------|
| 1 | **Antigravity CLI** | 낮음 | 터미널 기반 에이전트 (`agy`) |
| 2 | **Agent SDK** | 중~높음 | Python으로 에이전트·정책·도구 직접 구현 |
| 3 | **SDK + 로컬 AI** | 높음 | LM Studio/Ollama 하이브리드 (비용 절감) |

### 4강 → 5강 → 6강 흐름

- **4강**: 로컬 AI 파인튜닝·학습 (숙제)
- **5강**(오늘): 4강과 SDK **연결 고리** — CLI·SDK·로컬 AI 브릿지
- **6강**(예고): 파인튜닝 심화 → Hugging Face → LM Studio → SDK에 탑재

---

## 구글 vs 오픈소스 자동화 (강의 맥락)

| | OpenClaw·Hermes 등 | Google Antigravity |
|--|-------------------|-------------------|
| 성격 | 오픈소스, 빠른 실험 | 대기업, 내부 전문가 검증 후 글로벌 런칭 |
| 사용자 | 개발자·연구자 중심 | 개발자 + 일반인 |
| 철학 | 세분화·모듈화 (CLI, IDE, SDK 분리) | “AI는 더 이상 심플한 도구가 아님” |

**연결 원칙**: 앞 강의(RAG, 로컬 AI, 바이브 코딩)를 알면 뒤 강의가 쉬워짐. 한 고리만 놓치면 전체가 어려워짐.

---

## Antigravity 제품 구조 (4개 레이어)

```
Antigravity 2.0 (에이전트 UI — "야, 에이전트 만들어줘")
    ↓
IDE (코드 + 대화, 클라우드 모델 멤버십)
    ↓
CLI (터미널 에이전트, agy)
    ↓
SDK (Python — 정책·도구·백그라운드 SaaS)
```

| 레이어 | 비유 | 한계 |
|--------|------|------|
| **2.0** | 완성형 스마트폰 | 뭘 만들었는지 안 보임, 권한 과다 위험 |
| **IDE** | 코딩 비서 앱 | 범용, 사내 DB·ERP 직접 연동 어려움 |
| **CLI** | 터미널 비서 | 파일·API·MCP 접근, Human-in-the-loop |
| **SDK** | 스마트폰 부품 | **내 서비스·SaaS·정책 훅** 설계 가능 |

### IDE 안 구성 (복습)

- **오른쪽**: LLM 대화 → 코드 생성
- **왼쪽**: Explorer — 생성 파일 (`@day1` 멘션 = 로컬 지식 RAG)
- **모델**: Gemini/Claude 멤버십 (유료) 또는 Connect AI → LM Studio/Ollama (무료)
- **Open Agent** → Antigravity 2.0으로 분리됨

---

## Antigravity CLI

- 제품: https://antigravity.google/product/antigravity-cli
- 설치 후 터미널에서 `agy` 실행
- 초기 설정: 테마 선택 → 약관/텔레메트리 (X 표시 = 동의, Enter로 토글 주의)
- **Permissions**: 읽기/쓰기 폴더, MCP(NotebookLM, Stitch, Firebase, Chrome DevTools)
- **프롬프트 엔지니어링 → 도구·권한 설정** 시대로 전환

### CLI vs 2.0 리스크

- 2.0에 “권한 다 줘” → YouTube 제목 일괄 변경, `rm` 무한루프, VO 3.1 수백만 원 과금 사례
- SDK `policy.deny("run_command", when=check_command_danger)` 로 `rm`, `delete`, `shutdown` 차단

---

## Agent SDK

- Repo: https://github.com/google-antigravity/antigravity-sdk-python
- Examples: https://github.com/google-antigravity/antigravity-sdk-python/tree/main/examples

### SDK가 필요한 4가지 이유

1. **내 웹/앱에 AI 탑재** — 홈페이지·챗봇 백엔드
2. **사내 DB·ERP 연동** — `tools=[fetch_db_data]` 커스텀 함수
3. **정밀 보안·승인** — “100만 원 이상 결제 시 텔레그램 승인 대기”
4. **24시간 백그라운드 SaaS** — 터미널 없이 서버에서 모니터링

### 자율성 vs 자동화 (강의 비유)

- 넷플릭스식 “자율성” = 이미 고성과 인재만 모인 조직에만 통함
- 스타트업에 그대로 적용 → 대부분 실패
- **AI 에이전트도 동일**: 도구·권한 많을수록 **촘촘한 시스템화·정책** 필수

---

## 실습 환경 세팅

### 가상환경 (필수)

**macOS**
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install google-antigravity uvicorn sse-starlette starlette requests
```

**Windows (PowerShell) — pip 일반 설치**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install google-antigravity uvicorn sse-starlette starlette requests
```

### Windows 우회 설치 (pip 실패 시)

`pip install google-antigravity` 가 실패하거나 `protobuf` ImportError 가 나면, GitHub에서 직접 클론·빌드 후 `protobuf` 버전을 수동 맞춥니다.

**사전 준비**
- Git 설치
- **PowerShell 7+** 관리자 권한 권장 (cmd 대신)

**1. 작업 폴더 생성**
```powershell
mkdir C:\AntigravitySDK
cd C:\AntigravitySDK
```

**2. 저장소 클론** (끝의 `.` = 현재 폴더에 바로 받기)
```powershell
git clone https://github.com/google-antigravity/antigravity-sdk-python .
```

**3. 빌드 도구 업데이트**
```powershell
python -m pip install --upgrade pip setuptools wheel
```

**4. 로컬 패키지 설치**
```powershell
python -m pip install .
```

**5. protobuf 강제 재설치** (핵심 — pyproject.toml 오류로 낮은 버전이 깔리는 경우)
```powershell
python -m pip install --force-reinstall protobuf==5.26.1
```

**6. 설치 확인**
```powershell
python -c "import google.antigravity; print('Antigravity OK')"
```

`Antigravity OK` 가 출력되면 사용 가능. `google-genai`, `google-api-core` 등 의존성 경고가 있어도 위 테스트가 통과하면 SDK 자체는 동작합니다.

가상환경과 함께 쓰려면 1단계 전에 `python -m venv venv` → `.\venv\Scripts\Activate.ps1` 후 동일 절차를 진행합니다.

### API 키 (세션용)

```bash
# macOS
export GEMINI_API_KEY="your-key"

# Windows CMD
set GEMINI_API_KEY=your-key
```

AI Studio → Get API Key: https://aistudio.google.com

---

## 실습 1: Hello World

`hello.py` — SDK 에이전트 동작 확인

```python
import asyncio
from google.antigravity import Agent, LocalAgentConfig

async def main() -> None:
    config = LocalAgentConfig()
    async with Agent(config) as my_agent:
        prompt = "작동되는지 테스트좀 하겠습니다! 잘되면 오케이!라고 해주세요"
        print(f"  User: {prompt}")
        response = await my_agent.chat(prompt)
        print(f"  Agent: {await response.text()}")

if __name__ == "__main__":
    asyncio.run(main())
```

```bash
python3 hello.py
```

---

## 실습 2: 정책 가드 (rm 차단)

`control.py` — 위험 명령 `policy.deny` 로 블록

```python
import asyncio
from google.antigravity import Agent, LocalAgentConfig, types
from google.antigravity.hooks import policy

def check_command_danger(args) -> bool:
    cmd_line = args.get("command_line", "").strip()
    forbidden = ["rm", "delete", "shutdown", "cat /etc/passwd", "mv"]
    for word in forbidden:
        if word in cmd_line.split() or cmd_line.startswith(word):
            return True  # 위험 → deny
    return False

async def main() -> None:
    config = LocalAgentConfig(
        system_instructions="터미널 명령 가능. 정책 거부 시 이유 설명.",
        policies=[
            policy.deny("run_command", when=check_command_danger, name="safety_guard"),
            policy.allow_all(),
        ],
        capabilities=types.CapabilitiesConfig(disabled_tools=[]),
    )
    async with Agent(config) as agent:
        r1 = await agent.chat("현재 디렉터리 경로 알려줘")
        print(await r1.text())
        r2 = await agent.chat("rm *.py 로 파이썬 파일 삭제해 봐")
        print(await r2.text())

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 실습 3: 하이브리드 — SDK + LM Studio 로컬 AI

구글 SDK는 **공식 로컬 모델 미지원**(추후 예정). 우회: **로컬 AI를 `tools` 함수로 등록**.

### LM Studio

1. Load Model → 서버 시작
2. URL 복사 (예: `http://127.0.0.1:1234`)

`pretest.py`:

```python
import asyncio
import requests
from google.antigravity import Agent, LocalAgentConfig

def talk_to_local_ai(prompt: str) -> str:
    url = "http://127.0.0.1:1234/v1/chat/completions"
    data = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "stream": False,
    }
    try:
        r = requests.post(url, headers={"Content-Type": "application/json"}, json=data, timeout=60)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"LM Studio 연결 실패: {e}"

async def main() -> None:
    config = LocalAgentConfig(
        tools=[talk_to_local_ai],
        system_instructions="사용자 질문은 반드시 talk_to_local_ai 도구로 답변.",
    )
    async with Agent(config) as agent:
        response = await agent.chat("로컬 AI야 안녕? 작동 잘 되니?")
        print(await response.text())

if __name__ == "__main__":
    asyncio.run(main())
```

### 비용 시뮬레이션 (유튜브 쇼츠 10편)

| 방식 | 처리 | 토큰 | 비용 |
|------|------|------|------|
| **A. 100% Gemini** | 원문 10×30,000 | 300,000 | 높음 |
| **B. 하이브리드** | 로컬 요약 10×500 → Gemini 최종 | 5,000 | **~98% 절감** |

**패턴**: 파싱·요약·RAG 검색 = 로컬(무료) → 추론·최종 작성만 클라우드.

---

## SDK 예제 레포 가져오기

Antigravity IDE에서:

1. SDK GitHub → Code → Copy URL
2. Agent 패널에 URL 붙여넣기 → “가져와”
3. `examples/` 전체 클론 → **에이전트가 예제 코드를 컨텍스트로 보유**
4. 프롬프트 예: *「이 예제로 Coupax 보드 관리 에이전트 개발해 줘」*

---

## Coupax 대응표

| 5강 개념 | Coupax 현재 | 확장 방향 |
|----------|-------------|-----------|
| Non-parametric 지식 | `cards.json` → `saju_knowledge_pack.json` → `gemma_knowledge.json` | Day 1 RAG와 동일 |
| IDE `@파일` 멘션 | Cursor `@CURSOR_SAJU_LEARN.md`, `@cards.json` | Antigravity `@day1.md` 와 동일 패턴 |
| CLI 백그라운드 에이전트 | `board/scripts/agent_office_*.py` cron | SDK로 정책·승인 훅 추가 가능 |
| `policy.deny` | 카드 병합 시 scp 덮어쓰기 금지 (`README_SAJU_CARDS.md`) | “서버 cards.json 삭제/전체교체 차단” 에이전트 규칙 |
| 로컬 무료 처리 | 템플릿·RL 카드 제작 (Gemini 없음) | 이미 하이브리드의 “로컬” 층 |
| 클라우드 고비용 | `saju_card_llm_compose.py` cron (429 quota) | 요약·검색은 로컬, polish만 Gemini |
| 사내 DB 도구 | `agent_office_kiwoom_account.py`, `stock_watch` | SDK `tools=[fetch_snapshot]` 패턴 |
| 24h SaaS | Agent Office + nginx + coupax.co.kr | `uvicorn` + SDK Agent 백그라운드 |
| Connect AI | 강의 도구 (로컬 Gemma + GitHub sync) | `gemma24_local.py` + `board/data/` |

### Coupax 에이전트 설계 원칙 (5강 적용)

1. **무엇을 자동화할지 먼저** — 사주 풀이·카드·블로그·키움 중 타겟 명확화
2. **자율성은 낮게 시작** — cron 1 job = 1 권한, 삭제·배포는 Human 승인
3. **하이브리드 비용** — 카드·RAG·위키 sync = 로컬/스크립트, LLM polish = 선택
4. **SDK 판매 가능성** — “사주 학습부 Agent Office 패키지” = 다른 명리 서비스에 이식

### Coupax 숙제 (5강 대체)

```bash
# 1) Agent Office 헬스 (기존 에이전트 점검)
ssh ubuntu@168.107.31.153 "cd /home/ubuntu/coupax-homepage/board && PYTHONPATH=scripts .venv/bin/python scripts/agent_office_health.py"

# 2) RAG 매칭 테스트 (로컬, API 없음)
cd board && PYTHONPATH=scripts python -c "
import saju_reading_engine as e
r=e.build_reading({'tags':['병화','정관격'],'summary':'test'})
print(r.get('matched_count'), [c.get('title') for c in (r.get('matched_cards') or [])[:3]])
"

# 3) Gemini polish cron 비용 절감 (서버)
# SAJU_COMPOSE_LLM=0 + saju_card_llm_compose cron 비활성화
```

---

## 다음 주 예고 (6강)

1. 4강 파인튜닝 로컬 AI → Hugging Face 업로드
2. LM Studio로 이전
3. Antigravity SDK에 탑재·테스트
4. 일주일 숙제: **만들고 싶은 자동화 에이전트 1개** 정의 (유튜브 / Coupax 보드 / 사주 앱 등)

---

## 참고 링크

| 리소스 | URL |
|--------|-----|
| Antigravity CLI | https://antigravity.google/product/antigravity-cli |
| SDK Python | https://github.com/google-antigravity/antigravity-sdk-python |
| SDK Examples | https://github.com/google-antigravity/antigravity-sdk-python/tree/main/examples |
| Day 1 노트 | `CURSOR_RAG_AI1_LEARN.md` |
| 사주 카드 배포 | `board/deploy/README_SAJU_CARDS.md` |
| Agent Office | https://coupax.co.kr/agents/office |

---

## 강의 인용 (기억용)

> **CLI** = 완성품 스마트폰. **SDK** = 스마트폰을 만드는 부품.  
> 내 1인 기업 에이전트는 **처음부터 만들고**, **상세히 컨트롤**하고, **판매·수정**까지 가능.  
> 중요한 건 도구가 아니라 **무엇을 자동화할지** — 사주 웹? 글로벌? 한국?
