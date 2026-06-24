#!/usr/bin/env python3
"""Bulk push 후 synced_wiki_ids 를 gemma_knowledge wiki 전체로 맞춤."""
from __future__ import annotations

import board_env
import agent_office_wiki_store
import agent_office_swiki_sync as swiki

board_env.load_board_env()
data = agent_office_wiki_store.load_knowledge()
ids = sorted(
    w.get("id")
    for w in data.get("wiki") or []
    if isinstance(w, dict) and w.get("id")
)
state = swiki.load_state()
state["synced_wiki_ids"] = ids
state["last_error"] = ""
state["last_push"] = swiki._now()
swiki.save_state(state)
print(f"synced={len(ids)}")
