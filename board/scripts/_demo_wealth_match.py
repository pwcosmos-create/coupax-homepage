#!/usr/bin/env python3
import json
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))
import saju_reading_engine as eng

# 예시 명식: 병화 일간, 정재·편재 있음, 재물 테마
ctx = {
    "summary": "병화 일간, 월지 정재, 일지 편재",
    "day_master": "병화",
    "tags": ["재물", "재성", "정재", "편재", "병화", "세운"],
    "ten_gods": ["정재", "편재", "식신"],
    "geok": "정재격",
}

r = eng.build_reading(ctx)
wealth_sections = [s for s in r.get("sections") or [] if "재물" in (s.get("title") or "")]
wealth_matched = [
    c for c in r.get("matched_cards") or []
    if any(k in (c.get("title") or "") for k in ("재물", "재성", "현금"))
]

print(json.dumps({
    "mode": r.get("mode"),
    "llm_required": r.get("llm_required"),
    "matched_count": r.get("matched_count"),
    "wealth_section": wealth_sections,
    "wealth_in_top_matched": wealth_matched,
}, ensure_ascii=False, indent=2))

PY