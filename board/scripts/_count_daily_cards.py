#!/usr/bin/env python3
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))
import agent_office_saju_learn as learn

cards = [
    c
    for c in learn.load_store().get("cards") or []
    if isinstance(c, dict) and c.get("status") == "confirmed"
]
daily = []
for c in cards:
    t = (c.get("title") or "").strip()
    if "일운" in t or "오늘의 운세" in t or t == "해석·오늘의 운세" or t == "변수·일운 참고":
        daily.append((c.get("id"), t))

print(len(daily))
for i, t in daily:
    print(f"#{i} {t}")
