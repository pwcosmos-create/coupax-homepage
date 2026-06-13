#!/usr/bin/env python3
"""bot_settings_us.json — 무손실 ATR 루트 키 주입·atr_auto 종목 갱신 트리거.

  python scripts/apply_workisus_atr_musonsil.py --dry-run
  python scripts/apply_workisus_atr_musonsil.py --apply
  WONKISUS_SETTINGS=/path/to/bot_settings_us.json python scripts/apply_workisus_atr_musonsil.py --apply
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
PRESET_PATH = BOARD / "data" / "workisus_learning" / "bot_settings_us_atr_musonsil_preset.json"

MUSONSIL_ROOT_KEYS = {
    "us_atr_sell_mult": 1.0,
    "us_atr_sell_cap": 4.0,
    "us_atr_sell_min": 1.5,
    "us_atr_gap_musonsil_mult": 1.15,
    "sell_fee_buffer_pct_us": 0.12,
}


def _settings_path() -> Path:
    env = (os.getenv("WONKISUS_SETTINGS") or os.getenv("US_SETTINGS_FILE") or "").strip()
    if env:
        return Path(env)
    guess = Path(r"C:\커셔\주식\wonkisus\shared\매직스플릿\scripts\bot_settings_us.json")
    if guess.is_file():
        return guess
    return BOARD / "data" / "workisus_learning" / "bot_settings_us_atr_musonsil_preset.json"


def apply(*, dry_run: bool = True, run_atr: bool = False) -> dict:
    path = _settings_path()
    if not path.is_file():
        return {"ok": False, "error": f"settings not found: {path}"}
    cfg = json.loads(path.read_text(encoding="utf-8"))
    changed: list[str] = []
    for k, v in MUSONSIL_ROOT_KEYS.items():
        if cfg.get(k) != v:
            if not dry_run:
                cfg[k] = v
            changed.append(k)
    atr_n = 0
    if not dry_run and changed:
        path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if run_atr and not dry_run:
        sys.path.insert(0, str(Path(r"C:\커셔\주식\wonkisus\shared\매직스플릿\scripts")))
        try:
            import auto_bot

            out = auto_bot.update_atr_settings_us()
            atr_n = len(out or {})
        except Exception as e:
            return {"ok": False, "error": str(e), "changed": changed}
    PRESET_PATH.parent.mkdir(parents=True, exist_ok=True)
    PRESET_PATH.write_text(
        json.dumps({"musonsil_root": MUSONSIL_ROOT_KEYS, "note": "무손실 ATR 정본"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"ok": True, "path": str(path), "dry_run": dry_run, "changed": changed, "atr_updated": atr_n}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    p.add_argument("--run-atr", action="store_true", help="apply 후 update_atr_settings_us()")
    args = p.parse_args()
    out = apply(dry_run=not args.apply, run_atr=args.run_atr)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
