#!/usr/bin/env python3
"""강화학습형 카드 갭 탐지 → 우선순위 제작 → 위원회 → RL 상태 갱신.

  python scripts/saju_card_rl_autofill.py --dry-run
  python scripts/saju_card_rl_autofill.py --max-add 3
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import board_env

board_env.load_board_env()

import agent_office_saju_learn as learn  # noqa: E402
import json_store  # noqa: E402
import saju_card_gap_detector as gap_det  # noqa: E402

STATE_PATH = BOARD / "data" / "saju_learning" / "card_rl_state.json"

DEFAULT_STATE = {
    "version": 1,
    "category_weights": {},
    "history": [],
    "stats": {"runs": 0, "added": 0, "pass": 0, "fail": 0},
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def load_state() -> dict:
    return json_store.load_json(STATE_PATH, default=dict(DEFAULT_STATE))


def save_state(st: dict) -> None:
    st["updated_at"] = _now()
    json_store.save_json(STATE_PATH, st)


def _weight(st: dict, category: str) -> float:
    w = (st.get("category_weights") or {}).get(category, 1.0)
    return max(0.5, min(3.0, float(w)))


def _bump_weight(st: dict, category: str, delta: float) -> None:
    cw = dict(st.get("category_weights") or {})
    cw[category] = max(0.5, min(3.0, cw.get(category, 1.0) + delta))
    st["category_weights"] = cw


def _rank_missing(st: dict, gaps: dict) -> list[dict]:
    items = [m for m in gaps.get("missing") or [] if isinstance(m, dict)]
    scored: list[tuple[float, dict]] = []
    for m in items:
        if str(m.get("title", "")).startswith("__bucket__:"):
            continue
        if not m.get("spec") and m.get("category") != "deep":
            continue
        pri = float(m.get("priority") or 50)
        cat = str(m.get("category") or "other")
        score = pri * _weight(st, cat)
        if gaps.get("daily_reading", {}).get("llm_required") and cat == "daily":
            score += 50
        if gaps.get("full_reading", {}).get("llm_required") and cat in ("deep", "p0_p1", "variable"):
            score += 20
        scored.append((score, m))
    scored.sort(key=lambda x: (-x[0], x[1].get("title") or ""))
    return [m for _, m in scored]


def _ingest_spec(spec: dict) -> int | None:
    card = learn.add_card(
        body=spec["body"],
        title=spec["title"],
        source="rl_autofill",
        card_style=spec.get("card_style"),
    )
    cid = card.get("id")
    if not isinstance(cid, int):
        return None
    learn.confirm_card(cid, export_pack_now=False)
    tags = spec.get("tags") or []
    if tags:
        fresh = learn.get_card(cid) or card
        learn.update_confirmed_card(
            cid,
            tags=list(dict.fromkeys(list(fresh.get("tags") or []) + tags))[:12],
        )
    return cid


def _ingest_deep(title: str) -> int | None:
    from saju_deep_section_rich import rich_body_for_title

    body = rich_body_for_title(title)
    if not body:
        return None
    card = learn.add_card(body=body, title=title, source="rl_autofill_deep")
    cid = card.get("id")
    if isinstance(cid, int):
        learn.confirm_card(cid, export_pack_now=False)
    return cid if isinstance(cid, int) else None


def run(*, max_add: int = 3, sleep_sec: float = 0.2, dry_run: bool = False) -> dict:
    st = load_state()
    gaps = gap_det.detect_gaps()
    ranked = _rank_missing(st, gaps)
    plan = ranked[: max(0, max_add)]

    result: dict = {
        "dry_run": dry_run,
        "gaps": {
            "missing_count": gaps.get("missing_count"),
            "daily": gaps.get("daily_reading"),
            "full": gaps.get("full_reading"),
        },
        "planned": [m.get("title") for m in plan],
        "added": [],
        "skipped": [],
    }

    if dry_run:
        return result

    ids: list[int] = []
    for m in plan:
        title = (m.get("title") or "").strip()
        cat = str(m.get("category") or "other")
        spec = m.get("spec")
        cid: int | None = None
        if spec:
            cid = _ingest_spec(spec)
        elif cat == "deep" and title.startswith("심층·"):
            cid = _ingest_deep(title)
        if cid is None:
            result["skipped"].append(title)
            _bump_weight(st, cat, 0.3)
            continue
        ids.append(cid)
        result["added"].append({"id": cid, "title": title, "category": cat})
        if sleep_sec > 0:
            time.sleep(sleep_sec)

    council: dict = {}
    if ids:
        learn.export_pack()
        try:
            import agent_office_saju_card_council as cc

            council = cc.run_batch(min(len(ids) + 3, 40))
        except Exception as e:
            council = {"error": str(e)[:200]}
        try:
            import sync_saju_wiki_council as swc

            swc.main()
        except Exception:
            pass
        learn.export_pack()

        passed_n = 0
        fail_n = 0
        for item in result["added"]:
            cid = item["id"]
            cat = item["category"]
            fresh = learn.get_card(cid) or {}
            passed = tier_pass(fresh)
            entry = {
                "ts": _now(),
                "title": item["title"],
                "category": cat,
                "card_id": cid,
                "pass": passed,
            }
            hist = list(st.get("history") or [])
            hist.append(entry)
            st["history"] = hist[-200:]
            if passed:
                passed_n += 1
                _bump_weight(st, cat, -0.15)
            else:
                fail_n += 1
                _bump_weight(st, cat, 0.25)

        stats = dict(st.get("stats") or {})
        if result["added"]:
            stats["runs"] = int(stats.get("runs") or 0) + 1
            stats["pass"] = int(stats.get("pass") or 0) + passed_n
            stats["added"] = int(stats.get("added") or 0) + passed_n
            stats["fail"] = int(stats.get("fail") or 0) + fail_n
            st["stats"] = stats

    st["last_run"] = _now()
    st["last_gaps"] = gaps.get("missing_count")
    save_state(st)
    result["council"] = council
    result["stats"] = learn.stats()
    result["rl"] = st.get("stats")
    return result


def tier_pass(card: dict) -> bool:
    import saju_knowledge_tier as tier

    return tier.is_council_pass(card)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--max-add", type=int, default=int(__import__("os").getenv("SAJU_RL_MAX_ADD", "3")))
    p.add_argument("--sleep", type=float, default=0.2)
    args = p.parse_args()
    out = run(max_add=args.max_add, sleep_sec=args.sleep, dry_run=args.dry_run)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
