#!/usr/bin/env python3
"""원키스US ATR 갭 → RL 우선순위 → 강화학습 카드 제작·확정.

  python scripts/workisus_atr_card_rl_autofill.py --dry-run
  python scripts/workisus_atr_card_rl_autofill.py --max-add 3
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_workisus_learn as learn  # noqa: E402
import workisus_agent_card_compose as wac  # noqa: E402
import workisus_atr_card_gap_detector as gap_det  # noqa: E402
import workisus_atr_card_rl_compose as rl_comp  # noqa: E402
import workisus_atr_card_rl_engine as rle  # noqa: E402
import workisus_learning_errors as werr  # noqa: E402


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _rank_missing(st: dict, gaps: dict) -> list[dict]:
    items: list[dict] = []
    for m in gaps.get("missing") or []:
        if not isinstance(m, dict):
            continue
        title = str(m.get("title") or "")
        if title.startswith("__tag__:"):
            continue
        if title.startswith("__error_learn__:"):
            kind = title.split(":", 1)[-1].strip()
            m = dict(m)
            m["spec"] = rl_comp._error_spec(kind)
            if not m["spec"]:
                continue
        if not m.get("spec"):
            continue
        items.append(m)
    return rle.rerank_gaps(st, items)


def _ingest_spec(spec: dict) -> int | None:
    spec = rl_comp.enrich_spec(spec)
    seed = (spec.get("catalog_seed") or "").strip()
    title = learn.normalize_title(spec.get("title") or "")
    if title and learn.title_taken(title):
        werr.record("duplicate", "RL ATR 제목 중복", title=title)
        return None
    body = (spec.get("body") or "").strip()
    if len(body) < 30:
        werr.record("too_short", "RL ATR 본문 부족", title=title)
        return None
    try:
        if seed:
            card = wac.ensure_seed_card(seed, agent_id="workisus_atr_rl", confirm=True)
            if card and isinstance(card.get("id"), int):
                store = learn.load_store()
                for c in store.get("cards") or []:
                    if isinstance(c, dict) and c.get("id") == card["id"]:
                        c["category"] = "atr_rl"
                        c["source"] = "atr_rl_autofill"
                        c["rl_enriched"] = True
                        learn.save_store(store)
                        break
                return int(card["id"])
        card = learn.add_card(
            body=body,
            title=title,
            source="atr_rl_autofill",
            catalog_seed=seed,
            category="atr_rl",
            use_council=False,
        )
    except ValueError as e:
        werr.record("too_short", str(e)[:200], title=title)
        return None
    cid = card.get("id")
    if not isinstance(cid, int):
        return None
    confirmed = learn.confirm_card(cid)
    if not confirmed:
        learn.delete_card(cid)
        werr.record("confirm_failed", "RL ATR 확정 실패", title=title, card_id=cid)
        return None
    return cid


def run(
    *,
    max_add: int = 2,
    sleep_sec: float = 0.25,
    dry_run: bool = False,
    train_first: bool = True,
) -> dict:
    import workisus_learn_policy as wlp

    if not wlp.is_card_production_enabled():
        return {"skipped": True, "reason": wlp.disabled_message()}
    st = rle.load_state()
    train_info: dict = {}
    if train_first and not dry_run:
        train_info = rle.train_step()
    gaps = gap_det.detect_atr_gaps()
    ranked = _rank_missing(st, gaps)
    plan = ranked[: max(0, max_add)]

    result: dict = {
        "dry_run": dry_run,
        "gaps": {
            "missing_count": gaps.get("missing_count"),
            "atr_catalog": gaps.get("atr_catalog"),
            "confirmed": gaps.get("confirmed"),
        },
        "planned": [{"title": m.get("title"), "seed": m.get("catalog_seed")} for m in plan],
        "added": [],
        "skipped": [],
        "rl_train": train_info,
    }

    if dry_run:
        result["rl"] = rle.status()
        return result

    for m in plan:
        title = (m.get("title") or "").strip()
        cat = str(m.get("category") or "atr_rl")
        seed = (m.get("catalog_seed") or "").strip()
        spec = m.get("spec")
        cid: int | None = None
        if isinstance(spec, dict):
            cid = _ingest_spec(spec)
        if cid is None:
            result["skipped"].append(title or seed)
            rle.record_outcome(
                st, category=cat, title=title, catalog_seed=seed, success=False, source="atr_rl_autofill"
            )
            continue
        result["added"].append({"id": cid, "title": title, "seed": seed, "category": cat})
        rle.record_outcome(
            st,
            category="atr_rl",
            title=title,
            catalog_seed=seed,
            success=True,
            card_id=cid,
            source="atr_rl_autofill",
        )
        if sleep_sec > 0:
            time.sleep(sleep_sec)

    if result["added"]:
        learn.export_pack()
        try:
            import agent_office_wiki_store

            for row in result["added"]:
                c = learn.find_card_by_seed(row.get("seed") or "") if row.get("seed") else None
                if not c:
                    for x in learn.load_store().get("cards") or []:
                        if isinstance(x, dict) and x.get("id") == row.get("id"):
                            c = x
                            break
                if c:
                    agent_office_wiki_store.save_workisus_card_to_knowledge(c)
        except Exception:
            pass

    stats = dict(st.get("stats") or {})
    if result["added"] or result["skipped"]:
        stats["runs"] = int(stats.get("runs") or 0) + 1
        stats["added"] = int(stats.get("added") or 0) + len(result["added"])
    st["stats"] = stats
    st["last_run"] = _now()
    rle.save_state(st)
    result["stats"] = learn.stats()
    result["rl"] = rle.status()
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--max-add", type=int, default=int(os.getenv("WORKISUS_ATR_RL_MAX_ADD", "2") or "2"))
    p.add_argument("--sleep", type=float, default=0.25)
    args = p.parse_args()
    out = run(max_add=args.max_add, sleep_sec=args.sleep, dry_run=args.dry_run)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
