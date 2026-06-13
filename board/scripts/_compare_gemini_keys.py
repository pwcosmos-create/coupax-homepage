#!/usr/bin/env python3
"""Compare GEMINI key presence (prefix only)."""
from pathlib import Path

paths = [
    Path("/home/ubuntu/coupax-homepage/board/.env"),
    Path("/home/ubuntu/coupax_app/.env"),
]
for p in paths:
    if not p.exists():
        print(p, "MISSING")
        continue
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("GEMINI_API_KEY="):
            v = line.split("=", 1)[1].strip()
            print(p.parent.name, v[:14] + "..." + v[-4:], len(v))
