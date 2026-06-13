"""
차수거래 학습 카드 제작 오류 기록·playbook 학습.

  python scripts/kiwoom_learning_errors.py list
  python scripts/kiwoom_learning_errors.py stats
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import json_store

BOARD = Path(__file__).resolve().parents[1]
ERRORS_PATH = BOARD / "data" / "kiwoom_learning" / "learning_errors.json"
DIVISION = "kiwoom-chasu"

DEFAULT = {
    "updated_at": "",
    "playbook": {
        "too_short": "본문 30자 이상. 1차 수동·15초 2차·ATR buy_gaps·sell_pcts 익절을 구체적으로.",
        "pii": "계좌번호·API키·비밀번호·전화번호 제거. 끝 4자리만 허용.",
        "duplicate": "동일 제목·catalog_seed 카드가 이미 있음 — 제목 변경 또는 기존 카드 수정.",
        "tag_missing": "본문에 슬롯·1·2·3차·익절·ATR·체결·계좌·원히어로 키워드를 포함.",
        "confirm_failed": "확정·council 재검증 실패 — PII·태그 보강 후 재시도.",
        "unknown": "형식·길이·PII를 점검한 뒤 다시 저장.",
        "meta_card_fail": "meta_err_* 카탈로그 카드 seed_kiwoom_wonhero_rules.py --add 로 먼저 확정.",
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
    _maybe_update_playbook(data, k, message)
    save(data)
    _log_error(entry)


def _maybe_update_playbook(data: dict, kind: str, message: str) -> None:
    by = (data.get("stats") or {}).get("by_kind") or {}
    if int(by.get(kind) or 0) < 3:
        return
    pb = dict(data.get("playbook") or {})
    hint = (message or "")[:200]
    if hint and hint not in pb.get(kind, ""):
        pb[kind] = f"{pb.get(kind, '')} · 최근: {hint}"[:400]
    data["playbook"] = pb


def _log_error(entry: dict) -> None:
    try:
        import agent_office_log

        agent_office_log.append_message(
            from_id="kiwoom_error_fix",
            kind="system",
            text=(
                f"[학습 오류 {entry.get('kind')}] "
                f"{entry.get('title') or '—'} — {entry.get('message', '')[:120]}"
            ),
            division=DIVISION,
        )
    except Exception:
        pass


def recent_errors(limit: int = 20) -> list[dict]:
    errs = load().get("errors") or []
    return list(errs[-limit:])


def ensure_error_learning_cards() -> int:
    """반복 오류 종류별 meta 학습 카드가 없으면 1장 추가."""
    import agent_office_kiwoom_learn as learn

    data = load()
    by = (data.get("stats") or {}).get("by_kind") or {}
    titles = learn.existing_titles()
    used_seeds = {
        (c.get("catalog_seed") or "").strip()
        for c in learn.load_store().get("cards") or []
        if isinstance(c, dict) and (c.get("catalog_seed") or "").strip()
    }
    added = 0
    meta_titles = {
        "too_short": "학습 카드 작성 오류 — 본문·형식",
        "pii": "학습 카드 작성 오류 — PII·태그",
        "tag_missing": "학습 카드 작성 오류 — 태그·키워드 누락",
        "duplicate": "학습 카드 작성 오류 — 제목 중복(duplicate)",
        "confirm_failed": "학습 카드 작성 오류 — 확정 실패(confirm_failed)",
    }
    for kind, count in by.items():
        if int(count) < 2:
            continue
        mt = meta_titles.get(kind)
        if not mt or mt in used_seeds:
            continue
        hint = playbook_hint(kind)
        body = (
            f"오류 종류: {kind} (누적 {count}회).\n"
            f"수정 가이드: {hint}\n"
            "자동·수동 카드 제작 시 이 규칙을 먼저 적용한다."
        )
        try:
            import kiwoom_card_title_compose as kt

            spec = kt.enrich_spec(
                {
                    "body": body,
                    "category": "meta",
                    "error_kind": kind,
                    "catalog_seed": mt,
                },
                error_kind=kind,
            )
            import kiwoom_card_council as kc

            if kc.council_enabled():
                out = kc.create_card_via_council(spec, source="error_learn")
                if out and out.get("card_id"):
                    used_seeds.add(mt)
                    titles.add(learn.normalize_title(spec.get("title") or ""))
                    added += 1
                    continue
            card = learn.add_card(
                body=body,
                title=spec.get("title") or mt,
                source="error_learn",
                use_council=False,
            )
            cid = card.get("id")
            if isinstance(cid, int) and learn.confirm_card(cid):
                used_seeds.add(mt)
                titles.add(learn.normalize_title(card.get("title") or ""))
                added += 1
        except Exception as e:
            record("meta_card_fail", str(e)[:200], title=mt)
    return added


def summary_lines() -> list[str]:
    data = load()
    stats = data.get("stats") or {}
    by = stats.get("by_kind") or {}
    lines = [
        f"학습 오류 로그: 총 {stats.get('total', 0)}건",
    ]
    if by:
        top = sorted(by.items(), key=lambda x: -x[1])[:6]
        lines.append("  · " + ", ".join(f"{k}×{v}" for k, v in top))
    recent = recent_errors(3)
    for e in recent:
        lines.append(
            f"  · [{e.get('ts')}] {e.get('kind')}: {(e.get('title') or '')[:40]}"
        )
    return lines


def main() -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["list", "stats", "ensure-meta"], nargs="?", default="stats")
    args = p.parse_args()
    if args.cmd == "list":
        for e in recent_errors(30):
            print(e)
        return 0
    if args.cmd == "ensure-meta":
        print("added", ensure_error_learning_cards())
        return 0
    print(json.dumps(load().get("stats"), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
