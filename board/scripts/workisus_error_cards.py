"""원키스US — 카드 제작·검증·HTS·리밸런스·슬롯 오류 시나리오 카탈로그.

catalog_seed: workisus_err_* · workisus_trade_err_*
workisus_card_catalog.all_workisus_specs() 에 병합.
"""
from __future__ import annotations


def _meta(*, seed: str, kind: str, title_suffix: str, body: str, priority: int = 88) -> dict:
    return {
        "title": f"원키스US 오류 · {title_suffix}",
        "catalog_seed": seed,
        "category": "meta",
        "error_kind": kind,
        "priority": priority,
        "body": body,
    }


def _trade(*, seed: str, title: str, body: str, priority: int = 74) -> dict:
    return {
        "title": title,
        "catalog_seed": seed,
        "category": "ops_error",
        "priority": priority,
        "body": body,
    }


# --- 학습 카드 저장·검수 (agent_office_workisus_learn) ---
CARD_MAKING_ERROR_CARDS: list[dict] = [
    _meta(
        seed="workisus_err_too_short",
        kind="too_short",
        title_suffix="too_short — 본문 30자 미만",
        priority=96,
        body=(
            "오류 too_short: 본문 30자 미만이거나 no_slot·리밸런스·슬롯·US·KIS 설명이 빈약할 때. "
            "해결: 한 계좌·market=US·3001/3002·이익일 때만 매도·무손절을 각 1문장 이상. "
            "원키스US·workisus·차수·HTS 키워드를 포함한다."
        ),
    ),
    _meta(
        seed="workisus_err_pii",
        kind="pii",
        title_suffix="pii — 계좌·연락처",
        priority=95,
        body=(
            "오류 pii: 이메일·휴대폰·주민번호 형태·장문자 계좌번호가 본문에 있으면 [제거됨] 처리·거부. "
            "해결: 계좌는 끝 4자리만, KIS_APP_KEY·비밀번호·API키는 카드·Wiki에 넣지 않는다. "
            "US·슬롯·차수·리밸런스·무손절 운용 문장만 남긴다."
        ),
    ),
    _meta(
        seed="workisus_err_duplicate_title",
        kind="duplicate",
        title_suffix="duplicate — 제목 중복",
        priority=94,
        body=(
            "오류 duplicate: 동일 normalize_title 카드가 있으면 add_card 거부. "
            "해결: 기존 카드 revise·확정, 또는 제목에 · v2·시드 식별자. "
            "catalog_seed가 같으면 새 카드 대신 revise_card(권장)."
        ),
    ),
    _meta(
        seed="workisus_err_duplicate_seed",
        kind="duplicate",
        title_suffix="duplicate — catalog_seed",
        priority=93,
        body=(
            "catalog_seed 중복 시 ensure_seed_card·ingest는 본문만 갱신한다. "
            "workisus_err_*·wonkisus_* 시드를 유지하면 Wiki upsert가 안정적이다. "
            "별도 문서가 필요하면 _v2 시드 후 구형 삭제."
        ),
    ),
    _meta(
        seed="workisus_err_tag_missing_us",
        kind="tag_missing",
        title_suffix="tag_missing — US·원키스 없음",
        priority=92,
        body=(
            "오류 tag_missing: 본문에 US·원키스·workisus·해외·KIS·HTS 중 2개 미만. "
            "해결: stock.coupax.co.kr/workisus·한 계좌·해외 HTS를 명시. "
            "슬롯·차수·3001·3002·리밸런스·무손절 키워드를 함께 넣는다."
        ),
    ),
    _meta(
        seed="workisus_err_tag_missing_slot",
        kind="tag_missing",
        title_suffix="tag_missing — 슬롯·차수 없음",
        priority=91,
        body=(
            "오류 tag_missing: 슬롯·차수·market=US·3001·3002가 없으면 검수·태그 추출이 약하다. "
            "해결: 「/api/slots?market=US」「3002 차수=슬롯 번호」를 1문장 이상. "
            "원히어로 cascade·다계좌 문구는 원키스US 카드에 섞지 않는다."
        ),
    ),
    _meta(
        seed="workisus_err_tag_missing_risk",
        kind="tag_missing",
        title_suffix="tag_missing — 무손절·이익매도",
        priority=90,
        body=(
            "오류 tag_missing: 이익·무손절·리스크·플레이북 키워드 부족. "
            "해결: 손실 자동매도 없음·이익일 때만 매도·sell_pcts·us_rebalance 규칙을 적는다. "
            "hts_agents_us 리스크 젬마와 동일 정책을 유지한다."
        ),
    ),
    _meta(
        seed="workisus_err_confirm_failed",
        kind="confirm_failed",
        title_suffix="confirm_failed — 확정 실패",
        priority=89,
        body=(
            "오류 confirm_failed: confirm_card 시 PII·길이 재검증 실패. "
            "해결: API키·계좌번호 제거, US·슬롯·차수·리밸런스·무손절 보강 후 재확정. "
            "확정 후 workisus_knowledge_pack.json·Wiki(workisus-chasu) 반영."
        ),
    ),
    _meta(
        seed="workisus_err_office_paste",
        kind="tag_missing",
        title_suffix="office_paste — 수동 입력",
        priority=88,
        body=(
            "source=office_paste 시 본문에 US·슬롯·차수·KIS·무손절이 없으면 매매 플레이북 품질이 떨어진다. "
            "「카탈로그 시드」「갭 1장」으로 wonkisus·UI 카드를 먼저 채운 뒤 보완. "
            "계좌번호·토큰 원문은 붙여넣지 않는다."
        ),
    ),
    _meta(
        seed="workisus_err_compose_gap",
        kind="unknown",
        title_suffix="compose-gap — 갭 제작 실패",
        priority=87,
        body=(
            "compose_next_gap·ensure_seed_card 예외: catalog_seed 없음·제목 taken·본문 30자 미만. "
            "workisus_card_gap_detector로 missing 목록 확인. "
            "동기젬마 workisus_catalog_maintain 또는 seed_workisus_error_cards.py --add."
        ),
    ),
    _meta(
        seed="workisus_err_pack_stale",
        kind="unknown",
        title_suffix="pack_stale — 플레이북 미갱신",
        priority=86,
        body=(
            "증상: HTS·Cursor가 오래된 workisus_knowledge_pack.json을 참조. "
            "해결: 큐레이터 workisus_card_compose·pack_sync, 확정 카드 수 확인. "
            "GET trading-context.json 또는 export.json으로 최신 본문을 받는다."
        ),
    ),
    _meta(
        seed="workisus_err_wonhero_mix",
        kind="tag_missing",
        title_suffix="wonhero_mix — division 혼입",
        priority=85,
        body=(
            "오류: 원히어로·kiwoom-chasu·ATR·15초 2차·cascade만 있는 카드를 workisus-chasu에 넣음. "
            "해결: workisus_vs_wonhero_method 카드로 구분, US·no_slot·리밸런스·3002 수동 중심으로 다시 작성. "
            "pack·에이전트 division을 섞지 않는다."
        ),
    ),
    _meta(
        seed="workisus_err_meta_card_fail",
        kind="meta_card_fail",
        title_suffix="meta_card_fail — 오류 카드 시드 실패",
        priority=84,
        body=(
            "workisus_err_* 메타 카드 seed 실패 시 learning_errors에 기록. "
            "먼저 seed_workisus_error_cards.py --add 로 오류 카탈로그를 확정. "
            "이후 갭·에이전트 pulse가 담당 시드를 채운다."
        ),
    ),
]

# --- HTS·KIS US·리밸런스·슬롯 실운용 오류 (hts_agents_us · us_rebalance) ---
TRADE_RUNTIME_ERROR_CARDS: list[dict] = [
    _trade(
        seed="workisus_trade_err_token",
        title="매매오류 · KIS US 토큰·API",
        priority=88,
        body=(
            "증상: token 젬마 WARN — KIS_APP_KEY 없음·fetch_balance_us rt_cd≠0·US API 실패. "
            "해결: 토큰 갱신(허용된 자동 수정)·잔고 재조회 후 주문·리밸런스 보류. "
            "US·KIS·슬롯·차수·무손절·리밸런스 키워드로 로그 분류."
        ),
    ),
    _trade(
        seed="workisus_trade_err_balance_fail",
        title="매매오류 · 해외 잔고 미조회",
        priority=87,
        body=(
            "증상: balance 젬마 「잔고 미조회」·balance_fail·issues에 token: 포함. "
            "해결: 장중·네트워크·계좌 설정 확인, force 잔고 갱신 후 3001 in-place 패치. "
            "리밸런스 직전 KIS 해외 잔고 강제 재조회(us_rebalance)."
        ),
    ),
    _trade(
        seed="workisus_trade_err_settings_integrity",
        title="매매오류 · bot_settings_us 손상",
        priority=86,
        body=(
            "증상: run_us_trade_watch — settings_integrity_check 실패, token ERROR 「.bak 복구 권장」. "
            "해결: bot_settings_us.json·.bak 대조, [3003] 매매설정에서 재저장. "
            "손상 상태에서 자동 매매·리밸런스 금지."
        ),
    ),
    _trade(
        seed="workisus_trade_err_enabled_us_off",
        title="매매오류 · 해외봇 OFF",
        priority=85,
        body=(
            "증상: enabled_us=false·ready=false — watch issues·자동 젬마 OFF. "
            "해결: 대시보드 해외봇 ON, auto/manual·종목 enabled 확인. "
            "no_slot_trading=true여도 수동 [3002]는 가능하나 봇 매수는 게이트 통과 후만."
        ),
    ),
    _trade(
        seed="workisus_trade_err_rebalance_disabled",
        title="매매오류 · 리밸런스 OFF인데 목표비중 기대",
        priority=84,
        body=(
            "증상: rebalance_enabled=false — 리밸런스 젬마 「sell_pcts 일괄 익절 모드」. "
            "us_rebalance.run_us_rebalance_cycle 미실행. "
            "목표비중 운용 시 rebalance ON·enabled 종목·target_weight_pct 설정."
        ),
    ),
    _trade(
        seed="workisus_trade_err_rebalance_no_targets",
        title="매매오류 · 리밸런스 enabled 종목 0",
        priority=83,
        body=(
            "증상: rebalance ON인데 rebalance:enabled 종목 없음·rebalance_targets=0 WARN. "
            "해결: stock_settings에서 enabled=true, equal_stock_weights 또는 target_weight_pct>0. "
            "리밸런스 매도는 profit_pct>0(이익)일 때만."
        ),
    ),
    _trade(
        seed="workisus_trade_err_rebalance_loss_sell",
        title="매매오류 · 손실 종목 리밸런스 매도 기대",
        priority=82,
        body=(
            "증상: 손실 종목이 리밸런스로 팔리지 않음 — 정상(이익만 축소). "
            "오해: 무손절·손실 자동매도 없음 정책. "
            "손실 구간 시장가 매도는 HTS 수동이며 봇 자동 손절 경로 없음."
        ),
    ),
    _trade(
        seed="workisus_trade_err_no_slot_on",
        title="매매오류 · no_slot OFF 후 자동 차수 혼동",
        priority=81,
        body=(
            "증상: no_slot_trading=false면 US도 buy_gaps·cascade 유사 경로 가능 — 원히어로와 혼동. "
            "기본은 no_slot=true(차수 자동매수 OFF). "
            "원키스US 대표 운용: 슬롯 DB·3002 수동·차수 칸 표시."
        ),
    ),
    _trade(
        seed="workisus_trade_err_slot_market_kr",
        title="매매오류 · KR 슬롯이 US 탭에 표시",
        priority=80,
        body=(
            "증상: /api/slots가 market=KR 포함 → 0주·N슬롯 가짜 불일치(kis-us-slot-reconcile-fix). "
            "해결: GET /api/slots?market=US, reconcile_us는 US만, 캐시 KR↔US 혼입 금지. "
            "정합 젬마·reconcile은 매도 주문 없이 DB 보정만."
        ),
    ),
    _trade(
        seed="workisus_trade_err_reconcile_close",
        title="매매오류 · reconcile이 매도했다고 오해",
        priority=79,
        body=(
            "증상: reconcile·close_slot 후에도 증권 잔고와 슬롯 수량 불일치. "
            "원칙: reconcile_us는 KIS 해외 실잔고 vs market=US 슬롯 2단계 보정, 손실 매도 없음. "
            "HTS 수동 매도는 체결·3003·슬롯 번호로 추적."
        ),
    ),
    _trade(
        seed="workisus_trade_err_enabled_not_held",
        title="매매오류 · ON인데 미보유",
        priority=78,
        body=(
            "증상: stocks 젬마 「ON미보유 JOBY,…」 — enabled=true but qty=0. "
            "해결: [3002] 수동 매수·리밸런스 매수 대기·티커 조사 채팅. "
            "자동 봇은 게이트·장중·쿨다운 통과 후만."
        ),
    ),
    _trade(
        seed="workisus_trade_err_held_not_enabled",
        title="매매오류 · 보유인데 OFF",
        priority=77,
        body=(
            "증상: stocks WARN 「보유OFF」 — 잔고 있는데 enabled=false. "
            "해결: [3003]에서 종목 ON 또는 의도적 관망이면 리밸런스·봇 매수 제외 확인. "
            "익절 일괄(sell_pcts)은 enabled_us·종목 설정과 별도 게이트."
        ),
    ),
    _trade(
        seed="workisus_trade_err_profit_only_bulk",
        title="매매오류 · sell_pcts 일괄 익절 안 됨",
        priority=76,
        body=(
            "증상: no_slot·rebalance OFF — 합산 수익률이 sell_pcts[0]+buffer 미달로 익절 스킵. "
            "해결: broker 합산 수익률·sell_fee_buffer·_profit_only_sell_allowed 확인. "
            "손실만 보고 일괄 매도 기대는 정책 위반."
        ),
    ),
    _trade(
        seed="workisus_trade_err_order_gate",
        title="매매오류 · 봇 매수·수동 주문 게이트",
        priority=75,
        body=(
            "증상: [3002] 수동은 됐는데 봇 자동 매수 없음 — enabled_us·장중·쿨다운·enabled 종목. "
            "slot_num 지정 시 bot DB upsert 연동. "
            "주문 젬마·auto 젬마 로그와 bot.last_error 대조."
        ),
    ),
    _trade(
        seed="workisus_trade_err_bot_last_error",
        title="매매오류 · bot.last_error",
        priority=74,
        body=(
            "증상: watch issues에 bot:… — auto_bot US 경로 예외·주문 거절. "
            "해결: bot_log·대시보드 last_error, 잔고·토큰·종목 enabled 먼저. "
            "perm_fail 메시지는 1440분 쿨다운(us_rebalance)."
        ),
    ),
    _trade(
        seed="workisus_trade_err_rebalance_perm_fail",
        title="매매오류 · 리밸런스 perm_fail 쿨다운",
        priority=73,
        body=(
            "증상: us_rebalance 주문 실패 메시지가 perm_fail면 1440분(1일) 재시도 억제. "
            "일시 오류는 10분 쿨다운. "
            "티커 거래정지·최소주문·잔고 부족을 bot_log와 KIS msg1로 확인."
        ),
    ),
    _trade(
        seed="workisus_trade_err_manual_slot_num",
        title="매매오류 · 3002 차수(슬롯) 번호 불일치",
        priority=72,
        body=(
            "증상: 3002 「차수(자동)」= 슬롯 번호인데 DB·3001 차수 칸과 어긋남. "
            "해결: 주문 후 /api/slots?market=US 갱신, reconcile 점검. "
            "다계좌 cascade가 아닌 한 계좌 슬롯 메타임을 명시."
        ),
    ),
    _trade(
        seed="workisus_trade_err_ui_flicker",
        title="매매오류 · 잔고·슬롯 UI 깜빡임",
        priority=71,
        body=(
            "증상: 잔고 WS·폴링 시 3001 표 전체 re-render로 차수 칸 깜박임. "
            "해결: in-place 패치(_balPatchSlotCellInPlace·soft patch). "
            "운용 판단은 숫자만 바뀌고 레이아웃은 고정."
        ),
    ),
    _trade(
        seed="workisus_trade_err_quote_probe",
        title="매매오류 · 미국 시세·호가 조회 실패",
        priority=70,
        body=(
            "증상: _probe_us_quotes·Yahoo/KIS 시세 ERROR — 차트·현재가 0. "
            "해결: 티커·거래소(excd NASD)·장중 여부, 토큰 OK 후 재조회. "
            "시세 없이 시장가 주문 금지 권장."
        ),
    ),
    _trade(
        seed="workisus_trade_err_workspace_cache",
        title="매매오류 · KR/US 워크스페이스 캐시 혼입",
        priority=69,
        body=(
            "증상: 국내 탭 잔고가 US 탭에 보이거나 반대(workspace-panels 캐시). "
            "해결: 시장 다른 캐시 복원 금지, loadBalance 시장 필터. "
            "market=US 슬롯·대조만 US 탭에서 수행."
        ),
    ),
    _trade(
        seed="workisus_trade_err_safe_policy",
        title="매매오류 · safe_policy·자동 JSON 변경",
        priority=68,
        body=(
            "증상: bot_settings_us 자동 변경 기대 — 원키스US는 매매 JSON 자동 수정 없음(안전모드). "
            "허용: KIS US 토큰 갱신(실행 확인). "
            "sell_pcts·enabled는 [3003]·대시보드 수동만."
        ),
    ),
    _trade(
        seed="workisus_trade_err_watch_not_ready",
        title="매매오류 · watch ready=false",
        priority=67,
        body=(
            "증상: run_us_trade_watch ready=false — token·enabled_us·balance 중 하나 실패. "
            "issues 목록: token:…, balance_fail, rebalance:…, stocks:… "
            "주문·리밸런스 전 워치젬마 요약으로 보류."
        ),
    ),
    _trade(
        seed="workisus_trade_err_agent_board_flood",
        title="매매오류 · HTS 젬마 보드 폭주",
        priority=66,
        body=(
            "증상: watch_dedupe 미작동 시 동일 점검 메시지 반복. "
            "해결: _watch_dedupe_ok·realtime dedupe_key. "
            "Agent Office는 pulse·카드 제작으로 요약, HTS 보드는 점검만."
        ),
    ),
    _trade(
        seed="workisus_trade_err_division_pack",
        title="매매오류 · 잘못된 pack 참조",
        priority=65,
        body=(
            "증상: kiwoom_knowledge_pack·saju pack을 US HTS에 넣음 — 규칙 충돌. "
            "해결: workisus_knowledge_pack.json·trading-context.json만 사용. "
            "workisus_vs_wonhero_method 카드로 division 구분."
        ),
    ),
    _trade(
        seed="workisus_trade_err_rebalance_run_once",
        title="매매오류 · rebalance 1회 실행 실패",
        priority=64,
        body=(
            "증상: _run_us_rebalance_once ERROR rebalance_enabled=false. "
            "해결: bot_settings_us.json rebalance_enabled=true, no_slot_trading=true 유지. "
            "CLI·cron 전 enabled 종목·목표 현금 10% 확인."
        ),
    ),
    _trade(
        seed="workisus_trade_err_insufficient_cash",
        title="매매오류 · USD 예수금 부족",
        priority=63,
        body=(
            "증상: 리밸런스 매수·[3002] 매수 거절 — ord_psbl_frcr_amt 부족. "
            "해결: 3001 예수금·미수 D+2·총평가 확인, 목표 현금 target_cash_weight_pct. "
            "이익 매도 후 현금 확보는 sell_pcts·리밸런스 축소 경로."
        ),
    ),
    _trade(
        seed="workisus_trade_err_avg_defense_hold",
        title="매매오류 · 합산≤0 익절 보류",
        priority=88,
        body=(
            "증상: sell_pcts 충족인데 매도 안 됨 — get_account_avg_profit(US) 합산 ≤0% 정상 동작. "
            "로그: 「계좌 슬롯합산 손익 X%≤0 → 익절% 충족해도 매도 스킵」. "
            "해결: 3~N차로 평단 회복·합산 >0% 후 역순 익절. 무손절 원칙 유지."
        ),
    ),
    _trade(
        seed="workisus_trade_err_instant_2nd_15s",
        title="매매오류 · 2차 15초 미발동",
        priority=87,
        body=(
            "증상: 1차 register 후 2차 자동 매수 없음. "
            "원인: _slot1_secs_ago<15·no_slot_trading=true·enabled_us OFF·account_tag·스캘프·장외. "
            "해결: no_slot=false·15초 대기·bot_log instant_2nd_us 확인. 세븐 스플릿 1단계 카드 참조."
        ),
    ),
    _trade(
        seed="workisus_trade_err_slot1_999_anchor",
        title="매매오류 · 1차 999% 앵커 오해",
        priority=86,
        body=(
            "증상: 1차가 안 팔려서 고장—정상(999% 익절=앵커). 2차만 익절·재진입 사이클. "
            "1차를 수동 청산하면 max_slot·15초 2차 루프가 깨질 수 있음. "
            "의도적 청산 시 슬롯 DB·reconcile 점검."
        ),
    ),
    _trade(
        seed="workisus_trade_err_slot_open_count",
        title="매매오류 · 오픈 슬롯 과다",
        priority=62,
        body=(
            "증상: reconcile 「US DB 오픈슬롯 N건」 과다 — 미청산 슬롯 누적. "
            "해결: 체결 후 close_slot·3003 대조, 증권 0주인데 슬롯 open이면 reconcile. "
            "손실만 보고 close_slot 매도 기대 금지."
        ),
    ),
]


def all_error_specs() -> list[dict]:
    return [dict(s) for s in CARD_MAKING_ERROR_CARDS + TRADE_RUNTIME_ERROR_CARDS]


def error_kind_seeds() -> list[str]:
    return [s["catalog_seed"] for s in CARD_MAKING_ERROR_CARDS if s.get("catalog_seed")]
