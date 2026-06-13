#!/usr/bin/env python3
"""원히어로 실매매 bot_log 모니터링 → 학습 카드 갱신(시드당 1장 revise).

  WONHERO_MONITOR_ENABLED=1
  WONHERO_SQLITE_PATH=/home/ubuntu/kisstock/trade_history.sqlite
  WONHERO_MONITOR_MAX_CARDS=4
  WONHERO_MONITOR_AUTO_CONFIRM=1

  python scripts/wonhero_trade_monitor.py run
  python scripts/wonhero_trade_monitor.py run --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

STATE_PATH = BOARD / "data" / "kiwoom_learning" / "wonhero_monitor_state.json"
DEFAULT_SQLITE = Path("/home/ubuntu/kisstock/trade_history.sqlite")

_ACTION_SEEDS = {
    "register": ("monitor_live_register", "모니터 · 1차 register·슬롯"),
    "buy": ("monitor_live_buy", "모니터 · 매수·추가 차수"),
    "sell": ("monitor_live_sell", "모니터 · 익절·매도"),
    "error": ("monitor_live_error", "모니터 · 봇 error·스킵"),
    "other": ("monitor_live_other", "모니터 · 기타 봇 이벤트"),
}

_PII_RX = (
    re.compile(r"\d{10,}"),
    re.compile(r"01[0-9]-?\d{3,4}-?\d{4}"),
)


def _enabled() -> bool:
    return os.getenv("WONHERO_MONITOR_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _sqlite_path() -> Path:
    raw = os.getenv("WONHERO_SQLITE_PATH", "").strip()
    if raw:
        p = Path(raw)
        return p if p.is_absolute() else BOARD / p
    return DEFAULT_SQLITE


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def load_state() -> dict:
    if not STATE_PATH.is_file():
        return {"last_log_id": 0, "updated_at": ""}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        data = {}
    data.setdefault("last_log_id", 0)
    return data


def save_state(data: dict) -> None:
    data["updated_at"] = _now()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _redact(text: str) -> str:
    out = text or ""
    for rx in _PII_RX:
        out = rx.sub("[제거됨]", out)
    return out[:200]


def _classify_action(action: str, reason: str) -> str:
    a = (action or "").strip().lower()
    r = (reason or "").lower()
    if a == "error" or "error" in r or "fail" in r or "실패" in r:
        return "error"
    if a in _ACTION_SEEDS:
        return a
    if a in ("buy", "매수"):
        return "buy"
    if a in ("sell", "매도", "익절"):
        return "sell"
    if a in ("register", "등록"):
        return "register"
    return "other"


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (name,),
    ).fetchone()
    return row is not None


def fetch_new_events(since_id: int, *, limit: int = 200) -> list[dict]:
    path = _sqlite_path()
    if not path.is_file():
        return []
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        if _table_exists(conn, "bot_log"):
            rows = conn.execute(
                """
                SELECT id, ts, market, account, code, action, slot_num, qty, price, reason
                FROM bot_log
                WHERE id > ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (since_id, limit),
            ).fetchall()
        elif _table_exists(conn, "ms_auto_log"):
            rows = conn.execute(
                """
                SELECT id,
                       (date || ' ' || time) AS ts,
                       market, account, code,
                       side AS action,
                       slot AS slot_num,
                       qty, price,
                       (COALESCE(result,'') || ' ' || COALESCE(name,'')) AS reason
                FROM ms_auto_log
                WHERE id > ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (since_id, limit),
            ).fetchall()
        else:
            rows = []
    finally:
        conn.close()
    out: list[dict] = []
    for row in rows:
        d = dict(row)
        code = str(d.get("code") or "")
        if len(code) > 4:
            d["code"] = code[:2] + "…" + code[-2:]
        acct = str(d.get("account") or "")
        if acct:
            d["account"] = "****" + acct[-4:] if len(acct) >= 4 else "****"
        d["reason"] = _redact(str(d.get("reason") or ""))
        out.append(d)
    return out


def _hint_from_reason(reason: str) -> str:
    r = (reason or "").lower()
    hints: list[str] = []
    if "15" in r or "instant" in r or "즉시" in r:
        hints.append("15초·2차 instant 규칙 점검")
    if "gap" in r or "buy_gap" in r or "하락" in r:
        hints.append("ATR buy_gaps·3차+ 추가매수")
    if "register" in r or "인식" in r:
        hints.append("1차 HTS 수동·슬롯 register")
    if "sell" in r or "익절" in r or "pct" in r:
        hints.append("sell_pcts·익절·분할")
    if "스캘프" in r or "scalp" in r:
        hints.append("스캘프 모드 — instant 2차 예외 없음")
    if "잔고" in r or "부족" in r:
        hints.append("잔고·주문가능·계좌")
    return " · ".join(hints[:3])


def _build_body(action: str, events: list[dict]) -> str:
    seed_title = _ACTION_SEEDS.get(action, _ACTION_SEEDS["other"])[1]
    lines = [
        f"{seed_title} — 원히어로 auto_bot bot_log 실측 ({_now()}).",
        "1차·2차·3차·슬롯·익절·ATR·계좌·체결·원히어로 키워드로 학습부와 대조한다.",
        "",
    ]
    for ev in events[-8:]:
        slot = ev.get("slot_num")
        lines.append(
            f"- [{ev.get('ts')}] {ev.get('action')} slot={slot} "
            f"code={ev.get('code')} acct={ev.get('account')} "
            f"reason={ev.get('reason') or '—'}"
        )
    hint = _hint_from_reason(" ".join(str(e.get("reason") or "") for e in events))
    if hint:
        lines.append(f"운영 힌트: {hint}.")
    lines.append("투자 권유 아님 · 주문번호·계좌 전체는 저장하지 않음.")
    return "\n".join(lines)


def run(*, dry_run: bool = False, max_cards: int | None = None) -> dict:
    import agent_office_kiwoom_learn as learn

    if not _enabled():
        return {"ok": True, "skipped": "disabled"}

    max_cards = max_cards or int(os.getenv("WONHERO_MONITOR_MAX_CARDS", "4") or "4")
    auto_confirm = os.getenv("WONHERO_MONITOR_AUTO_CONFIRM", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )

    st = load_state()
    since = int(st.get("last_log_id") or 0)
    events = fetch_new_events(since)
    path = _sqlite_path()
    if not events:
        note = "신규 bot_log 없음"
        if not path.is_file():
            note = "SQLite 없음 — WONHERO_SQLITE_PATH 확인"
        elif path.is_file():
            try:
                conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
                has_bl = _table_exists(conn, "bot_log")
                has_ms = _table_exists(conn, "ms_auto_log")
                conn.close()
                if not has_bl and not has_ms:
                    note = "bot_log·ms_auto_log 테이블 없음 — auto_bot 마이그레이션 후 수집"
            except Exception:
                pass
        return {
            "ok": True,
            "new_events": 0,
            "last_log_id": since,
            "cards": [],
            "sqlite": str(path),
            "note": note,
        }

    by_action: dict[str, list[dict]] = defaultdict(list)
    for ev in events:
        act = _classify_action(str(ev.get("action") or ""), str(ev.get("reason") or ""))
        by_action[act].append(ev)

    max_id = max(int(e.get("id") or 0) for e in events)
    results: list[dict] = []
    updated = 0

    for action, evs in sorted(by_action.items(), key=lambda x: -len(x[1])):
        if updated >= max_cards:
            break
        seed, title = _ACTION_SEEDS.get(action, _ACTION_SEEDS["other"])
        body = _build_body(action, evs)
        if dry_run:
            results.append({"action": action, "seed": seed, "title": title, "events": len(evs)})
            updated += 1
            continue
        try:
            card = learn.add_card(
                body=body,
                title=title,
                source="wonhero_monitor",
                catalog_seed=seed,
                revise_if_seed_exists=True,
                use_council=False,
            )
        except ValueError as e:
            results.append({"action": action, "error": str(e)[:120]})
            continue

        cid = card.get("id")
        confirmed = False
        if auto_confirm and isinstance(cid, int):
            if card.get("status") != "confirmed":
                c2 = learn.confirm_card(cid, export_pack_now=False)
                confirmed = c2 is not None
            else:
                confirmed = True
            if confirmed:
                try:
                    import agent_office_wiki_store

                    agent_office_wiki_store.save_kiwoom_card_to_knowledge(
                        learn.find_card_by_id(cid) or card
                    )
                except Exception:
                    pass

        results.append(
            {
                "action": action,
                "seed": seed,
                "card_id": cid,
                "revised": bool(card.get("_revised")),
                "confirmed": confirmed,
                "events": len(evs),
            }
        )
        updated += 1

    if not dry_run:
        st["last_log_id"] = max_id
        save_state(st)
        if any(r.get("confirmed") for r in results):
            learn.export_pack()

    return {
        "ok": True,
        "dry_run": dry_run,
        "new_events": len(events),
        "last_log_id": max_id if not dry_run else since,
        "cards": results,
        "sqlite": str(_sqlite_path()),
    }


def main() -> int:
    import board_env

    board_env.load_board_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "status"], nargs="?", default="run")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-cards", type=int, default=0)
    args = ap.parse_args()
    if args.cmd == "status":
        st = load_state()
        path = _sqlite_path()
        print(
            json.dumps(
                {
                    "enabled": _enabled(),
                    "sqlite": str(path),
                    "sqlite_exists": path.is_file(),
                    "state": st,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    mc = args.max_cards if args.max_cards > 0 else None
    out = run(dry_run=args.dry_run, max_cards=mc)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
