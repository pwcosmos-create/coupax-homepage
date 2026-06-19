"""
관상 지식을 읽어와 로컬 Gemma 모델을 통해 Q&A(SFT) 데이터셋으로 증강하는 스크립트.
결과물은 Colab의 Unsloth 학습에 바로 사용 가능한 connect-ai-brain.jsonl 로 저장됩니다.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

BOARD = Path(__file__).resolve().parents[1]
_SCRIPTS = BOARD / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import agent_office_wiki_store as wiki_store

OUT_FILE = BOARD / "data" / "pwcosmos-swiki" / "connect-ai" / "connect-ai-brain.jsonl"

def call_local_llm(prompt: str) -> str | None:
    url = os.environ.get("GEMMA_OLLAMA_URL", "http://127.0.0.1:11434/api/generate").strip()
    model = os.environ.get("GEMMA_OLLAMA_MODEL", "gemma4:e2b-16k").strip()
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
        },
    }
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("response", "")
    except Exception as e:
        print(f"[LLM Error] {e}")
        return None

def generate_qa_pairs(card: dict) -> list[dict]:
    title = card.get("title", "")
    body = card.get("summary", "") + "\n" + card.get("body", "")
    
    # We ask the LLM to generate exactly a JSON array
    prompt = f"""<start_of_turn>user
당신은 관상학 데이터를 학습용 질의응답(Q&A) 데이터셋으로 변환하는 전문가입니다.
주어진 [지식]을 바탕으로, AI 모델을 똑똑하게 학습시키기 위한 다양한 관점의 Q&A 2개를 작성해주세요.
'앵무새(Echo)' 현상을 막기 위해 똑같은 문장을 베끼지 말고 자연스러운 대화체로 풀어서 질문과 답변을 구성하세요.

반드시 아래 JSON 배열 형식으로만 대답하세요. 다른 설명은 절대 추가하지 마세요.
[
  {{"q": "질문1", "a": "답변1"}},
  {{"q": "질문2", "a": "답변2"}}
]

[지식]
제목: {title}
내용:
{body[:2000]}
<end_of_turn>
<start_of_turn>model
"""
    response = call_local_llm(prompt)
    if not response:
        return []
    
    # JSON 파싱 시도
    match = re.search(r"\[\s*\{.*?\}\s*\]", response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
            
    return []

def main():
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    print("🚀 [1/3] 관상(gwansang) 지식 카드 로드 중...")
    data = wiki_store.load_knowledge()
    
    gwansang_cards = []
    for w in data.get("wiki", []):
        if not isinstance(w, dict):
            continue
        domain = wiki_store.wiki_domain(w)
        tags = w.get("tags", [])
        title = w.get("title", "")
        # domain 이 관상이거나, 태그나 제목에 관상이 포함된 경우 추출
        if domain == wiki_store.DOMAIN_GWANSANG or "관상" in tags or "관상" in title:
            gwansang_cards.append(w)
            
    print(f"✅ 총 {len(gwansang_cards)}개의 관상 카드를 찾았습니다.")
    if not gwansang_cards:
        print("생성할 카드가 없습니다. 종료합니다.")
        return

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"🚀 [2/3] 로컬 Gemma 4 모델을 통한 Q&A 증강 시작... (이 작업은 시간이 걸릴 수 있습니다)")
    
    success_count = 0
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        # 진행 상황 확인을 위해 최대 10개만 먼저 샘플로 돌려보기 (원한다면 나중에 더 돌려도 됨)
        for i, card in enumerate(gwansang_cards):
            print(f"   [{i+1}/{len(gwansang_cards)}] '{card.get('title', 'Unknown')}' 처리 중...")
            qa_list = generate_qa_pairs(card)
            
            for qa in qa_list:
                q = qa.get("q", "").strip()
                a = qa.get("a", "").strip()
                if not q or not a:
                    continue
                
                # Unsloth/HuggingFace 데이터셋 포맷 (conversations)
                record = {
                    "conversations": [
                        {"role": "user", "content": q},
                        {"role": "assistant", "content": a}
                    ]
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                success_count += 1

    print(f"🚀 [3/3] 변환 완료! 총 {success_count}개의 Q&A 세트가 생성되었습니다.")
    print(f"📂 저장 경로: {OUT_FILE}")
    print("이제 이 JSONL 파일을 구글 코랩에 업로드하여 학습을 시작할 수 있습니다!")

if __name__ == "__main__":
    main()
