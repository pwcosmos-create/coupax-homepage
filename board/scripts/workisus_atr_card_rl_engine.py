"""
원키스US ATR 학습 카드 강화학습 — 시드·카테고리 밴딧 + 확정·오류 피드백.

  python scripts/workisus_atr_card_rl_engine.py train
  python scripts/workisus_atr_card_rl_engine.py status
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import json_store  # noqa: E402

STATE_PATH = BOARD / "data" / "workisus_learning" / "atr_card_rl_state.json"
CATEGORIES = ("atr_rl", "atr_formula", "atr_policy", "atr_ops", "atr_error", "seven_split", "meta", "other")

DEFAULT_STATE = {
    "version": 1,
    "epsilon": 0.18,
    "learning_rate": 0.12,
    "category_weights": {"atr_rl": 1.2, "atr_formula": 1.15, "atr_policy": 1.1},
    "seed_weights": {},
    "title_bias": {},
    "history": [],
    "stats": {
        "runs": 0,
        "train_steps": 0,
        "added": 0,
        "pass": 0,
        "fail": 0,
        "confirm_rewards": 0,
        "error_penalties": 0,
    },
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _epsilon() -> float:
    return float(os.getenv("WORKISUS_ATR_RL_EPSILON", "0.18") or "0.18")


def _lr() -> float:
    return float(os.getenv("WORKISUS_ATR_RL_LEARNING_RATE", "0.12") or "0.12")


def load_state() -> dict:
    st = json_store.load_json(STATE_PATH, default=dict(DEFAULT_STATE))
    st.setdefault("category_weights", dict(DEFAULT_STATE["category_weights"]))
    st.setdefault("seed_weights", {})
    st.setdefault("title_bias", {})
    st.setdefault("history", [])
    st.setdefault("stats", dict(DEFAULT_STATE["stats"]))
    return st


def save_state(st: dict) -> None:
    st["updated_at"] = _now()
    st["epsilon"] = _epsilon()
    st["learning_rate"] = _lr()
    hist = st.get("history") or []
    if len(hist) > 200:
        st["history"] = hist[-200:]
    json_store.save_json(STATE_PATH, st)


def _slug(title: str) -> str:
    return re.sub(r"[^\w가-힣]+", "_", (title or "").strip())[:48] or "untitled"


def category_weight(st: dict, category: str) -> float:
    w = (st.get("category_weights") or {}).get(category, 1.0)
    return max(0.3, min(4.5, float(w)))


def seed_weight(st: dict, catalog_seed: str) -> float:
    sw = (st.get("seed_weights") or {}).get((catalog_seed or "").strip(), 1.0)
    return max(0.35, min(3.5, float(sw)))


def bump_category(st: dict, category: str, delta: float) -> None:
    cw = dict(st.get("category_weights") or {})
    cat = category if category in CATEGORIES else "other"
    cw[cat] = max(0.3, min(4.5, cw.get(cat, 1.0) + delta))
    st["category_weights"] = cw


def bump_seed(st: dict, catalog_seed: str, delta: float) -> None:
    if not catalog_seed:
        return
    sw = dict(st.get("seed_weights") or {})
    sw[catalog_seed] = max(0.35, min(3.5, sw.get(catalog_seed, 1.0) + delta))
    st["seed_weights"] = sw


def bump_title(st: dict, title: str, delta: float) -> None:
    tb = dict(st.get("title_bias") or {})
    key = _slug(title)
    tb[key] = max(-2.0, min(3.0, float(tb.get(key, 0.0)) + delta))
    st["title_bias"] = tb


def score_gap_item(st: dict, item: dict) -> float:
    cat = str(item.get("category") or "atr_rl")
    pri = float(item.get("priority") or 50)
    title = (item.get("title") or "").strip()
    seed = (item.get("catalog_seed") or "").strip()
    if not seed and isinstance(item.get("spec"), dict):
        seed = (item["spec"].get("catalog_seed") or "").strip()
    tb = (st.get("title_bias") or {}).get(_slug(title), 0.0)
    err_boost = 15.0 if item.get("error_kind") else 0.0
    tag_need = int(item.get("tag_need") or 0)
    return (
        pri * category_weight(st, cat)
        + seed_weight(st, seed) * 12.0
        + tb * 6.0
        + err_boost
        + tag_need * 4.0
    )


def rerank_gaps(st: dict, items: list[dict]) -> list[dict]:
    if not items:
        return []
    scored = [(score_gap_item(st, m), m) for m in items]
    scored.sort(key=lambda x: (-x[0], x[1].get("title") or ""))
    eps = _epsilon()
    if len(scored) > 2 and random.random() < eps:
        n = min(6, len(scored))
        head = [m for _, m in scored[:n]]
        random.shuffle(head)
        tail = [m for _, m in scored[n:]]
        return head + tail
    return [m for _, m in scored]


def record_outcome(
    st: dict,
    *,
    category: str,
    title: str,
    catalog_seed: str = "",
    success: bool,
    card_id: int | None = None,
    source: str = "autofill",
) -> None:
    lr = _lr()
    reward = 1.0 if success else -0.85
    bump_category(st, category, -lr * 0.1 if success else lr * 0.15)
    if catalog_seed:
        bump_seed(st, catalog_seed, lr * 0.2 if success else -lr * 0.18)
    if title:
        bump_title(st, title, lr * 0.22 if success else -lr * 0.18)
    hist = list(st.get("history") or [])
    hist.append(
        {
            "ts": _now(),
            "title": title[:120],
            "category": category,
            "catalog_seed": catalog_seed[:80],
            "card_id": card_id,
            "reward": reward,
            "success": success,
            "source": source,
        }
    )
    st["history"] = hist
    stats = dict(st.get("stats") or {})
    if success:
        stats["pass"] = int(stats.get("pass") or 0) + 1
        if source == "confirm":
            stats["confirm_rewards"] = int(stats.get("confirm_rewards") or 0) + 1
    else:
        stats["fail"] = int(stats.get("fail") or 0) + 1
    st["stats"] = stats


def record_confirm_success(card: dict) -> None:
    if not isinstance(card, dict):
        return
    seed = (card.get("catalog_seed") or "").strip()
    cat = (card.get("category") or "atr_rl").strip()
    if seed.startswith("workisus_atr_") or seed.startswith("wonkisus_atr") or seed.startswith("wonkisus_seven_split_atr"):
        cat = "atr_rl"
    elif "ATR" in (card.get("title") or "") or "atr" in seed:
        cat = "atr_formula"
    st = load_state()
    record_outcome(
        st,
        category=cat,
        title=str(card.get("title") or ""),
        catalog_seed=seed,
        success=True,
        card_id=card.get("id"),
        source="confirm",
    )
    save_state(st)


def _is_atr_card(card: dict) -> bool:
    seed = (card.get("catalog_seed") or "").strip()
    if seed.startswith(("workisus_atr_", "wonkisus_atr", "wonkisus_seven_split_atr")):
        return True
    tags = set(card.get("tags") or [])
    return bool({"ATR", "atr_rl"} & tags) or "ATR" in (card.get("title") or "")


def train_step() -> dict:
    import agent_office_workisus_learn as learn
    import workisus_learning_errors as werr

    st = load_state()
    lr = _lr()
    err_stats = (werr.load().get("stats") or {}).get("by_kind") or {}
    penalties = 0
    for kind, cnt in err_stats.items():
        n = int(cnt)
        if n < 1:
            continue
        penalties += n
        bump_category(st, "meta" if kind in ("too_short", "pii", "tag_missing") else "atr_error", lr * 0.06 * min(n, 5))

    atr_confirmed = 0
    for c in learn.load_store().get("cards") or []:
        if not isinstance(c, dict) or c.get("status") != "confirmed":
            continue
        if not _is_atr_card(c):
            continue
        atr_confirmed += 1
        seed = (c.get("catalog_seed") or "").strip()
        bump_seed(st, seed, lr * 0.04)
        bump_title(st, (c.get("title") or ""), lr * 0.03)

    for c in learn.load_store().get("cards") or []:
        if not isinstance(c, dict) or c.get("status") != "pending":
            continue
        if not _is_atr_card(c):
            continue
        tags = set(c.get("tags") or [])
        if not {"ATR", "무손실", "US"} & tags:
            bump_title(st, (c.get("title") or ""), -lr * 0.05)

    stats = dict(st.get("stats") or {})
    stats["train_steps"] = int(stats.get("train_steps") or 0) + 1
    stats["error_penalties"] = int(stats.get("error_penalties") or 0) + penalties
    st["stats"] = stats
    st["last_train"] = _now()
    save_state(st)
    return {
        "error_kinds": len(err_stats),
        "penalties": penalties,
        "atr_confirmed": atr_confirmed,
        "top_seeds": top_seeds(st, 6),
        "top_categories": top_categories(st, 5),
    }


def top_categories(st: dict, n: int = 5) -> list[dict]:
    cw = st.get("category_weights") or {}
    rows = [{"category": k, "weight": round(float(v), 3)} for k, v in cw.items()]
    rows.sort(key=lambda x: -x["weight"])
    return rows[:n]


def top_seeds(st: dict, n: int = 6) -> list[dict]:
    sw = st.get("seed_weights") or {}
    rows = [{"seed": k, "weight": round(float(v), 3)} for k, v in sw.items()]
    rows.sort(key=lambda x: -x["weight"])
    return rows[:n]


def status() -> dict:
    st = load_state()
    return {
        "epsilon": _epsilon(),
        "learning_rate": _lr(),
        "category_weights": st.get("category_weights") or {},
        "top_seeds": top_seeds(st, 8),
        "top_categories": top_categories(st, 6),
        "stats": dict(st.get("stats") or {}),
        "last_train": st.get("last_train") or "",
        "last_run": st.get("last_run") or "",
        "recent": (st.get("history") or [])[-8:],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["train", "status"], nargs="?", default="status")
    args = p.parse_args()
    if args.cmd == "train":
        print(json.dumps(train_step(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(status(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
