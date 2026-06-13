"""원히어로 매매원칙 — 학습 카드 (운용 철학·불변 원칙).

wonhero_card_catalog.all_wonhero_specs() 에 병합.
"""
from __future__ import annotations

WONHERO_PRINCIPLE_CARDS: list[dict] = [
    {
        "title": "매매원칙 · 무조건 익절",
        "catalog_seed": "principle_unconditional_take_profit",
        "category": "principle",
        "priority": 94,
        "body": (
            "원히어로 최상위 원칙: 익절 조건이 충족되면 반드시 청산한다. "
            "슬롯별 sell_pcts+수수료 버퍼·합산 이익 게이트·장중(is_kr_market_open)이 맞으면 "
            "봇이 시장가 익절을 넣으며, 「더 오를 것 같다」로 미루거나 HTS에서 임의로 취소하지 않는다. "
            "손절 자동매도는 없지만, 이익 구간에서 익절선 통과 후 미청산은 원칙 위반이다. "
            "익절·sell_pcts·슬롯·1차·2차·3차·ATR·계좌·체결·분할 키워드를 본문에 넣는다."
        ),
    },
    {
        "title": "매매원칙 · 분할·슬롯",
        "catalog_seed": "principle_split_slots",
        "category": "principle",
        "priority": 91,
        "body": (
            "한 번에 몰빵하지 않고 슬롯(1·2·3차…)으로 나눠 매수한다. "
            "각 슬롯은 독립 익절 sell_pcts를 가진다. "
            "차수거래의 핵심은 평단 분산과 구간별 청산이며, 원히어로 MagicSplit이 이를 자동화한다. "
            "1차·2차·3차·슬롯·익절·ATR·계좌 키워드로 규칙 카드와 연결한다."
        ),
    },
    {
        "title": "매매원칙 · 1차 HTS 수동",
        "catalog_seed": "principle_manual_first",
        "category": "principle",
        "priority": 90,
        "body": (
            "진입 타이밍·종목 선택은 사람이 1차 HTS 수동으로 결정한다. "
            "봇은 잔고 인식(register) 이후 2차·3차·익절을 규칙대로 실행한다. "
            "1차를 봇에 맡기지 않는 것이 원히어로 운용 원칙이다. "
            "1차·2차·슬롯·계좌·체결·원히어로를 본문에 명시한다."
        ),
    },
    {
        "title": "매매원칙 · 룰 우선·감정 배제",
        "catalog_seed": "principle_rule_over_emotion",
        "category": "principle",
        "priority": 89,
        "body": (
            "손실 구간에서 추가 감정 매수·복수 라운드를 하지 않고 buy_gaps·당일 스킵 규칙을 따른다. "
            "was_sold_today·쿨다운·enabled 플래그는 감정 매매를 막는 가드다. "
            "학습 카드·bot_log가 근거이며 추측으로 설정을 바꾸지 않는다. "
            "슬롯·익절·ATR·1차·2차·계좌 키워드를 유지한다."
        ),
    },
    {
        "title": "매매원칙 · 익절만 자동 청산",
        "catalog_seed": "principle_profit_exit_only",
        "category": "principle",
        "priority": 88,
        "body": (
            "자동 손절 매도 경로는 없다. 봇 청산은 익절(sell_pcts)뿐이며, 조건 충족 시 무조건 익절이 최상위다. "
            "손실 구간에서는 추가매수 중단·보유가 원칙이며 panic sell을 봇에 기대하지 않는다. "
            "합산 이익 게이트가 켜져 있으면 개별 슬롯 익절도 합산 손익을 본 뒤, 통과하면 반드시 익절한다. "
            "익절·분할·ATR·슬롯·1차·2차·손절 없음·sell_pcts를 명확히 한다."
        ),
    },
    {
        "title": "매매원칙 · ATR 변동성 맞춤",
        "catalog_seed": "principle_atr_adaptive",
        "category": "principle",
        "priority": 87,
        "body": (
            "고정 -30/+30%가 아니라 ATR 국면으로 buy_gaps·sell_pcts를 조정한다. "
            "변동성 큰 종목은 간격을 넓히고, 작으면 촘촘히 분할한다. "
            "장 시작 전 ATR 갱신 습관과 대시보드 수동 갱신을 병행한다. "
            "ATR·buy_gaps·sell_pcts·1차·2차·슬롯·익절·계좌를 포함한다."
        ),
    },
    {
        "title": "매매원칙 · 합산 이익 후 익절",
        "catalog_seed": "principle_avg_profit_first",
        "category": "principle",
        "priority": 86,
        "body": (
            "종목·계좌 합산 평단이 플러스일 때만 차수별 익절을 평가한다(게이트). "
            "한 슬롯만 이익이어도 전체가 손실이면 익절 주문을 내지 않는다. "
            "게이트를 통과한 뒤 sell_pcts가 충족되면 무조건 익절 원칙이 적용된다. "
            "익절·합산·슬롯·1차·2차·ATR·계좌·체결·sell_pcts 키워드를 넣는다."
        ),
    },
    {
        "title": "매매원칙 · 3차부터 추격 금지",
        "catalog_seed": "principle_no_chase_buy",
        "category": "principle",
        "priority": 85,
        "body": (
            "2차는 15초 규칙으로 빠르게 잡을 수 있으나, 3차 이후는 buy_gaps 하락 조건 없이 추가매수하지 않는다. "
            "상승 추격·뉴스 추격 매수는 원칙에 어긋난다. "
            "gap 미충족 시 로그만 남기고 기다리는 것이 정상이다. "
            "1차·2차·3차·슬롯·ATR·buy_gaps·익절·계좌를 본문에 쓴다."
        ),
    },
    {
        "title": "매매원칙 · 1번 계좌 메인",
        "catalog_seed": "principle_account1_main",
        "category": "principle",
        "priority": 84,
        "body": (
            "instant 2차·1차 수동·합산 게이트는 1번 메인 계좌 전제다. "
            "2번+ cascade·account_tag 종목은 규칙이 달라지므로 혼용하지 않는다. "
            "계좌 이체·cascade 전에 1번 슬롯·손익을 먼저 확인한다. "
            "계좌·cascade·1차·2차·슬롯·익절·ATR·체결을 포함한다."
        ),
    },
    {
        "title": "매매원칙 · 당일 라운드 제한",
        "catalog_seed": "principle_daily_round_limit",
        "category": "principle",
        "priority": 83,
        "body": (
            "당일 익절한 종목은 was_sold_today로 1차 자동 재등록을 막는다. "
            "같은 날 반복 진입·복수 라운드는 원칙상 제한하며 RE_ENTRY는 설정으로만 허용한다. "
            "과매매 방지가 분할·익절 원칙과 함께 운용 리스크를 낮춘다. "
            "슬롯·1차·2차·익절·ATR·계좌·당일 키워드를 명시한다."
        ),
    },
    {
        "title": "매매원칙 · cascade 손실 이전",
        "catalog_seed": "principle_cascade_handoff",
        "category": "principle",
        "priority": 82,
        "body": (
            "1번 합산 손실이 임계 이하면 3차+ 추가매수를 멈추고 cascade 계좌로 넘긴다. "
            "한 계좌에 손실을 무한히 쌓지 않는 것이 멀티 운용 원칙이다. "
            "cascade 행 buy_gaps·sell_pcts는 ATR 갱신 시 메인과 맞춘다. "
            "cascade·계좌·슬롯·1차·2차·3차·ATR·익절을 포함한다."
        ),
    },
    {
        "title": "매매원칙 · 잔고·DB 일치",
        "catalog_seed": "principle_reconcile_truth",
        "category": "principle",
        "priority": 81,
        "body": (
            "HTS 실잔고가 진실이며, DB 슬롯은 봇이 이해하는 모델이다. "
            "불일치 시 reconcile·self-heal로 맞추고 규칙 매매를 재개한다. "
            "수량·슬롯이 어긋난 채 2차·3차를 돌리지 않는다. "
            "reconcile·슬롯·1차·2차·익절·ATR·계좌·체결 키워드를 넣는다."
        ),
    },
    {
        "title": "매매원칙 · 학습 후 실전",
        "catalog_seed": "principle_learn_then_trade",
        "category": "principle",
        "priority": 80,
        "body": (
            "coupax 학습부 9단계·매매원칙 카드·규칙 카드를 읽은 뒤 원히어로에서 소액·1종목으로 리허설한다. "
            "카드는 주문을 대신하지 않으며, 실전 bot_log·monitor 카드로 복기한다. "
            "확정 카드·Wiki·학습 경로 진행률을 운용 체크리스트로 쓴다. "
            "원히어로·슬롯·1차·2차·익절·ATR·계좌·체결을 포함한다."
        ),
    },
    {
        "title": "매매원칙 · 수수료·버퍼",
        "catalog_seed": "principle_fee_buffer",
        "category": "principle",
        "priority": 79,
        "body": (
            "익절 판단에 sell_fee_buffer_pct를 더해 수수료·슬리피지를 반영한다. "
            "표시 수익이 임계를 살짝 넘는 착시 익절을 줄인다. "
            "sell_pcts를 너무 낮게 잡으면 체결·수수료 후 실익이 없을 수 있다. "
            "익절·분할·슬롯·1차·2차·ATR·계좌·체결 키워드를 본문에 넣는다."
        ),
    },
    {
        "title": "매매원칙 · 종목·설정 고정",
        "catalog_seed": "principle_config_lock",
        "category": "principle",
        "priority": 78,
        "body": (
            "장중에 buy_gaps·enabled·cascade를 잦게 바꾸지 않는다. "
            "변경은 ATR 갱신·장전 점검·학습 카드 수정 후에 한다. "
            "종목마다 stock_settings 한 벌을 명확히 두고 스캘프·멀티 여부를 혼동하지 않는다. "
            "ATR·슬롯·1차·2차·익절·계좌·cascade·원히어로를 포함한다."
        ),
    },
    {
        "title": "매매원칙 · 2차·3차 역할 분리",
        "catalog_seed": "principle_2nd_3rd_roles",
        "category": "principle",
        "priority": 77,
        "body": (
            "2차는 포지션 확보(15초 instant), 3차+는 하락 분할(buy_gaps)로 역할이 다르다. "
            "2차를 3차처럼 gap 대기하거나, 3차를 2차처럼 즉시 넣으려 하지 않는다. "
            "로그 reason으로 어떤 규칙이 발동했는지 항상 확인한다. "
            "1차·2차·3차·슬롯·15초·ATR·buy_gaps·익절·계좌·체결을 명시한다."
        ),
    },
    {
        "title": "매매원칙 · 목차·연결",
        "catalog_seed": "principle_index",
        "category": "principle",
        "priority": 76,
        "body": (
            "최상위: 매매원칙 · 무조건 익절(principle_unconditional_take_profit). "
            "이후 principle_* → wonhero_* → meta_err_* → monitor_live_* 순으로 읽는다. "
            "학습 경로 9단계는 실습 순서, 원칙 카드는 왜 그렇게 하는지 이유다. "
            "투자 권유·수익 약속 없음. "
            "원히어로·슬롯·1차·2차·3차·ATR·익절·분할·계좌·체결·cascade 키워드를 포함한다."
        ),
    },
    {
        "title": "매매원칙 · 1차 999% 앵커와 15초 무한 순환",
        "catalog_seed": "principle_anchor_and_infinite_loop",
        "category": "principle",
        "priority": 75,
        "body": (
            "세븐 스플릿(격자) 모델에서는 1차 익절을 999%로 설정해 절대 팔리지 않는 '앵커(닻)'로 사용한다. "
            "1차가 청산되지 않아 당일 라운드 종료(was_sold_today)가 발동하지 않으므로, "
            "빈 슬롯이 된 2차는 15초 즉시 매수 규칙을 통해 무한 재진입이 가능하다. "
            "안전하게 확보된 라운드 안에서 슬롯 1개(2차)만 사용해 횡보장 수익을 극대화하는 예외 규칙이다. "
            "원히어로·슬롯·1차·2차·익절·당일 재진입·15초 키워드를 포함한다."
        ),
    },
    {
        "title": "매매원칙 · 월배당 방어 (무적 트라이앵글)",
        "catalog_seed": "principle_monthly_dividend_defense",
        "category": "principle",
        "priority": 74,
        "body": (
            "수동 손절매가 없는 원히어로의 최종 방패는 '월배당 종목' 선택이다. "
            "상승/횡보장에서는 15초 순환 매매로 시세 차익(Capital Gain)을 창출하고, "
            "하락장에서는 슬롯을 분할(buy_gaps)하여 평단가를 방어하며, "
            "최악의 장기 침체로 시드가 묶였을 때는 강제 장기 투자가 아닌 월배당금(Cash Flow)을 수령하며 대기한다. "
            "슬롯·익절·분할·배당·손절 없음·원히어로 키워드를 본문에 넣는다."
        ),
    },
    {
        "title": "매매원칙 · 15초 순환 시세 차익 (Capital Gain)",
        "catalog_seed": "principle_15s_capital_gain",
        "category": "principle",
        "priority": 73,
        "body": (
            "1차 계좌(닻)가 배당 수익(Income Gain)을 장기적으로 확보하는 동안, "
            "가벼운 2차 계좌는 15초 단위로 샀다 팔았다를 반복하며 시세 차익(Capital Gain)을 쉴 새 없이 긁어모은다. "
            "이는 횡보장에서도 시스템이 수익을 내도록 만드는 투잡(Two-Job) 시스템의 행동 대장 역할이다. "
            "원히어로·슬롯·1차·2차·익절·배당·시세차익·15초 키워드를 포함한다."
        ),
    },
    {
        "title": "매매원칙 · ATR 그물망과 고정 퍼센트의 위험성",
        "catalog_seed": "principle_atr_dynamic_net",
        "category": "principle",
        "priority": 72,
        "body": (
            "초보자처럼 -5% 등 고정된 하락률로 물타기를 하면 야생마 종목에서는 당일에 시드가 전소되고, "
            "거북이 종목에서는 봇이 평생 노는 부작용이 발생한다. "
            "원히어로는 ATR(평균 진폭)을 기반으로 종목의 현재 변동성에 맞춰 추가 매수 그물(buy_gaps)의 간격을 "
            "고무줄처럼 자동 조절하는 충격 흡수 서스펜션을 사용한다. "
            "원히어로·슬롯·ATR·buy_gaps·익절·변동성·계좌·물타기 키워드를 포함한다."
        ),
    },
]

def all_principle_specs() -> list[dict]:
    return [dict(s) for s in WONHERO_PRINCIPLE_CARDS]
