"""관상 카탈로그·RL 확장 토픽 갭 탐지."""
from __future__ import annotations

from gwansang_card_catalog import all_gwansang_specs
from gwansang_rl_topics import all_expansion_topics


def _used_seeds_and_titles(store: dict) -> tuple[set[str], set[str]]:
    seeds: set[str] = set()
    titles: set[str] = set()
    for c in store.get("cards") or []:
        if not isinstance(c, dict):
            continue
        seed = (c.get("catalog_seed") or "").strip()
        if seed:
            seeds.add(seed)
        title = gl_normalize_title(c.get("title") or "")
        if title:
            titles.add(title)
    return seeds, titles


def gl_normalize_title(title: str) -> str:
    import re

    return re.sub(r"\s+", " ", (title or "").strip())[:120]


def detect_gaps(*, agent_id: str = "") -> dict:
    import agent_office_gwansang_learn as gl

    store = gl.load_store()
    used_seeds, used_titles = _used_seeds_and_titles(store)
    missing: list[dict] = []
    for spec in all_gwansang_specs():
        seed = (spec.get("catalog_seed") or "").strip()
        if seed and seed not in used_seeds:
            missing.append(
                {
                    "catalog_seed": seed,
                    "title": spec.get("title"),
                    "category": spec.get("category"),
                    "priority": spec.get("priority", 0),
                    "spec": spec,
                }
            )
    missing.sort(key=lambda x: -(int(x.get("priority") or 0)))

    expansion_missing: list[dict] = []
    for topic in all_expansion_topics():
        seed = (topic.get("catalog_seed") or "").strip()
        title = gl_normalize_title(topic.get("title") or "")
        if seed in used_seeds or title in used_titles:
            continue
        expansion_missing.append(dict(topic))

    return {
        "missing": missing,
        "missing_count": len(missing),
        "expansion_missing": expansion_missing,
        "expansion_count": len(expansion_missing),
        "agent_id": agent_id,
    }
