# Connect AI Lab ↔ Coupax 통합

Connect AI Lab(`Desktop\connect ai lab`) 지식을 Coupax RAG·학습 카드·swiki와 연결합니다.

## 구성

| 스크립트 | 역할 |
|----------|------|
| `scripts/import_connect_brain_jsonl.py` | `connect-ai-brain.jsonl` → `gemma_knowledge.json` |
| `scripts/sync_connect_ai_lab.py` | brain + CURSOR md + swiki + pack export |
| `deploy/sync_connect_ai_lab_windows.ps1` | Windows 일괄 실행 |
| `deploy/install_swiki_sync_cron.sh` | 서버 swiki 15분 sync |
| `deploy/uninstall_saju_gemini_compose_cron.sh` | Gemini polish cron 제거 |

## Windows (로컬)

```powershell
cd board
.\deploy\sync_connect_ai_lab_windows.ps1
```

또는:

```powershell
$env:CONNECT_AI_LAB_PATH = "$env:USERPROFILE\Desktop\connect ai lab"
$env:PYTHONPATH = "scripts"
python scripts/sync_connect_ai_lab.py full --skip-swiki
```

## 서버

`board/.env`:

```env
SAJU_COMPOSE_LLM=0
SWIKI_SYNC_ENABLED=1
SWIKI_GIT_TOKEN=ghp_...
CONNECT_AI_LAB_PATH=/path/if/server/has/lab
```

```bash
bash deploy/uninstall_saju_gemini_compose_cron.sh
bash deploy/install_swiki_sync_cron.sh
cd board && PYTHONPATH=scripts .venv/bin/python scripts/sync_connect_ai_lab.py full
```

## Agent Office

- POST `/api/agents/office/connect-ai-lab-sync` (로그인 필요) — 수동 full sync
- GET `/api/gemma/knowledge-hits?q=연금저축` — RAG 매칭 미리보기

## 답변 출처

`gemma24_local.format_knowledge_sources()` — 홈 Q&A·Ollama 답변 하단에 `참고 지식: ...` 표시

## Lab PC sync (기존)

`Desktop\connect ai lab\sync\pc-on.ps1` — lab ↔ GitHub  
Coupax `agent_office_swiki_sync.py` — swiki ↔ `gemma_knowledge.json`
