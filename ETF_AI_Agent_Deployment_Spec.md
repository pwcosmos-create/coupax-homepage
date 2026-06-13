# 🚀 [프로젝트 젬마24] 커스텀 ETF 로컬 AI 24시간 서버 구동 명세서

본 문서는 **프로젝트 '젬마24 (Gemma24)'**의 일환으로, 구글 코랩에서 ETF 도메인 지식으로 파인튜닝된 `gemma-2-2b.Q4_K_M.gguf` 커스텀 모델을 오라클 클라우드 신서버(168.107.31.153)에 이관하고, 24시간 자율 에이전트 시스템으로 연동하기 위한 시스템 구성 및 실행 가이드입니다.

---

## 1. 시스템 및 서버 구축 현황

* **서버 IP:** `168.107.31.153` (Oracle ARM A1 Flex Instance)
* **운영체제:** Ubuntu 22.04 LTS
* **SSH 접속 계정:** `ubuntu` (키 파일: `C:\Users\pwcos\.ssh\shinserver.key`)
* **로컬 LLM 엔진:** Ollama (`v0.1.x` 이상)
* **Ollama 서비스 포트:** `11434` (내부 API 통신용)
* **모델 저장 경로:** `/home/ubuntu/llm_models/gemma-2-2b.Q4_K_M.gguf`

---

## 2. 커스텀 모델(ETF-Gemma 2B) 상세 제원

* **베이스 모델:** Google Gemma 2 (2B Parameters)
* **양자화 방식:** Q4_K_M (4-bit Quantization, 정확도와 속도/메모리의 최적 균형)
* **파일 용량:** 약 1.67 GB (오라클 무료 ARM 서버의 24GB RAM 환경에서 초고속 구동 가능)
* **Ollama 등록 모델명:** `etf_gemma:2b`

---

## 3. Ollama Modelfile 구성 (템플릿 및 정지 토큰)

Gemma 2 모델의 무한 반복 출력 방지 및 완벽한 대화 턴(Turn) 제어를 위해 서버의 `/home/ubuntu/llm_models/Modelfile`에 아래와 같이 프롬프트 템플릿과 정지(Stop) 토큰이 적용되었습니다.

```dockerfile
FROM ./gemma-2-2b.Q4_K_M.gguf
TEMPLATE """<start_of_turn>user
{{ if .System }}{{ .System }}
{{ end }}{{ .Prompt }}<end_of_turn>
<start_of_turn>model
{{ .Response }}<end_of_turn>"""
PARAMETER stop "<start_of_turn>"
PARAMETER stop "<end_of_turn>"
```

### 서버에서 수동 모델 재생성 및 업데이트 시 명령어
```bash
cd /home/ubuntu/llm_models
ollama create etf_gemma:2b -f Modelfile
```

---

## 4. 자율 에이전트 연동 (Connect AI Lab 연동 규격)

서버 내에서 동작하는 파이썬 자율 에이전트 또는 백엔드 애플리케이션은 Ollama의 표준 REST API(`http://localhost:11434/api/generate` 또는 `api/chat`)를 통해 커스텀 ETF 모델을 호출할 수 있습니다.

### 파이썬(Python) 연동 예제 코드 (`test_query.py`)

```python
import urllib.request
import json

def ask_etf_ai(prompt_text):
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "etf_gemma:2b",
        "prompt": prompt_text,
        "stream": False,
        "options": {
            "temperature": 0.3, # ETF 금융 지식의 정확성을 높이기 위해 낮게 설정
            "top_p": 0.9
        }
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['response']
    except Exception as e:
        return f"AI 연동 에러 발생: {str(e)}"

# 실행 테스트
if __name__ == "__main__":
    question = "ETF 투자에서 분배금(배당금)이란 무엇이며 어떻게 활용해야 하나요?"
    print(f"[질문]: {question}\n")
    answer = ask_etf_ai(question)
    print(f"[AI 답변]:\n{answer}")
```

---

## 5. 향후 유지보수 및 24시간 자율주행 관리

1. **Ollama 서비스 모니터링:**
   서버 부팅 시 Ollama가 자동으로 백그라운드에서 실행되도록 설정되어 있습니다. 상태 확인은 아래 명령어로 수행합니다.
   ```bash
   sudo systemctl status ollama
   ```
2. **로그 확인:**
   모델의 응답 속도 및 오류 로그는 시스템 저널을 통해 실시간 확인 가능합니다.
   ```bash
   journalctl -u ollama -f
   ```
3. **지식 데이터셋(JSONL) 추가 파인튜닝:**
   새로운 ETF 종목이나 규정이 변경될 경우, `etf_training_data.jsonl`에 데이터를 추가한 뒤 코랩에서 동일한 과정으로 학습하고 `.gguf` 파일만 서버로 교체 업로드하면 즉시 지식이 갱신됩니다.
