#!/usr/bin/env python3
"""카드 제작 오류 해결(meta) — 제목 자동 생성 + 9젬마 협업. 중복 제목 생략."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_kiwoom_learn as learn  # noqa: E402
import kiwoom_card_catalog as catalog  # noqa: E402
import kiwoom_card_title_compose as kt  # noqa: E402


def _meta_specs() -> list[dict]:
    out: list[dict] = []
    seen_body: set[str] = set()
    for spec in catalog.KIWOOM_AUTO_CARD_POOL:
        if (spec.get("category") or "") != "meta":
            continue
        body = (spec.get("body") or "").strip()
        if not body or body in seen_body:
            continue
        seen_body.add(body)
        row = dict(spec)
        row["catalog_seed"] = (spec.get("title") or "").strip()
        kind = ""
        if "too_short" in row["catalog_seed"]:
            kind = "too_short"
        elif "duplicate" in row["catalog_seed"]:
            kind = "duplicate"
        elif "confirm_failed" in row["catalog_seed"]:
            kind = "confirm_failed"
        elif "PII" in row["catalog_seed"]:
            kind = "pii"
        elif "태그" in row["catalog_seed"]:
            kind = "tag_missing"
        row["error_kind"] = kind
        out.append(row)
    return out


def run(*, dry_run: bool = False, use_council: bool = True) -> dict:
    titles = learn.existing_titles()
    specs = kt.enrich_specs(_meta_specs())
    pending = [s for s in specs if learn.normalize_title(s.get("title") or "") not in titles]
    added: list[dict] = []
    skipped_duplicate = len(specs) - len(pending)

    if dry_run:
        return {
            "dry_run": True,
            "pending": [{"title": s.get("title"), "seed": s.get("catalog_seed")} for s in pending],
            "skipped_duplicate": skipped_duplicate,
        }

    import kiwoom_card_council as kc

    for spec in pending:
        title = learn.normalize_title(spec.get("title") or "")
        if not title or title in titles:
            skipped_duplicate += 1
            continue
        out = None
        if use_council and kc.council_enabled():
            out = kc.create_card_via_council(spec, source="error_method_seed")
        if out and out.get("card_id"):
            titles.add(title)
            added.append({"card_id": out["card_id"], "title": title, "seed": spec.get("catalog_seed")})

    if added:
        learn.export_pack()
        try:
            import sync_kiwoom_wiki as sw

            sw.main()
        except Exception:
            pass
    return {
        "added": added,
        "skipped_duplicate": skipped_duplicate,
        "created": len(added),
    }


def main() -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-council", action="store_true")
    args = p.parse_args()
    r = run(dry_run=args.dry_run, use_council=not args.no_council)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
