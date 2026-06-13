#!/usr/bin/env python3
"""
차수거래 학습 카드 자동 추가 (사주 auto_add_cards 와 동일 패턴).

  python scripts/kiwoom_auto_add_cards.py
  python scripts/kiwoom_auto_add_cards.py --hourly 4 --sleep 3
  python scripts/kiwoom_auto_add_cards.py --per-minute 2 --sleep 5
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_kiwoom_learn as learn  # noqa: E402
import kiwoom_card_catalog as catalog  # noqa: E402
import kiwoom_card_rl_autofill as rl  # noqa: E402
import kiwoom_card_validate as kval  # noqa: E402
import kiwoom_learning_errors as kerr  # noqa: E402


def _existing_titles() -> set[str]:
    return learn.existing_titles()


def ingest_pool(*, max_add: int = 2, sleep_sec: float = 0, train_first: bool = True) -> int:
    try:
        import wonhero_catalog_maintain as wcm

        wcm.run(merge=True, sync=True, dedupe=True, wiki=False)
    except Exception as e:
        print(f"catalog_maintain: {e}", file=sys.stderr)
    if train_first:
        try:
            import kiwoom_card_rl_engine as rle

            rle.train_step()
        except Exception:
            pass
    titles = _existing_titles()
    used_seeds = {
        (c.get("catalog_seed") or "").strip()
        for c in learn.load_store().get("cards") or []
        if isinstance(c, dict) and (c.get("catalog_seed") or "").strip()
    }
    pending = []
    for s in catalog.KIWOOM_AUTO_CARD_POOL:
        seed = (s.get("catalog_seed") or s.get("title") or "").strip()
        if seed in used_seeds:
            continue
        pending.append(s)
    pending.sort(key=lambda s: -int(s.get("priority") or 0))
    pending = pending[: max(0, max_add)]
    import kiwoom_card_council as kc
    import kiwoom_card_title_compose as kt

    added = 0
    for raw in pending:
        spec = kt.enrich_spec(dict(raw), taken=titles)
        title = learn.normalize_title(spec.get("title") or "")
        if not title or title in titles:
            continue
        if kc.council_enabled():
            out = kc.create_card_via_council(spec, source="auto_pool")
            if out and out.get("card_id"):
                titles.add(title)
                added += 1
                if sleep_sec > 0:
                    time.sleep(sleep_sec)
            continue
        body = (spec.get("body") or "").strip()
        ok, kind, hint = kval.validate_spec(title, body)
        if not ok:
            kerr.record(kind, hint, title=title)
            continue
        try:
            card = learn.add_card(
                body=body,
                title=title,
                source="auto_pool",
                catalog_seed=str(spec.get("catalog_seed") or ""),
                use_council=False,
            )
        except ValueError as e:
            kerr.record("too_short", str(e)[:200], title=title)
            continue
        cid = card.get("id")
        if not isinstance(cid, int):
            continue
        if not learn.confirm_card(cid, export_pack_now=False):
            learn.delete_card(cid)
            kerr.record("confirm_failed", "확정 실패", title=title, card_id=cid)
            continue
        titles.add(title)
        added += 1
        if sleep_sec > 0:
            time.sleep(sleep_sec)
    if added:
        learn.export_pack()
        try:
            import sync_kiwoom_wiki

            sync_kiwoom_wiki.main()
        except Exception:
            pass
    return added


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--max", type=int, default=None)
    p.add_argument("--hourly", type=int, default=None)
    p.add_argument("--per-minute", type=int, default=None)
    p.add_argument("--sleep", type=float, default=0)
    p.add_argument("--rl", action="store_true", help="RL 갭 보충도 실행")
    args = p.parse_args()

    if args.hourly is not None:
        n = ingest_pool(max_add=args.hourly, sleep_sec=args.sleep)
        print(f"pool_added={n}")
        if args.rl:
            out = rl.run(max_add=min(2, args.hourly), sleep_sec=args.sleep)
            print("rl", out)
        return 0
    if args.per_minute is not None:
        n = ingest_pool(max_add=args.per_minute, sleep_sec=args.sleep)
        print(f"pool_added={n}")
        return 0

    max_add = args.max if args.max is not None else 2
    n = ingest_pool(max_add=max_add, sleep_sec=args.sleep)
    print(f"pool_added={n}")
    if args.rl or n == 0:
        out = rl.run(max_add=max_add, sleep_sec=args.sleep)
        print("rl", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
