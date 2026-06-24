"""숏폼공장 — Gemini API 키 저장 (관리자 UI)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

BOARD_DIR = Path(__file__).resolve().parent
SECRETS_PATH = BOARD_DIR / "data" / "shorts_secrets.json"


def _mask_key(key: str) -> str:
    key = (key or "").strip()
    if not key:
        return ""
    if len(key) <= 12:
        return "••••"
    return f"{key[:6]}…{key[-4:]}"


def _read_file_key() -> str:
    if not SECRETS_PATH.is_file():
        return ""
    try:
        data = json.loads(SECRETS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ""
    return (data.get("gemini_api_key") or "").strip()


def get_google_api_key() -> str:
    """우선순위: 관리자 저장 파일 → SHORTS_GOOGLE_AI_API_KEY → GEMINI_API_KEY."""
    file_key = _read_file_key()
    if file_key:
        return file_key
    shorts_env = os.getenv("SHORTS_GOOGLE_AI_API_KEY", "").strip()
    if shorts_env:
        return shorts_env
    return os.getenv("GEMINI_API_KEY", "").strip()


def key_info() -> dict[str, str | bool]:
    file_key = _read_file_key()
    shorts_env = os.getenv("SHORTS_GOOGLE_AI_API_KEY", "").strip()
    gemini_env = os.getenv("GEMINI_API_KEY", "").strip()
    key = get_google_api_key()
    if file_key:
        source = "admin"
    elif shorts_env:
        source = "env_shorts"
    elif gemini_env:
        source = "env_gemini"
    else:
        source = ""
    updated = ""
    if SECRETS_PATH.is_file():
        try:
            data = json.loads(SECRETS_PATH.read_text(encoding="utf-8"))
            updated = data.get("updated") or ""
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "configured": bool(key),
        "masked": _mask_key(key),
        "source": source,
        "updated": updated,
    }


def save_google_api_key(api_key: str) -> None:
    api_key = api_key.strip()
    SECRETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "gemini_api_key": api_key,
        "updated": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    SECRETS_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    try:
        os.chmod(SECRETS_PATH, 0o600)
    except OSError:
        pass
