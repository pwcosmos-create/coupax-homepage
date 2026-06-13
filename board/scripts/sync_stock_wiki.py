#!/usr/bin/env python3
"""주식 시황 스냅샷 → gemma_knowledge(finance Wiki) 동기화."""
from __future__ import annotations

import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_stock_wiki as stock_wiki  # noqa: E402


def main() -> int:
    r = stock_wiki.sync_to_knowledge()
    if r.get("skipped"):
        print("skipped", r.get("reason"))
        return 0
    if not r.get("ok"):
        print("error", r.get("error"))
        return 1
    print(f"wiki_synced={r.get('wiki_id')} title={r.get('title')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
