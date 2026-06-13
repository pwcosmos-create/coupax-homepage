"""
원키스US 학습 카드 제작·확정 오류 기록.

  python scripts/workisus_learning_errors.py list
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import json_store

BOARD = Path(__file__).resolve().parents[1]
ERRORS_PATH = BOARD / "data" / "workisus_learning" / "learning_errors.json"
DIVISION = "workisus-chasu"

DEFAULT = {
    "updated_at": "",
    "playbook": {
        "too_short": "본문 30자 이상. US·슬롯·차수·no_slot·리밸런스·무손절·KIS·HTS를 구체적으로.",
        "pii": "계좌번호·API키·비밀번호·이메일·전화 제거.",
        "duplicate": "동일 제목·catalog_seed — revise 또는 제목 변경.",
        "tag_missing": "US·원키스·슬롯·차수·3001·3002·이익·리밸런스 키워드 포함.",
        "confirm_failed": "PII·길이 보강 후 재확정.",
        "unknown": "workisus_err_* 카탈로그 시드 후 재시도.",
        "meta_card_fail": "seed_workisus_error_cards.py --add 로 오류 카드 먼저 확정.",
    },
    "errors": [],
    "stats": {"total": 0, "by_kind": {}},
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def load() -> dict:
    try:
        data = json_store.load_json(ERRORS_PATH, default=dict(DEFAULT))
    except json_store.JsonStoreError:
        return dict(DEFAULT)
    data.setdefault("playbook", dict(DEFAULT["playbook"]))
    data.setdefault("errors", [])
    data.setdefault("stats", dict(DEFAULT["stats"]))
    return data


def save(data: dict) -> None:
    data["updated_at"] = _now()
    errs = data.get("errors") or []
    if len(errs) > 300:
        data["errors"] = errs[-300:]
    ERRORS_PATH.parent.mkdir(parents=True, exist_ok=True)
    json_store.save_json(ERRORS_PATH, data)


def playbook_hint(kind: str) -> str:
    pb = load().get("playbook") or {}
    return str(pb.get(kind) or pb.get("unknown") or "")


def record(
    kind: str,
    message: str,
    *,
    title: str = "",
    card_id: int | None = None,
) -> None:
    data = load()
    entry = {
        "ts": _now(),
        "kind": (kind or "unknown")[:40],
        "message": (message or "")[:500],
        "title": (title or "")[:120],
        "card_id": card_id,
    }
    errs = list(data.get("errors") or [])
    errs.append(entry)
    data["errors"] = errs
    stats = dict(data.get("stats") or {})
    stats["total"] = int(stats.get("total") or 0) + 1
    by = dict(stats.get("by_kind") or {})
    k = entry["kind"]
    by[k] = int(by.get(k) or 0) + 1
    stats["by_kind"] = by
    data["stats"] = stats
    save(data)
    try:
        import agent_office_log

        agent_office_log.append_message(
            from_id="workisus_error_fix",
            kind="system",
            text=(
                f"[원키스US 오류 {entry.get('kind')}] "
                f"{entry.get('title') or '—'} — {entry.get('message', '')[:120]}"
            ),
            division=DIVISION,
        )
    except Exception:
        pass


def recent_errors(limit: int = 20) -> list[dict]:
    errs = load().get("errors") or []
    return list(errs[-limit:])


def summary_lines() -> list[str]:
    data = load()
    stats = data.get("stats") or {}
    by = stats.get("by_kind") or {}
    lines = [f"원키스US 오류 로그: 총 {stats.get('total', 0)}건"]
    if by:
        top = sorted(by.items(), key=lambda x: -int(x[1] or 0))[:6]
        lines.append("  · " + ", ".join(f"{k}×{v}" for k, v in top))
    for e in recent_errors(3):
        lines.append(
            f"  · [{e.get('ts')}] {e.get('kind')}: {(e.get('title') or '')[:40]}"
        )
    return lines


def ensure_error_learning_cards(*, max_add: int = 8) -> int:
    """learning_errors kind → workisus_err_* 카드 확정(오류 젬마)."""
    import workisus_agent_card_compose as wac
    import workisus_error_resolver as res
    import workisus_error_cards as wec
    import agent_office_workisus_learn as learn

    added = 0
    data = load()
    by = (data.get("stats") or {}).get("by_kind") or {}
    for kind, cnt in sorted(by.items(), key=lambda x: -int(x[1] or 0)):
        if added >= max_add or int(cnt or 0) < 1:
            continue
        seed = res.seed_for_kind(kind)
        if not seed:
            continue
        existing = learn.find_card_by_seed(seed)
        if existing and existing.get("status") == "confirmed":
            continue
        wac.ensure_seed_card(seed, agent_id="workisus_error_fix", confirm=True)
        added += 1
    # 카탈로그 메타 시드 누락 보충
    for spec in wec.CARD_MAKING_ERROR_CARDS:
        if added >= max_add:
            break
        seed = (spec.get("catalog_seed") or "").strip()
        if not seed:
            continue
        ex = learn.find_card_by_seed(seed)
        if ex and ex.get("status") == "confirmed":
            continue
        wac.ensure_seed_card(seed, agent_id="workisus_error_fix", confirm=True)
        added += 1
    return added


def main() -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("cmd", nargs="?", default="list")
    args = p.parse_args()
    data = load()
    if args.cmd == "stats":
        print(json.dumps(data.get("stats") or {}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps((data.get("errors") or [])[-20:], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
