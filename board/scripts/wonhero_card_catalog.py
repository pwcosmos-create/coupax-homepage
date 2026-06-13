"""원히어로(MagicSplit) 매매 규칙 — 학습 카드 단일 출처.

stock.coupax.co.kr/wonhero · kisstock auto_bot.py 기준.
투자 권유 아님 · 운용·봇 규칙 문서화.
"""
from __future__ import annotations

WONHERO_CORE_CARDS: list[dict] = [
    {
        "title": "원히어로 vs 원키스US·매매 방법 차이",
        "catalog_seed": "wonhero_vs_workisus_method",
        "category": "concept",
        "priority": 101,
        "body": (
            "「차수매매」라는 말만 같을 뿐, 원히어로(/wonhero)와 원키스US(/workisus)는 매매 방법이 다르다. "
            "혼동 금지 — Agent Office도 탭·카드·pack을 분리한다(원히어로 차수거래 / 원키스US차수).\n"
            "【원히어로】 MagicSplit 자동봇(auto_bot): 종목별 enabled·stock_settings. "
            "1차는 잔고 인식·register, 15초 후 2차 즉시매수 가능, 이후 buy_gaps(ATR) 충족 시 자동 추가매수. "
            "sell_pcts+버퍼로 슬롯별 자동 익절, 합산 이익 게이트, 손절 자동매도 없음. "
            "multi+cascade_accounts면 1번 손실 시 2·3번 계좌로 체인 이전.\n"
            "【원키스US】 수동 HTS: 해외 계좌 1개, /api/slots?market=US 슬롯 메모·잔고 차수 칸 표시. "
            "3002에서 사용자가 차수·시장가 매수/매도 — 봇이 gap·익절 주문을 대신 넣지 않음. "
            "다계좌 cascade·ATR 자동 gap·register 루프 없음. UI는 값만 갱신(in-place)하는 잔고·차수 탭."
        ),
    },
    {
        "title": "원히어로·MagicSplit 정의",
        "catalog_seed": "wonhero_def",
        "category": "concept",
        "priority": 100,
        "body": (
            "원히어로는 MagicSplit 자동 차수매매 대시보드(stock.coupax.co.kr/wonhero)이다. "
            "한 종목을 슬롯(차수)으로 나눠 매수하고 슬롯별로 익절한다. "
            "추가매수·익절 %는 ATR이 stock_settings의 buy_gaps·sell_pcts에 반영한다. "
            "원키스US(workisus) 수동 HTS 차수와 매매 방법이 다름 — workisus-chasu 학습부 참고. "
            "coupax 영웅문 수동 메모와도 별도이며, 본 카드는 원히어로 봇 규칙만 다룬다."
        ),
    },
    {
        "title": "1번 계좌 1차 — 수동 매수·잔고 인식",
        "catalog_seed": "wonhero_slot1_manual",
        "category": "entry",
        "priority": 99,
        "body": (
            "1번 계좌 1차는 HTS에서 수동 시장가·지정가 매수 후 봇이 잔고를 인식한다. "
            "auto_bot은 미등록 종목을 1차 슬롯으로 upsert하고 bot_log에 register(잔고 자동인식 1차)를 남긴다. "
            "같은 15초 루프에서는 newly_registered로 추가매수를 스킵한다. "
            "계좌번호·API키는 카드에 저장하지 않는다."
        ),
    },
    {
        "title": "1차→2차 — 등록 15초 후 즉시 매수",
        "catalog_seed": "wonhero_instant_2nd",
        "category": "entry",
        "priority": 98,
        "body": (
            "1번 계좌·1차만 있을 때 register 후 15초 이상이면 _kr_instant_2nd_eligible로 2차 매수를 시도한다. "
            "하락률(buy_gaps) 충족 없이도 2차 주문이 나갈 수 있다(장중·쿨다운·잔고 통과 시). "
            "멀티 cascade_idx·1번 손실임계(multi_trigger_loss)는 1→2 예외에서 무시된다. "
            "스캘프 모드·2번 이상 계좌(account_tag)에서는 이 규칙이 적용되지 않는다."
        ),
    },
    {
        "title": "3차 이후 추가매수 — ATR buy_gaps",
        "catalog_seed": "wonhero_buy_gaps",
        "category": "entry",
        "priority": 97,
        "body": (
            "2차 슬롯 생성 후 추가매수는 직전 차 매수가 대비 drop_pct가 buy_gaps[k] 이하일 때만 실행된다. "
            "buy_gaps는 atr_auto 종목에서 update_atr_settings가 ATR20·ATR5 국면으로 채운다(보통 -0.5%~-5%대). "
            "1번 계좌에서 합산 평단이 multi_trigger_loss 이하면 3차 이상 추가매수는 차단되고 cascade 계좌로 넘긴다. "
            "마지막 차가 이익 구간이면 추가매수를 스킵하는 분기도 있다."
        ),
    },
    {
        "title": "ATR 자동 설정 — 국내·해외",
        "catalog_seed": "wonhero_atr_schedule",
        "category": "atr",
        "priority": 96,
        "body": (
            "atr_auto=true 이고 enabled=true 인 종목만 ATR 갱신 대상이다. "
            "국내: KST 08:30~08:44 update_atr_settings — gap·sell_pcts·cascade_accounts 동기. "
            "해외: KST 22:30~22:44 update_atr_settings_us(enabled_us). "
            "대시보드 국내ATR·해외ATR 버튼으로 수동 실행 가능. "
            "ATR은 _atr_to_gap·_atr_to_sell·_calc_dynamic_gap으로 하락·익절 %를 산출한다."
        ),
    },
    {
        "title": "슬롯별 익절 — sell_pcts·수수료 버퍼",
        "catalog_seed": "wonhero_sell_pcts",
        "category": "exit",
        "priority": 95,
        "body": (
            "매도는 sell_pcts[slot]+sell_fee_buffer_pct 이상의 표시 수익률일 때만 시장가 익절한다. "
            "1번 메인 계좌는 sell_pcts[0]=999 패턴으로 1차 슬롯은 익절하지 않고 2차부터 실익절한다. "
            "cascade 2번+ 계좌는 1차부터 실익절%를 쓴다. "
            "손실·무보수 구간에서는 익절선을 넘어도 매도 주문을 넣지 않는다."
        ),
    },
    {
        "title": "합산 이익 게이트 — get_account_avg_profit",
        "catalog_seed": "wonhero_avg_profit_gate",
        "category": "exit",
        "priority": 94,
        "body": (
            "해당 종목·계좌의 오픈 슬롯 DB 합산 평단 손익률이 0% 이하이면, "
            "개별 차수가 sell_pcts를 충족해도 익절 매도를 하지 않는다(get_account_avg_profit). "
            "합산이 플러스일 때만 차수별 익절을 평가한다. "
            "reconcile의 close_slot은 DB 정합용이며 손실 매도 주문은 발생하지 않는다."
        ),
    },
    {
        "title": "손절 자동매도 없음 — 무조건 익절",
        "catalog_seed": "wonhero_no_stop_loss",
        "category": "risk",
        "priority": 93,
        "body": (
            "원히어로 봇에는 손실 구간 시장가 손절 경로가 없다. "
            "청산은 sell_pcts 익절과 수동 대시보드 조작만 허용되며, 익절 조건 충족 시 반드시 매도한다(무조건 익절). "
            "합산 이익 게이트·버퍼·장중을 통과한 뒤 미청산·주문 취소는 원칙 위반이다. "
            "최대 슬롯까지 매수 후에는 추가매수만 중단하고 보유를 유지한다. "
            "슬롯·1차·2차·익절·ATR·계좌·체결 키워드로 학습 카드와 맞춘다."
        ),
    },
    {
        "title": "멀티 계좌 cascade — 1번→2번 이전",
        "catalog_seed": "wonhero_cascade",
        "category": "account",
        "priority": 92,
        "body": (
            "multi=true 종목은 cascade_accounts로 2번 이후 계좌 체인을 둔다. "
            "1번 합산 손실이 trigger_loss·multi_trigger_loss 이하이면 1번 3차+ 추가매수를 막고 다음 계좌로 cascade한다. "
            "cascade_idx가 k이면 k 미만 계좌는 추가매수만 차단하고 익절·잔고 동기는 유지한다. "
            "ATR 실행 시 cascade 행의 buy_gaps·sell_pcts·qty를 메인과 맞춘다."
        ),
    },
    {
        "title": "봇 루프·장중·interval 15초",
        "catalog_seed": "wonhero_loop",
        "category": "ops",
        "priority": 88,
        "body": (
            "auto_bot 기본 interval은 15초이며 잔고·현재가·익절·추가매수를 반복한다. "
            "국내 매매·익절 주문은 is_kr_market_open(평일 08:00~15:40 KST)에서 실행된다. "
            "run_24h·always_monitor_24h로 장외 reconcile·감시가 가능하다. "
            "체결 후 trade_history.sqlite 슬롯·bot_log를 갱신하고 알림을 보낸다."
        ),
    },
    {
        "title": "당일 익절 종목 재등록 스킵",
        "catalog_seed": "wonhero_sold_today",
        "category": "ops",
        "priority": 86,
        "body": (
            "was_sold_today로 당일 익절 완료한 종목은 잔고에 다시 보여도 1차 자동 재등록을 스킵한다. "
            "RE_ENTRY_SLOT0 등 재진입 설정이 있으면 1차 슬롯 비운 뒤 별도 규칙으로 재진입한다. "
            "감정 매매·당일 복수 라운드를 줄이기 위한 운용 가드이다."
        ),
    },
    {
        "title": "잔고 reconcile·슬롯 검증",
        "catalog_seed": "wonhero_reconcile",
        "category": "ops",
        "priority": 85,
        "body": (
            "키움 실잔고와 DB 오픈 슬롯을 주기적으로 대조한다(kr_slot_verify 등). "
            "수량 불일치 시 self-heal로 슬롯 수량·닫기를 맞추되 손실 매도는 하지 않는다. "
            "sync_cascade_idx_from_holdings로 bot_multi_state와 체인 끝을 맞춘다. "
            "PL 노이즈·평단 차이는 경고만 표시할 수 있다."
        ),
    },
    {
        "title": "학습부 지식 구조 — 원히어로 전용",
        "catalog_seed": "wonhero_schema",
        "category": "meta",
        "priority": 80,
        "body": (
            "domain=kiwoom-chasu, wiki_id=wiki_kiwoom_{card_id}. "
            "태그: 원히어로, 슬롯, 1차, 2차, 3차, ATR, buy_gaps, sell_pcts, 익절, 분할, cascade, 계좌. "
            "확정 카드는 kiwoom_knowledge_pack.json·CURSOR_KIWOM_LEARN.md로 export. "
            "자동·RL·9젬마 협업 제작도 동일 검증(익절·ATR·차수 키워드)을 통과해야 한다."
        ),
    },
]

# 카탈로그 확장 — 갭 보충·RL·--add 시드용
WONHERO_EXT_CARDS: list[dict] = [
    {
        "title": "ATR 국면 보정 — gap 배율",
        "catalog_seed": "wonhero_atr_phase",
        "category": "atr",
        "priority": 91,
        "body": (
            "_calc_dynamic_gap은 ATR5·ATR20 비율로 국면을 나눈다. "
            "극단변동(ATR20>6%)은 gap 2배로 추가매수를 억제하고, "
            "고변동·저변동은 각각 1.5배·0.7배로 조정한다. "
            "보통 국면은 _atr_to_gap(ATR20) 결과를 그대로 buy_gaps 10칸에 복제한다."
        ),
    },
    {
        "title": "ATR 익절 산식 — _atr_to_sell·KR 튜닝",
        "catalog_seed": "wonhero_atr_sell_formula",
        "category": "atr",
        "priority": 90,
        "body": (
            "익절 기본값은 ATR20×1.2를 1.0~5.0%로 클램프한 _atr_to_sell이다. "
            "bot_settings의 kr_atr_sell_mult·kr_atr_sell_cap으로 국내 익절%를 추가 조정할 수 있다. "
            "메인 sell_pcts는 [999]+[sell]×9 패턴이며 cascade 2번+는 1차부터 실익절%를 쓴다. "
            "ATR 실행 후 _atr_sync_cascade_account_rows로 cascade 행과 맞춘다."
        ),
    },
    {
        "title": "종목 enabled·atr_auto 스위치",
        "catalog_seed": "wonhero_enabled_atr_auto",
        "category": "ops",
        "priority": 87,
        "body": (
            "stock_settings에서 enabled=false면 해당 종목은 봇이 매매하지 않는다. "
            "atr_auto=false면 ATR 루프가 buy_gaps·sell_pcts를 덮어쓰지 않고 저장값을 유지한다. "
            "신규 등록·잔고 스캘프 승격 시 atr_auto를 켜는 경로(atr_balance_scalp)가 있다. "
            "대시보드 저장 후 reloadBotSettingsFromServer로 봇이 JSON을 다시 읽는다."
        ),
    },
    {
        "title": "최대 슬롯 max_slot·수량 buy_qtys",
        "catalog_seed": "wonhero_max_slot",
        "category": "entry",
        "priority": 86,
        "body": (
            "종목별 max_slot(기본 7)에 도달하면 추가매수를 중단한다. "
            "buy_qtys·buy_amts·buy_mode(qty/amt)로 차수별 수량·금액을 정한다. "
            "realtime_amt_opt가 켜지면 예수금 기반 하이브리드 수량(rt_amt)으로 3차 이상을 살 수 있다. "
            "슬롯 DB에는 차수·수량·매입가가 기록된다."
        ),
    },
    {
        "title": "KR 스캘프 모드 — instant 2차 제외",
        "catalog_seed": "wonhero_kr_scalp",
        "category": "entry",
        "priority": 85,
        "body": (
            "_is_kr_scalp_enabled 종목은 buy_gaps·sell_pcts·max_slot이 스캘프 프리셋으로 대체된다. "
            "스캘프 모드에서는 _kr_instant_2nd_eligible이 false라 15초 2차 예외가 적용되지 않는다. "
            "스캘프는 짧은 gap·낮은 익절%로 회전을 가정한다. "
            "일반 멀티 차수매매와 혼동하지 않도록 종목 설정을 확인한다."
        ),
    },
    {
        "title": "멀티 계좌 순차 매매 — staggered",
        "catalog_seed": "wonhero_staggered",
        "category": "account",
        "priority": 84,
        "body": (
            "_check_kr_staggered는 1번 계좌 처리 후 kr_multi_account_gap_sec 간격을 두고 "
            "2번+ 계좌를 _check_kr_multi_sub_accounts로 순차 처리한다. "
            "API 일괄 폭주·잔고 조회 충돌을 막기 위한 운용이다. "
            "cascade 계좌는 block_add_buy로 추가매수만 막고 익절은 계속 평가할 수 있다."
        ),
    },
    {
        "title": "cascade trigger_loss — 숫자·항상(null)",
        "catalog_seed": "wonhero_trigger_loss",
        "category": "account",
        "priority": 83,
        "body": (
            "cascade_accounts 각 행의 trigger_loss가 숫자이면 앞 계좌 손실% 임계로 다음 계좌를 연다. "
            "trigger_loss:null은 항상 발동으로 두며 ATR 동기 시 값을 바꾸지 않는다. "
            "multi_trigger_loss는 1번 계좌 손실 임계·ATR gap과 맞춰 갱신될 수 있다. "
            "bulk_set_multi_trigger_loss로 숫자 행만 일괄 수정한다."
        ),
    },
    {
        "title": "매수·매도 쿨다운·API 재시도",
        "catalog_seed": "wonhero_cooldown",
        "category": "ops",
        "priority": 82,
        "body": (
            "주문 실패·횟수 초과·장마감·네트워크 오류 시 종목·계좌별 buy/sell 쿨다운을 둔다. "
            "API-LIMIT 감지 시 수 초 대기 후 1분 쿨다운이 적용될 수 있다. "
            "영구차단 키워드(_is_perm_fail)는 blocked_stocks에 등록해 반복 주문을 막는다. "
            "익절·추가매수 판단 전 잔고·호가를 재조회한다."
        ),
    },
    {
        "title": "익절 수수료 버퍼 — ETF·국내·해외",
        "catalog_seed": "wonhero_fee_buffer",
        "category": "exit",
        "priority": 81,
        "body": (
            "sell_fee_buffer_pct는 순익이 sell_pcts에 닿도록 익절 조건에 가산한다. "
            "국내 주식·ETF·미국·코인별 기본 버퍼가 다르며 종목·지역 JSON으로 덮어쓸 수 있다. "
            "profit_pct가 버퍼 포함 목표 이상이고 _profit_only_sell_allowed(>0)일 때만 매도한다. "
            "ETF는 거래세 부담이 달라 kr_etf 버퍼가 낮을 수 있다."
        ),
    },
    {
        "title": "잔고 스캘프 후보 — ATR-BAL",
        "catalog_seed": "wonhero_atr_balance_scalp",
        "category": "atr",
        "priority": 80,
        "body": (
            "atr_balance_scalp=true(기본)이면 ATR 실행 시 키움 잔고에서 스캘프 적합 종목을 찾아 "
            "stock_settings에 자동 추가하거나 atr_auto만 켠다. "
            "ATR20이 너무 낮거나 높은 종목은 후보에서 제외한다. "
            "청산 정책은 변하지 않으며 익절 sell_pcts 경로만 사용한다."
        ),
    },
    {
        "title": "장중 시간 — 국내 08:00~15:40",
        "catalog_seed": "wonhero_kr_session",
        "category": "ops",
        "priority": 79,
        "body": (
            "is_kr_market_open은 평일 08:00~15:40 KST(공휴일 제외)이다. "
            "정규장 09:00~15:30이지만 준비·마감 버퍼로 앞뒤가 넓다. "
            "장외에는 추가매수·익절 주문을 스킵하고 로그만 남길 수 있다. "
            "run_24h면 장외에도 루프·reconcile이 돌 수 있다."
        ),
    },
    {
        "title": "해외 US — KIS·차수 비활성 옵션",
        "catalog_seed": "wonhero_us_kis",
        "category": "ops",
        "priority": 78,
        "body": (
            "미국은 KIS API로 운용하며 update_atr_settings_us로 buy_gaps·sell_pcts를 맞춘다. "
            "us_disable_chasu 등으로 해외 차수·cascade를 끄고 보유분 일괄 익절만 쓸 수 있다. "
            "장중은 뉴욕 시간 09:00~16:20 ET 기준이다. "
            "국내 키움 멀티와 설정 JSON이 분리(bot_settings_us)되어 있다."
        ),
    },
    {
        "title": "self-heal — 수량·수동 전량매도",
        "catalog_seed": "wonhero_self_heal",
        "category": "ops",
        "priority": 77,
        "body": (
            "매도 실패 시 잔고 재조회로 슬롯 수량을 실제와 맞추거나 슬롯을 닫는다. "
            "증권 잔고 0이면 수동 전량매도로 인식해 close_slot한다. "
            "이 과정에서 손실 시장가 청산 경로는 추가하지 않는다. "
            "kr_slot_verify는 슬롯·증권 수량·매입 차이를 주기 경고한다."
        ),
    },
    {
        "title": "RE_ENTRY·1차 슬롯 재진입",
        "catalog_seed": "wonhero_re_entry",
        "category": "entry",
        "priority": 76,
        "body": (
            "RE_ENTRY_SLOT0이 true이면 1차 익절 후 빈 슬롯에 재진입 규칙을 허용할 수 있다. "
            "was_sold_today와 함께 당일 복수 라운드를 제한한다. "
            "재진입 시에도 1차 수동·15초 2차·ATR 3차+ 흐름을 따른다. "
            "bot_log register 시각이 instant_2nd 15초 판단의 기준이 된다."
        ),
    },
    {
        "title": "대시보드 ATR 버튼·설정 저장",
        "catalog_seed": "wonhero_dashboard_atr",
        "category": "ops",
        "priority": 75,
        "body": (
            "POST /api/update_atr 로 국내·해외 ATR을 수동 실행한다. "
            "saveAutoSettings는 cascade 행의 buy_gaps·sell_pcts를 보존할 수 있다. "
            "ATR 성공 후 reloadBotSettingsFromServer로 localStorage·cascade 표를 갱신한다. "
            "종목별 atr_qty_amt·buy_mode는 대시보드와 bot_settings.json에 함께 저장된다."
        ),
    },
    {
        "title": "알림·로그 — bot_log·텔레그램",
        "catalog_seed": "wonhero_notify",
        "category": "ops",
        "priority": 74,
        "body": (
            "매수·매도·register·error는 bot_log에 남기고 trade_history.sqlite 슬롯과 연동한다. "
            "텔레그램·카카오 알림으로 체결·오류를 통지할 수 있다. "
            "1차→2차 즉시매수는 reason에 경과 초가 포함된다. "
            "학습 카드에는 주문번호 전체·계좌번호 전체를 넣지 않는다."
        ),
    },
]

WONHERO_META_CARDS: list[dict] = [
    {
        "title": "카드제작 가이드 · 본문·형식",
        "catalog_seed": "meta_body",
        "category": "meta",
        "priority": 95,
        "body": (
            "카드 본문은 최소 30자 이상, 1·2·3차·슬롯·익절·ATR·계좌 중 최소 2개 키워드를 포함. "
            "계좌번호 전체·비밀번호·API키·전화번호는 저장하지 않는다(자동 [제거됨]). "
            "제목은 원히어로 규칙을 한 줄로(예: 「ATR buy_gaps 갱신」). "
            "오류 시 learning_errors playbook을 참고해 수정 후 재저장."
        ),
    },
    {
        "title": "카드제작 가이드 · pii",
        "catalog_seed": "meta_pii",
        "category": "meta",
        "priority": 94,
        "body": (
            "PII 패턴(장문자 번호·전화·API키)이 탐지되면 카드 저장이 거부되거나 마스킹된다. "
            "태그에 슬롯·익절·ATR·계좌·체결 중 누락이 있으면 검수 힌트가 뜬다. "
            "동일 제목·catalog_seed 카드는 중복 추가하지 않는다."
        ),
    },
    {
        "title": "자동 카드 제작 실패 복구",
        "catalog_seed": "meta_recover",
        "category": "meta",
        "priority": 93,
        "body": (
            "RL·자동 풀 제작 실패 시: ① 오류 종류(too_short, pii, duplicate, tag_missing) 확인 "
            "② playbook 수정안 적용 ③ seed_kiwoom_wonhero_rules.py --reset 또는 수동 재저장. "
            "원히어로 규칙 카탈로그(wonhero_card_catalog)를 우선 참고한다."
        ),
    },
    {
        "title": "카드제작 가이드 · too_short",
        "catalog_seed": "meta_too_short",
        "category": "meta",
        "priority": 92,
        "body": (
            "오류 too_short: 본문 30자 미만 또는 슬롯·익절·ATR 설명이 빈약할 때 발생. "
            "해결: 1차 수동·15초 2차·ATR buy_gaps·sell_pcts 익절을 각 1문장 이상 추가. "
            "예) 「1차 HTS 수동 / 15초 후 2차 / 3차는 ATR gap -2% / 2차 익절 +2%」."
        ),
    },
    {
        "title": "카드제작 가이드 · duplicate",
        "catalog_seed": "meta_duplicate",
        "category": "meta",
        "priority": 91,
        "body": (
            "오류 duplicate: 동일 제목 또는 catalog_seed가 이미 있을 때 추가가 거부된다. "
            "해결: 기존 카드 본문 수정·확정 또는 제목에 규칙 식별자를 붙여 구분한다. "
            "갭 보충·RL은 중복을 스킵하고 learning_errors에 기록한다."
        ),
    },
    {
        "title": "카드제작 가이드 · tag_missing",
        "catalog_seed": "meta_tag",
        "category": "meta",
        "priority": 90,
        "body": (
            "오류 tag_missing: 본문에 차수·슬롯·익절·ATR·계좌·체결 키워드가 부족할 때 검수 실패. "
            "해결: 「1차」「2차」「슬롯」「익절」「ATR」「계좌」 중 최소 3개를 명시한다. "
            "구 coupax 수동 HTS 카드 문구는 사용하지 않는다."
        ),
    },
    {
        "title": "카드제작 가이드 · confirm_failed",
        "catalog_seed": "meta_confirm",
        "category": "meta",
        "priority": 89,
        "body": (
            "오류 confirm_failed: 확정 단계 PII·태그·길이 재검증 실패 시 카드가 삭제된다. "
            "해결: PII 제거, 원히어로·슬롯·익절·ATR 키워드 보강, 30자 이상 재저장. "
            "9젬마 협업 제작 후에도 동일 검증을 통과해야 Wiki·pack에 반영된다."
        ),
    },
]

# 카드 제작·검증·RL·매매 오류 시나리오 (wonhero_error_cards.py)
from wonhero_error_cards import all_error_specs as _all_error_specs  # noqa: E402
from wonhero_principle_cards import all_principle_specs as _all_principle_specs  # noqa: E402


def all_wonhero_specs() -> list[dict]:
    out: list[dict] = []
    for s in (
        WONHERO_CORE_CARDS
        + _all_principle_specs()
        + WONHERO_EXT_CARDS
        + WONHERO_META_CARDS
        + _all_error_specs()
    ):
        row = dict(s)
        row.setdefault("category", "wonhero")
        row.setdefault("priority", 70)
        out.append(row)
    return out
