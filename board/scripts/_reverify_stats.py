#!/usr/bin/env python3
import sys
from pathlib import Path
BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))
import agent_office_saju_learn as learn
import agent_office_saju_card_council as c

cards = [x for x in learn.load_store().get("cards") or [] if x.get("status") == "confirmed"]
st = c.council_stats()
modes = {}
for x in cards:
    m = (x.get("council_mode") or "initial").strip() or "initial"
    modes[m] = modes.get(m, 0) + 1
footer = sum(1 for x in cards if "본 내용은 명리 참고용" in (x.get("body") or ""))
enriched = sum(1 for x in cards if (x.get("council_enriched_at") or "").strip())
llm = sum(1 for x in cards if (x.get("llm_composed_at") or "").strip())
print("council", st)
print("council_modes", dict(sorted(modes.items(), key=lambda i: -i[1])[:8]))
print("footer_ok", footer, "/", len(cards))
print("enriched", enriched, "llm", llm)
print("fast_mode", c.council_fast_mode())
