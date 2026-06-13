"""에이전트 부서 간 융합 토론 위원회 (Crossover Council)"""
from __future__ import annotations

import json
import os
import random
import urllib.error
import urllib.request
from datetime import datetime

def _ollama_enabled() -> bool:
    return os.environ.get("GEMMA_OLLAMA_ENABLED", "1").strip().lower() not in ("0", "false", "no")

def run_crossover_debate() -> tuple[bool, str]:
    """프론트엔드 + 디자인 + UX 라이터 부서간 합동 회의"""
    if not _ollama_enabled():
        return False, "LLM이 비활성화되어 융합 토론을 건너뜁니다."

    url = os.environ.get("GEMMA_OLLAMA_URL", "http://127.0.0.1:11434/api/generate").strip()
    model = os.environ.get("GEMMA_OLLAMA_MODEL", "gemma2:2b").strip()
    
    topics = [
        ("사주 운세 결과 페이지 UI 개편", "모바일 환경에서 운세 결과를 어떻게 가독성 있게 보여주면서 렌더링 속도도 챙길 것인가?"),
        ("주식 매매 에러 알림 화면", "에러 발생 시 사용자에게 겁을 주지 않으면서도 개발자가 원인을 파악하기 쉽게 UI와 문구를 어떻게 짤 것인가?"),
        ("다크 모드 전환 최적화", "사용자가 다크 모드로 전환할 때 깜빡임(FOUC)을 막는 프론트엔드 기법과 어울리는 디자인 색상표는?")
    ]
    
    title_topic, context = random.choice(topics)
    
    prompt = f"""<start_of_turn>user
당신은 쿠팩스(coupax) 서비스의 '융합 토론 위원회'입니다.
다음에 제시된 주제에 대해 [수석 개발자 젬마], [홈페이지 디자인 젬마], [UX 라이터 젬마(블로그)] 3개 부서의 에이스들이 합동 회의를 진행해 주세요.
응답 형식:
【토론 주제】 (요약)
【수석 개발자의 의견】 ...
【홈페이지 디자인의 의견】 ...
【UX 라이터의 의견】 ...
【최종 융합 결론】 ...

주제: {title_topic}
관련 컨텍스트: {context}
<end_of_turn>
<start_of_turn>model
"""

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7, "top_p": 0.9},
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        text = (data.get("response") or "").strip()
        if len(text) > 30:
            import agent_office_chief_dev_learn as cdl
            title_lines = text.split("\\n", 1)
            title = title_lines[0].replace("【토론 주제】", "").replace("【", "").replace("】", "").strip()[:50]
            if not title:
                title = f"융합 토론: {title_topic}"
            
            cdl.add_card("융합, 크로스오버", title, text)
            
            # 텔레그램 알림 발송
            try:
                import alert_notifier
                alert_notifier.send_telegram_alert(
                    "융합 토론 완료",
                    f"[{title_topic}] 주제로 부서 간 합동 회의가 완료되어 지식 카드로 저장되었습니다.",
                    "🤝 융합"
                )
            except Exception:
                pass
                
            return True, f"융합 토론 저장 완료: {title}"
            
    except Exception as e:
        return False, f"융합 토론 중 오류 발생: {e!s}"
        
    return False, "알 수 없는 이유로 토론에 실패했습니다."

if __name__ == "__main__":
    ok, msg = run_crossover_debate()
    print(msg)
