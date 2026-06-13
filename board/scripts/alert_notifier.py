"""에이전트 작업 중 긴급 에러/이슈 발생 시 텔레그램 푸시 알림 발송 모듈."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")

def send_telegram_alert(title: str, message: str, level: str = "🚨 긴급") -> bool:
    """
    텔레그램 봇 API를 이용하여 메시지를 발송합니다.
    .env 파일에 TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 가 설정되어 있어야 합니다.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    
    # 설정이 없는 경우 콘솔(또는 로그)에만 출력하고 패스
    if not token or not chat_id:
        print(f"[알림 보류 - 토큰 없음] {level} | {title}: {message}")
        return False
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    text = f"{level} [{title}]\n시간: {_now()}\n\n{message}"
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("ok", False)
    except Exception as e:
        print(f"[텔레그램 발송 실패] {e!s}")
        return False
