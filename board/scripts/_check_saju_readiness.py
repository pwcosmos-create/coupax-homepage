#!/usr/bin/env python3
"""사주 풀이에 필요한 카드 점검 — 10섹션·권장 버킷."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import saju_knowledge_tier as tier  # noqa: E402
import saju_reading_engine as eng  # noqa: E402

d = json.loads((BOARD / "data/saju_learning/cards.json").read_text(encoding="utf-8"))
cards = d if isinstance(d, list) else d.get("cards", [])
pass_c = [
    c
    for c in cards
    if isinstance(c, dict)
    and c.get("status") == "confirmed"
    and tier.is_council_pass(c)
]

DEEP = [
    "심층·[1] 인사·성향",
    "심층·[2] 사주팔자",
    "심층·[3] 오행 균형",
    "심층·[4] 십신·격국",
    "심층·[5] 용신·기신",
    "심층·[6] 대운·세운",
    "심층·[7] 재물",
    "심층·[8] 연애·관계",
    "심층·[9] 직업",
    "심층·[10] 실천·주의",
]

GUIDE_MIN = {
    "deep_10": 10,
    "stem_day": 10,
    "stem_chen": 12,
    "gyeok": 11,
    "branch": 7,
    "yongsin_heesin": 10,
}

print("=== 사주 풀이 카드 점검 ===")
print("PASS_total", len(pass_c))
print("confirmed_total", sum(1 for c in cards if c.get("status") == "confirmed"))

print("\n[10섹션 뼈대 — 심층·[1]~[10]]")
for t in DEEP:
    hit = [c for c in pass_c if (c.get("title") or "").strip() == t]
    st = "OK" if hit else "MISSING"
    ln = len((hit[0].get("body") or "")) if hit else 0
    print(f"  {st}  {t}  ({ln}자)")

inv = eng.pass_inventory()
print("\n[버킷별 PASS — 가이드 권장 대비]")
labels = {
    "stem-chen": ("띠 12지", 12),
    "stem-day": ("일주·천간 10", 10),
    "gyeok": ("격국 10+칠살", 11),
    "branch": ("지지", 7),
    "yongsin": ("용신·희신", 10),
    "gisin": ("기신", 6),
    "deep/other": ("해석·기타", 0),
}
for k, (label, need) in labels.items():
    n = inv["buckets"].get(k, 0)
    ok = "OK" if need == 0 or n >= need else f"부족({n}/{need})"
    print(f"  {ok}  {label}: {n}장")

print("\n[섹션별 매칭 테스트 — 샘플 명식]")
ctx = {"tags": ["일주", "병화", "정관", "용신", "오행", "재물", "연애"], "summary": "병화 일주 정관격"}
r = eng.build_reading(ctx)
print("  mode", r.get("mode"), "matched", r.get("matched_count"))
for sec, card in eng._pick_section_cards(eng.match_pass_cards(ctx), ctx):
    print(f"    {sec} -> {(card.get('title') or '')[:45]}")

print("\n[결론]")
deep_ok = all(any((c.get("title") or "").strip() == t for c in pass_c) for t in DEEP)
print("  10섹션 뼈대:", "충족" if deep_ok else "일부 누락")
print("  풀 운영(200+ PASS):", "충족" if len(pass_c) >= 200 else "부족")
print("  권장 50~80장:", "충족" if len(pass_c) >= 50 else "부족")
