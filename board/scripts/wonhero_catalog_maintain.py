#!/usr/bin/env python3
"""원히어로·매매원칙 카탈로그 — 항상 제작(sync) + 구형 카드 합치기(merge).

  python scripts/wonhero_catalog_maintain.py run
  python scripts/wonhero_catalog_maintain.py run --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_kiwoom_learn as learn  # noqa: E402
import agent_office_wiki_store as wiki  # noqa: E402
from wonhero_card_catalog import all_wonhero_specs  # noqa: E402

# 구형 제목 → 현행 catalog_seed (제목 변경·중복 합침)
LEGACY_TITLE_TO_SEED: dict[str, str] = {
    learn.normalize_title("손절 자동매도 없음 — 익절만"): "wonhero_no_stop_loss",
    learn.normalize_title("원히어로·차수거래 정의"): "wonhero_def",
    learn.normalize_title("MagicSplit·원히어로 정의"): "wonhero_def",
    learn.normalize_title("1차 수동·HTS 매수"): "wonhero_slot1_manual",
    learn.normalize_title("2차 즉시 매수·15초"): "wonhero_instant_2nd",
}

# 잘못된 seed·구 시드 접두
INVALID_SEEDS = frozenset({"catalog_seed", "chasu", "kiwoom_chasu", ""})
LEGACY_SOURCE_RE = re.compile(
    r"chasu|hero_hts|manual_chasu|catalog_seed|kiwoom_chasu",
    re.I,
)


def _canonical_maps() -> tuple[dict[str, dict], dict[str, dict]]:
    by_seed: dict[str, dict] = {}
    by_title: dict[str, dict] = {}
    for s in all_wonhero_specs():
        seed = (s.get("catalog_seed") or "").strip()
        if seed:
            by_seed[seed] = s
        t = learn.normalize_title(s.get("title") or "")
        if t:
            by_title[t] = s
    return by_seed, by_title


def _pick_keeper(rows: list[dict]) -> dict:
    confirmed = [c for c in rows if c.get("status") == "confirmed"]
    pool = confirmed or rows
    return max(pool, key=lambda c: (c.get("id") or 0))


def _resolve_target_seed(
    card: dict,
    *,
    by_seed: dict[str, dict],
    by_title: dict[str, dict],
) -> str | None:
    raw = (card.get("catalog_seed") or "").strip()
    if raw in INVALID_SEEDS:
        raw = ""
    if raw and raw in by_seed:
        return raw
    title = learn.normalize_title(card.get("title") or "")
    if title in LEGACY_TITLE_TO_SEED:
        s = LEGACY_TITLE_TO_SEED[title]
        if s in by_seed:
            return s
    if title in by_title:
        return (by_title[title].get("catalog_seed") or "").strip() or None
    body = (card.get("body") or "") + " " + (card.get("title") or "")
    src = (card.get("source") or "")
    if LEGACY_SOURCE_RE.search(src) or LEGACY_SOURCE_RE.search(body[:200]):
        for t, spec in by_title.items():
            if t and t in title:
                return (spec.get("catalog_seed") or "").strip() or None
    return None


def merge_legacy_cards(*, dry_run: bool = True) -> dict:
    """동일 catalog_seed·구형 제목 카드를 1장으로 합침(나머지 삭제)."""
    by_seed, by_title = _canonical_maps()
    store = learn.load_store()
    cards = [c for c in store.get("cards") or [] if isinstance(c, dict)]

    groups: dict[str, list[dict]] = defaultdict(list)
    unmapped: list[dict] = []

    for c in cards:
        seed = _resolve_target_seed(c, by_seed=by_seed, by_title=by_title)
        if seed:
            groups[seed].append(c)
        else:
            unmapped.append(c)

    delete_ids: list[int] = []
    reassigned: list[int] = []

    for seed, rows in groups.items():
        if len(rows) < 2:
            only = rows[0]
            cur = (only.get("catalog_seed") or "").strip()
            if cur != seed and not dry_run:
                learn.revise_card(
                    int(only["id"]),
                    catalog_seed=seed,
                    reconfirm=only.get("status") == "confirmed",
                )
                reassigned.append(int(only["id"]))
            continue
        keeper = _pick_keeper(rows)
        kid = keeper.get("id")
        for c in rows:
            cid = c.get("id")
            if isinstance(cid, int) and cid != kid:
                delete_ids.append(cid)
        if (keeper.get("catalog_seed") or "").strip() != seed and not dry_run:
            learn.revise_card(
                int(kid),
                catalog_seed=seed,
                reconfirm=keeper.get("status") == "confirmed",
            )
            reassigned.append(int(kid))

    # 제목만 같고 seed 없는 중복(카탈로그 제목과 일치)
    title_groups: dict[str, list[dict]] = defaultdict(list)
    for c in unmapped:
        t = learn.normalize_title(c.get("title") or "")
        if t in by_title:
            title_groups[t].append(c)
    for t, rows in title_groups.items():
        spec = by_title[t]
        seed = (spec.get("catalog_seed") or "").strip()
        if not seed:
            continue
        if seed in groups and groups[seed]:
            keeper_id = _pick_keeper(groups[seed]).get("id")
            for c in rows:
                cid = c.get("id")
                if isinstance(cid, int) and cid != keeper_id:
                    delete_ids.append(cid)
        elif len(rows) >= 1 and not dry_run:
            k = _pick_keeper(rows)
            learn.revise_card(
                int(k["id"]),
                title=spec.get("title"),
                body=spec.get("body"),
                catalog_seed=seed,
                reconfirm=k.get("status") == "confirmed",
            )
            reassigned.append(int(k["id"]))

    deleted = 0
    if not dry_run:
        for cid in sorted(set(delete_ids)):
            if learn.delete_card(cid):
                deleted += 1

    return {
        "dry_run": dry_run,
        "canonical_seeds": len(by_seed),
        "mapped_groups": len(groups),
        "duplicate_groups": sum(1 for r in groups.values() if len(r) > 1),
        "would_delete": len(set(delete_ids)),
        "deleted": deleted,
        "reassigned": len(reassigned),
        "unmapped": len(unmapped),
    }


def sync_catalog_specs(*, dry_run: bool = True) -> dict:
    """카탈로그 전체 — 없으면 추가, 있으면 revise(항상 최신 본문·제목)."""
    if dry_run:
        used = {
            (c.get("catalog_seed") or "").strip()
            for c in learn.load_store().get("cards") or []
            if isinstance(c, dict)
        }
        missing = [
            s
            for s in all_wonhero_specs()
            if (s.get("catalog_seed") or "").strip() not in used
        ]
        return {
            "dry_run": True,
            "would_sync": len(all_wonhero_specs()),
            "would_add": len(missing),
        }

    added = 0
    revised = 0
    skipped = 0
    for s in all_wonhero_specs():
        seed = (s.get("catalog_seed") or "").strip()
        if not seed:
            skipped += 1
            continue
        try:
            card = learn.add_card(
                body=s["body"],
                title=s["title"],
                source="wonhero_maintain",
                catalog_seed=seed,
                use_council=False,
            )
        except ValueError as e:
            print(f"skip: {s.get('title')}: {e}", file=sys.stderr)
            skipped += 1
            continue
        if card.get("_revised"):
            revised += 1
            if card.get("status") != "confirmed":
                learn.confirm_card(int(card["id"]))
        else:
            added += 1
            c = learn.confirm_card(int(card["id"]))
            if c:
                wiki.save_kiwoom_card_to_knowledge(c)
    if added or revised:
        learn.export_pack()
    return {
        "dry_run": False,
        "synced": len(all_wonhero_specs()),
        "added": added,
        "revised": revised,
        "skipped": skipped,
    }


def run(
    *,
    dry_run: bool = False,
    merge: bool = True,
    sync: bool = True,
    dedupe: bool = True,
    wiki: bool = True,
) -> dict:
    out: dict = {"dry_run": dry_run}
    if merge:
        out["merge"] = merge_legacy_cards(dry_run=dry_run)
    if dedupe and not dry_run:
        import dedupe_kiwoom_cards_by_seed as dd

        out["dedupe"] = dd.run(dry_run=False)
    if sync:
        out["sync"] = sync_catalog_specs(dry_run=dry_run)
    if not dry_run:
        try:
            from seed_kiwoom_wonhero_rules import write_meta_structure

            write_meta_structure()
            out["meta"] = True
        except Exception as e:
            out["meta_error"] = str(e)[:120]
        if wiki:
            try:
                import sync_kiwoom_wiki

                sync_kiwoom_wiki.main()
                out["wiki"] = True
            except Exception as e:
                out["wiki_error"] = str(e)[:120]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", nargs="?", default="run", choices=("run", "merge", "sync"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-merge", action="store_true")
    ap.add_argument("--no-sync", action="store_true")
    ap.add_argument("--no-dedupe", action="store_true")
    ap.add_argument("--no-wiki", action="store_true")
    args = ap.parse_args()

    if args.command == "merge":
        out = merge_legacy_cards(dry_run=args.dry_run)
    elif args.command == "sync":
        out = sync_catalog_specs(dry_run=args.dry_run)
    else:
        out = run(
            dry_run=args.dry_run,
            merge=not args.no_merge,
            sync=not args.no_sync,
            dedupe=not args.no_dedupe,
            wiki=not args.no_wiki,
        )
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
