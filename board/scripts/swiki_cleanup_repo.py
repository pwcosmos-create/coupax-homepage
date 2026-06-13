#!/usr/bin/env python3
"""pwcosmos-swiki 로컬 클론 정리 — 고아 Wiki md 제거·Graph 중복 노드 병합.

  python scripts/swiki_cleanup_repo.py --dry-run
  python scripts/swiki_cleanup_repo.py --apply
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

COUPAX_DIR = Path("10_Wiki/Topics/Coupax")
GRAPH = Path("20_Meta/Graph.json")


def _active_wiki_ids() -> set[str]:
    ids: set[str] = set()
    loaders = [
        ("agent_office_kiwoom_learn", "wiki_kiwoom_"),
        ("agent_office_homepage_design_learn", "wiki_design_"),
        ("agent_office_gwansang_learn", None),
        ("agent_office_saju_learn", None),
        ("agent_office_workisus_learn", "wiki_workisus_"),
        ("agent_office_stock_learn", "wiki_stock_"),
        ("agent_office_finance_learn", "wiki_finance_"),
    ]
    import importlib

    for mod_name, prefix in loaders:
        try:
            learn = importlib.import_module(mod_name)
            for c in learn.load_store().get("cards") or []:
                if not isinstance(c, dict):
                    continue
                if c.get("status") != "confirmed":
                    continue
                wid = (c.get("wiki_id") or "").strip()
                if not wid and prefix:
                    cid = c.get("id")
                    if isinstance(cid, int):
                        wid = f"{prefix}{cid}"
                if wid:
                    ids.add(wid)
        except Exception:
            pass
    return ids


def _dedupe_graph(graph: dict) -> dict:
    nodes = graph.get("nodes") or []
    links = graph.get("links") or []
    by_id: dict[str, dict] = {}
    for n in nodes:
        if not isinstance(n, dict):
            continue
        nid = (n.get("id") or "").strip()
        if not nid:
            continue
        if nid not in by_id or len(str(n.get("label") or "")) > len(str(by_id[nid].get("label") or "")):
            by_id[nid] = n
    graph["nodes"] = list(by_id.values())
    seen_links: set[tuple] = set()
    out_links = []
    for lk in links:
        if not isinstance(lk, dict):
            continue
        key = (lk.get("source"), lk.get("target"), lk.get("type"))
        if key in seen_links:
            continue
        seen_links.add(key)
        out_links.append(lk)
    graph["links"] = out_links
    return graph


def cleanup(*, apply: bool = False) -> dict:
    import agent_office_swiki_sync as sw

    repo = sw._repo_path()
    coupax = repo / COUPAX_DIR
    if not coupax.is_dir():
        return {"ok": False, "error": "no coupax dir"}

    active = _active_wiki_ids()
    removed: list[str] = []
    kept = 0
    for md in coupax.glob("wiki_*.md"):
        wid = md.stem
        if wid in active:
            kept += 1
            continue
        if wid.startswith(("wiki_office_", "wiki_pulse_")):
            kept += 1
            continue
        removed.append(wid)
        if apply:
            md.unlink()

    graph_changed = False
    gf = repo / GRAPH
    if gf.is_file():
        try:
            graph = json.loads(gf.read_text(encoding="utf-8"))
            before_n = len(graph.get("nodes") or [])
            graph = _dedupe_graph(graph)
            if apply:
                active_set = active | {f"wiki_office_{i}" for i in range(1, 500)}
                graph["nodes"] = [
                    n
                    for n in graph.get("nodes") or []
                    if isinstance(n, dict)
                    and (
                        (n.get("id") or "") in active_set
                        or (n.get("id") or "").startswith("wiki_office_")
                        or (n.get("id") or "").startswith("wiki_pulse_")
                    )
                ]
                gf.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
            graph_changed = len(graph.get("nodes") or []) != before_n
        except Exception as e:
            return {"ok": False, "error": str(e), "removed": removed}

    return {
        "ok": True,
        "apply": apply,
        "active_wiki_ids": len(active),
        "kept": kept,
        "removed_orphans": removed[:30],
        "removed_count": len(removed),
        "graph_changed": graph_changed,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    out = cleanup(apply=args.apply and not args.dry_run)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
