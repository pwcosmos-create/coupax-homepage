#!/usr/bin/env python3
"""서버/로컬 cards.json 제목 목록 (그룹별)."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_saju_learn as learn  # noqa: E402


def bucket(title: str) -> str:
    t = (title or "").strip()
    if t.startswith("심층·"):
        return "심층"
    if t.startswith("해석·"):
        return "해석"
    if t.startswith("변수·"):
        rest = t[3:]
        if rest.startswith("띠 "):
            return "변수·띠"
        if rest.startswith("격 "):
            return "변수·격"
        if "일운" in rest or "오늘" in rest:
            return "변수·일운"
        if rest.startswith("운 "):
            return "변수·운"
        if rest.startswith("천간"):
            return "변수·천간"
        if "지지" in rest:
            return "변수·지지"
        if "십신" in rest:
            return "변수·십신"
        if "오행" in rest:
            return "변수·오행"
        return "변수·기타"
    return "기타"


def main() -> int:
    cards = [c for c in learn.load_store().get("cards") or [] if isinstance(c, dict)]
    confirmed = [c for c in cards if c.get("status") == "confirmed"]
    groups: dict[str, list[str]] = defaultdict(list)
    for c in sorted(confirmed, key=lambda x: (x.get("title") or "")):
        groups[bucket(c.get("title") or "")].append((c.get("title") or "").strip())

    order = [
        "심층",
        "해석",
        "변수·일운",
        "변수·띠",
        "변수·격",
        "변수·운",
        "변수·천간",
        "변수·지지",
        "변수·십신",
        "변수·오행",
        "변수·기타",
        "기타",
    ]
    out = {
        "total": len(confirmed),
        "groups": {
            k: {"count": len(groups[k]), "titles": groups[k]}
            for k in order
            if groups.get(k)
        },
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
