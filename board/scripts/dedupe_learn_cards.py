#!/usr/bin/env python3
"""학습 카드 중복 제거·병합 — 사업부별.

유지 우선: confirmed > council_agents > web_research > 본문 길이 > 높은 id
동일 제목·동일 axis·동일 catalog_seed 그룹에서 1장 유지.

  python scripts/dedupe_learn_cards.py --unit all --dry-run
  python scripts/dedupe_learn_cards.py --unit homepage-design --apply
"""
from __future__ import annotations

import argparse
import importlib
import re
import sys
from collections import defaultdict
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

from office_web_research_units import UNIT_CONFIGS, all_unit_ids

_VARIANT_RE = re.compile(r"\s*[\(·]\s*v\d+[\)]?$|\s*\(v\d+\)$|\s*재검토\s*\([a-f0-9]+\)\s*—")
_AXIS_RE = re.compile(r"^debate_web_([^_]+(?:_[^_]+)*)_[a-f0-9]{6,8}$")


def _norm_title(title: str) -> str:
    t = re.sub(r"\s+", " ", (title or "").strip())
    t = _VARIANT_RE.sub("", t)
    return t[:120]


def _axis_key(seed: str) -> str:
    m = _AXIS_RE.match((seed or "").strip())
    return m.group(1) if m else ""


def _score(card: dict) -> tuple:
    body = card.get("body") or ""
    cid = int(card.get("id") or 0)
    return (
        1 if card.get("status") == "confirmed" else 0,
        1 if card.get("council_agents") else 0,
        1 if card.get("web_research") else 0,
        1 if (card.get("category") or "") == "debate" else 0,
        len(body),
        cid,
    )


def _merge_bodies(keeper: dict, others: list[dict]) -> str:
    body = (keeper.get("body") or "").strip()
    seen = {body}
    for c in others:
        b = (c.get("body") or "").strip()
        if b and b not in seen and b not in body:
            body += "\n\n——— 병합 ———\n" + b[:2000]
            seen.add(b)
    return body[:24000]


def dedupe_unit(unit_id: str, *, apply: bool = False) -> dict:
    cfg = UNIT_CONFIGS.get(unit_id)
    if not cfg:
        return {"unit": unit_id, "error": "unknown unit"}
    learn = importlib.import_module(cfg.learn_module)
    if not hasattr(learn, "load_store"):
        return {"unit": unit_id, "skipped": True}

    cards = [c for c in learn.load_store().get("cards") or [] if isinstance(c, dict)]
    groups: dict[str, list[dict]] = defaultdict(list)

    for c in cards:
        seed = (c.get("catalog_seed") or "").strip()
        title = _norm_title(c.get("title") or "")
        axis = _axis_key(seed)
        if seed:
            groups[f"seed:{seed}"].append(c)
        if axis:
            groups[f"axis:{axis}"].append(c)
        if title:
            groups[f"title:{title}"].append(c)

    remove_ids: set[int] = set()
    merge_notes: list[dict] = []

    for key, items in groups.items():
        if len(items) < 2:
            continue
        items = sorted(items, key=_score, reverse=True)
        keep = items[0]
        keep_id = int(keep.get("id") or 0)
        dups = [c for c in items[1:] if int(c.get("id") or 0) != keep_id]
        if not dups:
            continue
        dup_ids = {int(c.get("id") or 0) for c in dups if int(c.get("id") or 0)}
        if apply and dup_ids:
            merged_body = _merge_bodies(keep, dups)
            if merged_body != (keep.get("body") or ""):
                revise = getattr(learn, "revise_card", None)
                if callable(revise):
                    revise(keep_id, body=merged_body, reconfirm=False)
        remove_ids |= dup_ids
        merge_notes.append(
            {
                "group": key,
                "keep_id": keep_id,
                "remove_ids": sorted(dup_ids),
                "count": len(items),
            }
        )

    removed = 0
    if apply and remove_ids:
        delete = getattr(learn, "delete_card", None)
        if callable(delete):
            for cid in sorted(remove_ids):
                if delete(cid):
                    removed += 1
        export = getattr(learn, "export_pack", None)
        if callable(export):
            try:
                export()
            except Exception:
                pass

    return {
        "unit": unit_id,
        "before": len(cards),
        "after": len(cards) - removed,
        "removed": removed,
        "groups": len(merge_notes),
        "samples": merge_notes[:8],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--unit", default="all")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    apply = args.apply and not args.dry_run
    units = all_unit_ids() if args.unit == "all" else [args.unit]
    results = [dedupe_unit(u, apply=apply) for u in units]
    import json

    print(json.dumps({"apply": apply, "results": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
