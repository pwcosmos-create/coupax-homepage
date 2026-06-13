"""agent_registry.json — 원키스US 젬마 (wonkisus Wiki 정본 · HTS 11종 + 지식·ATR·운영)."""
from __future__ import annotations

import json
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
REGISTRY_PATH = BOARD / "data" / "agent_registry.json"

# hts_agents_us.py 미러 + Agent Office (학습 카드 에이전트는 퇴역)
RETIRED_AGENT_IDS = frozenset(
    {
        "workisus_curator",
        "workisus_sync",
        "workisus_atr_rl",
        "workisus_error_fix",
    }
)

WORKISUS_AGENTS: list[dict] = [
    {
        "id": "workisus_watch",
        "name": "워치젬마",
        "emoji": "👁️",
        "role": "전 에이전트·정본 점검",
        "division": "workisus-chasu",
        "mode_on": True,
        "interval_minutes": 30,
        "interval_label": "30분",
        "job": "workisus_watch_pulse",
        "skills": [{"id": "watch", "title": "10%·무손실", "summary": "wonkisus-grid-trading-rules 요약."}],
    },
    {
        "id": "workisus_knowledge",
        "name": "지식젬마",
        "emoji": "📖",
        "role": "wonkisus Wiki 정본",
        "division": "workisus-chasu",
        "mode_on": True,
        "interval_minutes": 60,
        "interval_label": "1시간",
        "job": "workisus_wiki_pulse",
        "skills": [
            {"id": "wiki-rules", "title": "grid-trading-rules", "summary": "gemma24/10_Wiki 정본 동기."},
            {"id": "playbook", "title": "플레이북", "summary": "export_trading_context → Cursor."},
        ],
    },
    {
        "id": "workisus_mode",
        "name": "모드젬마",
        "emoji": "🎚️",
        "role": "자동·안전·리밸런스·격자",
        "division": "workisus-chasu",
        "mode_on": True,
        "interval_minutes": 45,
        "interval_label": "45분",
        "job": "workisus_mode_pulse",
        "skills": [{"id": "modes", "title": "3모드", "summary": "§3 자동/안전·리밸런스·차수(격자)."}],
    },
    {
        "id": "workisus_balance",
        "name": "잔고젬마",
        "emoji": "💰",
        "role": "현금10%+종목 비중",
        "division": "workisus-chasu",
        "mode_on": True,
        "interval_minutes": 60,
        "interval_label": "1시간",
        "job": "workisus_balance_pulse",
        "skills": [{"id": "kis-bal", "title": "10자산", "summary": "원금10%·9종목 각10% 대조."}],
    },
    {
        "id": "workisus_stocks",
        "name": "종목젬마",
        "emoji": "📈",
        "role": "9종목·enabled·보유",
        "division": "workisus-chasu",
        "mode_on": True,
        "interval_minutes": 75,
        "interval_label": "75분",
        "job": "workisus_stocks_pulse",
        "skills": [{"id": "tickers", "title": "종목", "summary": "ON/OFF·미보유·10% 목표."}],
    },
    {
        "id": "workisus_rules",
        "name": "매매규칙젬마",
        "emoji": "⚙️",
        "role": "bot_settings_us·10%",
        "division": "workisus-chasu",
        "mode_on": True,
        "interval_minutes": 80,
        "interval_label": "80분",
        "job": "workisus_rules_pulse",
        "skills": [{"id": "settings", "title": "target_cash", "summary": "target_cash_weight_pct=10."}],
    },
    {
        "id": "workisus_risk",
        "name": "리스크젬마",
        "emoji": "🛡️",
        "role": "무손실 매도·손절 없음",
        "division": "workisus-chasu",
        "mode_on": True,
        "interval_minutes": 70,
        "interval_label": "70분",
        "job": "workisus_risk_pulse",
        "skills": [{"id": "no-loss", "title": "§2", "summary": "Profit>0만 Trim·Profit≤0 홀딩."}],
    },
    {
        "id": "workisus_rebalance",
        "name": "리밸런스젬마",
        "emoji": "⚖️",
        "role": "Trim/Buy 10%·Cycle 2건",
        "division": "workisus-chasu",
        "mode_on": True,
        "interval_minutes": 90,
        "interval_label": "90분",
        "job": "workisus_rebalance_pulse",
        "skills": [
            {"id": "trim", "title": "Trim 10%", "summary": "Profit>0만 초과분 매도."},
            {"id": "buy-up", "title": "Buy 10%", "summary": "하락 괴리 최우선 보충."},
            {"id": "gradual", "title": "Cycle≤2", "summary": "rebalance_max_trades_per_cycle."},
        ],
    },
    {
        "id": "workisus_token",
        "name": "토큰젬마",
        "emoji": "🔑",
        "role": "KIS US 토큰·API",
        "division": "workisus-chasu",
        "mode_on": True,
        "interval_minutes": 120,
        "interval_label": "2시간",
        "job": "workisus_token_pulse",
        "skills": [{"id": "kis-token", "title": "토큰", "summary": "잔고 API OK."}],
    },
    {
        "id": "workisus_reconcile",
        "name": "정합젬마",
        "emoji": "🔄",
        "role": "US 슬롯 DB·대조",
        "division": "workisus-chasu",
        "mode_on": True,
        "interval_minutes": 75,
        "interval_label": "75분",
        "job": "workisus_reconcile_pulse",
        "skills": [{"id": "slots-us", "title": "market=US", "summary": "KR 슬롯 혼입 방지."}],
    },
    {
        "id": "workisus_order",
        "name": "주문젬마",
        "emoji": "📋",
        "role": "[3002] 수동·슬롯",
        "division": "workisus-chasu",
        "mode_on": True,
        "interval_minutes": 65,
        "interval_label": "65분",
        "job": "workisus_order_pulse",
        "skills": [{"id": "manual-ord", "title": "수동", "summary": "차수=슬롯·격자 1차 앵커."}],
    },
    {
        "id": "workisus_auto",
        "name": "자동젬마",
        "emoji": "🤖",
        "role": "리밸런스 자동·격자",
        "division": "workisus-chasu",
        "mode_on": True,
        "interval_minutes": 55,
        "interval_label": "55분",
        "job": "workisus_auto_pulse",
        "skills": [
            {"id": "auto-us", "title": "해외봇", "summary": "enabled_us·10% 수렴."},
            {"id": "cycle-cap", "title": "Cycle 2", "summary": "주기당 최대 2건 집행."},
        ],
    },
    {
        "id": "workisus_multi",
        "name": "멀티젬마",
        "emoji": "👥",
        "role": "단일 해외·10자산",
        "division": "workisus-chasu",
        "mode_on": True,
        "interval_minutes": 100,
        "interval_label": "100분",
        "job": "workisus_multi_pulse",
        "skills": [{"id": "portfolio", "title": "10×10%", "summary": "원금+9종목 균등."}],
    },
    {
        "id": "workisus_slots",
        "name": "차수젬마",
        "emoji": "📊",
        "role": "슬롯·차수 칸",
        "division": "workisus-chasu",
        "mode_on": True,
        "interval_minutes": 75,
        "interval_label": "75분",
        "job": "workisus_slots_pulse",
        "skills": [{"id": "cascade-slots", "title": "1·2·3차", "summary": "격자 병행 시 슬롯 표시."}],
    },
    {
        "id": "workisus_hts",
        "name": "HTS젬마",
        "emoji": "🖥️",
        "role": "3001~3005 다창",
        "division": "workisus-chasu",
        "mode_on": True,
        "interval_minutes": 90,
        "interval_label": "90분",
        "job": "workisus_hts_pulse",
        "skills": [{"id": "panels", "title": "다창", "summary": "workisus HTS UI."}],
    },
    {
        "id": "workisus_atr",
        "name": "ATR젬마",
        "emoji": "📐",
        "role": "ATR gap·sell·PPO",
        "division": "workisus-chasu",
        "mode_on": True,
        "interval_minutes": 55,
        "interval_label": "55분",
        "job": "workisus_atr_pulse",
        "skills": [
            {"id": "atr-gap", "title": "§4 gap", "summary": "극단/고변동 gap 배율."},
            {"id": "atr-ppo", "title": "PPO", "summary": "train_rl·atr_timer_run."},
        ],
    },
    {
        "id": "workisus_ops",
        "name": "운영젬마",
        "emoji": "🔧",
        "role": "무손실·점진2건·확인",
        "division": "workisus-chasu",
        "mode_on": True,
        "interval_minutes": 50,
        "interval_label": "50분",
        "job": "workisus_ops_pulse",
        "skills": [
            {"id": "gates", "title": "무손실", "summary": "Profit>0만 Trim·손절 없음."},
            {"id": "gradual", "title": "Cycle≤2", "summary": "점진 매매·몰아치기 금지."},
            {"id": "confirm", "title": "실행확인", "summary": "§5 설정 변경 서명."},
        ],
    },
]


def _upsert_agent(agents: list, row: dict) -> str:
    aid = row.get("id")
    mode_on = bool(row.get("mode_on", False))
    for i, a in enumerate(agents):
        if isinstance(a, dict) and a.get("id") == aid:
            agents[i] = {**a, **row, "mode_on": mode_on, "division": "workisus-chasu"}
            return "updated"
    agents.append({**row, "mode_on": mode_on, "division": "workisus-chasu"})
    return "added"


def _retire_legacy(agents: list) -> int:
    n = 0
    for a in agents:
        if not isinstance(a, dict):
            continue
        if (a.get("id") or "") in RETIRED_AGENT_IDS and (a.get("division") or "") == "workisus-chasu":
            if a.get("mode_on"):
                n += 1
            a["mode_on"] = False
            role = (a.get("role") or "").strip()
            if "[퇴역" not in role:
                a["role"] = (role + " [퇴역·board카드]").strip()
    return n


def main() -> int:
    if not REGISTRY_PATH.is_file():
        print("registry missing:", REGISTRY_PATH)
        return 1
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    agents = data.get("agents") or []
    counts = {"added": 0, "updated": 0}
    for row in WORKISUS_AGENTS:
        action = _upsert_agent(agents, row)
        counts[action] = counts.get(action, 0) + 1
    retired = _retire_legacy(agents)
    data["agents"] = agents
    REGISTRY_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"workisus-chasu agents: {counts} · retired_off={retired} · "
        f"active={sum(1 for r in WORKISUS_AGENTS if r.get('mode_on'))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
