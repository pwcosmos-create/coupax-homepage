#!/usr/bin/env python3
"""원키스US ATR 학습 카드 갭 — catalog_seed·태그·RL 우선 큐."""
from __future__ import annotations

import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_workisus_learn as learn  # noqa: E402
import workisus_atr_cards as atr_cat  # noqa: E402
import workisus_card_catalog as catalog  # noqa: E402

ATR_TAG_MIN = {
    "ATR": 8,
    "무손실": 6,
    "US": 10,
    "슬롯": 6,
    "차수": 4,
}


def _used_seeds() -> set[str]:
    out: set[str] = set()
    for c in learn.load_store().get("cards") or []:
        if isinstance(c, dict):
            seed = (c.get("catalog_seed") or "").strip()
            if seed:
                out.add(seed)
    return out


def _tag_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for c in learn.load_store().get("cards") or []:
        if not isinstance(c, dict) or c.get("status") != "confirmed":
            continue
        for t in c.get("tags") or []:
            counts[t] = counts.get(t, 0) + 1
    return counts


def _atr_specs() -> list[dict]:
    seeds = set()
    specs: list[dict] = []
    for spec in atr_cat.all_atr_specs():
        seed = (spec.get("catalog_seed") or "").strip()
        if seed and seed not in seeds:
            seeds.add(seed)
            specs.append(dict(spec))
    for spec in catalog.all_workisus_specs():
        seed = (spec.get("catalog_seed") or "").strip()
        if not seed or seed in seeds:
            continue
        if "atr" in seed.lower() or "ATR" in (spec.get("title") or ""):
            seeds.add(seed)
            s = dict(spec)
            s.setdefault("category", "atr_rl")
            specs.append(s)
    return specs


def detect_atr_gaps() -> dict:
    used = _used_seeds()
    titles = learn.existing_titles()
    missing: list[dict] = []

    for spec in _atr_specs():
        seed = (spec.get("catalog_seed") or "").strip()
        title = (spec.get("title") or "").strip()
        if not seed or seed in used or title in titles:
            continue
        cat = spec.get("category") or "atr_rl"
        if cat == "ops_error":
            cat = "atr_error"
        missing.append(
            {
                "title": title,
                "catalog_seed": seed,
                "category": cat,
                "priority": int(spec.get("priority") or 85),
                "spec": spec,
            }
        )

    tag_counts = _tag_counts()
    for tag, need in ATR_TAG_MIN.items():
        if tag_counts.get(tag, 0) >= need:
            continue
        missing.append(
            {
                "title": f"__tag__:{tag}",
                "catalog_seed": "",
                "category": "atr_rl",
                "priority": 70,
                "tag_need": need - tag_counts.get(tag, 0),
                "spec": None,
            }
        )

    try:
        import workisus_learning_errors as werr

        by = (werr.load().get("stats") or {}).get("by_kind") or {}
        for kind, cnt in sorted(by.items(), key=lambda x: -int(x[1] or 0)):
            if int(cnt or 0) < 2:
                continue
            missing.append(
                {
                    "title": f"__error_learn__:{kind}",
                    "catalog_seed": "",
                    "category": "meta",
                    "priority": 88,
                    "error_kind": kind,
                    "spec": None,
                }
            )
    except Exception:
        pass

    missing.sort(key=lambda m: -int(m.get("priority") or 0))
    return {
        "missing_count": len(missing),
        "missing": missing,
        "used_seed_count": len(used),
        "atr_catalog": len(_atr_specs()),
        "confirmed": sum(
            1
            for c in learn.load_store().get("cards") or []
            if isinstance(c, dict) and c.get("status") == "confirmed"
        ),
    }


def main() -> int:
    import json

    print(json.dumps(detect_atr_gaps(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
