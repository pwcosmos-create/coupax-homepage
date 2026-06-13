"""
차수거래 학습 카드 강화학습 — 카테고리·제목 밴딧 + 오류·확정 피드백.

  python scripts/kiwoom_card_rl_engine.py train
  python scripts/kiwoom_card_rl_engine.py status
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

STATE_PATH = BOARD / "data" / "kiwoom_learning" / "card_rl_state.json"
CATEGORIES = ("meta", "risk", "ops", "account", "etf", "phase2", "seed", "catalog", "other")

DEFAULT_STATE = {
    "version": 2,
    "epsilon": 0.15,
    "learning_rate": 0.1,
    "category_weights": {},
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
    return float(os.getenv("KIWOM_RL_EPSILON", "0.15") or "0.15")


def _lr() -> float:
    return float(os.getenv("KIWOM_RL_LEARNING_RATE", "0.1") or "0.1")


def load_state() -> dict:
    st = json_store.load_json(STATE_PATH, default=dict(DEFAULT_STATE))
    st.setdefault("category_weights", {})
    st.setdefault("title_bias", {})
    st.setdefault("history", [])
    st.setdefault("stats", dict(DEFAULT_STATE["stats"]))
    return st


def save_state(st: dict) -> None:
    st["updated_at"] = _now()
    st["epsilon"] = _epsilon()
    st["learning_rate"] = _lr()
    hist = st.get("history") or []
    if len(hist) > 250:
        st["history"] = hist[-250:]
    tb = st.get("title_bias") or {}
    if len(tb) > 400:
        keys = sorted(tb.keys(), key=lambda k: tb[k], reverse=True)[:400]
        st["title_bias"] = {k: tb[k] for k in keys}
    json_store.save_json(STATE_PATH, st)


def _slug(title: str) -> str:
    return re.sub(r"[^\w가-힣]+", "_", (title or "").strip())[:48] or "untitled"


def category_weight(st: dict, category: str) -> float:
    w = (st.get("category_weights") or {}).get(category, 1.0)
    return max(0.35, min(4.0, float(w)))


def bump_category(st: dict, category: str, delta: float) -> None:
    cw = dict(st.get("category_weights") or {})
    cat = category if category in CATEGORIES else "other"
    cw[cat] = max(0.35, min(4.0, cw.get(cat, 1.0) + delta))
    st["category_weights"] = cw


def bump_title(st: dict, title: str, delta: float) -> None:
    tb = dict(st.get("title_bias") or {})
    key = _slug(title)
    tb[key] = max(-2.0, min(3.0, float(tb.get(key, 0.0)) + delta))
    st["title_bias"] = tb


def score_gap_item(st: dict, item: dict) -> float:
    cat = str(item.get("category") or "other")
    if cat.startswith("tag:"):
        cat = "catalog"
    pri = float(item.get("priority") or 50)
    title = (item.get("title") or "").strip()
    tb = (st.get("title_bias") or {}).get(_slug(title), 0.0)
    err_boost = 0.0
    if item.get("error_kind"):
        err_boost = 25.0 * category_weight(st, "meta")
    tag_need = int(item.get("tag_need") or 0)
    return pri * category_weight(st, cat) + tb * 8.0 + err_boost + tag_need * 3.0


def rerank_gaps(st: dict, items: list[dict]) -> list[dict]:
    """ε-greedy: exploitation 정렬 + 소량 탐색."""
    if not items:
        return []
    scored = [(score_gap_item(st, m), m) for m in items]
    scored.sort(key=lambda x: (-x[0], x[1].get("title") or ""))
    eps = _epsilon()
    if len(scored) > 2 and random.random() < eps:
        n = min(5, len(scored))
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
    success: bool,
    card_id: int | None = None,
    source: str = "autofill",
) -> None:
    lr = _lr()
    reward = 1.0 if success else -0.8
    bump_category(st, category, -lr * 0.12 if success else lr * 0.18)
    if title:
        bump_title(st, title, lr * 0.25 if success else -lr * 0.2)
    hist = list(st.get("history") or [])
    hist.append(
        {
            "ts": _now(),
            "title": title[:120],
            "category": category,
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
    """수동·자동 확정 시 양성 보상."""
    if not isinstance(card, dict):
        return
    st = load_state()
    tags = card.get("tags") or []
    cat = "ops"
    if "ETF" in tags or "배당" in (card.get("title") or ""):
        cat = "etf"
    elif any(t in tags for t in ("계좌", "이체", "CMA")):
        cat = "account"
    elif any(t in tags for t in ("손절", "익절", "리스크")):
        cat = "risk"
    record_outcome(
        st,
        category=cat,
        title=str(card.get("title") or ""),
        success=True,
        card_id=card.get("id"),
        source="confirm",
    )
    save_state(st)


def train_step() -> dict:
    """오류 로그·확정 카드·대기 카드로 가중치 재학습."""
    import agent_office_kiwoom_learn as learn
    import kiwoom_card_validate as kval
    import kiwoom_learning_errors as kerr

    st = load_state()
    lr = _lr()
    err_stats = (kerr.load().get("stats") or {}).get("by_kind") or {}
    penalties = 0
    for kind, cnt in err_stats.items():
        n = int(cnt)
        if n < 1:
            continue
        penalties += n
        if kind in ("too_short", "pii", "tag_missing", "duplicate"):
            bump_category(st, "meta", lr * 0.08 * min(n, 5))
        bump_category(st, "other", lr * 0.03 * min(n, 3))

    validated = 0
    for c in learn.list_cards(status="pending", limit=15):
        ok, kind, _ = kval.validate_card(c)
        title = (c.get("title") or "").strip()
        if ok:
            bump_title(st, title, lr * 0.05)
            validated += 1
        else:
            bump_category(st, "meta" if kind in ("too_short", "pii", "tag_missing") else "other", lr * 0.1)

    for c in learn.list_cards(limit=40):
        if c.get("status") != "confirmed":
            continue
        tags = set(c.get("tags") or [])
        if {"차수", "1차", "2차", "3차"} & tags and {"손절", "익절", "분할"} & tags:
            bump_title(st, (c.get("title") or ""), lr * 0.02)

    stats = dict(st.get("stats") or {})
    stats["train_steps"] = int(stats.get("train_steps") or 0) + 1
    stats["error_penalties"] = int(stats.get("error_penalties") or 0) + penalties
    st["stats"] = stats
    st["last_train"] = _now()
    save_state(st)
    return {
        "error_kinds": len(err_stats),
        "penalties": penalties,
        "pending_scored": validated,
        "top_categories": top_categories(st, 5),
    }


def top_categories(st: dict, n: int = 5) -> list[dict]:
    cw = st.get("category_weights") or {}
    rows = [{"category": k, "weight": round(float(v), 3)} for k, v in cw.items()]
    rows.sort(key=lambda x: -x["weight"])
    return rows[:n]


def status() -> dict:
    st = load_state()
    stats = dict(st.get("stats") or {})
    return {
        "epsilon": _epsilon(),
        "learning_rate": _lr(),
        "category_weights": st.get("category_weights") or {},
        "top_categories": top_categories(st, 6),
        "stats": stats,
        "last_train": st.get("last_train") or "",
        "last_run": st.get("last_run") or "",
        "recent": (st.get("history") or [])[-6:],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["train", "status"], nargs="?", default="status")
    args = p.parse_args()
    if args.cmd == "train":
        out = train_step()
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(status(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
