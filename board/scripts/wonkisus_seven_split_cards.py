"""
원키스US(wonkisus) — 세븐 스플릿(Seven Split) 격자형 차수 매매 기법 카탈로그.

단일 해외 계좌 · 슬롯 DB · ATR(무손실) · 합산 평단 방어.
auto_bot.py US 경로(no_slot_trading=false 시) 기준.
"""
from __future__ import annotations


def all_seven_split_specs() -> list[dict]:
    return list(SEVEN_SPLIT_CARDS)


SEVEN_SPLIT_CARDS: list[dict] = [
    {
        "title": "원키스US·세븐 스플릿 매매법(정본)",
        "catalog_seed": "wonkisus_seven_split_canon",
        "category": "workisus",
        "priority": 98,
        "body": (
            "원키스US 미국주식 자동매매의 정본은 「세븐 스플릿(Seven Split)」 철학 기반 "
            "단일 계좌 격자형(Grid) 분할 매매이다. 증권 잔고는 KIS 해외 1계좌이나, "
            "봇 DB(positions·/api/slots?market=US)에서 종목별 슬롯 1~N을 독립 관리한다. "
            "ATR(실시간 변동성)으로 buy_gaps·sell_pcts·매수 수량을 갱신하고, "
            "합산 평단 방어(get_account_avg_profit)로 계좌·종목 전체가 손실(≤0%)일 때 "
            "개별 차수 익절을 보류한다. 절대 원칙: 무손실—손실 상태 시장가 매도 없음. "
            "no_slot_trading=false·enabled_us·atr_auto=true일 때 auto_bot US 루프가 이 기법을 실행한다. "
            "Agent Office 젬마·학습 카드는 이 정본을 우선한다."
        ),
    },
    {
        "title": "원키스US·세븐 스플릿 3대 철학",
        "catalog_seed": "wonkisus_seven_split_philosophy",
        "category": "workisus",
        "priority": 97,
        "body": (
            "① 무손실: 폭락해도 손실 구간에서 팔지 않는다. 시간·추가 분할 매수로 평단을 낮추고 "
            "수익 전환을 기다린다(_profit_only_sell_allowed·손실 자동매도 경로 없음). "
            "② 슬롯 독립: 한 계좌 안에서 차수(슬롯)마다 매수가·익절 목표(sell_pcts)를 따로 둔다. "
            "③ ATR 연동: 고정 % 대신 20일 ATR 등으로 하락 진입폭(buy_gaps)·익절%(sell_pcts)·"
            "수량을 시장 변동에 맞게 갱신(update_atr US/KR 스케줄). "
            "원히어로 multi cascade·다계좌 이체와 별개—원키스US는 해외 단일 계좌 격자가 중심."
        ),
    },
    {
        "title": "원키스US·1단계 1차 앵커·999% 익절",
        "catalog_seed": "wonkisus_seven_split_slot1_anchor",
        "category": "workisus",
        "priority": 96,
        "body": (
            "진입: 대표님이 MTS/HTS([3002]) 또는 증권 앱으로 최초 수동 매수 → 봇이 register로 "
            "[1차 슬롯] 인식. 1차 sell_pcts는 999% 패턴(자동 익절 안 됨)—드는 기준점(앵커). "
            "주문젬마·auto 젬마: 1차 등록 시각(_slot1_secs_ago)을 기록. "
            "합산 평단 방어 전에도 1차는 팔리지 않아 2차 순환의 기준이 된다."
        ),
    },
    {
        "title": "원키스US·1단계 2차 15초·무한 재진입",
        "catalog_seed": "wonkisus_seven_split_slot2_cycle",
        "category": "workisus",
        "priority": 95,
        "body": (
            "1차 등록 후 가격 무관 **15초 경과** 시 instant_2nd_us → 2차 시장가 매수·[2차 슬롯] 확보. "
            "2차 익절: 2차 매수가 대비 sell_pcts[1](예 +5%) 충족 시 **2차만** 시장가 익절. "
            "2차 청산 후 max_slot==1이면 다시 15초 뒤 2차 자동 재매수—횡보·상승에서 2차만 반복 수익. "
            "조건: account_tag 없음·단일 계좌·no_slot_trading=false·enabled_us·장중 게이트. "
            "스캘프·다계좌 태그 있으면 instant 2차 예외(off)."
        ),
    },
    {
        "title": "원키스US·2단계 3~N차 그물망·buy_gaps",
        "catalog_seed": "wonkisus_seven_split_grid_buy",
        "category": "workisus",
        "priority": 94,
        "body": (
            "하락장: 2차까지 진입 후 직전 차수 매수가 대비 buy_gaps 하락률(예 -5%씩) 충족 시 "
            "3·4·5…차 추가 매수로 격자 그물망. max_slot(기본 7)·enabled·쿨다운·장중 통과 후만. "
            "매매규칙 젬마: stock_settings buy_gaps·sell_pcts·target_weight를 [3003]과 대조. "
            "newly_registered 같은 루프 스킵은 2·3차 동시 폭주 방지."
        ),
    },
    {
        "title": "원키스US·ATR 수량(Qty)·목표금액",
        "catalog_seed": "wonkisus_seven_split_atr_qty",
        "category": "workisus",
        "priority": 93,
        "body": (
            "atr_auto=true: update_atr_settings_us()가 무손실 맞춤 ATR을 씀. "
            "buy_gaps: ATR20→_atr_to_gap + 국면(극단/고/저변동) + us_atr_gap_musonsil_mult(기본1.15)로 "
            "하락 격자 간격 확대(과밀 분할 억제). "
            "sell_pcts: [999]+[sell]×9, sell=clamp(ATR20×1.2, us_atr_sell_min 1.5%, cap 4%). "
            "수량: atr_qty_amt(예 $1000)÷현재가. sell_fee_buffer_pct_us 0.12%p. "
            "매매규칙·자동 젬마: ATR 갱신 후 [3003]·bot_settings_us 대조."
        ),
    },
    {
        "title": "원키스US·무손실 ATR 정책(정본)",
        "catalog_seed": "wonkisus_atr_musonsil_policy",
        "category": "workisus",
        "priority": 99,
        "body": (
            "원칙: 무손실—손실%에서 매도 금지·합산 평단≤0%면 개별 익절 보류. "
            "ATR 산출(update_atr_settings_us): "
            "① 1차 sell_pcts[0]=999%(앵커). "
            "② 2~10차 sell=ATR20×1.2, 최소 1.5%·최대 4%(us_atr_sell_min/cap). "
            "③ buy_gap=ATR20 기반 음수(-0.5~-5%), 국면별 배율 후 ×1.15(us_atr_gap_musonsil_mult). "
            "④ 익절 판정: 표시 수익>0 + sell_pcts+fee_buffer(0.12%p US). "
            "⑤ 추가매수: 최고차 플러스면 다음 차 스킵(_last_slot_profitable_for_add_buy). "
            "bot_settings_us 루트 키 없으면 auto_bot이 위 기본값 주입. "
            "리스크·매매규칙·오류젬마가 이 정책과 카드 #wonkisus_atr_musonsil_policy를 우선 참조."
        ),
    },
    {
        "title": "원키스US·3단계 역순 익절·슬롯별 매도",
        "catalog_seed": "wonkisus_seven_split_sell_ladder",
        "category": "workisus",
        "priority": 92,
        "body": (
            "반등 시: 가장 싼 차수(높은 slot_num)부터 sell_pcts 돌파 시 **해당 슬롯만** 독립 익절. "
            "리스크 젬마: 무손실—손실 구간 매도 없음. 익절% 충족이어도 합산≤0%면 스킵. "
            "no_slot_trading=true 모드는 차수 자동매수 OFF·sell_pcts 일괄 익절 또는 리밸런스로 전환—"
            "세븐 스플릿 자동 격자와 구분한다."
        ),
    },
    {
        "title": "원키스US·합산 평단 방어(최종 안전장치)",
        "catalog_seed": "wonkisus_seven_split_avg_defense",
        "category": "workisus",
        "priority": 91,
        "body": (
            "get_account_avg_profit(US, code, account_tag, cur): 해당 종목·계좌 **오픈 슬롯 합산 평단** 손익%. "
            "합산 ≤0%이면 개별 슬롯이 sell_pcts를 넘어도 매도 보류(로그: 익절% 충족해도 매도 스킵). "
            "합산 >0%일 때만 차수별 익절 평가—계좌 손실 누적 원천 차단. "
            "리스크·auto 젬마가 무손실·이 게이트를 함께 점검한다."
        ),
    },
    {
        "title": "원키스US·세븐 스플릿 vs 리밸런스 모드",
        "catalog_seed": "wonkisus_seven_split_vs_rebalance",
        "category": "workisus",
        "priority": 90,
        "body": (
            "세븐 스플릿(격자): no_slot_trading=false — 슬롯·buy_gaps·15초 2차·합산 방어. "
            "안전/대기 모드: no_slot_trading=true — 2·3차 자동 OFF, rebalance_enabled면 목표비중·"
            "이익만 축소(us_rebalance), OFF면 broker 합산 sell_pcts 일괄 익절. "
            "모드 젬마: enabled_us·no_slot·rebalance 스위치를 먼저 읽고 젬마·카드 해석을 맞춘다."
        ),
    },
    {
        "title": "원키스US·세븐 스플릿 젬마 학습 맵",
        "catalog_seed": "wonkisus_seven_split_agent_map",
        "category": "workisus",
        "priority": 89,
        "body": (
            "주문젬마: 1차 수동·3002·슬롯번호. 자동젬마: 15초 2차·3~N차 buy_gaps·enabled_us. "
            "매매규칙젬마: sell_pcts·buy_gaps·ATR·[3003]. 리스크젬마: 무손실·합산 평단 방어. "
            "정합젬마: market=US 슬롯·reconcile. 잔고젬마: USD·비중. "
            "오류젬마: 15초 미만·합산≤0 익절 스킵·ATR 미갱신 등 trade_err 카드 참조. "
            "큐레이터·동기: wonkisus_seven_split_* 시드 우선 sync."
        ),
    },
]
