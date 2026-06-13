#!/usr/bin/env python3
import json
from pathlib import Path

base = Path(__file__).resolve().parents[1]
p = base / "data" / "saju_learning" / "_server_cards_list.json"
out = base / "data" / "saju_learning" / "_server_cards_summary.txt"
d = json.loads(p.read_text(encoding="utf-8"))
lines = [f"TOTAL {d['total']}"]
for g, info in d["groups"].items():
    titles = info["titles"]
    uniq = sorted(set(titles))
    dup = len(titles) - len(uniq)
    extra = f", 중복 {dup}" if dup else ""
    lines.append(f"\n## {g} ({info['count']}장, 고유 {len(uniq)}{extra})")
    for t in uniq:
        c = titles.count(t)
        prefix = f"  x{c} " if c > 1 else "     "
        lines.append(f"{prefix}{t}")
out.write_text("\n".join(lines), encoding="utf-8")
print(str(out))
