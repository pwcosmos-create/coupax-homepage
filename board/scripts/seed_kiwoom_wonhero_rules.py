#!/usr/bin/env python3
"""원히어로 매매 규칙 학습 카드 시드.

  python scripts/seed_kiwoom_wonhero_rules.py --reset   # 전면 교체
  python scripts/seed_kiwoom_wonhero_rules.py --add     # catalog_seed 없는 카드만 추가
  python scripts/seed_kiwoom_wonhero_rules.py --sync    # catalog_seed 있으면 본문·제목 갱신
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_kiwoom_learn as learn  # noqa: E402
import agent_office_wiki_store as wiki  # noqa: E402
import json_store  # noqa: E402
from wonhero_card_catalog import all_wonhero_specs  # noqa: E402

META_PATH = BOARD / "data" / "kiwoom_learning" / "knowledge_structure.json"


def reset_cards() -> None:
    data = {"updated_at": learn._now(), "cards": []}
    json_store.save_json(learn.CARDS_PATH, data)


def _used_seeds() -> set[str]:
    out: set[str] = set()
    for c in learn.load_store().get("cards") or []:
        if not isinstance(c, dict):
            continue
        seed = (c.get("catalog_seed") or "").strip()
        if seed:
            out.add(seed)
    return out


def write_meta_structure(confirmed: list[dict] | None = None) -> None:
    if confirmed is None:
        confirmed = [
            c
            for c in learn.load_store().get("cards") or []
            if isinstance(c, dict) and c.get("status") == "confirmed"
        ]

    def _layer(name: str, pred) -> dict:
        return {
            "id": name.lower().replace(" ", "_"),
            "name": name,
            "cards": [c["id"] for c in confirmed if pred(c)],
        }

    structure = {
        "domain": "kiwoom-chasu",
        "layer": "20_Meta",
        "title": "원히어로 매매 규칙 지식 구조",
        "updated_at": learn._now(),
        "source": "wonhero",
        "layers": [
            _layer("개념", lambda c: "정의" in (c.get("title") or "")),
            _layer(
                "진입·슬롯",
                lambda c: any(k in (c.get("title") or "") for k in ("1차", "2차", "buy_gaps", "15초", "max_slot", "RE_ENTRY")),
            ),
            _layer("ATR", lambda c: "ATR" in (c.get("title") or "") or "atr" in (c.get("tags") or [])),
            _layer("익절·리스크", lambda c: any(k in (c.get("title") or "") for k in ("익절", "합산", "버퍼", "손절"))),
            _layer(
                "계좌·cascade",
                lambda c: "cascade" in (c.get("title") or "").lower()
                or "멀티" in (c.get("title") or "")
                or "trigger" in (c.get("title") or ""),
            ),
            _layer(
                "운영·reconcile",
                lambda c: any(
                    k in (c.get("title") or "")
                    for k in ("봇", "reconcile", "당일", "쿨다운", "장중", "알림", "self-heal", "enabled")
                ),
            ),
            _layer("메타·카드제작", lambda c: "카드제작" in (c.get("title") or "") or "지식 구조" in (c.get("title") or "")),
            _layer(
                "매매원칙",
                lambda c: "매매원칙" in (c.get("title") or "")
                or str(c.get("catalog_seed") or "").startswith("principle_"),
            ),
        ],
        "tag_index": {},
    }
    tag_index: dict[str, list[int]] = {}
    for c in confirmed:
        for t in c.get("tags") or []:
            tag_index.setdefault(t, []).append(c["id"])
    structure["tag_index"] = {k: sorted(set(v)) for k, v in sorted(tag_index.items())}
    try:
        import wonhero_learn_path as lp

        path_ids = []
        for spec in lp.TRADING_LEARN_STEPS:
            seed = spec.get("catalog_seed") or ""
            for c in confirmed:
                if (c.get("catalog_seed") or "").strip() == seed:
                    path_ids.append(c["id"])
                    break
        structure["learning_path"] = {
            "title": "원히어로 매매 방법 — 단계별 학습",
            "steps": [
                {
                    "step": s["step"],
                    "catalog_seed": s["catalog_seed"],
                    "title": s["title"],
                    "card_id": path_ids[i] if i < len(path_ids) else None,
                }
                for i, s in enumerate(lp.TRADING_LEARN_STEPS)
            ],
        }
    except Exception:
        pass
    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(json.dumps(structure, ensure_ascii=False, indent=2), encoding="utf-8")


def _seed_specs(specs: list[dict]) -> tuple[list[int], list[dict]]:
    ids: list[int] = []
    confirmed: list[dict] = []
    for s in specs:
        try:
            card = learn.add_card(
                body=s["body"],
                title=s["title"],
                source="wonhero_seed",
                catalog_seed=str(s.get("catalog_seed") or ""),
                use_council=False,
            )
        except ValueError as e:
            print(f"skip: {s.get('title')}: {e}", file=sys.stderr)
            continue
        cid = card.get("id")
        if isinstance(cid, int):
            ids.append(cid)
            c = learn.confirm_card(cid)
            if c:
                confirmed.append(c)
                wiki.save_kiwoom_card_to_knowledge(c)
    return ids, confirmed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="cards.json 비우고 카탈로그 전체 시드")
    ap.add_argument("--add", action="store_true", help="catalog_seed 없는 카탈로그 항목만 추가")
    ap.add_argument("--sync", action="store_true", help="카탈로그 전체를 seed 기준으로 revise·추가")
    args = ap.parse_args()

    if not args.reset and not args.add and not args.sync:
        print("Use --reset, --add, or --sync", file=sys.stderr)
        return 2

    before = len(learn.load_store().get("cards") or [])
    all_specs = all_wonhero_specs()

    if args.reset:
        reset_cards()
        to_seed = all_specs
    elif args.sync:
        to_seed = all_specs
    else:
        used = _used_seeds()
        titles = learn.existing_titles()
        to_seed = []
        for s in all_specs:
            seed = (s.get("catalog_seed") or "").strip()
            title = learn.normalize_title(s.get("title") or "")
            if seed and seed in used:
                continue
            if title and title in titles:
                continue
            to_seed.append(s)

    ids, confirmed = _seed_specs(to_seed)
    pack = learn.export_pack()
    write_meta_structure()
    after = len(learn.load_store().get("cards") or [])
    print(
        f"before={before} added={len(ids)} confirmed={len(confirmed)} "
        f"after={after} pack={pack.get('card_count')}"
    )
    print(f"meta={META_PATH}")
    print(f"cursor={learn.CURSOR_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
