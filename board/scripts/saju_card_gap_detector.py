#!/usr/bin/env python3
"""사주 카드 부족·매칭 실패 탐지 — RL 자동 제작 입력."""
from __future__ import annotations

import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import saju_knowledge_tier as tier  # noqa: E402
import saju_reading_engine as eng  # noqa: E402

DEEP_TITLES = list(eng.DEEP_TITLE_BY_SECTION.values())

BUCKET_MIN = {
    "stem-chen": 12,
    "stem-day": 10,
    "gyeok": 11,
    "branch": 7,
    "yongsin": 10,
    "gisin": 6,
}

DAILY_REQUIRED = (
    "변수·일운 참고",
    "해석·오늘의 운세",
)


def _pass_titles() -> set[str]:
    import agent_office_saju_learn as learn

    out: set[str] = set()
    for c in learn.load_store().get("cards") or []:
        if not isinstance(c, dict) or c.get("status") != "confirmed":
            continue
        if tier.is_council_pass(c):
            out.add((c.get("title") or "").strip())
    return out


def _catalog_specs() -> dict[str, dict]:
    from ingest_saju_app_gaps import daily_fortune_specs, gap_specs
    from ingest_saju_app_p0_p1 import all_specs

    specs: dict[str, dict] = {}
    for s in all_specs() + gap_specs() + daily_fortune_specs():
        t = (s.get("title") or "").strip()
        if t:
            specs[t] = s
    return specs


def detect_gaps() -> dict:
    titles = _pass_titles()
    catalog = _catalog_specs()
    missing: list[dict] = []

    for t, spec in catalog.items():
        if t not in titles:
            cat = "p0_p1"
            if t.startswith("변수·띠"):
                cat = "zodiac"
            elif "일운" in t or "오늘" in t:
                cat = "daily"
            elif t.startswith("변수·"):
                cat = "variable"
            pri = {"daily": 95, "p0_p1": 90, "zodiac": 70, "variable": 60}.get(cat, 50)
            missing.append(
                {
                    "title": t,
                    "category": cat,
                    "priority": pri,
                    "spec": spec,
                }
            )

    for t in DEEP_TITLES:
        if t not in titles:
            missing.append(
                {
                    "title": t,
                    "category": "deep",
                    "priority": 100,
                    "spec": None,
                }
            )

    inv = eng.pass_inventory().get("buckets") or {}
    for bucket, need in BUCKET_MIN.items():
        have = int(inv.get(bucket) or 0)
        if have < need:
            missing.append(
                {
                    "title": f"__bucket__:{bucket}",
                    "category": f"bucket:{bucket}",
                    "priority": 40,
                    "spec": None,
                    "bucket_need": need,
                    "bucket_have": have,
                }
            )

    daily_ctx = {"reading_kind": "daily", "tags": ["일운", "오늘", "식신"]}
    daily = eng.build_reading(daily_ctx)
    full_ctx = {"tags": ["일주", "병화", "정관", "용신", "오행"]}
    full = eng.build_reading(full_ctx)

    for t in DAILY_REQUIRED:
        if t not in titles:
            if not any(m["title"] == t for m in missing):
                missing.append(
                    {
                        "title": t,
                        "category": "daily",
                        "priority": 98,
                        "spec": catalog.get(t),
                    }
                )

    return {
        "pass_total": len(titles),
        "missing_count": len(missing),
        "missing": missing,
        "daily_reading": {
            "mode": daily.get("mode"),
            "matched": daily.get("matched_count"),
            "llm_required": daily.get("llm_required"),
        },
        "full_reading": {
            "mode": full.get("mode"),
            "matched": full.get("matched_count"),
            "llm_required": full.get("llm_required"),
        },
    }
