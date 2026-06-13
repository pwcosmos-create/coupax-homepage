#!/usr/bin/env python3
"""키움 학습 카드·gemma_knowledge 중복 점검 (일회성)."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_kiwoom_learn as learn  # noqa: E402


def check_cards() -> dict:
    cards = [
        c
        for c in learn.load_store().get("cards") or []
        if isinstance(c, dict)
    ]
    titles = [learn.normalize_title(c.get("title") or "") for c in cards]
    seeds = [(c.get("catalog_seed") or "").strip() for c in cards]
    ids = [c.get("id") for c in cards]
    tc = Counter(titles)
    sc = Counter(s for s in seeds if s)
    ic = Counter(ids)
    dup_t = [(t, n) for t, n in tc.items() if n > 1 and t]
    dup_s = [(s, n) for s, n in sc.items() if n > 1]
    dup_i = [(i, n) for i, n in ic.items() if n > 1]
    wonhero = [
        c
        for c in cards
        if "원히어로" in (c.get("title") or "")
        or "wonhero" in (c.get("source") or "")
        or str(c.get("catalog_seed") or "").startswith("wonhero_")
    ]
    wt = Counter(learn.normalize_title(c.get("title") or "") for c in wonhero)
    ws = Counter(
        (c.get("catalog_seed") or "").strip()
        for c in wonhero
        if (c.get("catalog_seed") or "").strip()
    )
    return {
        "count": len(cards),
        "dup_title": len(dup_t),
        "dup_seed": len(dup_s),
        "dup_id": len(dup_i),
        "dup_title_samples": dup_t[:10],
        "dup_seed_samples": dup_s[:10],
        "dup_id_samples": dup_i[:10],
        "wonhero_count": len(wonhero),
        "wonhero_dup_title": sum(1 for _, n in wt.items() if n > 1),
        "wonhero_dup_seed": sum(1 for _, n in ws.items() if n > 1),
    }


def check_gemma() -> dict:
    p = BOARD / "data" / "gemma_knowledge.json"
    if not p.is_file():
        return {"error": "missing gemma_knowledge.json"}
    data = json.loads(p.read_text(encoding="utf-8"))
    wiki = [w for w in data.get("wiki") or [] if isinstance(w, dict)]
    ids = [str(w.get("id") or "") for w in wiki]
    titles = [(w.get("title") or "").strip() for w in wiki]
    ic = Counter(ids)
    tc = Counter(titles)
    dup_i = [(i, n) for i, n in ic.items() if n > 1 and i]
    dup_t = [(t, n) for t, n in tc.items() if n > 1 and t]
    return {
        "wiki_count": len(wiki),
        "dup_wiki_id": len(dup_i),
        "dup_wiki_title": len(dup_t),
        "dup_id_samples": dup_i[:10],
        "dup_title_samples": dup_t[:10],
    }


if __name__ == "__main__":
    out = {"kiwoom_cards": check_cards(), "gemma_knowledge": check_gemma()}
    print(json.dumps(out, ensure_ascii=False, indent=2))
