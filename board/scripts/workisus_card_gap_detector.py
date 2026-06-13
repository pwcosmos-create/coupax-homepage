#!/usr/bin/env python3
"""원키스US 학습 카드 갭 탐지 — 카탈로그 시드·에이전트 담당 시드."""
from __future__ import annotations

import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_workisus_learn as learn  # noqa: E402
import workisus_agent_card_map as amap  # noqa: E402
import workisus_card_catalog as catalog  # noqa: E402


def _spec_index() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for spec in catalog.all_workisus_specs():
        seed = (spec.get("catalog_seed") or "").strip()
        if seed:
            out[seed] = spec
    return out


def _used_seeds() -> set[str]:
    out: set[str] = set()
    for c in learn.load_store().get("cards") or []:
        if isinstance(c, dict):
            seed = (c.get("catalog_seed") or "").strip()
            if seed:
                out.add(seed)
    return out


def detect_gaps(*, agent_id: str | None = None) -> dict:
    """missing: catalog 시드 중 cards.json에 없는 항목 (priority 내림차순)."""
    used = _used_seeds()
    idx = _spec_index()
    missing: list[dict] = []

    priority_seeds: list[str] = []
    if agent_id:
        priority_seeds.extend(amap.seeds_for_agent(agent_id))
    priority_seeds.extend(amap.SHARED_CATALOG_PRIORITY)
    try:
        import workisus_error_cards as wec

        for spec in wec.all_error_specs():
            seed = (spec.get("catalog_seed") or "").strip()
            if seed and (spec.get("category") or "") == "ops_error":
                priority_seeds.append(seed)
        import workisus_atr_cards as wac

        for spec in wac.all_atr_specs():
            seed = (spec.get("catalog_seed") or "").strip()
            if seed:
                priority_seeds.append(seed)
    except Exception:
        pass

    seen: set[str] = set()
    ordered: list[str] = []
    for s in priority_seeds:
        if s and s not in seen:
            seen.add(s)
            ordered.append(s)
    for spec in catalog.all_workisus_specs():
        seed = (spec.get("catalog_seed") or "").strip()
        if seed and seed not in seen:
            seen.add(seed)
            ordered.append(seed)

    for seed in ordered:
        if seed in used:
            continue
        spec = idx.get(seed)
        if not spec:
            continue
        missing.append(
            {
                "catalog_seed": seed,
                "title": spec.get("title") or seed,
                "category": spec.get("category") or "workisus",
                "priority": int(spec.get("priority") or 70),
                "spec": spec,
            }
        )

    missing.sort(key=lambda m: -int(m.get("priority") or 0))
    return {
        "missing_count": len(missing),
        "missing": missing,
        "used_seed_count": len(used),
        "catalog_count": len(idx),
    }


def main() -> int:
    import json

    gaps = detect_gaps()
    print(json.dumps(gaps, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
