"""원키스US 젬마 ↔ 매매 정본 초점 (wonkisus-grid-trading-rules · board 카드 미사용)."""
from __future__ import annotations

import workisus_wiki_rules as wiki

# 레거시 catalog_seed — 카드 제작 중지 시 갭/시드 미사용
AGENT_CATALOG_SEEDS: dict[str, list[str]] = {}

TRADING_FOOTER: dict[str, str] = {
    "workisus_watch": "10분할·Trim/Buy·Cycle≤2·무손실·정본 준수.",
    "workisus_knowledge": "wonkisus-grid-trading-rules · 20_Meta · index.json.",
    "workisus_mode": "§3: 자동/안전·리밸런스·격자.",
    "workisus_balance": "현금10% + 9종목×10% 실비중.",
    "workisus_stocks": "9종목 enabled·목표 10%.",
    "workisus_rules": "target_cash_weight_pct=10 · rebalance_max_trades_per_cycle=2.",
    "workisus_risk": "Profit>0만 Trim · 손실 홀딩·손절 없음.",
    "workisus_rebalance": "Trim 10%(이익) · Buy 10%(하락 괴리 최우선) · Cycle 2건.",
    "workisus_token": "KIS US 토큰·잔고 API.",
    "workisus_reconcile": "market=US 슬롯·잔고 정합.",
    "workisus_order": "[3002] 수동·슬롯=차수.",
    "workisus_auto": "리밸런스 자동·Cycle당 max 2건·격자 병행.",
    "workisus_multi": "단일 해외 계좌·10자산 포트폴리오.",
    "workisus_slots": "차수 칸·슬롯 DB (격자 병행 시).",
    "workisus_hts": "workisus 3001~3005 다창.",
    "workisus_atr": "§4: ATR gap/sell · PPO · atr_timer_run.",
    "workisus_ops": "§2 Cycle≤2 · §5 실행확인·설정 서명.",
}


def seeds_for_agent(agent_id: str) -> list[str]:
    _ = agent_id
    return []


def trading_footer(agent_id: str) -> str:
    aid = (agent_id or "").strip()
    return (TRADING_FOOTER.get(aid) or wiki.focus_for_agent(aid)).strip()
