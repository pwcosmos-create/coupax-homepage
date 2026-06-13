#!/usr/bin/env python3
"""관상 학습 — 카탈로그 갭 + RL/Gemini 확장 토픽 자동 제작.

  python scripts/gwansang_card_rl_autofill.py --dry-run
  python scripts/gwansang_card_rl_autofill.py --max-add 2
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
sys.path.insert(0, str(BOARD / "scripts"))

try:
    import board_env

    board_env.load_board_env()
except ImportError:
    pass

import agent_office_gwansang_learn as learn  # noqa: E402
import gwansang_card_compose as gcc  # noqa: E402
import gwansang_card_gap_detector as gap_det  # noqa: E402
import json_store  # noqa: E402

STATE_PATH = BOARD / "data" / "gwansang_learning" / "card_rl_state.json"
DEFAULT_STATE = {
    "version": 1,
    "category_weights": {},
    "history": [],
    "stats": {"runs": 0, "catalog_added": 0, "rl_added": 0, "fail": 0},
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


def _rank_expansion(st: dict, gaps: dict) -> list[dict]:
    items = [m for m in gaps.get("expansion_missing") or [] if isinstance(m, dict)]
    scored: list[tuple[float, dict]] = []
    for m in items:
        pri = float(m.get("priority") or 50)
        cat = str(m.get("category") or "feature")
        scored.append((pri * _weight(st, cat), m))
    scored.sort(key=lambda x: (-x[0], x[1].get("title") or ""))
    return [m for _, m in scored]


def run(
    *,
    max_add: int = 2,
    sleep_sec: float = 0.3,
    dry_run: bool = False,
    agent_id: str = "gwansang_gap_autofill",
) -> dict:
    st = load_state()
    gaps = gap_det.detect_gaps(agent_id=agent_id)
    result: dict = {
        "dry_run": dry_run,
        "gaps": {
            "catalog_missing": gaps.get("missing_count", 0),
            "expansion_missing": gaps.get("expansion_count", 0),
        },
        "added": [],
        "skipped": [],
    }
    if dry_run:
        plan_cat = (gaps.get("missing") or [])[:max_add]
        plan_rl = _rank_expansion(st, gaps)[: max(0, max_add - len(plan_cat))]
        result["planned_catalog"] = [m.get("title") for m in plan_cat]
        result["planned_rl"] = [m.get("title") for m in plan_rl]
        return result

    added_n = 0
    for _ in range(max_add):
        out = gcc.compose_next_gap(agent_id=agent_id)
        if not out or not out.get("card_id"):
            break
        result["added"].append({"kind": "catalog", **out})
        added_n += 1
        _bump_weight(st, "catalog", -0.1)
        if sleep_sec > 0:
            time.sleep(sleep_sec)

    if added_n < max_add:
        import gwansang_card_llm_compose as llm

        if llm.llm_available():
            for topic in _rank_expansion(st, gaps)[: max_add - added_n]:
                out = llm.compose_topic(topic, agent_id=agent_id, confirm=True)
                if not out:
                    result["skipped"].append(topic.get("title"))
                    _bump_weight(st, str(topic.get("category") or "feature"), 0.2)
                    continue
                if out.get("skipped"):
                    result["skipped"].append(out.get("title") or topic.get("title"))
                    continue
                result["added"].append({"kind": "rl_gemini", **out})
                added_n += 1
                cat = str(topic.get("category") or "feature")
                _bump_weight(st, cat, -0.15)
                hist = list(st.get("history") or [])
                hist.append(
                    {
                        "ts": _now(),
                        "title": out.get("title"),
                        "card_id": out.get("card_id"),
                        "kind": "rl_gemini",
                        "category": cat,
                    }
                )
                st["history"] = hist[-120:]
                if sleep_sec > 0:
                    time.sleep(sleep_sec)
                if added_n >= max_add:
                    break

    if result["added"]:
        learn.export_pack()
        stats = dict(st.get("stats") or {})
        stats["runs"] = int(stats.get("runs") or 0) + 1
        cat_n = sum(1 for a in result["added"] if a.get("kind") == "catalog")
        rl_n = sum(1 for a in result["added"] if a.get("kind") == "rl_gemini")
        stats["catalog_added"] = int(stats.get("catalog_added") or 0) + cat_n
        stats["rl_added"] = int(stats.get("rl_added") or 0) + rl_n
        st["stats"] = stats

    st["last_run"] = _now()
    save_state(st)
    result["stats"] = learn.stats()
    result["rl"] = st.get("stats")
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--max-add",
        type=int,
        default=int(os.getenv("GWANSANG_RL_MAX_ADD", "2") or "2"),
    )
    p.add_argument("--sleep", type=float, default=0.3)
    args = p.parse_args()
    out = run(max_add=args.max_add, sleep_sec=args.sleep, dry_run=args.dry_run)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
