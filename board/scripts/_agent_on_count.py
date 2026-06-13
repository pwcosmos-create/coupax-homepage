"""Quick agent on/off count."""
from __future__ import annotations

import agent_registry as ar

d = ar.load_registry()
agents = [a for a in d.get("agents") or [] if isinstance(a, dict)]
on = [a["id"] for a in agents if a.get("mode_on")]
off = [a["id"] for a in agents if not a.get("mode_on")]
print("office_always_on", d.get("office_always_on"))
print("on", len(on), "off", len(off), "total", len(agents))
if off:
    print("off_ids", off)
