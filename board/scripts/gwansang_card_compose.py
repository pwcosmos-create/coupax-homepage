"""관상 학습 카드 제작·확정."""
from __future__ import annotations

import gwansang_card_gap_detector as gap_det
import agent_office_gwansang_learn as learn
from gwansang_card_catalog import all_gwansang_specs


def _spec_for_seed(seed: str) -> dict | None:
    for spec in all_gwansang_specs():
        if (spec.get("catalog_seed") or "").strip() == seed:
            return spec
    return None


def compose_next_gap(*, agent_id: str = "gwansang_compose") -> dict | None:
    gaps = gap_det.detect_gaps(agent_id=agent_id)
    missing = gaps.get("missing") or []
    if not missing:
        return None
    row = missing[0]
    seed = (row.get("catalog_seed") or "").strip()
    spec = _spec_for_seed(seed)
    if not spec:
        return None
    card = learn.add_card(
        body=spec.get("body") or "",
        title=spec.get("title") or seed,
        source="catalog_compose",
        catalog_seed=seed,
        category=spec.get("category") or "",
        agent_id=agent_id,
        revise_if_seed_exists=False,
    )
    if card and card.get("id"):
        learn.confirm_card(int(card["id"]))
        card = learn.find_card_by_seed(seed) or card
    return {
        "card_id": card.get("id") if card else None,
        "title": card.get("title") if card else row.get("title"),
        "catalog_seed": seed,
        "status": card.get("status") if card else "pending",
        "agent_id": agent_id,
    }
