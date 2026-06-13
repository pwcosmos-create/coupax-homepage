#!/usr/bin/env python3
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))
try:
    import board_env

    board_env.load_board_env()
except ImportError:
    pass

from saju_card_llm_compose import gemini_api_key, gemini_model  # noqa: E402

api_key = gemini_api_key()
model = gemini_model()
print("key_prefix", (api_key[:8] + "..." if api_key else "NONE"))
print("model", model)

url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
payload = {
    "contents": [{"role": "user", "parts": [{"text": "한국어로 5문장 인사해 주세요."}]}],
    "generationConfig": {"temperature": 0.5, "maxOutputTokens": 1024},
}
try:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    parts = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
    print("http_ok", True, "text_len", len(text))
    print("preview", text[:200])
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")[:400]
    print("http_ok", False, "code", e.code)
    print("error_body", body)
except Exception as e:
    print("http_ok", False, "exc", type(e).__name__, str(e)[:200])
