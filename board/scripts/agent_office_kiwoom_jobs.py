"""키움 차수거래 학습부 주기 job."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
DIVISION = "kiwoom-chasu"

_PII_PATTERNS = (
    (re.compile(r"\d{10,}"), "장문자번호"),
    (re.compile(r"01[0-9]-?\d{3,4}-?\d{4}"), "전화"),
    (re.compile(r"(?i)api[_-]?key"), "API키"),
    (re.compile(r"비밀번호|password"), "비밀번호"),
)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _kiwoom_stats() -> dict:
    import agent_office_kiwoom_learn

    return agent_office_kiwoom_learn.stats()


def job_kiwoom_pii_scan(agent: dict) -> tuple[bool, str]:
    import agent_office_kiwoom_learn

    hits: list[str] = []
    for c in agent_office_kiwoom_learn.list_cards(status="pending", limit=20):
        body = c.get("body") or ""
        for rx, label in _PII_PATTERNS:
            if rx.search(body):
                hits.append(f"카드#{c.get('id')} {label}")
                break
    st = _kiwoom_stats()
    if hits:
        return False, f"차수거래 PII: {len(hits)}건 — " + "; ".join(hits[:5])
    return True, f"차수거래 PII: 대기 {st['pending']}건 — 이상 없음"


_ACCOUNT_KW = ("예수금", "주문가능", "잔고", "계좌", "D+2", "출금", "입금", "평가금", "매입금")


def job_kiwoom_account_pulse(agent: dict) -> tuple[bool, str]:
    """증권 계좌 스냅샷(잔고·평가·보유) + 학습 카드 교차 점검."""
    import agent_office_kiwoom_account
    import agent_office_kiwoom_learn

    try:
        agent_office_kiwoom_account.import_from_env_file()
    except Exception:
        pass

    lines = agent_office_kiwoom_account.summary_lines()
    st_acc = agent_office_kiwoom_account.stats()
    if not st_acc.get("has_data"):
        return False, "\n".join(lines)

    card_hits: list[str] = []
    for c in agent_office_kiwoom_learn.list_cards(limit=15):
        body = (c.get("body") or "") + " " + (c.get("title") or "")
        found = [k for k in _ACCOUNT_KW if k in body]
        if found:
            card_hits.append(f"카드#{c.get('id')}")
    if card_hits:
        lines.append("학습 카드 교차: " + ", ".join(card_hits[:5]))

    ok = not st_acc.get("stale")
    return ok, "【계좌 젬마 · 증권 잔고】\n" + "\n".join(lines)


def job_kiwoom_card_pulse(agent: dict) -> tuple[bool, str]:
    st = _kiwoom_stats()
    coop = ""
    try:
        import kiwoom_card_council as kc

        if kc.council_enabled():
            coop = " · 협업제작 ON(9젬마)"
    except Exception:
        pass
    return True, (
        f"차수거래 카드: 전체 {st['total']} · 대기 {st['pending']} · 확정 {st['confirmed']} ({_now()})"
        f"{coop}"
    )


def job_kiwoom_card_compose(agent: dict) -> tuple[bool, str]:
    """9젬마 협업으로 갭 카드 1장 제작."""
    try:
        import kiwoom_card_council as kc
        import kiwoom_card_gap_detector as gap_det

        if not kc.council_enabled():
            return True, "협업 제작 비활성(KIWOM_CARD_COUNCIL_ENABLED=0)"
        gaps = gap_det.detect_gaps()
        missing = [m for m in gaps.get("missing") or [] if isinstance(m.get("spec"), dict)]
        if not missing:
            return True, f"협업 제작 ({_now()}): 갭 없음"
        out = kc.create_card_via_council(missing[0]["spec"], source="council_compose")
        if not out:
            return False, f"협업 제작 실패 ({_now()})"
        pack_note = ""
        if out.get("confirmed"):
            ok_p, pack_note = job_kiwoom_pack_sync(agent)
            if not ok_p:
                pack_note = ""
        agents = ", ".join(
            (x.get("name") or "")[:6] for x in (out.get("contributors") or [])[:5]
        )
        return True, (
            f"협업 제작 ({_now()}): #{out['card_id']} {out.get('title', '')[:28]} · "
            f"{out.get('agent_count', 0)}젬마 — {agents}…"
            + (f" · {pack_note[:60]}" if pack_note else "")
        )
    except Exception as e:
        return False, f"협업 제작 오류: {e!s}"


def job_kiwoom_tag_digest(agent: dict) -> tuple[bool, str]:
    import agent_office_kiwoom_learn

    tags: dict[str, int] = {}
    for c in agent_office_kiwoom_learn.list_cards(limit=40):
        for t in c.get("tags") or []:
            tags[t] = tags.get(t, 0) + 1
    top = sorted(tags.items(), key=lambda x: -x[1])[:8]
    summary = ", ".join(f"{k}×{v}" for k, v in top) if top else "태그 없음"
    return True, f"차수 태그 분포: {summary}"


def job_kiwoom_review_hint(agent: dict) -> tuple[bool, str]:
    import agent_office_kiwoom_learn

    pending = agent_office_kiwoom_learn.list_cards(status="pending", limit=5)
    if not pending:
        return True, "검수 대기 카드 없음"
    lines = []
    for c in pending:
        tags = c.get("tags") or []
        miss = [k for k in ("손절", "익절", "차수") if k not in tags]
        hint = f"태그 보완: {', '.join(miss)}" if miss else "태그 양호"
        lines.append(f"  #{c.get('id')} {hint}")
    return True, "차수 검수 힌트:\n" + "\n".join(lines)


def job_kiwoom_pack_sync(agent: dict) -> tuple[bool, str]:
    import agent_office_kiwoom_learn

    pack = agent_office_kiwoom_learn.export_pack()
    agent_office_kiwoom_learn.render_cursor_md()
    return True, f"pack {pack.get('card_count', 0)}건 · CURSOR_KIWOM_LEARN.md 갱신"


def job_kiwoom_daily_conclusion(agent: dict) -> tuple[bool, str]:
    st = _kiwoom_stats()
    return True, (
        f"차수거래 학습 결론 ({_now()}): 확정 {st['confirmed']} · 대기 {st['pending']}. "
        "다음 — 대기 카드 검수·확정 후 pack export."
    )


def job_kiwoom_gap_autofill(agent: dict) -> tuple[bool, str]:
    """갭 탐지 → RL 우선순위 → 카드 자동 제작·오류 playbook."""
    import os

    try:
        import kiwoom_card_rl_autofill as krl

        max_add = max(1, int(os.getenv("KIWOM_RL_MAX_ADD", "2") or "2"))
        out = krl.run(max_add=max_add, dry_run=False, train_first=True)
        gaps = out.get("gaps") or {}
        added = out.get("added") or []
        planned = out.get("planned") or []
        rl = out.get("rl") or {}
        rl_stats = rl.get("stats") or {}
        eps = rl.get("epsilon", "?")
        titles = ", ".join(a.get("title", "")[:22] for a in added[:4]) or "(없음)"
        top = rl.get("top_categories") or []
        top_s = ", ".join(f"{x.get('category')}×{x.get('weight')}" for x in top[:3])
        msg = (
            f"차수 카드 RL ({_now()}): ε={eps} · 갭 {gaps.get('missing_count', '?')} · "
            f"계획 {len(planned)} · 추가 {len(added)} · "
            f"PASS {rl_stats.get('pass', 0)} FAIL {rl_stats.get('fail', 0)} · "
            f"가중치 {top_s or '—'} · {titles}"
        )
        return True, msg
    except Exception as e:
        return False, f"차수 카드 RL 실패: {e!s}"


def job_kiwoom_rl_train(agent: dict) -> tuple[bool, str]:
    """RL 가중치 학습만 (확정·오류·대기 카드 피드백)."""
    try:
        import kiwoom_card_rl_engine as rle

        tr = rle.train_step()
        st = rle.status()
        top = tr.get("top_categories") or st.get("top_categories") or []
        top_s = ", ".join(f"{x.get('category')}×{x.get('weight')}" for x in top[:4])
        return True, (
            f"차수 RL 학습 ({_now()}): 오류종 {tr.get('error_kinds', 0)} · "
            f"대기점검 {tr.get('pending_scored', 0)} · ε={st.get('epsilon')} · {top_s or '—'}"
        )
    except Exception as e:
        return False, f"차수 RL 학습 실패: {e!s}"


def job_homepage_design_pulse(agent: dict) -> tuple[bool, str]:
    """홈페이지 디자인부 상태 점검(지시·로그 중심)."""
    try:
        import agent_office_tasks as tasks

        pending = [
            t
            for t in tasks.list_tasks(limit=50)
            if isinstance(t, dict)
            and (t.get("division") or "") == "homepage-design"
            and (t.get("status") or "") in ("queued", "in_progress")
        ]
        n = len(pending)
        return True, (
            f"홈페이지 디자인 ({_now()}): 대기·진행 지시 {n}건 · "
            "레이아웃·토큰·컴포넌트는 작업 지시로 전달하세요."
        )
    except Exception as e:
        return False, f"홈페이지 디자인 점검 실패: {e!s}"


def job_kiwoom_catalog_maintain(agent: dict) -> tuple[bool, str]:
    """카탈로그(원히어로·매매원칙·오류) 항상 sync + 구형 카드 합침."""
    try:
        import wonhero_catalog_maintain as wcm

        out = wcm.run(merge=True, sync=True, dedupe=True, wiki=True)
        m = out.get("merge") or {}
        s = out.get("sync") or {}
        d = out.get("dedupe") or {}
        return True, (
            f"카탈로그 유지 ({_now()}): 합침 삭제 {m.get('deleted', 0)} · "
            f"sync +{s.get('added', 0)} ↻{s.get('revised', 0)} · "
            f"중복정리 {d.get('deleted', 0)}"
        )
    except Exception as e:
        return False, f"카탈로그 유지 실패: {e!s}"


def job_kiwoom_wonhero_monitor(agent: dict) -> tuple[bool, str]:
    """kisstock bot_log → 모니터 카드 revise·확정."""
    import os

    try:
        import wonhero_trade_monitor as mon

        if not mon._enabled():
            return True, "원히어로 모니터 비활성(WONHERO_MONITOR_ENABLED=0)"
        max_c = max(1, int(os.getenv("WONHERO_MONITOR_MAX_CARDS", "4") or "4"))
        out = mon.run(dry_run=False, max_cards=max_c)
        if not out.get("ok"):
            return False, f"원히어로 모니터 실패 ({_now()})"
        cards = out.get("cards") or []
        if int(out.get("new_events") or 0) == 0:
            return True, f"원히어로 모니터 ({_now()}): 신규 bot_log 없음"
        parts = [
            f"{c.get('action')}→#{c.get('card_id')}{'↻' if c.get('revised') else '+'}"
            for c in cards[:5]
            if c.get("card_id")
        ]
        detail = ", ".join(parts) or "(카드 갱신 없음)"
        return True, (
            f"원히어로 모니터 ({_now()}): bot_log +{out.get('new_events')}건 · "
            f"last_id={out.get('last_log_id')} · {detail}"
        )
    except Exception as e:
        return False, f"원히어로 모니터 오류: {e!s}"


def job_kiwoom_error_resolve(agent: dict) -> tuple[bool, str]:
    issues: list[str] = []
    try:
        import agent_office_health

        for c in agent_office_health.run_checks().get("checks") or []:
            if isinstance(c, dict) and not c.get("ok"):
                issues.append(f"{c.get('name')}: {str(c.get('detail') or '')[:72]}")
    except Exception as e:
        issues.append(f"health: {e!s}")
    try:
        st = _kiwoom_stats()
        if int(st.get("pending") or 0) > 25:
            issues.append(f"학습 대기 {st['pending']}건 과다")
    except Exception as e:
        issues.append(f"학습부: {e!s}")
    try:
        import kiwoom_learning_errors as kerr

        meta_added = kerr.ensure_error_learning_cards()
        err_lines = kerr.summary_lines()
        if meta_added:
            err_lines.insert(0, f"오류 학습 카드 +{meta_added}")
    except Exception as e:
        err_lines = [f"오류 로그: {e!s}"[:80]]

    if issues:
        return False, "오류 점검 ⚠ " + "; ".join(issues[:6]) + "\n" + "\n".join(err_lines[:4])
    return True, f"오류 점검 ({_now()}): 학습부·health — 이상 없음\n" + "\n".join(err_lines[:5])
