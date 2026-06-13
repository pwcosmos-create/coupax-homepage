#!/usr/bin/env python3
"""원키스 US 학습 카드·pack·Wiki·RL 상태 일괄 삭제 (로컬/서버 동일 경로).

  cd board && PYTHONPATH=scripts .venv/bin/python scripts/purge_workisus_learning_cards.py
  cd board && PYTHONPATH=scripts .venv/bin/python scripts/purge_workisus_learning_cards.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

DATA_DIR = BOARD / "data" / "workisus_learning"
CARDS_PATH = DATA_DIR / "cards.json"
PACK_PATH = DATA_DIR / "workisus_knowledge_pack.json"
ERRORS_PATH = DATA_DIR / "learning_errors.json"
RL_STATE_PATH = DATA_DIR / "atr_card_rl_state.json"
CURSOR_MD = BOARD.parent / "CURSOR_WORKISUS_LEARN.md"


def _empty_cards_store() -> dict:
    import agent_office_workisus_learn as wl

    return {"updated_at": wl._now(), "cards": []}


def _empty_pack() -> dict:
    return {
        "version": 1,
        "purpose": "workisus_us_single_account_cascade",
        "exported_at": "",
        "card_count": 0,
        "cards": [],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    import json_store

    before = 0
    if CARDS_PATH.is_file():
        try:
            data = json.loads(CARDS_PATH.read_text(encoding="utf-8"))
            before = len(data.get("cards") or [])
        except Exception:
            before = -1

    wiki_removed = {"wiki": 0, "meta": 0}
    try:
        import agent_office_wiki_store as ws

        if not args.dry_run:
            out = ws.split_domain_to_file(
                ws.DOMAIN_WORKISUS,
                remove_from_unified=True,
            )
            wiki_removed = out.get("removed_from_unified") or wiki_removed
            wiki_removed["wiki_count"] = out.get("wiki_count", 0)
    except Exception as e:
        print("wiki purge warn:", e)

    if args.dry_run:
        print(f"dry-run: would delete {before} cards, wiki_removed={wiki_removed}")
        return 0

    json_store.save_json(CARDS_PATH, _empty_cards_store())
    json_store.save_json(PACK_PATH, _empty_pack())
    for path in (ERRORS_PATH, RL_STATE_PATH):
        if path.is_file():
            path.unlink()
        lock = path.with_suffix(path.suffix + ".lock")
        if lock.is_file():
            lock.unlink()

    try:
        import agent_office_workisus_learn as wl

        wl.render_cursor_md(_empty_cards_store())
    except Exception:
        CURSOR_MD.write_text(
            "# Cursor — 원키스 US 차수매매 학습부\n\n학습 카드 제작 중지 · 데이터 없음.\n",
            encoding="utf-8",
        )

    print(
        json.dumps(
            {
                "ok": True,
                "cards_removed": before,
                "wiki_removed": wiki_removed,
                "paths": {
                    "cards": str(CARDS_PATH),
                    "pack": str(PACK_PATH),
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
