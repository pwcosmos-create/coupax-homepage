#!/usr/bin/env python3
import json
import statistics as st
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
d = json.loads((BOARD / "data/saju_learning/cards.json").read_text(encoding="utf-8"))
cards = d if isinstance(d, list) else d.get("cards", [])
confirmed = [c for c in cards if isinstance(c, dict) and c.get("status") == "confirmed"]


def body_len(c: dict) -> int:
    b = (c.get("body") or "").strip()
    while "본 내용은 명리" in b:
        b = b[: b.find("본 내용은 명리")].strip()
    return len(b)


def bucket(c: dict) -> str:
    t = c.get("title") or ""
    if t.startswith("심층·"):
        return "deep"
    if t.startswith("해석·"):
        return "interp"
    if t.startswith("변수·"):
        return "var"
    return "other"


lens = [body_len(c) for c in confirmed]
groups: dict[str, list[int]] = {}
for c in confirmed:
    groups.setdefault(bucket(c), []).append(body_len(c))

print("total_confirmed", len(confirmed))
print(
    "chars",
    "min",
    min(lens),
    "max",
    max(lens),
    "avg",
    round(st.mean(lens)),
    "median",
    round(st.median(lens)),
)
for g in sorted(groups):
    L = groups[g]
    print(
        f"  {g}: n={len(L)} min={min(L)} max={max(L)} "
        f"avg={round(st.mean(L))} median={round(st.median(L))}"
    )
llm = [body_len(c) for c in confirmed if (c.get("llm_composed_at") or "").strip()]
nollm = [body_len(c) for c in confirmed if not (c.get("llm_composed_at") or "").strip()]
if llm:
    print(
        f"  gemini: n={len(llm)} avg={round(st.mean(llm))} median={round(st.median(llm))}"
    )
if nollm:
    print(
        f"  template_only: n={len(nollm)} avg={round(st.mean(nollm))} "
        f"median={round(st.median(nollm))}"
    )
under400 = sum(1 for x in lens if x < 400)
under800 = sum(1 for x in lens if x < 800)
over1200 = sum(1 for x in lens if x >= 1200)
print(f"  under_400={under400} under_800={under800} over_1200={over1200}")
