#!/usr/bin/env python3
import json
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))
import saju_reading_engine as eng  # noqa: E402

d = json.loads((BOARD / "data/saju_learning/cards.json").read_text(encoding="utf-8"))
cards = [c for c in (d if isinstance(d, list) else d["cards"]) if c.get("status") == "confirmed"]
titles = {(c.get("title") or "").strip() for c in cards}

checks = [
    ("십신", [f"변수·십신 {n}" for n in "비견 겁재 식신 상관 편재 정재 편관 정관 편인 정인".split()]),
    ("오행", [f"변수·오행 {e}" for e in "목 화 토 금 수".split()]),
    ("격", [f"변수·격 {n}" for n in "정관격 편관격 정재격 편재격 식신격 상관격 정인격 편인격".split()]),
    ("천간", [f"변수·천간 {n}" for n in "갑목 을목 병화 정화 무토 기토 경금 신금 임수 계수".split()]),
    ("지지", [f"변수·지지 {n}" for n in "자수 축토 인목 묘목 진토 사화 오화 미토 신금 유금 술토 해수".split()]),
    ("신살", [f"변수·신살 {n}" for n in "역마 도화 화개 문창 천을".split()]),
]
for label, want in checks:
    miss = [t for t in want if t not in titles]
    have = len(want) - len(miss)
    print(label, f"{have}/{len(want)}", "missing:", miss[:5], "..." if len(miss) > 5 else "")
