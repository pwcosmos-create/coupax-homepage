"""관상 학습부 주기 job — SEO 카드 제작·확정."""
from __future__ import annotations

import os
from datetime import datetime


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _stats() -> dict:
    import agent_office_gwansang_learn as gl

    return gl.stats()


def _card_ensure_on_pulse() -> bool:
    return (os.getenv("GWANSANG_CARD_ENSURE_ON_PULSE", "1") or "1").strip() not in ("0", "false", "no")


def _ensure_one_gap(agent_id: str) -> str:
    if not _card_ensure_on_pulse():
        return ""
    try:
        import gwansang_card_compose as gcc

        out = gcc.compose_next_gap(agent_id=agent_id)
        if out and out.get("card_id"):
            return f" · 카드 #{out.get('card_id')}"
    except Exception as e:
        return f" · 카드:{e!s}"[:60]
    return ""


def job_gwansang_pulse(agent: dict) -> tuple[bool, str]:
    try:
        import agent_office_tasks as tasks

        st = _stats()
        pending = sum(
            1
            for t in tasks.list_tasks(limit=50)
            if isinstance(t, dict)
            and (t.get("division") or "") == "gwansang-learn"
            and (t.get("status") or "") in ("queued", "in_progress")
        )
        return True, (
            f"관상 학습 ({_now()}): 카드 {st['total']}·확정{st['confirmed']} · "
            f"지시대기 {pending} · SEO 200자+ pack"
        )
    except Exception as e:
        return False, f"관상 점검 실패: {e!s}"


def job_gwansang_pack_sync(agent: dict) -> tuple[bool, str]:
    import agent_office_gwansang_learn as gl

    pack = gl.export_pack()
    st = _stats()
    return True, f"관상 pack ({_now()}): 확정 {st['confirmed']}건 · CURSOR_GWANSANG_LEARN.md · {pack.get('card_count', 0)}"


def job_gwansang_catalog_maintain(agent: dict) -> tuple[bool, str]:
    try:
        import seed_gwansang_cards as sg
        import gwansang_card_compose as gcc

        out = sg.seed_all(sync=True, confirm=True)
        gap = gcc.compose_next_gap(agent_id="gwansang_catalog")
        extra = f" · 갭+1 #{gap.get('card_id')}" if gap else ""
        st = _stats()
        return True, (
            f"관상 카탈로그 ({_now()}): +{out.get('added', 0)} ↻{out.get('synced', 0)} · "
            f"확정{st['confirmed']}{extra}"
        )
    except Exception as e:
        return False, f"관상 카탈로그 실패: {e!s}"


def job_gwansang_card_compose(agent: dict) -> tuple[bool, str]:
    try:
        import gwansang_card_compose as gcc
        import agent_office_gwansang_learn as gl

        aid = (agent.get("id") or "gwansang_compose").strip()
        out = gcc.compose_next_gap(agent_id=aid)
        pack = gl.export_pack()
        if not out:
            return True, f"관상 카드 ({_now()}): 갭 없음 · pack {pack.get('card_count', 0)}건"
        return True, (
            f"관상 카드 ({_now()}): #{out.get('card_id')} "
            f"{(out.get('title') or '')[:28]} · pack {pack.get('card_count', 0)}건"
        )
    except Exception as e:
        return False, f"관상 카드 제작 실패: {e!s}"


def job_gwansang_seo_pulse(agent: dict) -> tuple[bool, str]:
    note = _ensure_one_gap("gwansang_seo")
    st = _stats()
    return True, f"SEO젬마 ({_now()}): 200자+·키워드·확정 {st['confirmed']}{note}"


def job_gwansang_pii_scan(agent: dict) -> tuple[bool, str]:
    import re
    import agent_office_gwansang_learn as gl

    hits: list[str] = []
    pats = (
        (re.compile(r"01[0-9]-?\d{3,4}-?\d{4}"), "전화"),
        (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), "이메일"),
    )
    for c in gl.list_cards(status="pending", limit=20):
        body = c.get("body") or ""
        for rx, label in pats:
            if rx.search(body):
                hits.append(f"#{c.get('id')} {label}")
                break
    st = _stats()
    if hits:
        return False, f"관상 PII: {len(hits)}건 — " + "; ".join(hits[:5])
    return True, f"프라이버시 ({_now()}): 대기 {st['pending']} — 이상 없음"


def _role_pulse(agent: dict, role: str, hint: str) -> tuple[bool, str]:
    aid = (agent.get("id") or "gwansang_scholar").strip()
    note = _ensure_one_gap(aid)
    st = _stats()
    return True, f"{role} ({_now()}): {hint} · 카드 {st['total']}{note}"


def job_gwansang_scholar_pulse(agent: dict) -> tuple[bool, str]:
    return _role_pulse(agent, "학자젬마", "오관·삼정·전통 이론")


def job_gwansang_features_pulse(agent: dict) -> tuple[bool, str]:
    return _role_pulse(agent, "오관젬마", "이마·눈·코·입·귀")


def job_gwansang_fortune_pulse(agent: dict) -> tuple[bool, str]:
    return _role_pulse(agent, "운세젬마", "길상·재물·연애 경향")


def job_gwansang_reader_pulse(agent: dict) -> tuple[bool, str]:
    return _role_pulse(agent, "리더젬마", "수집·요약·카드 초안")


def job_gwansang_structurer_pulse(agent: dict) -> tuple[bool, str]:
    return _role_pulse(agent, "구조젬마", "【】소제목·분류·태그")


def job_gwansang_watch_pulse(agent: dict) -> tuple[bool, str]:
    st = _stats()
    return True, f"워치 ({_now()}): SEO·오관·확정{st['confirmed']} · 갭 제작 활성"


def job_gwansang_gap_autofill(agent: dict) -> tuple[bool, str]:
    """카탈로그 갭 + RL/Gemini 확장 토픽 자동 제작."""
    import os

    try:
        import gwansang_card_gap_detector as gap
        import gwansang_card_rl_autofill as rl

        max_add = max(1, int(os.getenv("GWANSANG_RL_MAX_ADD", os.getenv("GWANSANG_GAP_MAX_ADD", "2")) or "2"))
        gaps = gap.detect_gaps(agent_id="gwansang_gap_autofill")
        out = rl.run(max_add=max_add, agent_id="gwansang_gap_autofill")
        added = out.get("added") or []
        titles = ", ".join((a.get("title") or "")[:22] for a in added[:3]) or "(없음)"
        cat_n = sum(1 for a in added if a.get("kind") == "catalog")
        rl_n = sum(1 for a in added if a.get("kind") == "rl_gemini")
        return True, (
            f"관상 갭 ({_now()}): 카탈로그누락 {gaps.get('missing_count', 0)} · "
            f"RL대기 {gaps.get('expansion_count', 0)} · 추가 {len(added)} "
            f"(시드{cat_n}+Gemini{rl_n}) · {titles}"
        )
    except Exception as e:
        return False, f"관상 갭 자동 실패: {e!s}"


def job_gwansang_wiki_sync(agent: dict) -> tuple[bool, str]:
    """확정 카드 중 Wiki 미반영분 동기화."""
    try:
        import agent_office_gwansang_learn as gl
        import agent_office_wiki_store as wiki

        synced = 0
        for c in gl.list_cards(status="confirmed", limit=80):
            if not isinstance(c, dict) or c.get("wiki_id"):
                continue
            row = wiki.save_gwansang_card_to_knowledge(c)
            if row:
                synced += 1
                cid = c.get("id")
                if isinstance(cid, int):
                    store = gl.load_store()
                    for c2 in store.get("cards") or []:
                        if isinstance(c2, dict) and c2.get("id") == cid:
                            c2["wiki_id"] = row.get("id")
                            break
                    gl.save_store(store)
        st = _stats()
        return True, f"Wiki 동기화 ({_now()}): +{synced} · 확정 {st['confirmed']}"
    except Exception as e:
        return False, f"관상 Wiki 동기화 실패: {e!s}"


def job_gwansang_error_fix(agent: dict) -> tuple[bool, str]:
    """본문 200자 미만·태그 누락·PII 점검."""
    import re
    import agent_office_gwansang_learn as gl
    from gwansang_card_catalog import MIN_BODY_CHARS

    issues: list[str] = []
    for c in gl.list_cards(limit=40):
        if not isinstance(c, dict):
            continue
        cid = c.get("id")
        body = c.get("body") or ""
        if len(body) < MIN_BODY_CHARS:
            issues.append(f"#{cid} 본문{len(body)}자")
        if not (c.get("tags") or []):
            issues.append(f"#{cid} 태그없음")
        for rx in (
            re.compile(r"01[0-9]-?\d{3,4}-?\d{4}"),
            re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
        ):
            if rx.search(body):
                issues.append(f"#{cid} PII")
                break
    if issues:
        return False, f"관상 품질 ({_now()}): {len(issues)}건 — " + "; ".join(issues[:5])
    st = _stats()
    return True, f"오류점검 ({_now()}): 카드 {st['total']} — 이상 없음"


def job_gwansang_daily_conclusion(agent: dict) -> tuple[bool, str]:
    st = _stats()
    return True, (
        f"관상 학습 결론 ({_now()}): 확정 {st['confirmed']} · 대기 {st['pending']}. "
        "다음 — 갭 자동·SEO 보강·Wiki 동기화."
    )


def job_gwansang_review_hint(agent: dict) -> tuple[bool, str]:
    import agent_office_gwansang_learn as gl

    pending = gl.list_cards(status="pending", limit=5)
    if not pending:
        st = _stats()
        return True, f"검수 ({_now()}): 대기 0 · 확정 {st['confirmed']}"
    hints = ", ".join(f"#{c.get('id')}" for c in pending[:4])
    return True, f"검수 ({_now()}): 대기 {len(pending)} — {hints}"


def job_gwansang_tag_digest(agent: dict) -> tuple[bool, str]:
    import agent_office_gwansang_learn as gl

    tag_counts: dict[str, int] = {}
    for c in gl.list_cards(status="confirmed", limit=60):
        for t in c.get("tags") or []:
            tag_counts[str(t)] = tag_counts.get(str(t), 0) + 1
    top = sorted(tag_counts.items(), key=lambda x: -x[1])[:5]
    top_s = ", ".join(f"{k}×{v}" for k, v in top) or "—"
    return True, f"태그 ({_now()}): {top_s}"
