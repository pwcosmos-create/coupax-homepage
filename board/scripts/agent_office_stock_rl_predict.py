"""
오늘 관심종목 상승·하락·횡보 예측 — 컨텍스트 밴딧형 강화학습 (선형 Q, ε-greedy).

  python scripts/agent_office_stock_rl_predict.py run
  python scripts/agent_office_stock_rl_predict.py status

환경 변수:
  STOCK_RL_EPSILON=0.12
  STOCK_RL_LEARNING_RATE=0.08
  STOCK_RL_FLAT_THRESHOLD_PCT=0.45
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import json_store  # noqa: E402
import agent_office_stock_watch as sw  # noqa: E402

STATE_PATH = BOARD / "data" / "stock_watch" / "stock_rl_state.json"
ACTIONS = ("down", "flat", "up")
ACTION_KO = {"down": "하락", "flat": "횡보", "up": "상승"}
N_FEATURES = 8

DEFAULT_STATE = {
    "version": 1,
    "weights": {
        "up": [0.18, 0.06, 0.22, 0.08, 0.04, 0.02, 0.05, 0.06],
        "flat": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.12],
        "down": [-0.18, -0.06, -0.22, -0.08, -0.04, -0.02, -0.05, 0.06],
    },
    "symbol_bias": {},
    "pending": [],
    "history": [],
    "stats": {"predictions": 0, "settled": 0, "hits": 0},
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _epsilon() -> float:
    return float(os.getenv("STOCK_RL_EPSILON", "0.12") or "0.12")


def _lr() -> float:
    return float(os.getenv("STOCK_RL_LEARNING_RATE", "0.08") or "0.08")


def _flat_thr() -> float:
    return float(os.getenv("STOCK_RL_FLAT_THRESHOLD_PCT", "0.45") or "0.45")


def load_state() -> dict:
    st = json_store.load_json(STATE_PATH, default=dict(DEFAULT_STATE))
    st.setdefault("weights", dict(DEFAULT_STATE["weights"]))
    for a in ACTIONS:
        w = list((st["weights"].get(a) or DEFAULT_STATE["weights"][a]))
        if len(w) < N_FEATURES:
            w.extend([0.0] * (N_FEATURES - len(w)))
        st["weights"][a] = w[:N_FEATURES]
    st.setdefault("symbol_bias", {})
    st.setdefault("pending", [])
    st.setdefault("history", [])
    st.setdefault("stats", dict(DEFAULT_STATE["stats"]))
    return st


def save_state(st: dict) -> None:
    st["updated_at"] = _now()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    json_store.save_json(STATE_PATH, st)


def _label_from_pct(pct: float) -> str:
    thr = _flat_thr()
    if pct > thr:
        return "up"
    if pct < -thr:
        return "down"
    return "flat"


def _signal_score(signal: str) -> float:
    s = (signal or "").strip()
    if s in ("강세",):
        return 1.0
    if s in ("약한 상승",):
        return 0.45
    if s in ("약세",):
        return -1.0
    if s in ("약한 하락",):
        return -0.45
    return 0.0


def _index_change(snap: dict, region: str) -> float:
    mk = (snap.get("markets") or {}).get(region) or {}
    for q in mk.get("indices") or []:
        if isinstance(q, dict):
            return float(q.get("change_pct") or 0) / 10.0
    return 0.0


def _analyst_score(ins: dict, symbol: str, name: str) -> float:
    items = (ins.get("analyst_reports") or {}).get("items") or []
    sym_u = (symbol or "").upper()
    name_l = (name or "").lower()
    hits = 0
    bull = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        co = (it.get("company") or "").lower()
        if sym_u and sym_u[:4] in co:
            hits += 1
        elif name_l and name_l[:2] in co:
            hits += 1
        else:
            continue
        topic = (it.get("topic") or "").lower()
        if any(k in topic for k in ("매수", "buy", "상향", "목표가 상향")):
            bull += 1
        if any(k in topic for k in ("매도", "sell", "하향", "축소")):
            bull -= 1
    if hits == 0:
        return 0.0
    return max(-1.0, min(1.0, bull / max(hits, 1)))


def _news_score(ins: dict) -> float:
    news = (ins.get("news") or {}).get("items") or []
    if not news:
        return 0.0
    pos = sum(
        1
        for it in news[:8]
        if isinstance(it, dict)
        and any(k in (it.get("title") or "").lower() for k in ("상승", "급등", "호재", "surge"))
    )
    neg = sum(
        1
        for it in news[:8]
        if isinstance(it, dict)
        and any(k in (it.get("title") or "").lower() for k in ("하락", "급락", "악재", "plunge"))
    )
    return max(-1.0, min(1.0, (pos - neg) / 4.0))


def build_features(
    q: dict,
    *,
    snap: dict,
    ins: dict,
    chart_by_sym: dict[str, dict],
) -> list[float]:
    sym = q.get("symbol") or ""
    region = q.get("region") or ("kr" if ".KS" in sym or sym.startswith("^K") else "us")
    pct = float(q.get("change_pct") or 0)
    chart = chart_by_sym.get(sym) or {}
    is_index = (sym or "").startswith("^")
    return [
        max(-3.0, min(3.0, pct / 10.0)),
        _signal_score(chart.get("signal") or ""),
        _index_change(snap, region),
        _analyst_score(ins, sym, q.get("name") or ""),
        _news_score(ins),
        1.0 if not is_index else 0.0,
        1.0 if region == "kr" else 0.0,
        1.0,
    ]


def _q_value(st: dict, action: str, features: list[float], symbol: str) -> float:
    w = st["weights"].get(action) or DEFAULT_STATE["weights"][action]
    q = sum(float(w[i]) * float(features[i]) for i in range(N_FEATURES))
    bias = (st.get("symbol_bias") or {}).get(symbol) or {}
    q += float(bias.get(action, 0.0))
    return q


def _softmax_choice(st: dict, features: list[float], symbol: str, *, explore: bool) -> tuple[str, float, dict[str, float]]:
    import random

    scores = {a: _q_value(st, a, features, symbol) for a in ACTIONS}
    if explore and random.random() < _epsilon():
        action = random.choice(ACTIONS)
        conf = 0.33
        return action, conf, scores
    mx = max(scores.values())
    exps = {a: math.exp(scores[a] - mx) for a in ACTIONS}
    z = sum(exps.values()) or 1.0
    probs = {a: exps[a] / z for a in ACTIONS}
    action = max(probs, key=probs.get)
    conf = probs[action]
    return action, conf, scores


def _update_weights(
    st: dict,
    action: str,
    features: list[float],
    reward: float,
    symbol: str,
) -> None:
    lr = _lr()
    q = _q_value(st, action, features, symbol)
    err = reward - q
    w = list(st["weights"][action])
    for i in range(N_FEATURES):
        w[i] = float(w[i]) + lr * err * float(features[i])
    st["weights"][action] = w
    sb = dict(st.get("symbol_bias") or {})
    cur = dict(sb.get(symbol) or {})
    cur[action] = float(cur.get(action, 0.0)) + lr * err * 0.35
    sb[symbol] = cur
    st["symbol_bias"] = sb


def _reward(predicted: str, actual: str) -> float:
    if predicted == actual:
        return 1.0
    if predicted == "flat" or actual == "flat":
        return -0.35
    return -1.0


def settle_pending(st: dict, snap: dict) -> list[dict]:
    """이전 예측과 현재 시세를 비교해 RL 가중치 갱신."""
    pending = list(st.get("pending") or [])
    if not pending:
        return []
    quotes: dict[str, dict] = {}
    for q in sw.iter_kr_quotes(snap):
        sym = q.get("symbol") or ""
        if sym:
            quotes[sym] = q

    settled: list[dict] = []
    remain: list[dict] = []
    for p in pending:
        sym = p.get("symbol") or ""
        q = quotes.get(sym)
        if not q:
            remain.append(p)
            continue
        old_pct = float(p.get("change_pct") or 0)
        new_pct = float(q.get("change_pct") or 0)
        delta = new_pct - old_pct
        actual = _label_from_pct(delta)
        pred = p.get("predicted") or "flat"
        rew = _reward(pred, actual)
        feats = p.get("features") or []
        if len(feats) >= N_FEATURES:
            _update_weights(st, pred, feats, rew, sym)
        settled.append(
            {
                "symbol": sym,
                "predicted": pred,
                "actual": actual,
                "reward": rew,
                "delta_pct": round(delta, 3),
            }
        )
        st["stats"]["settled"] = int(st["stats"].get("settled") or 0) + 1
        if rew > 0:
            st["stats"]["hits"] = int(st["stats"].get("hits") or 0) + 1

    st["pending"] = remain
    hist = list(st.get("history") or [])
    hist.extend(settled[-40:])
    st["history"] = hist[-120:]
    return settled


def _chart_map(ins: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for it in (ins.get("chart") or {}).get("items") or []:
        if isinstance(it, dict) and it.get("symbol"):
            out[it["symbol"]] = it
    return out


def _all_watch_quotes(snap: dict) -> list[dict]:
    import agent_office_stock_watch as sw

    out: list[dict] = []
    for q in sw.iter_kr_quotes(snap, buckets=sw.KR_EQUITY_BUCKETS):
        if (q.get("symbol") or "").startswith("^"):
            continue
        row = dict(q)
        row["bucket"] = q.get("bucket") or q.get("pool") or "watchlist"
        out.append(row)
    return out


def run_predictions(*, explore: bool = True) -> dict:
    snap = sw.load_snapshot()
    if not snap.get("updated_at"):
        sync = sw.sync_market_data(force=False)
        if sync.get("ok"):
            snap = sw.load_snapshot()

    ins = sw.load_insights()
    st = load_state()
    settled = settle_pending(st, snap)
    chart_map = _chart_map(ins)
    items: list[dict] = []
    pending_new: list[dict] = []

    for q in _all_watch_quotes(snap):
        sym = q.get("symbol") or ""
        feats = build_features(q, snap=snap, ins=ins, chart_by_sym=chart_map)
        action, conf, scores = _softmax_choice(st, feats, sym, explore=explore)
        pct = float(q.get("change_pct") or 0)
        reasons: list[str] = []
        if abs(pct) >= 1.0:
            reasons.append(f"당일 {pct:+.2f}%")
        sig = (chart_map.get(sym) or {}).get("signal")
        if sig:
            reasons.append(f"차트 {sig}")
        if scores:
            ranked = sorted(scores.items(), key=lambda x: -x[1])
            reasons.append(
                "Q점수 "
                + ", ".join(f"{ACTION_KO[a]} {v:.2f}" for a, v in ranked)
            )

        items.append(
            {
                "symbol": sym,
                "name": q.get("name") or sym,
                "region": q.get("region"),
                "bucket": q.get("bucket") or q.get("pool") or "",
                "change_pct": pct,
                "predicted": action,
                "predicted_ko": ACTION_KO[action],
                "confidence": round(conf, 3),
                "scores": {ACTION_KO[k]: round(v, 3) for k, v in scores.items()},
                "reason": " · ".join(reasons)[:240],
                "price": q.get("price"),
            }
        )
        pending_new.append(
            {
                "date": _today(),
                "ts": _now(),
                "symbol": sym,
                "predicted": action,
                "features": feats,
                "change_pct": pct,
                "price": q.get("price"),
                "bucket": q.get("bucket") or q.get("pool") or "",
            }
        )

    pool_rank = {"kospi200": 0, "kosdaq150": 1, "watchlist": 2}
    items.sort(
        key=lambda x: (
            pool_rank.get(x.get("bucket") or "", 3),
            -float(x.get("confidence") or 0),
        )
    )
    st["pending"] = (list(st.get("pending") or []) + pending_new)[-80:]
    st["stats"]["predictions"] = int(st.get("stats", {}).get("predictions") or 0) + len(
        items
    )
    save_state(st)

    summary_lines = [
        f"RL예측젬마 ({_now()}) — ε={_epsilon():.2f}, 학습률={_lr():.2f}",
        f"정산 {len(settled)}건 · 누적 적중 {st['stats'].get('hits', 0)}/{max(st['stats'].get('settled', 0), 1)}",
    ]
    for it in items[:6]:
        if (it.get("bucket") or "") not in ("kospi200", "kosdaq150", "watchlist"):
            continue
        if (it.get("symbol") or "").startswith("^"):
            continue
        summary_lines.append(
            f"  · {it.get('name')}: {it.get('predicted_ko')} "
            f"(신뢰 {float(it.get('confidence') or 0):.0%})"
        )
    summary = "\n".join(summary_lines)[:2000]

    block = sw.save_insights_section(
        "rl_predictions",
        items,
        summary=summary,
        extra={
            "model": "contextual_bandit_linear_q",
            "epsilon": _epsilon(),
            "settled_last_run": len(settled),
            "stats": dict(st.get("stats") or {}),
        },
    )
    return {
        "ok": True,
        "items": len(items),
        "settled": len(settled),
        "summary": block.get("summary", "")[:200],
    }


def status() -> dict:
    st = load_state()
    ins = sw.load_insights()
    rl = ins.get("rl_predictions") or {}
    return {
        "state_updated": st.get("updated_at"),
        "stats": st.get("stats"),
        "pending_count": len(st.get("pending") or []),
        "predictions_ts": rl.get("ts"),
        "predictions_count": len(rl.get("items") or []),
        "weights_sample": {a: (st.get("weights") or {}).get(a, [])[:4] for a in ACTIONS},
    }


def main() -> int:
    try:
        import board_env

        board_env.load_board_env()
    except ImportError:
        pass

    p = argparse.ArgumentParser(description="주식 RL 상승·하락 예측")
    p.add_argument("cmd", choices=["run", "status"], nargs="?", default="run")
    args = p.parse_args()
    if args.cmd == "status":
        out = status()
    else:
        out = run_predictions()
    print(out)
    return 0 if out.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
