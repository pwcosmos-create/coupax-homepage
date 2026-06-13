"""사업부 공통 웹 검색 토론 cron job."""
from __future__ import annotations

from datetime import datetime

from office_web_research_units import all_unit_ids


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


_AGENT_UNIT = {
    "finance_web_research": "finance",
    "saju_web_research": "saju-learn",
    "gwansang_web_research": "gwansang-learn",
    "kiwoom_web_research": "kiwoom-chasu",
    "stock_web_research": "stock-watch",
    "design_web_research": "homepage-design",
    "workisus_web_research": "workisus-chasu",
    "office_web_research": "",
}


def job_office_web_research_pulse(agent: dict) -> tuple[bool, str]:
    import office_web_research_debate as owrd

    aid = (agent.get("id") or "").strip()
    unit = _AGENT_UNIT.get(aid) or (agent.get("division") or "").strip()
    targets = [unit] if unit in all_unit_ids() else all_unit_ids()
    lines: list[str] = []
    ok = True
    for uid in targets:
        try:
            if uid == "homepage-design":
                import homepage_design_web_research as hdwr

                out = hdwr.run_web_research_debate(max_n=1) if hdwr.enabled() else {"skipped": True}
            else:
                out = owrd.run_web_research_debate(uid, max_n=1)
            if out.get("skipped"):
                continue
            n = int(out.get("created") or 0)
            if out.get("errors"):
                ok = False
            if n and (out.get("items") or []):
                it = out["items"][0]
                lines.append(f"{uid}: #{it.get('card_id')} refs={it.get('refs', 0)}")
            elif not n:
                lines.append(f"{uid}: —")
        except Exception as e:
            ok = False
            lines.append(f"{uid}: err {e!s:.40}")
    if not lines:
        return True, f"웹리서치 ({_now()}): 비활성"
    return ok, f"웹리서치 ({_now()}): " + " · ".join(lines[:6])
