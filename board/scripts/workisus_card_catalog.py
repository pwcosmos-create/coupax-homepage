"""원키스 US 카탈로그 — UI(workisus) + 운용 규칙(wonkisus)."""
from __future__ import annotations

from homepage_design_card_catalog import WORKISUS_CARDS
from wonkisus_card_catalog import WONKISUS_RULE_CARDS, all_wonkisus_specs as _rules_only
from wonkisus_seven_split_cards import all_seven_split_specs as _seven_split_specs
from workisus_atr_cards import all_atr_specs as _atr_specs
from workisus_error_cards import all_error_specs as _error_specs


def all_workisus_specs() -> list[dict]:
    by_seed: dict[str, dict] = {}
    for spec in (
        list(_seven_split_specs())
        + list(_atr_specs())
        + list(WORKISUS_CARDS)
        + list(WONKISUS_RULE_CARDS)
        + list(_error_specs())
    ):
        seed = (spec.get("catalog_seed") or "").strip()
        if not seed:
            continue
        prev = by_seed.get(seed)
        if not prev or (spec.get("priority") or 0) >= (prev.get("priority") or 0):
            by_seed[seed] = spec
    return sorted(by_seed.values(), key=lambda s: -(s.get("priority") or 0))


def all_rules_specs() -> list[dict]:
    return _rules_only()
