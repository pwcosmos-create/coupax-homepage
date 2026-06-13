"""홈페이지 디자인부 주기 job."""
from __future__ import annotations

from datetime import datetime


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _design_stats() -> dict:
    import agent_office_homepage_design_learn as dl

    return dl.stats()


def job_homepage_design_pulse(agent: dict) -> tuple[bool, str]:
    """지시·카드 현황 점검."""
    try:
        import agent_office_tasks as tasks

        st = _design_stats()
        pending_tasks = [
            t
            for t in tasks.list_tasks(limit=50)
            if isinstance(t, dict)
            and (t.get("division") or "") == "homepage-design"
            and (t.get("status") or "") in ("queued", "in_progress")
        ]
        return True, (
            f"홈페이지 디자인 ({_now()}): 카드 {st['total']} · 확정 {st['confirmed']} · "
            f"대기 지시 {len(pending_tasks)}건 · 재사용 플레이북 pack 동기화 가능"
        )
    except Exception as e:
        return False, f"홈페이지 디자인 점검 실패: {e!s}"


def job_homepage_design_pack_sync(agent: dict) -> tuple[bool, str]:
    import agent_office_homepage_design_learn as dl

    dl.export_pack()
    st = _design_stats()
    return True, f"디자인 pack ({_now()}): 확정 {st['confirmed']}건 · CURSOR_HOMEPAGE_DESIGN_LEARN.md 갱신"


def job_homepage_design_catalog_maintain(agent: dict) -> tuple[bool, str]:
    try:
        import homepage_design_catalog_maintain as hcm

        out = hcm.run(debate=True)
        s = out.get("sync") or {}
        d = out.get("debate") or {}
        return True, (
            f"디자인 카탈로그 ({_now()}): +{s.get('added', 0)} ↻{s.get('revised', 0)} · "
            f"토론 {d.get('seed') or '—'}"
        )
    except Exception as e:
        return False, f"디자인 카탈로그 실패: {e!s}"


def job_homepage_design_council_debate(agent: dict) -> tuple[bool, str]:
    try:
        import homepage_design_council as hdc

        out = hdc.run_debate_cycle()
        if out.get("skipped"):
            return True, f"디자인 위원회 ({_now()}): 비활성"
        items = out.get("items") or []
        if items:
            first = items[0]
            extra = f" 외 {len(items) - 1}건" if len(items) > 1 else ""
            return True, (
                f"디자인 토론·자동 ({_now()}): +{out.get('created', 0)} · "
                f"#{first.get('card_id')} {first.get('seed', '')[:40]}{extra} · "
                f"대기주제 ~{out.get('pending_specs', '?')}"
            )
        if out.get("created", 0) == 0:
            return True, f"디자인 위원회 ({_now()}): {out.get('message', '토론 없음')}"
        auto = "·자동" if out.get("auto") else ""
        return True, (
            f"디자인 토론 ({_now()}){auto}: #{out.get('card_id')} · "
            f"{out.get('seed')} · 패널 {out.get('panel', 0)}명"
        )
    except Exception as e:
        return False, f"디자인 토론 실패: {e!s}"


def _role_pulse(agent: dict, role: str, hint: str) -> tuple[bool, str]:
    st = _design_stats()
    return True, f"{role} ({_now()}): {hint} · 카드 {st['total']} · 토론 {st.get('debate_cards', 0)}"


def job_homepage_design_token_pulse(agent: dict) -> tuple[bool, str]:
    return _role_pulse(agent, "토큰젬마", "Midnight/Copper/Accent 변수 점검")


def job_homepage_design_typography_pulse(agent: dict) -> tuple[bool, str]:
    return _role_pulse(agent, "타이포젬마", "제목 clamp·본문 16px·line-height")


def job_homepage_design_layout_pulse(agent: dict) -> tuple[bool, str]:
    return _role_pulse(agent, "레이아웃젬마", "8px 그리드·375~1024 브레이크포인트")


def job_homepage_design_component_pulse(agent: dict) -> tuple[bool, str]:
    return _role_pulse(agent, "컴포넌트젬마", "헤더·카드·CTA·폼 패턴")


def job_homepage_design_a11y_pulse(agent: dict) -> tuple[bool, str]:
    return _role_pulse(agent, "접근성젬마", "대비·focus·aria")


def job_homepage_design_handoff_pulse(agent: dict) -> tuple[bool, str]:
    return _role_pulse(agent, "핸드오프젬마", "style.css :root 반영")


def job_homepage_design_ux_pulse(agent: dict) -> tuple[bool, str]:
    return _role_pulse(agent, "UX카피젬마", "CTA·placeholder·에러 문구")


def job_homepage_design_research_pulse(agent: dict) -> tuple[bool, str]:
    try:
        import homepage_design_web_research as hdwr

        if not hdwr.enabled():
            return _role_pulse(agent, "리서치젬마", "웹 리서치 비활성")
        out = hdwr.run_web_research_debate(max_n=1)
        if out.get("skipped"):
            return True, f"리서치 ({_now()}): 비활성"
        items = out.get("items") or []
        if items:
            it = items[0]
            return True, (
                f"웹리서치 토론 ({_now()}): #{it.get('card_id')} "
                f"출처 {it.get('refs', 0)}건 · {it.get('query', '')[:36]}"
            )
        if out.get("errors"):
            return False, f"웹리서치 실패: {out['errors'][0][:80]}"
        return True, f"리서치 ({_now()}): 신규 주제 없음 · 기존 축 소진"
    except Exception as e:
        return False, f"리서치젬마 실패: {e!s}"


def job_homepage_design_pii_scan(agent: dict) -> tuple[bool, str]:
    import re

    import agent_office_homepage_design_learn as dl

    hits: list[str] = []
    pats = (
        (re.compile(r"01[0-9]-?\d{3,4}-?\d{4}"), "전화"),
        (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), "이메일"),
    )
    for c in dl.list_cards(status="pending", limit=20):
        body = c.get("body") or ""
        for rx, label in pats:
            if rx.search(body):
                hits.append(f"#{c.get('id')} {label}")
                break
    st = _design_stats()
    if hits:
        return False, f"디자인 PII: {len(hits)}건 — " + "; ".join(hits[:5])
    return True, f"디자인 PII ({_now()}): 대기 {st['pending']} — 이상 없음"
