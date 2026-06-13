"""수석 개발자실 다중 젬마 LLM 토론 생성기."""
from __future__ import annotations

import json
import os
import random
import urllib.error
import urllib.request

def _ollama_enabled() -> bool:
    return os.environ.get("GEMMA_OLLAMA_ENABLED", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )

def generate_debate_card(topic: str, context: str) -> tuple[str, str]:
    """
    주어진 주제(topic)와 문맥(context)에 대해 로컬 LLM을 호출하여 
    프론트엔드/백엔드/데브옵스 관점의 토론 내용과 결론을 생성합니다.
    (title, body) 반환
    """
    if not _ollama_enabled():
        return f"{topic} 분석 결과", f"LLM이 비활성화되어 기본 텍스트를 반환합니다.\n문맥: {context}"

    url = os.environ.get("GEMMA_OLLAMA_URL", "http://127.0.0.1:11434/api/generate").strip()
    model = os.environ.get("GEMMA_OLLAMA_MODEL", "gemma2:2b").strip()
    
    prompt = f"""<start_of_turn>user
당신은 쿠팩스(coupax) 서비스의 수석 개발자 젬마(AI) 위원회입니다.
다음에 제시된 주제에 대해 '수석 아키텍트', '프론트엔드/RAG 전문가', 'DevOps 관리자' 3명의 관점에서 토론하고 최종 결론을 200자 이내로 요약해 주세요.
응답 형식:
【토론 주제】 (주제 요약)
【수석 아키텍트의 의견】 ...
【RAG 전문가의 의견】 ...
【DevOps의 의견】 ...
【최종 결론】 ...

주제: {topic}
관련 컨텍스트: {context}
<end_of_turn>
<start_of_turn>model
"""

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.6,
            "top_p": 0.9,
        },
    }
    timeout = 60

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        text = (data.get("response") or "").strip()
        if not text or len(text) < 30:
            return f"{topic} 리뷰 완료", f"에이전트들이 분석을 마쳤습니다. (응답이 너무 짧습니다)\n문맥: {context}"
            
        title_lines = text.split("\n", 1)
        title = title_lines[0].replace("【토론 주제】", "").replace("【", "").replace("】", "").strip()[:50]
        if not title:
            title = f"{topic}에 대한 에이전트 토론"
        
        return title, text
        
    except Exception as e:
        return f"{topic} (LLM 호출 실패)", f"에이전트 토론 중 오류가 발생했습니다: {e!s}\n문맥: {context}"

def get_random_topic(job_type: str) -> tuple[str, str, str]:
    """job_type에 따른 (tag, topic, context) 반환"""
    topics = {
        "chief_arch_review": [
            ("React, 아키텍처", "가계부 앱 컴포넌트 분리 전략", "App.jsx에 집중된 상태 관리를 Context API나 Zustand로 분리하는 방안"),
            ("아키텍처, 성능", "대용량 리스트 렌더링 최적화", "화면에 렌더링되는 수백 개의 카드 요소를 가상화(Virtualization)하여 렌더링 성능을 높이는 방안"),
            ("백엔드, 설계", "마이크로서비스 도입 타당성", "현재 단일 Flask 서버로 운영되는 구조를 역할별(블로그, 대시보드, RAG)로 분리할지 논의"),
        ],
        "chief_rag_crawler": [
            ("RAG, 벡터DB", "Pinecone 검색 속도 최적화", "현재 45ms 응답속도를 20ms 이하로 단축하기 위한 하이브리드 서치 도입 방안"),
            ("프론트엔드, 문서", "React 19 Server Components 적용", "새로 크롤링된 React 19 공식 문서를 바탕으로 Server Components를 가계부 앱에 부분 도입하는 전략"),
            ("RAG, 품질", "환각(Hallucination) 방지 프롬프트", "RAG 응답 시 없는 사실을 지어내는 현상을 막기 위한 프롬프트 엔지니어링 전략"),
        ],
        "chief_devops_monitor": [
            ("DevOps, 서버", "Gunicorn 워커 개수 최적화", "현재 2개인 워커 수를 Oracle Cloud 메모리 여유분에 맞추어 4개로 늘릴 때의 장단점"),
            ("보안, 취약점", "의존성 패키지 정기 업데이트", "최신 CVE 취약점 데이터베이스 스캔 결과 발견된 일부 오래된 패키지의 일괄 업데이트 전략"),
            ("DevOps, CI/CD", "GitHub Actions 파이프라인 단축", "현재 3분 걸리는 빌드 및 배포 파이프라인 속도를 캐싱을 통해 1분 내외로 단축하는 방안"),
        ],
        "chief_web_search": [
            ("Tech Radar, 프론트엔드", "Vite 5.0 빌드 성능 향상", "최신 Vite 5.0 릴리즈 노트를 바탕으로, Webpack을 대체할 때 얻는 구체적인 이점"),
            ("Tech Radar, CSS", "Tailwind vs Vanilla CSS", "컴포넌트 재사용성이 높은 디자인 시스템에서 어떤 방식의 스타일링이 유지보수에 더 유리한지"),
            ("Tech Radar, 인프라", "서버리스 데이터베이스 동향", "최근 각광받는 서버리스 DB를 현재 사이드 프로젝트에 도입할 때의 비용 및 성능 이점"),
        ]
    }
    pool = topics.get(job_type, topics["chief_arch_review"])
    return random.choice(pool)
