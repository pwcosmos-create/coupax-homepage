"""원키스US 오류 젬마 — learning_errors·HTS 이슈 → 확정 오류 카드 매칭·playbook."""
from __future__ import annotations

import re
from typing import Any

# 제작 오류 kind → meta 카드 시드
KIND_TO_SEED: dict[str, str] = {
    "too_short": "workisus_err_too_short",
    "pii": "workisus_err_pii",
    "duplicate": "workisus_err_duplicate_title",
    "tag_missing": "workisus_err_tag_missing_us",
    "confirm_failed": "workisus_err_confirm_failed",
    "unknown": "workisus_err_compose_gap",
    "meta_card_fail": "workisus_err_meta_card_fail",
}

# HTS watch·bot 이슈 키워드 → 매매 오류 카드 시드
ISSUE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"token|KIS_APP|API\s*실패", re.I), "workisus_trade_err_token"),
    (re.compile(r"balance_fail|잔고\s*미조회", re.I), "workisus_trade_err_balance_fail"),
    (re.compile(r"bot:|last_error", re.I), "workisus_trade_err_bot_last_error"),
    (re.compile(r"rebalance:enabled\s*종목\s*없음", re.I), "workisus_trade_err_rebalance_no_targets"),
    (re.compile(r"stocks:enabled\s*종목\s*0", re.I), "workisus_trade_err_held_not_enabled"),
    (re.compile(r"settings_integrity|\.bak\s*복구", re.I), "workisus_trade_err_settings_integrity"),
    (re.compile(r"ready=false|enabled_us", re.I), "workisus_trade_err_enabled_us_off"),
    (re.compile(r"ON미보유|enabled_not_held", re.I), "workisus_trade_err_enabled_not_held"),
    (re.compile(r"보유OFF|held_not_enabled", re.I), "workisus_trade_err_held_not_enabled"),
    (re.compile(r"market=US|KR\s*슬롯", re.I), "workisus_trade_err_slot_market_kr"),
    (re.compile(r"reconcile", re.I), "workisus_trade_err_reconcile_close"),
    (re.compile(r"perm_fail", re.I), "workisus_trade_err_rebalance_perm_fail"),
    (re.compile(r"합산|avg_profit|익절.*스킵", re.I), "workisus_trade_err_avg_defense_hold"),
    (re.compile(r"15초|instant_2nd|2차.*없", re.I), "workisus_trade_err_instant_2nd_15s"),
    (re.compile(r"999|앵커|1차.*안", re.I), "workisus_trade_err_slot1_999_anchor"),
    (re.compile(r"ATR|atr_auto|갱신.*실패|데이터\s*부족", re.I), "workisus_atr_error_data"),
    (re.compile(r"buy_gap|sell_pct.*10", re.I), "workisus_atr_manual_edit"),
    (re.compile(r"no_slot", re.I), "workisus_trade_err_no_slot_on"),
    (re.compile(r"sell_pcts|일괄\s*익절", re.I), "workisus_trade_err_profit_only_bulk"),
]


def _card_by_seed(seed: str) -> dict | None:
    import agent_office_workisus_learn as learn

    c = learn.find_card_by_seed(seed)
    if c and c.get("status") == "confirmed":
        return c
    return c


def _card_line(card: dict | None, *, prefix: str = "") -> str:
    if not card:
        return ""
    cid = card.get("id")
    title = (card.get("title") or "")[:36]
    summary = (card.get("summary") or (card.get("body") or ""))[:100]
    return f"{prefix}#{cid} {title} — {summary}"


def seed_for_kind(kind: str) -> str:
    return (KIND_TO_SEED.get((kind or "").strip()) or "workisus_err_unknown").strip()


def seed_for_issue(text: str) -> str:
    blob = text or ""
    for rx, seed in ISSUE_PATTERNS:
        if rx.search(blob):
            return seed
    return ""


def ensure_missing_error_cards(*, max_add: int = 12, agent_id: str = "workisus_error_fix") -> int:
    """오류 카탈로그 중 미확정 시드를 젬마가 채움."""
    import workisus_agent_card_compose as wac
    import workisus_error_cards as wec
    import agent_office_workisus_learn as learn

    added = 0
    for spec in wec.all_error_specs():
        if added >= max_add:
            break
        seed = (spec.get("catalog_seed") or "").strip()
        if not seed:
            continue
        existing = learn.find_card_by_seed(seed)
        if existing and existing.get("status") == "confirmed":
            continue
        wac.ensure_seed_card(seed, agent_id=agent_id, confirm=True)
        added += 1
    return added


def advise_for_kind(kind: str) -> dict[str, Any]:
    import workisus_learning_errors as werr

    seed = seed_for_kind(kind)
    card = _card_by_seed(seed)
    return {
        "kind": kind,
        "seed": seed,
        "card": card,
        "playbook": werr.playbook_hint(kind),
        "line": _card_line(card, prefix="[카드] "),
    }


def advise_for_issue(issue: str) -> dict[str, Any]:
    seed = seed_for_issue(issue)
    if not seed:
        return {"issue": issue, "seed": "", "card": None, "line": ""}
    card = _card_by_seed(seed)
    return {
        "issue": issue[:120],
        "seed": seed,
        "card": card,
        "line": _card_line(card, prefix="[매매오류카드] "),
    }


def resolve_recent_errors(*, limit: int = 8) -> list[dict[str, Any]]:
    import workisus_learning_errors as werr

    out: list[dict[str, Any]] = []
    for e in werr.recent_errors(limit):
        if not isinstance(e, dict):
            continue
        kind = (e.get("kind") or "unknown").strip()
        adv = advise_for_kind(kind)
        adv["ts"] = e.get("ts")
        adv["log_title"] = e.get("title")
        adv["message"] = (e.get("message") or "")[:80]
        out.append(adv)
    return out


def run_resolve(*, agent_id: str = "workisus_error_fix") -> dict[str, Any]:
    """오류 젬마 1회 실행 — 카드 확보 + 최근 오류·이슈에 카드 연결."""
    import agent_office_workisus_learn as learn
    import workisus_learning_errors as werr

    seeded = ensure_missing_error_cards(max_add=15, agent_id=agent_id)
    meta_from_log = werr.ensure_error_learning_cards(max_add=6)

    issues: list[str] = []
    st = learn.stats()
    if int(st.get("pending") or 0) > 20:
        issues.append(f"학습 대기 {st['pending']}건")
    err_cards = sum(
        1
        for c in learn.load_store().get("cards") or []
        if isinstance(c, dict)
        and c.get("status") == "confirmed"
        and (
            (c.get("catalog_seed") or "").startswith("workisus_err_")
            or (c.get("catalog_seed") or "").startswith("workisus_trade_err_")
        )
    )

    advices = resolve_recent_errors(limit=6)
    lines: list[str] = []
    cited: set[int] = set()
    for a in advices:
        card = a.get("card")
        if card and card.get("id"):
            cited.add(int(card["id"]))
        line = (a.get("line") or "").strip()
        if line:
            lines.append(f"  · {a.get('kind')}: {line}")
        elif a.get("playbook"):
            lines.append(f"  · {a.get('kind')}: {a['playbook'][:90]}")

    # pack에서 오류 카드 샘플 (젬마가 항상 참조할 앵커)
    pack = learn.export_pack()
    anchor = [
        c
        for c in (pack.get("cards") or [])
        if (c.get("catalog_seed") or "").startswith("workisus_trade_err_token")
        or (c.get("catalog_seed") or "").startswith("workisus_err_too_short")
    ][:2]
    for c in anchor:
        if c.get("id"):
            cited.add(int(c["id"]))

    try:
        import agent_office_log

        if lines:
            agent_office_log.append_message(
                from_id=agent_id,
                kind="conclusion",
                text="【오류 젬마 · playbook】\n" + "\n".join(lines[:6]),
                division="workisus-chasu",
            )
    except Exception:
        pass

    return {
        "seeded": seeded,
        "meta_from_log": meta_from_log,
        "error_cards_confirmed": err_cards,
        "cited_card_ids": sorted(cited),
        "advice_lines": lines,
        "issues": issues,
        "stats": st,
    }


def main() -> int:
    import json

    print(json.dumps(run_resolve(), ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
