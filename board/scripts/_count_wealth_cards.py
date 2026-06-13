#!/usr/bin/env python3
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))
import agent_office_saju_learn as learn


def is_wealth_title(t: str) -> bool:
    t = (t or "").strip()
    if "재물" in t or "재성" in t or "재물운" in t or "현금흐름" in t:
        return True
    if t == "심층·[7] 재물":
        return True
    if "지출" in t and "재" in t:
        return True
    return False


cards = [
    c
    for c in learn.load_store().get("cards") or []
    if isinstance(c, dict) and c.get("status") == "confirmed"
]
matched = [(c.get("id"), (c.get("title") or "").strip()) for c in cards if is_wealth_title(c.get("title"))]
print(len(matched))
for i, t in sorted(matched, key=lambda x: x[1]):
    print(f"#{i} {t}")
