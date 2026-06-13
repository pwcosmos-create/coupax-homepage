"""원히어로 차수거래 — 카드 제작·검증·확정·RL·매매 오류 시나리오 카탈로그.

wonhero_card_catalog.all_wonhero_specs() 에 병합.
catalog_seed=meta_err_* · meta_trade_err_* — 중복 추가 방지용.
"""
from __future__ import annotations


def _meta(
    *,
    seed: str,
    kind: str,
    title_suffix: str,
    body: str,
    priority: int = 88,
) -> dict:
    return {
        "title": f"카드제작 가이드 · {title_suffix}",
        "catalog_seed": seed,
        "category": "meta",
        "error_kind": kind,
        "priority": priority,
        "body": body,
    }


def _trade_err(
    *,
    seed: str,
    title: str,
    body: str,
    priority: int = 72,
) -> dict:
    return {
        "title": title,
        "catalog_seed": seed,
        "category": "ops_error",
        "priority": priority,
        "body": body,
    }


# --- 카드 저장·검증·확정 (kiwoom_card_validate · learn · council) ---
CARD_MAKING_ERROR_CARDS: list[dict] = [
    _meta(
        seed="meta_err_too_short",
        kind="too_short",
        title_suffix="too_short — 본문 30자 미만",
        priority=96,
        body=(
            "오류 too_short: 본문이 30자 미만이거나 1·2·3차·슬롯·익절·ATR 설명이 빈약할 때 발생한다. "
            "해결: 1차 HTS 수동 인식, 15초 후 2차, 3차 ATR buy_gaps, sell_pcts 익절을 각 1문장 이상 쓴다. "
            "원히어로 auto_bot·슬롯·계좌 키워드를 반드시 포함한다."
        ),
    ),
    _meta(
        seed="meta_err_too_short_title",
        kind="too_short",
        title_suffix="too_short — 제목·본문 공백",
        priority=95,
        body=(
            "오류 too_short/unknown: 제목이 비었거나 add_card ValueError가 난 경우다. "
            "제목에 규칙 한 줄(예: ATR buy_gaps 갱신)을 넣고 본문 30자 이상·슬롯·익절·ATR을 채운다. "
            "1차·2차·계좌·체결 키워드로 검수를 통과시킨다."
        ),
    ),
    _meta(
        seed="meta_err_pii",
        kind="pii",
        title_suffix="pii — 장문자 번호",
        priority=94,
        body=(
            "오류 pii: 본문에 10자리 이상 연속 숫자(계좌·주민번호 형태)가 있으면 거부된다. "
            "해결: 계좌는 끝 4자리만, API키·비밀번호·전화번호는 [제거됨] 처리 후 재저장. "
            "원히어로·슬롯·1차·2차·익절·ATR·체결·계좌 키워드는 유지한다."
        ),
    ),
    _meta(
        seed="meta_err_pii_secret",
        kind="pii",
        title_suffix="pii — API키·비밀번호",
        priority=93,
        body=(
            "오류 pii: api_key·API키·비밀번호 문자열이 본문에 있으면 저장이 차단된다. "
            "대시보드·봇 설정은 서버 env에만 두고 카드에는 넣지 않는다. "
            "1차 수동·15초 2차·슬롯·익절·ATR·계좌 운용 문장만 남긴다."
        ),
    ),
    _meta(
        seed="meta_err_tag_missing_chasu",
        kind="tag_missing",
        title_suffix="tag_missing — 차수·슬롯 없음",
        priority=92,
        body=(
            "오류 tag_missing: 본문에 차수·슬롯·1차·2차·3차 중 하나가 없으면 검수 실패다. "
            "해결: 「1차 HTS 수동」「2차 15초」「3차 buy_gaps」처럼 슬롯 단계를 명시한다. "
            "익절·ATR·계좌·체결·원히어로 키워드와 함께 저장한다."
        ),
    ),
    _meta(
        seed="meta_err_tag_missing_risk",
        kind="tag_missing",
        title_suffix="tag_missing — 익절·ATR 없음",
        priority=91,
        body=(
            "오류 tag_missing: 익절·분할·ATR 중 하나가 본문·태그에 없으면 실패한다. "
            "해결: sell_pcts 익절, ATR buy_gaps, 분할 매도 버퍼를 1문장 이상 적는다. "
            "1차·2차·슬롯·계좌·체결과 함께 원히어로 규칙 카드로 확정한다."
        ),
    ),
    _meta(
        seed="meta_err_tag_missing_both",
        kind="tag_missing",
        title_suffix="tag_missing — 차수·리스크 둘 다 부족",
        priority=90,
        body=(
            "오류 tag_missing: 차수·슬롯 키워드와 익절·ATR 키워드가 모두 부족할 때다. "
            "최소 3개: 1차·2차·슬롯·익절·ATR·계좌·체결·원히어로. "
            "구 coupax 수동 HTS 문구는 쓰지 않고 MagicSplit·auto_bot 기준만 쓴다."
        ),
    ),
    _meta(
        seed="meta_err_duplicate_title",
        kind="duplicate",
        title_suffix="duplicate — 제목 중복",
        priority=89,
        body=(
            "오류 duplicate: normalize_title 기준 동일 제목 카드가 이미 있으면 add_card가 거부된다. "
            "해결: 기존 카드 본문 수정·확정, 또는 제목에 · v2·규칙 식별자를 붙인다. "
            "RL·자동 풀은 중복을 스킵하고 learning_errors에 기록한다."
        ),
    ),
    _meta(
        seed="meta_err_duplicate_seed",
        kind="duplicate",
        title_suffix="duplicate — catalog_seed 중복",
        priority=88,
        body=(
            "catalog_seed가 이미 있으면 add_card·ingest는 새 카드 대신 revise_card로 본문을 갱신한다(권장). "
            "수동 합치기: 구현+신규 내용을 붙여 넣을 때 catalog_seed를 유지하면 wiki_kiwoom_{동일id}만 upsert. "
            "정말 별도 문서면 새 seed(예: _v2) 후 구형 삭제. dedupe_kiwoom_cards_by_seed.py --apply."
        ),
    ),
    _meta(
        seed="meta_err_confirm_failed",
        kind="confirm_failed",
        title_suffix="confirm_failed — 확정 실패",
        priority=87,
        body=(
            "오류 confirm_failed: confirm_card 재검증(PII·태그·길이) 실패 시 카드가 삭제된다. "
            "해결: PII 제거, 슬롯·1차·2차·익절·ATR·계좌 키워드 보강 후 재저장. "
            "9젬마 협업(council) 후에도 동일 검증을 통과해야 Wiki·pack에 반영된다."
        ),
    ),
    _meta(
        seed="meta_err_confirm_council",
        kind="confirm_failed",
        title_suffix="confirm_failed — 협업 제작 실패",
        priority=86,
        body=(
            "오류 confirm_failed: council_enabled 시 create_card_via_council이 card_id 없이 끝날 때다. "
            "Gemini·에이전트 타임아웃·본문 검증 실패를 점검한다. "
            "수동으로 본문을 넣고 1차·2차·슬롯·익절·ATR·계좌 키워드를 채운 뒤 재시도한다."
        ),
    ),
    _meta(
        seed="meta_err_unknown",
        kind="unknown",
        title_suffix="unknown — 형식·검수",
        priority=85,
        body=(
            "오류 unknown: 제목 누락·카드 dict 손상·예외 분류 불가 시 기록된다. "
            "형식·길이·PII·태그를 kiwoom_card_validate로 먼저 점검한다. "
            "원히어로·슬롯·익절·ATR·1차·2차·계좌·체결을 본문에 넣고 재저장한다."
        ),
    ),
    _meta(
        seed="meta_err_meta_card_fail",
        kind="meta_card_fail",
        title_suffix="meta_card_fail — 오류 메타 카드 생성 실패",
        priority=84,
        body=(
            "오류 meta_card_fail: ensure_error_learning_cards·error_learn 경로에서 예외가 난 경우다. "
            "catalog_seed 중복·제목 taken·council 실패를 확인한다. "
            "meta_err_* 시드 카드를 카탈로그에서 --add로 먼저 확정해 둔다."
        ),
    ),
    _meta(
        seed="meta_err_rl_autofill",
        kind="unknown",
        title_suffix="RL autofill — 제작·확정 루프",
        priority=83,
        body=(
            "kiwoom_card_rl_autofill: 갭·오류 통계 기반 자동 제작. duplicate·confirm_failed·too_short 시 learning_errors 기록. "
            "cron --max-add 로 건수 제한. 원히어로 카탈로그·meta_err_* 를 우선 채운 뒤 RL을 돌린다. "
            "1차·2차·슬롯·익절·ATR·계좌·체결 키워드 없는 초안은 tag_missing으로 거절된다."
        ),
    ),
    _meta(
        seed="meta_err_gap_detector",
        kind="unknown",
        title_suffix="갭 탐지 — __error_learn__ · __tag__",
        priority=82,
        body=(
            "kiwoom_card_gap_detector: 카탈로그 누락·태그 버킷 부족·오류 kind≥2회 시 missing 큐에 넣는다. "
            "__error_learn__:kind 는 meta_err 카드 또는 RL _error_spec으로 채운다. "
            "슬롯·ATR·익절·1차·2차·cascade·계좌 태그 최소 개수를 confirmed 카드로 맞춘다."
        ),
    ),
    _meta(
        seed="meta_err_title_compose",
        kind="duplicate",
        title_suffix="제목 자동 · v2 접미",
        priority=81,
        body=(
            "kiwoom_card_title_compose.ensure_unique_title: 제목 중복 시 「· v2」~「· v29」 또는 날짜 접미를 붙인다. "
            "catalog_seed는 원문을 보존하고 제목만 유일화할 수 있다. "
            "동일 seed 중복 카드는 만들지 말고 본문만 수정한다. 1차·2차·슬롯·익절·ATR·계좌."
        ),
    ),
    _meta(
        seed="meta_err_office_paste",
        kind="tag_missing",
        title_suffix="사무실 붙여넣기 — 검수",
        priority=80,
        body=(
            "source=office_paste·paste 시 council 기본 ON. 본문에 원히어로·슬롯·1차·2차·익절·ATR·계좌가 없으면 tag_missing. "
            "PII·too_short·duplicate는 저장 전에 걸러진다. "
            "확정 후 sync_kiwoom_wiki로 gemma_knowledge(공개)에 반영된다."
        ),
    ),
]

# --- 원히어로 실매매·봇 동작 오류 (운용 카드 — 검수 키워드 포함) ---
TRADE_RUNTIME_ERROR_CARDS: list[dict] = [
    _trade_err(
        seed="meta_trade_err_instant_2nd_15s",
        title="매매오류 · 2차 — 등록 15초 미만",
        body=(
            "증상: register 직후 15초 미만이면 _kr_instant_2nd_eligible가 false, 2차 주문 없음. "
            "bot_log reason에 경과 초가 찍힌다. 1차 슬롯·max_slot=1·계좌 1번을 확인한다. "
            "해결: 15초 대기 후 루프 재시도. 익절·ATR·슬롯·체결 로그로 시각을 맞춘다."
        ),
    ),
    _trade_err(
        seed="meta_trade_err_instant_2nd_scalp",
        title="매매오류 · 2차 — 스캘프 모드 차단",
        body=(
            "증상: 스캘프 모드 종목은 1→2 즉시매수 규칙이 적용되지 않는다. "
            "1차·2차·슬롯 설정과 auto_bot 플래그를 대시보드에서 확인한다. "
            "일반 차수매매는 ATR buy_gaps·sell_pcts 익절·계좌 태그로 구분한다."
        ),
    ),
    _trade_err(
        seed="meta_trade_err_instant_2nd_account",
        title="매매오류 · 2차 — account_tag·다계좌",
        body=(
            "증상: account_tag가 있거나 2번 이상 계좌면 instant 2nd 예외가 꺼진다. "
            "1번 계좌·1차 수동·15초 2차 전제를 깨면 2차가 안 나간다. "
            "cascade·멀티 계좌 이체 시 슬롯·익절·ATR·체결·계좌 로그를 대조한다."
        ),
    ),
    _trade_err(
        seed="meta_trade_err_newly_registered",
        title="매매오류 · 같은 루프 1차 직후 추가매수 스킵",
        body=(
            "증상: newly_registered 플래그로 같은 15초 루프에서 2차·3차 매수를 스킵한다. "
            "다음 루프에서 15초·buy_gaps 조건을 본다. 1차 register·슬롯·계좌 인식을 확인. "
            "bot_log·익절·ATR·체결 타임스탬프로 순서를 검증한다."
        ),
    ),
    _trade_err(
        seed="meta_trade_err_buy_gaps",
        title="매매오류 · 3차+ buy_gaps 미충족",
        body=(
            "증상: 3차 이후는 ATR buy_gaps 하락률 미달 시 추가매수가 나가지 않는다. "
            "stock_settings·update_atr_schedule(국내 08:30~08:44) 후 gap 값을 확인. "
            "1차·2차·슬롯·익절·sell_pcts·계좌·체결 로그와 대시보드 cascade 표를 맞춘다."
        ),
    ),
    _trade_err(
        seed="meta_trade_err_sell_pcts",
        title="매매오류 · 익절 sell_pcts·버퍼",
        body=(
            "증상: 슬롯별 sell_pcts·버퍼·합산 이익 게이트 미달 시 익절 주문이 지연·스킵된다. "
            "1차 999% 패턴·분할 익절 규칙을 카드와 bot_settings에서 대조. "
            "손절 자동매도 경로는 없다 — 리스크는 익절·슬롯·계좌·ATR로 관리."
        ),
    ),
    _trade_err(
        seed="meta_trade_err_no_stop",
        title="매매오류 · 손절 자동매도 없음",
        body=(
            "증상: 손실 구간 시장가 손절 경로가 원히어로 봇에 없다 — 기대와 다르면 설정 오해다. "
            "익절 sell_pcts·합산 이익·1차·2차·슬롯·ATR·계좌 규칙으로 운용. "
            "HTS 수동 손절은 1차 인식 전후 reconcile·체결 로그로 맞춘다."
        ),
    ),
    _trade_err(
        seed="meta_trade_err_reconcile",
        title="매매오류 · reconcile·잔고 불일치",
        body=(
            "증상: HTS 잔고와 bot 슬롯 수량 불일치 시 register·추가매수가 꼬인다. "
            "reconcile·self-heal·당일 was_sold_today를 점검. 1차·2차·슬롯·익절·ATR·계좌·체결. "
            "학습 카드에 주문번호 전체·계좌번호 전체를 넣지 않는다."
        ),
    ),
    _trade_err(
        seed="meta_trade_err_balance",
        title="매매오류 · 잔고·주문 거절",
        body=(
            "증상: 잔고 부족·최소주문·거래정지 시 매수·익절이 실패하고 bot_log error가 남는다. "
            "1번 계좌 1차 수동 후 슬롯 인식·2차 15초·3차 buy_gaps 순서를 확인. "
            "텔레그램·알림·체결·계좌·익절·ATR 키워드로 원인을 분류한다."
        ),
    ),
    _trade_err(
        seed="meta_trade_err_market_hours",
        title="매매오류 · 장중·쿨다운",
        body=(
            "증상: 장 마감·쿨다운·enabled=false면 주문이 나가지 않는다. "
            "장중 스케줄·당일 복수 라운드·RE_ENTRY_SLOT0과 함께 1차·2차·슬롯을 본다. "
            "익절·ATR·계좌·체결·auto_bot 설정을 대시보드에서 확인."
        ),
    ),
    _trade_err(
        seed="meta_trade_err_cascade",
        title="매매오류 · cascade·multi_trigger",
        body=(
            "증상: cascade_idx·multi_trigger_loss는 1→2 instant 예외에서 무시되지만 "
            "3차+·다계좌 이체에서는 슬롯 행이 어긋날 수 있다. "
            "saveAutoSettings·cascade buy_gaps·sell_pcts·1차·2차·익절·ATR·계좌를 맞춘다."
        ),
    ),
    _trade_err(
        seed="meta_trade_err_atr_window",
        title="매매오류 · ATR 갱신 창",
        body=(
            "증상: 국내 ATR update_atr_settings 창(08:30~08:44) 밖 수동 갱신 시 gap이 어제 값일 수 있다. "
            "POST /api/update_atr 후 reloadBotSettingsFromServer. "
            "1차·2차·3차 슬롯·buy_gaps·sell_pcts 익절·계좌·체결·원히어로 로그를 확인."
        ),
    ),
    _trade_err(
        seed="meta_trade_err_was_sold_today",
        title="매매오류 · was_sold_today·재진입",
        body=(
            "증상: 당일 매도 이력 was_sold_today·RE_ENTRY_SLOT0 조합에 따라 재진입이 막힌다. "
            "1차 익절 후 빈 슬롯 재진입도 15초·슬롯·익절·ATR 규칙을 따른다. "
            "register 시각·bot_log·계좌·체결로 당일 라운드를 추적한다."
        ),
    ),
]


def all_error_specs() -> list[dict]:
    return [dict(s) for s in CARD_MAKING_ERROR_CARDS + TRADE_RUNTIME_ERROR_CARDS]


def error_kind_seeds() -> list[str]:
    """gap_detector·RL용 고정 오류 kind → catalog_seed."""
    return [s["catalog_seed"] for s in CARD_MAKING_ERROR_CARDS if s.get("catalog_seed")]
