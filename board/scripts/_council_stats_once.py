#!/usr/bin/env python3
import sys
from pathlib import Path
BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))
import agent_office_saju_card_council as c
import agent_office_saju_learn as learn
st = c.council_stats()
cards = [x for x in learn.load_store().get("cards") or [] if x.get("status")=="confirmed"]
fail = [x for x in cards if (x.get("council_status") or "")=="fail"]
print("council", st)
print("fail_sample", [(x.get("id"), (x.get("title") or "")[:40]) for x in fail[:5]])
