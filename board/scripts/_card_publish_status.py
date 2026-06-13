#!/usr/bin/env python3
import json
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))
import saju_knowledge_tier as tier  # noqa: E402
import agent_office_saju_learn as learn  # noqa: E402

cards = learn.load_store().get("cards") or []
pending = [c for c in cards if c.get("status") == "pending"]
confirmed = [c for c in cards if c.get("status") == "confirmed"]
not_pass = [c for c in confirmed if not tier.is_council_pass(c)]
gemini_wait = [
    c
    for c in confirmed
    if tier.is_council_pass(c)
    and not (c.get("llm_composed_at") or "").strip()
    and (
        (c.get("card_style") or "") == "interpretive"
        or (c.get("title") or "").startswith("해석·")
        or (c.get("title") or "").startswith("심층·")
    )
]
st = learn.stats()
print(json.dumps(
    {
        "total": st["total"],
        "pending_발행전": len(pending),
        "confirmed": len(confirmed),
        "confirmed_PASS": sum(1 for c in confirmed if tier.is_council_pass(c)),
        "confirmed_위원회미통과": len(not_pass),
        "PASS_Gemini대기": len(gemini_wait),
    },
    ensure_ascii=False,
))
if pending:
    print("pending_samples:", [(c.get("id"), (c.get("title") or "")[:40]) for c in pending[:5]])
