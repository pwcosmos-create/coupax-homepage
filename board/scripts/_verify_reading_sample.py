#!/usr/bin/env python3
import json
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import saju_reading_engine as eng  # noqa: E402
from saju_reading_display import normalize_body_for_reading  # noqa: E402

d = json.loads((BOARD / "data/saju_learning/cards.json").read_text(encoding="utf-8"))
cards = d if isinstance(d, list) else d["cards"]
for c in cards:
    if "지지관계" in (c.get("title") or "") and "육합" in (c.get("title") or ""):
        b = c.get("body") or ""
        print("TITLE", c.get("title"))
        print("LEN", len(b))
        print("META", "풀이 절차" in b, "활용 키워드" in b)
        print("PREVIEW", normalize_body_for_reading(b)[:500])
        break

deep = next((c for c in cards if (c.get("title") or "") == "심층·[8] 연애·관계"), None)
if deep:
    print("DEEP8_LEN", len(deep.get("body") or ""))

ctx = {"tags": ["연애", "일주", "합", "충", "배우자"], "summary": "연애 관계"}
r = eng.build_reading(ctx)
for i, line in enumerate((r.get("text") or "").split("\n")):
    if line.startswith("8.") and "연애" in line:
        print("---SECTION8---")
        print("\n".join((r.get("text") or "").split("\n")[i : i + 12]))
        break
