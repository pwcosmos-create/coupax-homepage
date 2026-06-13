"""
수석 개발자실 지식 카드 로컬 JSON 관리 모듈
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

import json_store

BOARD = Path(__file__).resolve().parents[1]
DATA_DIR = BOARD / "data" / "chief_dev_learning"
CARDS_PATH = DATA_DIR / "cards.json"
MAX_CARDS = 800

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")

def _default_store() -> dict:
    return {"updated_at": "", "cards": []}

def load_store() -> dict:
    try:
        data = json_store.load_json(CARDS_PATH, default=_default_store())
    except json_store.JsonStoreError:
        return _default_store()
    if not isinstance(data, dict):
        return _default_store()
    data.setdefault("cards", [])
    return data

def save_store(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _now()
    cards = data.get("cards")
    if isinstance(cards, list) and len(cards) > MAX_CARDS:
        data["cards"] = cards[-MAX_CARDS:]
    json_store.save_json(CARDS_PATH, data)

def _summary(text: str, n: int = 160) -> str:
    t = re.sub(r"\s+", " ", (text or "")).strip()
    return t[:n] + ("…" if len(t) > n else "")

def add_card(tag: str, title: str, body: str) -> dict:
    store = load_store()
    cards = store.get("cards") or []
    next_id = 1
    for c in cards:
        if isinstance(c, dict) and isinstance(c.get("id"), int):
            next_id = max(next_id, c["id"] + 1)

    card = {
        "id": next_id,
        "ts": _now(),
        "tag": tag[:100],
        "title": title[:120],
        "body": body[:24000],
        "summary": _summary(body),
    }

    cards.append(card)
    store["cards"] = cards
    save_store(store)
    return card

def list_cards(limit: int = 50) -> list[dict]:
    cards = [c for c in load_store().get("cards") or [] if isinstance(c, dict)]
    cards.sort(key=lambda c: c.get("id") or 0, reverse=True)
    return cards[:limit]

def clear_cards() -> None:
    save_store(_default_store())

def delete_card(card_id: int) -> bool:
    store = load_store()
    before = len(store.get("cards") or [])
    store["cards"] = [
        c for c in store.get("cards") or []
        if not (isinstance(c, dict) and c.get("id") == card_id)
    ]
    if len(store["cards"]) == before:
        return False
    save_store(store)
    return True
