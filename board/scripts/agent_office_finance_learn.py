"""금융 블로그 — 웹 검색 토론·E-E-A-T 카드."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import json_store

BOARD = Path(__file__).resolve().parents[1]
DATA_DIR = BOARD / "data" / "finance_learning"
CARDS_PATH = DATA_DIR / "cards.json"
PACK_PATH = DATA_DIR / "finance_knowledge_pack.json"
DIVISION = "finance"
MIN_BODY = 80


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
    json_store.save_json(CARDS_PATH, data)


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").strip())[:120]


def title_taken(title: str) -> bool:
    t = normalize_title(title)
    return any(
        normalize_title(c.get("title") or "") == t
        for c in load_store().get("cards") or []
        if isinstance(c, dict)
    )


def find_card_by_seed(catalog_seed: str) -> dict | None:
    seed = (catalog_seed or "").strip()
    if not seed:
        return None
    for c in load_store().get("cards") or []:
        if isinstance(c, dict) and (c.get("catalog_seed") or "").strip() == seed:
            return c
    return None


def _summary(text: str, n: int = 160) -> str:
    t = re.sub(r"\s+", " ", (text or "")).strip()
    return t[:n] + ("…" if len(t) > n else "")


def revise_card(
    card_id: int,
    *,
    body: str | None = None,
    title: str | None = None,
    catalog_seed: str | None = None,
    reconfirm: bool = True,
) -> dict | None:
    store = load_store()
    target = next(
        (c for c in store.get("cards") or [] if isinstance(c, dict) and c.get("id") == card_id),
        None,
    )
    if not target:
        return None
    if body is not None:
        target["body"] = (body or "")[:24000]
        target["summary"] = _summary(target["body"])
    if title is not None and normalize_title(title):
        target["title"] = normalize_title(title)
    if catalog_seed is not None:
        target["catalog_seed"] = str(catalog_seed).strip()[:120]
    target["revised_at"] = _now()
    save_store(store)
    return target


def add_card(
    *,
    body: str,
    title: str = "",
    source: str = "paste",
    catalog_seed: str = "",
    category: str = "",
    use_council: bool = False,
    revise_if_seed_exists: bool = True,
    compose: bool = False,
) -> dict:
    seed = (catalog_seed or "").strip()
    if revise_if_seed_exists and seed:
        existing = find_card_by_seed(seed)
        if existing and isinstance(existing.get("id"), int):
            return revise_card(int(existing["id"]), body=body, title=title or None, catalog_seed=seed) or existing

    raw = (body or "").strip()
    if len(raw) < MIN_BODY:
        raise ValueError(f"본문 {MIN_BODY}자 이상 필요.")
    title_in = normalize_title(title) or _summary(raw, 50)
    if title_taken(title_in):
        raise ValueError("동일 제목의 카드가 이미 있습니다.")

    store = load_store()
    cards = store.get("cards") or []
    next_id = max((int(c["id"]) for c in cards if isinstance(c, dict) and isinstance(c.get("id"), int)), default=0) + 1
    card = {
        "id": next_id,
        "ts": _now(),
        "title": title_in,
        "body": raw[:24000],
        "summary": _summary(raw),
        "source": source[:40],
        "status": "pending",
        "tags": ["금융블로그", "웹리서치"] if "웹리서치" in title_in else ["금융블로그"],
    }
    if seed:
        card["catalog_seed"] = seed[:120]
    if category:
        card["category"] = category[:40]
    cards.append(card)
    store["cards"] = cards
    save_store(store)
    return card


def confirm_card(card_id: int, *, export_pack_now: bool = True) -> dict | None:
    store = load_store()
    for c in store.get("cards") or []:
        if isinstance(c, dict) and c.get("id") == card_id:
            c["status"] = "confirmed"
            c["confirmed_at"] = _now()
            save_store(store)
            if export_pack_now:
                export_pack()
            return c
    return None


def delete_card(card_id: int) -> bool:
    store = load_store()
    before = len(store.get("cards") or [])
    store["cards"] = [c for c in store.get("cards") or [] if not (isinstance(c, dict) and c.get("id") == card_id)]
    if len(store["cards"]) == before:
        return False
    save_store(store)
    return True


def stats() -> dict:
    cards = [c for c in load_store().get("cards") or [] if isinstance(c, dict)]
    return {
        "total": len(cards),
        "pending": sum(1 for c in cards if c.get("status") == "pending"),
        "confirmed": sum(1 for c in cards if c.get("status") == "confirmed"),
        "debate_cards": sum(1 for c in cards if (c.get("category") or "") == "debate"),
        "updated_at": load_store().get("updated_at") or "",
    }


def export_pack() -> None:
    cards = [c for c in load_store().get("cards") or [] if isinstance(c, dict) and c.get("status") == "confirmed"]
    pack = {
        "updated_at": _now(),
        "division": DIVISION,
        "cards": [
            {
                "id": c.get("id"),
                "title": c.get("title"),
                "summary": c.get("summary"),
                "body": (c.get("body") or "")[:8000],
                "catalog_seed": c.get("catalog_seed") or "",
            }
            for c in cards[-200:]
        ],
    }
    json_store.save_json(PACK_PATH, pack)
