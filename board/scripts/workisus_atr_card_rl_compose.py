"""ATR 강화학습 카드 본문·제목 보강 — RL 상태·HTS atr_rl 스냅샷 반영."""
from __future__ import annotations

import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import workisus_atr_card_rl_engine as rle  # noqa: E402


def _hts_atr_rl_us() -> dict | None:
    try:
        import auto_bot

        snap = auto_bot.atr_rl_snapshot()
        if snap.get("ok") and isinstance(snap.get("us"), dict):
            return snap["us"]
    except Exception:
        pass
    return None


def enrich_spec(spec: dict, *, error_kind: str = "") -> dict:
    """RL 메타·습관 점수를 카드 spec에 붙인다."""
    spec = dict(spec or {})
    st = rle.load_state()
    seed = (spec.get("catalog_seed") or "").strip()
    cat = spec.get("category") or "atr_rl"
    if cat == "ops_error":
        cat = "atr_error"
    if seed.startswith("workisus_atr_") or seed.startswith("wonkisus_atr"):
        cat = "atr_rl"

    sw = rle.seed_weight(st, seed) if seed else 1.0
    cw = rle.category_weight(st, cat)
    us_rl = _hts_atr_rl_us()
    rl_lines = [
        "【ATR 강화학습 카드】",
        f"RL 카테고리={cat} · seed가중치={sw:.2f} · category가중치={cw:.2f} · ε={rle._epsilon():.2f}",
    ]
    if us_rl:
        rl_lines.append(
            f"HTS ATR습관(US): 누적={us_rl.get('cumulative', 0)} ema={float(us_rl.get('ema', 0)):.3f} "
            "(atr_rl_record_success·미실행 페널티)"
        )
    if error_kind:
        rl_lines.append(f"오류학습 kind={error_kind}")
    rl_lines.append(
        "무손실 ATR 정본: sell 1.5~4%(ATR×1.2)·buy_gap×1.15·1차999%·합산평단>0%만 익절."
    )
    block = "\n".join(rl_lines)
    body = (spec.get("body") or "").strip()
    if "【ATR 강화학습 카드】" not in body:
        spec["body"] = f"{body}\n\n{block}" if body else block
    spec["category"] = "atr_rl"
    spec["rl_enriched"] = True
    if not spec.get("title"):
        spec["title"] = f"ATR·RL · {seed or '학습'}"
    elif "RL" not in spec["title"] and "강화학습" not in spec["title"]:
        spec["title"] = f"{spec['title']} · RL"
    return spec


def _error_spec(kind: str) -> dict | None:
    import workisus_learning_errors as werr
    import workisus_error_cards as wec

    for spec in wec.CARD_MAKING_ERROR_CARDS:
        if spec.get("error_kind") == kind:
            return enrich_spec(dict(spec), error_kind=kind)
    hint = werr.playbook_hint(kind)
    return enrich_spec(
        {
            "title": f"원키스US 오류 · {kind}",
            "catalog_seed": f"workisus_err_rl_{kind}"[:120],
            "category": "meta",
            "priority": 87,
            "body": (
                f"오류 {kind} (누적 RL 학습).\n수정: {hint}\n"
                "ATR·무손실·US·슬롯·차수·buy_gaps·sell_pcts 키워드 포함."
            ),
        },
        error_kind=kind,
    )
