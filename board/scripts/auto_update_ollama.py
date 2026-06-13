"""
Ollama AI 엔진 야간 자동 업데이트 데몬
새로운 젬마(Gemma) 패치가 구글에서 배포되면, 새벽 시간에 자동으로 다운로드하여 최신 상태를 유지합니다.
"""
from __future__ import annotations

import os
import subprocess
import time
from datetime import datetime

def update_ai_engine():
    # 현재 설정된 주력 모델 이름 가져오기 (기본값: gemma2:2b)
    target_model = os.environ.get("GEMMA_OLLAMA_MODEL", "gemma2:2b").strip()
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🤖 AI 엔진 자동 업데이트 시작: {target_model}")
    
    try:
        # ollama pull 명령어를 백그라운드에서 실행하여 최신 버전을 덮어씌움
        result = subprocess.run(
            ["ollama", "pull", target_model], 
            capture_output=True, 
            text=True,
            timeout=600 # 최대 10분 대기
        )
        
        if result.returncode == 0:
            print(f"[성공] 엔진 업데이트 완료: {target_model}")
            try:
                import alert_notifier
                # alert_notifier.send_telegram_alert("엔진 자동 업데이트", f"{target_model} 모델이 최신 버전으로 갱신되었습니다.", "🚀 업데이트")
            except ImportError:
                pass
        else:
            print(f"[실패] 엔진 업데이트 중 오류 발생: {result.stderr}")
            
    except Exception as e:
        print(f"[오류] 자동 업데이트 실행 실패: {e!s}")

if __name__ == "__main__":
    update_ai_engine()
