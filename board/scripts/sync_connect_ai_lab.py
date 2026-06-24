"""
Connect AI Lab ↔ Coupax 전체 동기화 오케스트레이터.

  PYTHONPATH=scripts python scripts/sync_connect_ai_lab.py full
  PYTHONPATH=scripts python scripts/sync_connect_ai_lab.py import-brain
  PYTHONPATH=scripts python scripts/sync_connect_ai_lab.py ingest-docs
  PYTHONPATH=scripts python scripts/sync_connect_ai_lab.py swiki
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
_REPO = BOARD.parent
_SCRIPTS = BOARD / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import board_env  # noqa: E402

DOC_INGEST: list[tuple[str, str, str, str]] = [
    (
        "CURSOR_RAG_AI1_LEARN.md",
        "finance",
        "connect_ai_rag_day1",
        "Connect AI · RAG 1일차 (AI 1인 기업)",
    ),
    (
        "CURSOR_RAG_AI5_LEARN.md",
        "finance",
        "connect_ai_agent_sdk_day5",
        "Connect AI · Antigravity SDK 5강",
    ),
    (
        "assets/design_briefs/style_reference_masterclass_midnight.md",
        "homepage-design",
        "masterclass_midnight_refero",
        "디자인 레퍼런스 · MasterClass Midnight",
    ),
]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _read_doc(rel: str) -> str | None:
    p = _REPO / rel.replace("/", os.sep)
    if not p.is_file():
        return None
    return p.read_text(encoding="utf-8")


def cmd_import_brain(dry_run: bool = False) -> dict:
    import import_connect_brain_jsonl as brain

    return brain.import_jsonl(dry_run=dry_run)


def cmd_ingest_docs(*, confirm: bool = True) -> dict:
    import agent_office_finance_learn as fl
    import agent_office_homepage_design_learn as hdl

    out = {"ingested": [], "skipped": [], "errors": []}
    for rel, division, seed, title in DOC_INGEST:
        body = _read_doc(rel)
        if not body or len(body.strip()) < 80:
            out["skipped"].append({"file": rel, "reason": "missing_or_short"})
            continue
        try:
            if division == "finance":
                mod = fl
            elif division == "homepage-design":
                mod = hdl
            else:
                out["skipped"].append({"file": rel, "reason": f"unknown_division:{division}"})
                continue
            existing = mod.find_card_by_seed(seed) if hasattr(mod, "find_card_by_seed") else None
            card = mod.add_card(
                body=body[:24000],
                title=title,
                source="connect_ai_lab",
                catalog_seed=seed,
                revise_if_seed_exists=True,
            )
            if confirm and card.get("id"):
                mod.confirm_card(int(card["id"]))
            out["ingested"].append(
                {"file": rel, "id": card.get("id"), "title": card.get("title"), "revised": bool(existing)}
            )
        except Exception as e:
            out["errors"].append({"file": rel, "error": str(e)[:200]})
    return out


def cmd_swiki() -> dict:
    if os.getenv("SWIKI_SYNC_ENABLED", "0").strip() not in ("1", "true", "yes"):
        return {
            "ok": False,
            "skipped": True,
            "hint": "Set SWIKI_SYNC_ENABLED=1 and SWIKI_GIT_TOKEN in board/.env",
        }
    import agent_office_swiki_sync as sw

    try:
        return {"ok": True, **sw.sync_all()}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


def cmd_export_packs() -> dict:
    results: dict[str, str] = {}
    try:
        import agent_office_finance_learn as fl

        fl.export_pack()
        results["finance"] = "ok"
    except Exception as e:
        results["finance"] = str(e)[:120]
    try:
        import agent_office_homepage_design_learn as hdl

        hdl.export_pack()
        results["homepage_design"] = "ok"
    except Exception as e:
        results["homepage_design"] = str(e)[:120]
    try:
        import agent_office_saju_learn as sl

        sl.export_pack()
        results["saju"] = "ok"
    except Exception as e:
        results["saju"] = str(e)[:120]
    return results


def cmd_full(*, dry_run: bool = False, skip_swiki: bool = False) -> dict:
    report = {
        "at": _now(),
        "brain": cmd_import_brain(dry_run=dry_run),
        "docs": {} if dry_run else cmd_ingest_docs(),
        "swiki": {} if dry_run or skip_swiki else cmd_swiki(),
        "packs": {} if dry_run else cmd_export_packs(),
    }
    state_path = BOARD / "data" / "connect_ai_lab_sync_state.json"
    if not dry_run:
        state_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    board_env.load_board_env()
    p = argparse.ArgumentParser(description="Connect AI Lab ↔ Coupax sync")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--skip-swiki", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("full", help="brain + docs + swiki + export packs")
    sub.add_parser("import-brain", help="jsonl → gemma_knowledge.json")
    sub.add_parser("ingest-docs", help="CURSOR/design md → learn cards")
    sub.add_parser("swiki", help="pwcosmos-swiki bidirectional sync")
    sub.add_parser("export-packs", help="refresh knowledge packs")
    args = p.parse_args()

    if args.cmd == "full":
        out = cmd_full(dry_run=args.dry_run, skip_swiki=args.skip_swiki)
    elif args.cmd == "import-brain":
        out = cmd_import_brain(dry_run=args.dry_run)
    elif args.cmd == "ingest-docs":
        out = cmd_ingest_docs()
    elif args.cmd == "swiki":
        out = cmd_swiki()
    else:
        out = cmd_export_packs()

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
