"""
키움(증권) 계좌 스냅샷 — 계좌 젬마가 잔고·평가·보유를 '알고' 작업하도록.

HTS/영웅문에서 확인한 수치를 사무실에서 갱신 (계좌번호 전체·API키는 저장하지 않음).
추후 Open API 연동 시 import_snapshot() 만 교체하면 됨.

  python scripts/agent_office_kiwoom_account.py show
  python scripts/agent_office_kiwoom_account.py set --deposit 1000000 --orderable 950000
"""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import json_store

BOARD = Path(__file__).resolve().parents[1]
DATA_DIR = BOARD / "data" / "kiwoom_account"
SNAPSHOT_PATH = DATA_DIR / "snapshot.json"
DEFAULT_BROKER = "키움증권"
STALE_HOURS = int(os.getenv("KIWOM_ACCOUNT_STALE_HOURS", "36") or "36")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _default_snapshot() -> dict:
    return {
        "updated_at": "",
        "broker": DEFAULT_BROKER,
        "source": "manual",
        "accounts": [],
        "positions": [],
        "note": "",
    }


def load_snapshot() -> dict:
    try:
        data = json_store.load_json(SNAPSHOT_PATH, default=_default_snapshot())
    except json_store.JsonStoreError:
        return _default_snapshot()
    if not isinstance(data, dict):
        return _default_snapshot()
    data.setdefault("broker", DEFAULT_BROKER)
    data.setdefault("accounts", [])
    data.setdefault("positions", [])
    return data


def save_snapshot(data: dict) -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _now()
    json_store.save_json(SNAPSHOT_PATH, data)
    return data


def _mask_account(raw: str) -> str:
    s = re.sub(r"\D", "", (raw or "").strip())
    if len(s) >= 4:
        return "****" + s[-4:]
    return "****"


def _parse_int(v: Any) -> int | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return int(v)
    s = re.sub(r"[^\d\-]", "", str(v))
    if not s or s == "-":
        return None
    try:
        return int(s)
    except ValueError:
        return None


def update_snapshot(
    *,
    broker: str = DEFAULT_BROKER,
    account_mask: str = "",
    deposit: int | None = None,
    orderable: int | None = None,
    eval_amount: int | None = None,
    profit_loss: int | None = None,
    profit_rate_pct: float | None = None,
    positions: list[dict] | None = None,
    note: str = "",
    source: str = "manual",
) -> dict:
    data = load_snapshot()
    acct = {
        "label": "위탁",
        "account_mask": _mask_account(account_mask),
        "deposit": deposit,
        "orderable": orderable,
        "eval_amount": eval_amount,
        "profit_loss": profit_loss,
        "profit_rate_pct": profit_rate_pct,
        "currency": "KRW",
    }
    if data.get("accounts") and isinstance(data["accounts"][0], dict):
        prev = data["accounts"][0]
        for k, v in acct.items():
            if v is None and k in prev:
                acct[k] = prev[k]
    data["accounts"] = [acct]
    if positions is not None:
        clean: list[dict] = []
        for p in positions[:30]:
            if not isinstance(p, dict):
                continue
            clean.append(
                {
                    "name": (p.get("name") or "")[:40],
                    "code": re.sub(r"\D", "", str(p.get("code") or ""))[:6],
                    "qty": _parse_int(p.get("qty")),
                    "eval": _parse_int(p.get("eval")),
                    "profit": _parse_int(p.get("profit")),
                }
            )
        data["positions"] = clean
    data["broker"] = (broker or DEFAULT_BROKER)[:40]
    data["note"] = (note or data.get("note") or "")[:500]
    data["source"] = (source or "manual")[:30]
    return save_snapshot(data)


def is_stale(hours: int | None = None) -> bool:
    data = load_snapshot()
    ts = (data.get("updated_at") or "").strip()
    if not ts:
        return True
    try:
        dt = datetime.strptime(ts, "%Y-%m-%d %H:%M")
    except ValueError:
        return True
    limit = timedelta(hours=max(1, hours or STALE_HOURS))
    return datetime.now() - dt > limit


def _fmt_won(n: int | None) -> str:
    if n is None:
        return "—"
    return f"{n:,}원"


def summary_lines() -> list[str]:
    data = load_snapshot()
    lines: list[str] = []
    if not (data.get("updated_at") or "").strip():
        lines.append("계좌 스냅샷 없음 — HTS에서 예수금·평가금 확인 후 「계좌 현황 갱신」")
        return lines

    lines.append(f"{data.get('broker') or DEFAULT_BROKER} · 갱신 {data.get('updated_at')}")
    if is_stale():
        lines.append(f"⚠ {STALE_HOURS}시간 초과 — 잔고 재갱신 권장")

    for a in data.get("accounts") or []:
        if not isinstance(a, dict):
            continue
        mask = a.get("account_mask") or "****"
        lines.append(
            f"계좌 {mask}: 예수금 {_fmt_won(a.get('deposit'))} · "
            f"주문가능 {_fmt_won(a.get('orderable'))} · "
            f"평가 {_fmt_won(a.get('eval_amount'))}"
        )
        pl = a.get("profit_loss")
        if pl is not None:
            rate = a.get("profit_rate_pct")
            rate_s = f" ({rate}%)" if rate is not None else ""
            lines.append(f"  평가손익 {_fmt_won(pl)}{rate_s}")

    pos = [p for p in data.get("positions") or [] if isinstance(p, dict) and p.get("name")]
    if pos:
        lines.append(f"보유 {len(pos)}종목:")
        for p in pos[:8]:
            lines.append(
                f"  · {p.get('name')} {p.get('code') or ''} "
                f"수량 {p.get('qty') or '—'} 평가 {_fmt_won(p.get('eval'))}"
            )
    elif (data.get("accounts") or []):
        lines.append("보유 종목: (미입력)")

    note = (data.get("note") or "").strip()
    if note:
        lines.append(f"메모: {note[:120]}")
    return lines


def summary_text() -> str:
    return "\n".join(summary_lines())


def stats() -> dict:
    data = load_snapshot()
    acct = (data.get("accounts") or [{}])[0] if isinstance(data.get("accounts"), list) else {}
    if not isinstance(acct, dict):
        acct = {}
    pos = [p for p in data.get("positions") or [] if isinstance(p, dict)]
    return {
        "updated_at": data.get("updated_at") or "",
        "broker": data.get("broker") or DEFAULT_BROKER,
        "stale": is_stale(),
        "has_data": bool(data.get("updated_at")),
        "deposit": acct.get("deposit"),
        "orderable": acct.get("orderable"),
        "eval_amount": acct.get("eval_amount"),
        "profit_loss": acct.get("profit_loss"),
        "position_count": len(pos),
        "source": data.get("source") or "manual",
    }


def import_from_env_file() -> bool:
    """KIWOM_ACCOUNT_IMPORT_PATH JSON 파일이 있으면 병합 (로컬 자동화용)."""
    path = os.getenv("KIWOM_ACCOUNT_IMPORT_PATH", "").strip()
    if not path or not Path(path).is_file():
        return False
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return False
    if not isinstance(payload, dict):
        return False
    update_snapshot(
        broker=payload.get("broker") or DEFAULT_BROKER,
        account_mask=str(payload.get("account_mask") or ""),
        deposit=_parse_int(payload.get("deposit")),
        orderable=_parse_int(payload.get("orderable")),
        eval_amount=_parse_int(payload.get("eval_amount")),
        profit_loss=_parse_int(payload.get("profit_loss")),
        profit_rate_pct=payload.get("profit_rate_pct"),
        positions=payload.get("positions") if isinstance(payload.get("positions"), list) else None,
        note=str(payload.get("note") or ""),
        source="import_file",
    )
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("show")
    p_set = sub.add_parser("set")
    p_set.add_argument("--deposit", type=int, default=None)
    p_set.add_argument("--orderable", type=int, default=None)
    p_set.add_argument("--eval", dest="eval_amount", type=int, default=None)
    p_set.add_argument("--mask", default="")
    args = ap.parse_args()
    if args.cmd == "set":
        update_snapshot(
            account_mask=args.mask,
            deposit=args.deposit,
            orderable=args.orderable,
            eval_amount=args.eval_amount,
        )
        print(summary_text())
        return 0
    print(summary_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
