#!/usr/bin/env python3
"""[deprecated] 구 coupax 수동 차수 시드 — wonhero 전용 시드로 대체됨.

  python scripts/seed_kiwoom_wonhero_rules.py --reset
"""
from __future__ import annotations

import sys

if __name__ == "__main__":
    print(
        "seed_kiwoom_chasu_knowledge.py 는 deprecated 입니다.\n"
        "  python scripts/seed_kiwoom_wonhero_rules.py --reset",
        file=sys.stderr,
    )
    raise SystemExit(2)
