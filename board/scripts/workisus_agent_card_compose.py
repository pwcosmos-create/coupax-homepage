#!/usr/bin/env python3
"""원키스US 젬마 — 담당 catalog_seed 학습 카드 제작·확정·pack 반영."""
from __future__ import annotations

import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_workisus_learn as learn  # noqa: E402
import agent_office_wiki_store as wiki  # noqa: E402
import workisus_agent_card_map as amap  # noqa: E402
import workisus_card_gap_detector as gap_det  # noqa: E402


def _enrich_body(spec: dict, agent_id: str) -> str:
    body = (spec.get("body") or "").strip()
    footer = amap.trading_footer(agent_id)
    if footer and footer not in body:
        body = f"{body}\n\n【매매 적용】{footer}"
    agent_note = (agent_id or "").strip()
    if agent_note and f"담당 젬마: {agent_note}" not in body:
        body = f"{body}\n\n담당 젬마: {agent_note} · Agent Office workisus-chasu"
    return body[:24000]


def ensure_seed_card(
    seed: str,
    *,
    agent_id: str = "",
    confirm: bool = True,
) -> dict | None:
    """시드 1건 — 없으면 추가, 있으면 본문 동기화 후 선택적 확정."""
    import workisus_learn_policy as wlp

    wlp.require_card_production()
    seed = (seed or "").strip()
    if not seed:
        return None
    from workisus_card_catalog import all_workisus_specs

    spec = None
    for s in all_workisus_specs():
        if (s.get("catalog_seed") or "").strip() == seed:
            spec = s
            break
    if not spec:
        return learn.find_card_by_seed(seed)

    existing = learn.find_card_by_seed(seed)
    body = _enrich_body(spec, agent_id or "workisus_sync")
    if existing and isinstance(existing.get("id"), int):
        learn.revise_card(
            int(existing["id"]),
            body=body,
            title=spec.get("title") or seed,
            catalog_seed=seed,
            reconfirm=existing.get("status") == "confirmed",
        )
        card = learn.find_card_by_seed(seed) or existing
    else:
        card = learn.add_card(
            body=body,
            title=spec.get("title") or seed,
            source="agent_compose",
            catalog_seed=seed,
            category=spec.get("category") or "workisus",
            use_council=False,
        )
    if not card or not isinstance(card.get("id"), int):
        return card
    if confirm and card.get("status") != "confirmed":
        card = learn.confirm_card(int(card["id"])) or card
    try:
        wiki.save_workisus_card_to_knowledge(learn.find_card_by_seed(seed) or card)
    except Exception:
        pass
    return learn.find_card_by_seed(seed) or card


def ensure_agent_cards(agent_id: str, *, confirm: bool = True) -> list[dict]:
    """에이전트 담당 시드 전부 확보."""
    out: list[dict] = []
    for seed in amap.seeds_for_agent(agent_id):
        c = ensure_seed_card(seed, agent_id=agent_id, confirm=confirm)
        if c:
            out.append(c)
    return out


def compose_next_gap(*, agent_id: str = "workisus_curator") -> dict | None:
    """갭 1건 제작 (큐레이터·동기용)."""
    import workisus_learn_policy as wlp

    if not wlp.is_card_production_enabled():
        return None
    gaps = gap_det.detect_gaps(agent_id=agent_id)
    missing = gaps.get("missing") or []
    if not missing:
        return None
    row = missing[0]
    seed = (row.get("catalog_seed") or "").strip()
    if not seed:
        return None
    card = ensure_seed_card(seed, agent_id=agent_id, confirm=True)
    if not card:
        return None
    return {
        "card_id": card.get("id"),
        "title": card.get("title"),
        "catalog_seed": seed,
        "status": card.get("status"),
        "agent_id": agent_id,
    }


def export_trading_context(*, max_cards: int = 32, max_chars: int = 18000) -> str:
    """HTS·Cursor용 플레이북 — wonkisus Wiki 정본 (board 카드 없음)."""
    import workisus_wiki_rules as wr

    _ = max_cards
    return wr.export_trading_context(max_chars=max_chars)


def main() -> int:
    import argparse
    import json

    p = argparse.ArgumentParser()
    p.add_argument("--agent", default="workisus_curator")
    p.add_argument("--gap", action="store_true", help="갭 1건 제작")
    p.add_argument("--ensure-agent", action="store_true")
    p.add_argument("--export-context", action="store_true")
    args = p.parse_args()
    if args.export_context:
        print(export_trading_context())
        return 0
    if args.ensure_agent:
        cards = ensure_agent_cards(args.agent)
        print(json.dumps({"count": len(cards), "ids": [c.get("id") for c in cards]}, ensure_ascii=False))
        return 0
    if args.gap:
        out = compose_next_gap(agent_id=args.agent)
        print(json.dumps(out or {"ok": "no_gap"}, ensure_ascii=False, indent=2))
        learn.export_pack()
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
