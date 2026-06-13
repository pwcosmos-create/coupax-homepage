"""원키스US(wonkisus) HTS 젬마 job — wonkisus-grid-trading-rules 정본 점검."""
from __future__ import annotations

import os
from datetime import datetime

import workisus_learn_policy as wlp
import workisus_wiki_rules as wiki

_AGENT_BRIEF: dict[str, str] = dict(wiki.AGENT_FOCUS)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _wiki_note() -> str:
    st = wiki.wiki_status()
    if not st.get("ok"):
        return f" · Wiki⚠ {st.get('error', '')[:48]}"
    return f" · 정본 {st.get('wiki_id', '')} ({st.get('updated_at', '')})"


def _agent_label(agent: dict) -> str:
    return (agent.get("name") or agent.get("id") or "젬마")[:24]


def _card_ensure_on_pulse() -> bool:
    return False


def _card_job_disabled() -> tuple[bool, str]:
    return True, f"원키스US ({_now()}): {wlp.disabled_message()}"


def _pulse(agent: dict, topic: str | None = None) -> tuple[bool, str]:
    aid = (agent.get("id") or "").strip()
    topic = topic or wiki.focus_for_agent(aid)
    return True, f"{_agent_label(agent)} ({_now()}): {topic}{_wiki_note()}"


def job_workisus_pulse(agent: dict) -> tuple[bool, str]:
    try:
        import agent_office_tasks as tasks

        st = wiki.wiki_status()
        pending = sum(
            1
            for t in tasks.list_tasks(limit=50)
            if isinstance(t, dict)
            and (t.get("division") or "") == "workisus-chasu"
            and (t.get("status") or "") in ("queued", "in_progress")
        )
        ok = "연결" if st.get("ok") else "미연결"
        return True, (
            f"원키스US ({_now()}): Wiki {ok} · {st.get('wiki_id', WIKI_ID)} · "
            f"지시대기 {pending} · 10%수렴·무손실"
        )
    except Exception as e:
        return False, f"원키스US 점검 실패: {e!s}"


WIKI_ID = wiki.WIKI_ID


def job_workisus_wiki_pulse(agent: dict) -> tuple[bool, str]:
    """지식젬마 — wonkisus Wiki 정본·플레이북."""
    st = wiki.wiki_status()
    lines = wiki.summary_lines(max_lines=3)
    ctx_len = len(wiki.export_trading_context(max_chars=500))
    head = f"지식젬마 ({_now()}): {st.get('title', '')[:32]}"
    if not st.get("ok"):
        return False, head + f" ⚠ {st.get('error', '')}"
    return True, head + f" · {ctx_len}자 미리보기 · " + " / ".join(lines[:2])


def job_workisus_atr_pulse(agent: dict) -> tuple[bool, str]:
    return _pulse(agent, wiki.AGENT_FOCUS.get("workisus_atr"))


def job_workisus_ops_pulse(agent: dict) -> tuple[bool, str]:
    return True, (
        f"운영젬마 ({_now()}): Cycle≤2·Profit>0 Trim·손실 홀딩·실행확인{_wiki_note()}"
    )


def job_workisus_pack_sync(agent: dict) -> tuple[bool, str]:
    ctx = wiki.export_trading_context(max_chars=20000)
    st = wiki.wiki_status()
    return True, (
        f"플레이북 ({_now()}): {st.get('wiki_id', '')} · {len(ctx)}자 · "
        f"CURSOR_WORKISUS_LEARN.md"
    )


def job_workisus_card_compose(agent: dict) -> tuple[bool, str]:
    return _card_job_disabled()


def job_workisus_catalog_maintain(agent: dict) -> tuple[bool, str]:
    return _card_job_disabled()


def job_workisus_atr_rl_autofill(agent: dict) -> tuple[bool, str]:
    return _card_job_disabled()


def job_workisus_error_resolve(agent: dict) -> tuple[bool, str]:
    return job_workisus_ops_pulse(agent)


def job_workisus_error_seed(agent: dict) -> tuple[bool, str]:
    return _card_job_disabled()


def job_workisus_watch_pulse(agent: dict) -> tuple[bool, str]:
    topics = " · ".join(
        _AGENT_BRIEF.get(k, "")[:28]
        for k in (
            "workisus_rebalance",
            "workisus_risk",
            "workisus_balance",
            "workisus_mode",
        )
        if _AGENT_BRIEF.get(k)
    )
    return True, f"워치 ({_now()}): {topics[:160]}{_wiki_note()}"


def job_workisus_mode_pulse(agent: dict) -> tuple[bool, str]:
    return _pulse(agent)


def job_workisus_balance_pulse(agent: dict) -> tuple[bool, str]:
    return _pulse(agent)


def job_workisus_stocks_pulse(agent: dict) -> tuple[bool, str]:
    return _pulse(agent)


def job_workisus_rules_pulse(agent: dict) -> tuple[bool, str]:
    return _pulse(agent)


def job_workisus_risk_pulse(agent: dict) -> tuple[bool, str]:
    return _pulse(agent)


def job_workisus_rebalance_pulse(agent: dict) -> tuple[bool, str]:
    return _pulse(agent)


def job_workisus_token_pulse(agent: dict) -> tuple[bool, str]:
    return _pulse(agent)


def job_workisus_reconcile_pulse(agent: dict) -> tuple[bool, str]:
    return _pulse(agent)


def job_workisus_order_pulse(agent: dict) -> tuple[bool, str]:
    return _pulse(agent)


def job_workisus_auto_pulse(agent: dict) -> tuple[bool, str]:
    return _pulse(agent)


def job_workisus_multi_pulse(agent: dict) -> tuple[bool, str]:
    return _pulse(agent)


def job_workisus_slots_pulse(agent: dict) -> tuple[bool, str]:
    return _pulse(agent)


def job_workisus_hts_pulse(agent: dict) -> tuple[bool, str]:
    return job_workisus_watch_pulse(agent)
