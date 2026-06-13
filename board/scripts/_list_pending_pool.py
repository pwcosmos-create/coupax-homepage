#!/usr/bin/env python3
import json
import sys
from collections import Counter
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))
import saju_auto_add_cards as auto  # noqa: E402

d = json.loads((BOARD / "data/saju_learning/cards.json").read_text(encoding="utf-8"))
cards = [c for c in (d if isinstance(d, list) else d["cards"]) if c.get("status") == "confirmed"]
titles = {(c.get("title") or "").strip() for c in cards}
pending_i = [s for s in auto.INTERPRETIVE_CARD_POOL_FULL if s["title"] not in titles]
pending_v = [s for s in auto.AUTO_CARD_POOL_FULL if s["title"] not in titles]
print("pending_interpretive", len(pending_i))
for t in pending_i[:20]:
    print(" ", t["title"])
print("pending_variable", len(pending_v))
for t in pending_v[:20]:
    print(" ", t["title"])
c = Counter()
for card in cards:
    t = card.get("title") or ""
    if t.startswith("해석·"):
        c["해석"] += 1
    elif t.startswith("변수·"):
        c["변수"] += 1
    elif t.startswith("심층·"):
        c["심층"] += 1
    else:
        c["기타"] += 1
print("counts", dict(c))
