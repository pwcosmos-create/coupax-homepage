#!/usr/bin/env python3
"""차수거래 학습 카드 갭 탐지 — 카탈로그·태그·오류 재시도."""
from __future__ import annotations

import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_kiwoom_learn as learn  # noqa: E402
import kiwoom_card_catalog as catalog  # noqa: E402
import kiwoom_learning_errors as kerr  # noqa: E402

TAG_BUCKET_MIN = {
    "차수": 10,
    "슬롯": 8,
    "ATR": 6,
    "익절": 8,
    "1차": 6,
    "2차": 6,
    "cascade": 4,
    "계좌": 6,
}


def _confirmed_titles() -> set[str]:
    out: set[str] = set()
    for c in learn.load_store().get("cards") or []:
        if isinstance(c, dict) and c.get("status") == "confirmed":
            t = learn.normalize_title(c.get("title") or "")
            if t:
                out.add(t)
    return out


def _tag_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for c in learn.load_store().get("cards") or []:
        if not isinstance(c, dict) or c.get("status") != "confirmed":
            continue
        for t in c.get("tags") or []:
            counts[t] = counts.get(t, 0) + 1
    return counts


def _used_catalog_seeds() -> set[str]:
    out: set[str] = set()
    for c in learn.load_store().get("cards") or []:
        if not isinstance(c, dict):
            continue
        seed = (c.get("catalog_seed") or "").strip()
        if seed:
            out.add(seed)
    return out


def detect_gaps() -> dict:
    titles = _confirmed_titles()
    all_titles = learn.existing_titles()
    used_seeds = _used_catalog_seeds()
    missing: list[dict] = []

    seen_spec: set[str] = set()
    for spec in catalog.all_catalog_specs():
        t = (spec.get("title") or "").strip()
        if not t or t in seen_spec:
            continue
        seen_spec.add(t)
        if t in all_titles or t in used_seeds:
            continue
        missing.append(
            {
                "title": t,
                "category": spec.get("category") or "catalog",
                "priority": int(spec.get("priority") or 70),
                "spec": spec,
            }
        )

    counts = _tag_counts()
    for tag, need in TAG_BUCKET_MIN.items():
        have = counts.get(tag, 0)
        if have < need:
            missing.append(
                {
                    "title": f"__tag__:{tag}",
                    "category": f"tag:{tag}",
                    "priority": 45,
                    "spec": None,
                    "tag_need": need - have,
                }
            )

    err_stats = (kerr.load().get("stats") or {}).get("by_kind") or {}
    queued_err: set[str] = set()
    for kind, cnt in err_stats.items():
        if int(cnt) >= 2 and kind not in ("duplicate", "meta_card_fail"):
            key = f"__error_learn__:{kind}"
            if key not in queued_err:
                queued_err.add(key)
                missing.append(
                    {
                        "title": key,
                        "category": "meta",
                        "priority": 92,
                        "spec": None,
                        "error_kind": kind,
                    }
                )

    # 카탈로그에 정의된 오류·매매 시나리오 카드 — stats 없어도 RL 큐에 포함
    for spec in catalog.all_catalog_specs():
        seed = (spec.get("catalog_seed") or "").strip()
        if not seed.startswith(("meta_err_", "meta_trade_err_")):
            continue
        if seed in used_seeds:
            continue
        t = learn.normalize_title(spec.get("title") or "")
        if t in all_titles:
            continue
        missing.append(
            {
                "title": t,
                "category": spec.get("category") or "meta",
                "priority": int(spec.get("priority") or 80),
                "spec": spec,
            }
        )

    missing.sort(key=lambda m: (-int(m.get("priority") or 0), m.get("title") or ""))
    return {
        "missing": missing,
        "missing_count": len([m for m in missing if not str(m.get("title", "")).startswith("__")]),
        "catalog_missing": len([m for m in missing if m.get("spec")]),
        "confirmed": len(titles),
        "total_cards": len(all_titles),
    }


def main() -> int:
    import json

    print(json.dumps(detect_gaps(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
