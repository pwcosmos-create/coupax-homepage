#!/usr/bin/env python3
"""차수거래 갭 탐지 → RL 우선순위 → 카드 자동 제작·오류 학습.

  python scripts/kiwoom_card_rl_autofill.py --dry-run
  python scripts/kiwoom_card_rl_autofill.py --max-add 2
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import board_env

board_env.load_board_env()

import agent_office_kiwoom_learn as learn  # noqa: E402
import json_store  # noqa: E402
import kiwoom_card_gap_detector as gap_det  # noqa: E402
import kiwoom_card_rl_engine as rle  # noqa: E402
import kiwoom_card_validate as kval  # noqa: E402
import kiwoom_learning_errors as kerr  # noqa: E402


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def load_state() -> dict:
    return rle.load_state()


def save_state(st: dict) -> None:
    rle.save_state(st)


def _rank_missing(st: dict, gaps: dict) -> list[dict]:
    items: list[dict] = []
    for m in gaps.get("missing") or []:
        if not isinstance(m, dict):
            continue
        title = str(m.get("title") or "")
        if title.startswith("__tag__:"):
            continue
        if title.startswith("__error_learn__:"):
            m = dict(m)
            m["spec"] = _error_spec(title.split(":", 1)[-1])
            if not m["spec"]:
                continue
        if not m.get("spec"):
            continue
        items.append(m)
    return rle.rerank_gaps(st, items)


def _error_spec(kind: str) -> dict | None:
    seed = f"meta_err_{kind}"
    try:
        import kiwoom_card_catalog as cat

        for spec in cat.all_catalog_specs():
            if (spec.get("catalog_seed") or "").strip() == seed:
                return dict(spec)
    except Exception:
        pass
    hint = kerr.playbook_hint(kind)
    body = (
        f"오류 유형: {kind}.\n"
        f"수정: {hint}\n"
        "1차 수동·15초 2차·ATR buy_gaps·sell_pcts 익절·슬롯·계좌 키워드를 본문에 포함. "
        "계좌번호·API키는 저장하지 않는다."
    )
    try:
        import kiwoom_card_title_compose as kt

        return kt.enrich_spec(
            {
                "body": body,
                "category": "meta",
                "priority": 93,
                "error_kind": kind,
                "catalog_seed": seed,
            },
            error_kind=kind,
        )
    except Exception:
        return {
            "title": f"카드제작 가이드 · {kind}",
            "body": body,
            "category": "meta",
            "priority": 93,
            "catalog_seed": seed,
        }


def _existing_titles() -> set[str]:
    return learn.existing_titles()


def _ingest_spec(spec: dict) -> int | None:
    import kiwoom_card_council as kc

    if kc.council_enabled():
        out = kc.create_card_via_council(spec, source="rl_autofill", log_feed=True)
        if out and out.get("card_id"):
            return int(out["card_id"])
        title = learn.normalize_title(spec.get("title") or "")
        if title and title in _existing_titles():
            kerr.record("duplicate", "제목 중복 — 제작 생략", title=title)
            return None
        if title:
            kerr.record("confirm_failed", "협업 제작 실패", title=title)
        return None

    title = (spec.get("title") or "").strip()
    body = (spec.get("body") or "").strip()
    if title in _existing_titles():
        kerr.record("duplicate", "제목 중복", title=title)
        return None
    ok, kind, hint = kval.validate_spec(title, body)
    if not ok:
        kerr.record(kind, hint, title=title)
        return None
    try:
        card = learn.add_card(body=body, title=title, source="rl_autofill", use_council=False)
    except ValueError as e:
        kerr.record("too_short", str(e)[:200], title=title)
        return None
    cid = card.get("id")
    if not isinstance(cid, int):
        return None
    confirmed = learn.confirm_card(cid, export_pack_now=False)
    if not confirmed:
        learn.delete_card(cid)
        kerr.record("confirm_failed", "확정 실패", title=title, card_id=cid)
        return None
    return cid


def run(
    *,
    max_add: int = 2,
    sleep_sec: float = 0.3,
    dry_run: bool = False,
    train_first: bool = True,
) -> dict:
    st = load_state()
    train_info: dict = {}
    if train_first and not dry_run:
        train_info = rle.train_step()
    kerr.ensure_error_learning_cards()
    gaps = gap_det.detect_gaps()
    ranked = _rank_missing(st, gaps)
    plan = ranked[: max(0, max_add)]

    result: dict = {
        "dry_run": dry_run,
        "gaps": {
            "missing_count": gaps.get("missing_count"),
            "catalog_missing": gaps.get("catalog_missing"),
            "confirmed": gaps.get("confirmed"),
        },
        "planned": [m.get("title") for m in plan],
        "added": [],
        "skipped": [],
        "rl_train": train_info,
        "rl_status": rle.status() if dry_run else {},
    }

    if dry_run:
        result["rl_status"] = rle.status()
        return result

    for m in plan:
        title = (m.get("title") or "").strip()
        cat = str(m.get("category") or "other")
        spec = m.get("spec")
        cid: int | None = None
        if isinstance(spec, dict):
            cid = _ingest_spec(spec)
        if cid is None:
            result["skipped"].append(title)
            rle.record_outcome(st, category=cat, title=title, success=False, source="autofill")
            continue
        result["added"].append({"id": cid, "title": title, "category": cat})
        rle.record_outcome(
            st, category=cat, title=title, success=True, card_id=cid, source="autofill"
        )
        if sleep_sec > 0:
            time.sleep(sleep_sec)

    if result["added"]:
        learn.export_pack()
        try:
            import sync_kiwoom_wiki

            sync_kiwoom_wiki.main()
        except Exception:
            pass
        try:
            from seed_kiwoom_phase2_continue import write_meta_structure

            write_meta_structure()
        except Exception:
            pass

    stats = dict(st.get("stats") or {})
    if result["added"] or result["skipped"]:
        stats["runs"] = int(stats.get("runs") or 0) + 1
        stats["added"] = int(stats.get("added") or 0) + len(result["added"])
    st["stats"] = stats
    st["last_run"] = _now()
    save_state(st)
    result["stats"] = learn.stats()
    result["rl"] = rle.status()
    result["errors"] = kerr.load().get("stats")
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--max-add",
        type=int,
        default=int(os.getenv("KIWOM_RL_MAX_ADD", "2") or "2"),
    )
    p.add_argument("--sleep", type=float, default=0.3)
    args = p.parse_args()
    out = run(max_add=args.max_add, sleep_sec=args.sleep, dry_run=args.dry_run)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
