"""
원키스US(wonkisus) 매매·운용 카탈로그 — C:\\커셔\\주식\\wonkisus 소스 기준.

hts_agents_us.py · us_rebalance.py · auto_bot.py(US) · gemma24 Wiki.
원히어로(kiwoom) 규칙과 분리 — Agent Office workisus-chasu 전용.
"""
from __future__ import annotations

WONKISUS_RULE_CARDS: list[dict] = [
    {
        "title": "원키스US·운영 개요(wonkisus)",
        "catalog_seed": "wonkisus_ops_overview",
        "category": "workisus",
        "priority": 90,
        "body": (
            "원키스US는 stock.coupax.co.kr/workisus(소스: wonkisus/shared/매직스플릿) "
            "KIS 해외(US) HTS·자동봇이다. 정본 매매법: 세븐 스플릿—단일 계좌 격자·슬롯 독립·"
            "ATR·합산 평단 방어·무손실(wonkisus_seven_split_canon). "
            "HTS 젬마 11종+오류젬마가 잔고·규칙·리스크·리밸런스·토큰·정합·주문·자동을 점검. "
            "no_slot_trading=true면 격자 자동 OFF(리밸런스/일괄 익절 대기 모드). "
            "Agent Office workisus-chasu는 세븐 스플릿 카드·오류 카드를 pack으로 축적한다."
        ),
    },
    {
        "title": "원키스US·모드(no_slot·리밸런스)",
        "catalog_seed": "wonkisus_mode_no_slot",
        "category": "workisus",
        "priority": 89,
        "body": (
            "세븐 스플릿 자동 격자: bot_settings_us no_slot_trading=false·enabled_us ON. "
            "대기/안전: no_slot_trading=true → 2·3차·15초 2차·buy_gaps 자동 OFF. "
            "rebalance_enabled=false면 sell_pcts 충족 시 broker 합산 일괄 익절. "
            "rebalance_enabled=true면 us_rebalance 목표비중·이익만 축소. "
            "모드 젬마: 스위치를 읽고 세븐 스플릿 vs 리밸런스 해석을 분기한다."
        ),
    },
    {
        "title": "원키스US·한 계좌 차수(수동·슬롯 DB)",
        "catalog_seed": "wonkisus_manual_slot_db",
        "category": "workisus",
        "priority": 88,
        "body": (
            "세븐 스플릿: 해외 1계좌·종목별 슬롯 1(앵커)·2(15초)·3~N(buy_gaps)을 "
            "positions DB·/api/slots?market=US로 관리. 1차는 HTS 수동 register, 2차 이후 자동. "
            "3001 차수 칸·차수매매 탭=슬롯 상태 표시. 3002 차수=슬롯 번호. "
            "market=US 필터·reconcile_us 정합(손실 매도 없음)."
        ),
    },
    {
        "title": "원키스US·리밸런스 규칙",
        "catalog_seed": "wonkisus_rebalance_rules",
        "category": "workisus",
        "priority": 87,
        "body": (
            "us_rebalance.run_us_rebalance_cycle: no_slot_trading且rebalance_enabled일 때. "
            "매도: 보유 비중이 목표보다 크고 profit_pct>0(이익)일 때만 과대분 축소. "
            "매수: 목표 비중 미달 종목 보충. "
            "target_weight_pct 미설정 시 enabled 종목에 잔여 비중 균등. "
            "리밸런스 직전 KIS 해외 잔고 강제 재조회. "
            "리밸런스 젬마: enabled 종목 0이면 WARN."
        ),
    },
    {
        "title": "원키스US·리스크(무손실·이익만 매도)",
        "catalog_seed": "wonkisus_risk_profit_only",
        "category": "workisus",
        "priority": 86,
        "body": (
            "무손실 원칙: 손실 구간 시장가 매도·손절 없음. "
            "익절만: 표시 수익>0 + sell_pcts+fee_buffer(US 0.12%p). "
            "합산 평단≤0%면 개별 익절 보류(get_account_avg_profit). "
            "ATR 2~10차 sell 1.5~4%(wonkisus_atr_musonsil_policy). "
            "리스크 젬마·safe_policy_banner 동일 안내."
        ),
    },
    {
        "title": "원키스US·bot_settings_us·종목",
        "catalog_seed": "wonkisus_stock_settings",
        "category": "workisus",
        "priority": 85,
        "body": (
            "stock_settings[티커]: enabled, target_weight_pct, buy_gaps, sell_pcts, buy_qtys 등. "
            "매매규칙 젬마: ON 종목 수·sell_pcts·target_weight — 변경은 [3003] 매매설정. "
            "종목 젬마: enabled vs 실잔고 보유 대조·「티커 조사」채팅. "
            "enabled 미보유·보유 but OFF 경고. "
            "자동 젬마: enabled_us·mode auto/manual. "
            "멀티 젬마 스위치는 rebalance_enabled(리밸런스/멀티매매)와 연동."
        ),
    },
    {
        "title": "원키스US·잔고·KIS API",
        "catalog_seed": "wonkisus_balance_kis",
        "category": "workisus",
        "priority": 84,
        "body": (
            "잔고 젬마: KIS 해외 실잔고·USD 예수금·종목 비중%. "
            "토큰 젬마: KIS_APP_KEY·fetch_balance_us 성공 여부. "
            "parse_us_portfolio_totals: 총평가·주문가능 현금. "
            "잔고 갱신 시 슬롯 셀 in-place 패치(깜빡임 방지). "
            "계좌번호·API키는 학습 카드·로그에 넣지 않는다."
        ),
    },
    {
        "title": "원키스US·주문·3002",
        "catalog_seed": "wonkisus_order_3002",
        "category": "workisus",
        "priority": 83,
        "body": (
            "주문 젬마: [3002] 수동 주문·미체결. "
            "봇 자동 매수는 게이트( enabled·쿨다운·장중) 통과 후만. "
            "slot_num 지정 시 bot DB upsert/close 연동(dashboard 주문 API). "
            "시장가·정정취소·25/50/전액 UI. "
            "원히어로 자동 register·15초 2차와 별개 — 사용자가 차수·수량을 직접 결정."
        ),
    },
    {
        "title": "원키스US·HTS 젬마 에이전트 11종",
        "catalog_seed": "wonkisus_hts_agents_roster",
        "category": "workisus",
        "priority": 82,
        "body": (
            "hts_agents_us AGENTS: mode(상시)·balance·stocks·rules·risk·rebalance·"
            "token·reconcile·order·auto·multi. "
            "run_us_trade_watch가 enabled 에이전트별 _run_agent_live 점검 후 board에 post. "
            "Agent Office workisus-chasu 에이전트는 동일 역할을 "
            "학습·지시·cron job으로 미러링한다. "
            "소스 경로: wonkisus/shared/매직스플릿/scripts/hts_agents_us.py."
        ),
    },
    {
        "title": "원키스US vs 원히어로·매매 방법",
        "catalog_seed": "workisus_vs_wonhero_method",
        "category": "workisus",
        "priority": 81,
        "body": (
            "원키스US: KIS 해외·기본 no_slot+선택적 리밸런스·수동 HTS·슬롯 DB. "
            "원히어로: 키움·MagicSplit 자동·ATR gap·멀티 cascade. "
            "US에서 no_slot_trading=false면 자동 차수 로직이 원히어로와 유사해질 수 있으나 "
            "증권사·설정·계좌 구조가 다르다. "
            "카드·pack·에이전트 division을 섞지 않는다."
        ),
    },
]


def all_wonkisus_specs() -> list[dict]:
    return sorted(WONKISUS_RULE_CARDS, key=lambda s: -(s.get("priority") or 0))
