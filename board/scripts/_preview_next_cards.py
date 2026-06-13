#!/usr/bin/env python3
"""다음 자동 제작 예정 카드 (고빈도 우선)."""
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))
import agent_office_saju_learn as learn  # noqa: E402
import saju_auto_add_cards as auto  # noqa: E402
from saju_card_usage_priority import usage_score_for_spec  # noqa: E402

titles = {(c.get("title") or "").strip() for c in learn.list_cards(limit=800)}
pending = auto._pending_from_pool(auto.AUTO_CARD_POOL_FULL, titles, high_usage_only=True)
pending_i = [
    s
    for s in auto.HIGH_USAGE_INTERPRETIVE_POOL
    if (s.get("title") or "").strip() not in titles
]
print("=== 다음 고빈도 변수/일주 풀 (상위 10) ===")
for s in pending[:10]:
    print(f"  {usage_score_for_spec(s):4d}  {s['title']}")
print("=== 다음 고빈도 해석 풀 (상위 10) ===")
for s in sorted(pending_i, key=usage_score_for_spec, reverse=True)[:10]:
    print(f"  {usage_score_for_spec(s):4d}  {s['title']}")
