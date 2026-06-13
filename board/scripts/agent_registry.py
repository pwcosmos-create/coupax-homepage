"""
에이전트 레지스트리: 스킬 목록, mode_on, 작업 주기.

  python scripts/agent_registry.py list
  python scripts/agent_registry.py mode etf_sync on
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import json_store

BOARD = Path(__file__).resolve().parents[1]
REGISTRY_PATH = BOARD / "data" / "agent_registry.json"
FEED_PATH = BOARD / "data" / "agent_office_feed.json"


def _default_registry() -> dict:
    return {"global_always_on": False, "office_always_on": False, "agents": []}


DIVISION_FINANCE = "finance"
DIVISION_SAJU = "saju-learn"
DIVISION_KIWOM = "kiwoom-chasu"
DIVISION_STOCK = "stock-watch"
DIVISION_DESIGN = "homepage-design"
DIVISION_WORKISUS = "workisus-chasu"
DIVISION_GWANSANG = "gwansang-learn"
DIVISION_CHIEF_DEV = "chief-dev"
ALL_DIVISIONS = (
    DIVISION_FINANCE,
    DIVISION_SAJU,
    DIVISION_KIWOM,
    DIVISION_STOCK,
    DIVISION_DESIGN,
    DIVISION_WORKISUS,
    DIVISION_GWANSANG,
    DIVISION_CHIEF_DEV,
)

# 사무실 UI — 사업부별 팀장 호칭 (탭·픽셀 사무실·피드 공통)
DIVISION_META: dict[str, dict[str, str]] = {
    DIVISION_FINANCE: {
        "short": "금융 블로그",
        "team_leader": "금융 블로그 팀장",
        "emoji": "💰",
    },
    DIVISION_CHIEF_DEV: {
        "short": "수석 개발자",
        "team_leader": "수석 개발자 팀장",
        "emoji": "👨‍💻",
        "note": "학습 중",
    },
    DIVISION_SAJU: {
        "short": "사주 학습",
        "team_leader": "사주 학습 팀장",
        "emoji": "✦",
    },
    DIVISION_GWANSANG: {
        "short": "관상 학습",
        "team_leader": "관상 학습 팀장",
        "emoji": "👤",
    },
    DIVISION_KIWOM: {
        "short": "원히어로 차수거래",
        "team_leader": "원히어로 차수 팀장",
        "emoji": "📈",
    },
    DIVISION_STOCK: {
        "short": "주식 시황",
        "team_leader": "주식 시황 팀장",
        "emoji": "🌐",
    },
    DIVISION_DESIGN: {
        "short": "홈페이지 디자인",
        "team_leader": "홈페이지 디자인 팀장",
        "emoji": "🎨",
    },
    DIVISION_WORKISUS: {
        "short": "원키스US차수",
        "team_leader": "원키스US차수 팀장",
        "emoji": "🇺🇸",
    },
}


def division_team_leader(division: str) -> str:
    meta = DIVISION_META.get((division or "").strip(), {})
    if meta.get("team_leader"):
        return str(meta["team_leader"])
    short = meta.get("short") or (division or DIVISION_FINANCE)
    return f"{short} 팀장"


def division_meta_for(division: str) -> dict[str, str]:
    d = (division or DIVISION_FINANCE).strip()
    base = dict(DIVISION_META.get(d, {}))
    if not base.get("team_leader"):
        base["team_leader"] = division_team_leader(d)
    base.setdefault("short", d)
    base.setdefault("emoji", "🏢")
    return base


def agent_division(agent: dict | None) -> str:
    if not isinstance(agent, dict):
        return DIVISION_FINANCE
    d = (agent.get("division") or DIVISION_FINANCE).strip()
    return d if d in ALL_DIVISIONS else DIVISION_FINANCE


def division_for_agent_id(agent_id: str, registry: dict | None = None) -> str:
    aid = (agent_id or "").strip()
    if not aid:
        return DIVISION_FINANCE
    for a in (registry or load_registry()).get("agents") or []:
        if isinstance(a, dict) and a.get("id") == aid:
            return agent_division(a)
    return DIVISION_FINANCE


def filter_agents_by_division(agents: list, division: str) -> list[dict]:
    div = (division or DIVISION_FINANCE).strip()
    out: list[dict] = []
    for a in agents or []:
        if isinstance(a, dict) and agent_division(a) == div:
            out.append(a)
    return out


def agent_ids_for_division(agents: list, division: str) -> set[str]:
    return {(a.get("id") or "").strip() for a in filter_agents_by_division(agents, division) if a.get("id")}


def _normalize_registry(data: dict) -> dict:
    if not isinstance(data, dict):
        return _default_registry()
    data.setdefault("office_always_on", False)
    data.setdefault("global_always_on", False)
    agents = data.get("agents")
    data["agents"] = agents if isinstance(agents, list) else []
    for a in data["agents"]:
        if isinstance(a, dict):
            a.setdefault("division", DIVISION_FINANCE)
    return data


def load_registry() -> dict:
    try:
        data = json_store.load_json(REGISTRY_PATH, default=_default_registry())
    except json_store.JsonStoreError:
        return _default_registry()
    return _normalize_registry(data)


def save_registry(data: dict) -> None:
    json_store.save_json(REGISTRY_PATH, _normalize_registry(data))


def registry_map(data: dict | None = None) -> dict[str, dict]:
    data = data or load_registry()
    out: dict[str, dict] = {}
    for a in data.get("agents") or []:
        if isinstance(a, dict):
            aid = (a.get("id") or "").strip()
            if aid:
                out[aid] = a
    return out


def merge_agents_for_office(feed: dict, registry: dict | None = None) -> list[dict]:
    """피드 agents + 레지스트리(스킬·mode) 병합."""
    registry = registry or load_registry()
    rmap = registry_map(registry)
    seen: set[str] = set()
    merged: list[dict] = []

    for a in registry.get("agents") or []:
        if not isinstance(a, dict):
            continue
        aid = (a.get("id") or "").strip()
        if not aid:
            continue
        seen.add(aid)
        row = dict(a)
        row.setdefault("division", DIVISION_FINANCE)
        merged.append(row)

    for a in feed.get("agents") or []:
        if not isinstance(a, dict):
            continue
        aid = (a.get("id") or "").strip()
        if not aid or aid in seen:
            continue
        seen.add(aid)
        row = dict(a)
        row.setdefault("mode_on", False)
        row.setdefault("skills", [])
        row.setdefault("interval_minutes", 120)
        row.setdefault("job", "heartbeat")
        merged.append(row)

    return merged


def set_agent_mode(agent_id: str, mode_on: bool, *, global_always_on: bool | None = None) -> dict:
    data = load_registry()
    found = False
    for a in data.get("agents") or []:
        if isinstance(a, dict) and a.get("id") == agent_id:
            a["mode_on"] = bool(mode_on)
            found = True
            break
    if not found:
        raise KeyError(f"unknown agent: {agent_id}")
    if not mode_on and is_office_active(data):
        data["office_always_on"] = False
        data["global_always_on"] = False
    if global_always_on is not None:
        data["global_always_on"] = bool(global_always_on)
        data["office_always_on"] = bool(global_always_on)
    save_registry(data)
    _sync_feed_agents(merge_agents_for_office(_load_feed_light(), data))
    return registry_map(data)[agent_id]


def set_office_always_on(enabled: bool) -> dict:
    """사무실 전체 상시 ON — 모든 에이전트 ON + worker 가동."""
    data = load_registry()
    on = bool(enabled)
    data["office_always_on"] = on
    data["global_always_on"] = on
    for a in data.get("agents") or []:
        if isinstance(a, dict):
            a["mode_on"] = on
    save_registry(data)
    _sync_feed_agents(merge_agents_for_office(_load_feed_light(), data))
    return data


def set_global_always_on(enabled: bool) -> dict:
    """전체 에이전트 ON (사무실 전체 ON 과 동기)."""
    return set_office_always_on(enabled)


def activate_all_agents(*, skip_ids: frozenset[str] | None = None) -> dict:
    """사무실 전체 ON + 개별 mode_on 활성화 (skip_ids 제외)."""
    skip = skip_ids or frozenset({"etf_sync"})
    data = set_office_always_on(True)
    for a in data.get("agents") or []:
        if isinstance(a, dict) and (a.get("id") or "") not in skip:
            a["mode_on"] = True
    save_registry(data)
    _sync_feed_agents(merge_agents_for_office(_load_feed_light(), data))
    return data


def is_office_active(data: dict | None = None) -> bool:
    data = data or load_registry()
    return bool(data.get("office_always_on") or data.get("global_always_on"))


def update_agent_run(agent_id: str, status: str) -> None:
    data = load_registry()
    for a in data.get("agents") or []:
        if isinstance(a, dict) and a.get("id") == agent_id:
            a["last_run_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            a["last_status"] = status[:40]
            break
    save_registry(data)


def _load_feed_light() -> dict:
    if not FEED_PATH.is_file():
        return {"agents": [], "messages": []}
    with open(FEED_PATH, encoding="utf-8") as f:
        d = json.load(f)
    return d if isinstance(d, dict) else {"agents": [], "messages": []}


def _sync_feed_agents(agents: list[dict]) -> None:
    """피드 JSON의 agents 목록을 레지스트리 병합본과 동기(이름·역할만)."""
    feed = _load_feed_light()
    slim = []
    for a in agents:
        slim.append(
            {
                "id": a.get("id"),
                "name": a.get("name"),
                "emoji": a.get("emoji"),
                "role": a.get("role"),
            }
        )
    feed["agents"] = slim
    FEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(FEED_PATH, "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list")

    m = sub.add_parser("mode")
    m.add_argument("agent_id")
    m.add_argument("on_off", choices=["on", "off"])

    g = sub.add_parser("global")
    g.add_argument("on_off", choices=["on", "off"])

    o = sub.add_parser("office")
    o.add_argument("on_off", choices=["on", "off"])

    args = p.parse_args()
    if args.cmd == "list":
        for a in load_registry().get("agents") or []:
            on = "ON" if a.get("mode_on") else "off"
            print(f"{a.get('id')}: {on} job={a.get('job')} every {a.get('interval_minutes')}m")
        return 0
    if args.cmd == "mode":
        set_agent_mode(args.agent_id, args.on_off == "on")
        print("OK", args.agent_id, args.on_off)
        return 0
    if args.cmd == "global":
        set_global_always_on(args.on_off == "on")
        print("OK global", args.on_off)
        return 0
    if args.cmd == "office":
        set_office_always_on(args.on_off == "on")
        print("OK office", args.on_off)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
