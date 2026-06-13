"""
원키스US ATR 지식 카드 — 무손실·세븐 스플릿용 수치·산출·갱신·점검.

auto_bot.py: _atr_to_gap · _atr_to_sell · _calc_dynamic_gap_us · update_atr_settings_us
"""
from __future__ import annotations


def all_atr_specs() -> list[dict]:
    return list(ATR_KNOWLEDGE_CARDS)


ATR_KNOWLEDGE_CARDS: list[dict] = [
    {
        "title": "원키스US·ATR 개요(20일·5일)",
        "catalog_seed": "workisus_atr_overview",
        "category": "atr_rl",
        "priority": 97,
        "body": (
            "ATR(평균진폭): KIS US calc_atr_full_us → ATR20(장기)·ATR5(단기)·현재가. "
            "atr_auto=true·enabled 종목만 update_atr_settings_us() 대상. "
            "무손실 세븐 스플릿: ATR로 buy_gaps(하락 진입폭)·2~10차 sell_pcts(익절%)·"
            "atr_qty_amt 기반 수량을 맞춘다. 고정 -5%/-3%만 쓰지 않는다. "
            "매매규칙·자동·리스크 젬마가 갱신 로그·[3003] 값과 카드를 대조한다."
        ),
    },
    {
        "title": "원키스US·ATR→buy_gap 산식",
        "catalog_seed": "workisus_atr_buy_gap_formula",
        "category": "atr_rl",
        "priority": 96,
        "body": (
            "기본: _atr_to_gap(ATR20%) → 양수 0.5~5.0 클램프 후 0.5단위 음수(-0.5~-5.0). "
            "예: ATR20=3% → gap 약 -3%. "
            "국면(_calc_dynamic_gap): ATR20>6% 극단변동 gap×2(매수 억제), "
            "ATR5>ATR20×1.5 고변동 ×1.5, ATR5<ATR20×0.7 저변동 ×0.7. "
            "무손실: _calc_dynamic_gap_us 후 ×us_atr_gap_musonsil_mult(기본1.15) 추가 확대. "
            "stock_settings buy_gaps 10칸 동일값으로 저장."
        ),
    },
    {
        "title": "원키스US·ATR→sell_pct 산식(2~10차)",
        "catalog_seed": "workisus_atr_sell_formula",
        "category": "atr_rl",
        "priority": 96,
        "body": (
            "기본: _atr_to_sell(ATR20)=ATR20×1.2, 0.5단위, 1.0~5.0 클램프. "
            "무손실 튜닝 _us_tune_atr_sell_pct: "
            "×us_atr_sell_mult(기본1.0), 하한 us_atr_sell_min=1.5%, 상한 us_atr_sell_cap=4%. "
            "저장: sell_pcts=[999.0]+[sell]×9 — 1차 999% 앵커, 2차 15초 순환·3~N차 익절에 사용. "
            "실제 매도: 표시수익>0 + sell%+sell_fee_buffer_pct_us(0.12) + 합산평단>0%."
        ),
    },
    {
        "title": "원키스US·ATR 국면(극단·고·저변동)",
        "catalog_seed": "workisus_atr_market_phase",
        "category": "atr_rl",
        "priority": 95,
        "body": (
            "ATR 갱신 로그 phase: 극단변동·고변동·보통·저변동·무손실(접미). "
            "극단(ATR20>6%): gap 넓게—급락장 과밀 분할 방지. "
            "고변동(ATR5>1.5×ATR20): 신중 진입. "
            "저변동: gap 좁게—횡보 적극 격자(무손실 mult 적용 후에도 상한 -0.5). "
            "자동젬마·매매규칙: phase 급변 시 [3003] 재저장·bot_log [ATR-US] 확인."
        ),
    },
    {
        "title": "원키스US·ATR 수량·atr_qty_amt",
        "catalog_seed": "workisus_atr_qty_amt",
        "category": "atr_rl",
        "priority": 94,
        "body": (
            "종목 atr_qty_amt(USD 목표, 예 1000): qty=max(1, int(amt÷현재가)). "
            "buy_qtys=[1]+[qty]×9 — 1차는 수동 register 수량, 2~N차 자동은 ATR 산출 qty. "
            "_realtime_optimal_buy_amt: 남은 차수·현금·max_slot로 실주문액 조율. "
            "잔고젬마: USD 예수금 부족 시 qty 과대 주문 거절—atr_qty_amt 하향 검토."
        ),
    },
    {
        "title": "원키스US·ATR 갱신·실행",
        "catalog_seed": "workisus_atr_update_run",
        "category": "atr_rl",
        "priority": 93,
        "body": (
            "함수: update_atr_settings_us() → bot_settings_us.json 저장·atr_rl_record_success. "
            "트리거: 대시보드 ATR 버튼·cron·apply_workisus_atr_musonsil.py --run-atr. "
            "조건: stock_settings[티커].atr_auto=true and enabled=true. "
            "실패: ATR20≤0 데이터 부족—[ATR-US] 로그, 종목 excd(NASD 등) 확인. "
            "갱신 후: enabled_us·no_slot=false면 세븐 스플릿 격자 파라미터가 즉시 반영."
        ),
    },
    {
        "title": "원키스US·bot_settings_us ATR 루트키",
        "catalog_seed": "workisus_atr_root_keys",
        "category": "atr_rl",
        "priority": 92,
        "body": (
            "bot_settings_us.json 루트(무손실 기본): "
            "us_atr_sell_mult=1.0, us_atr_sell_cap=4.0, us_atr_sell_min=1.5, "
            "us_atr_gap_musonsil_mult=1.15, sell_fee_buffer_pct_us=0.12. "
            "종목: enabled, atr_auto, atr_qty_amt, buy_gaps[10], sell_pcts[10], buy_qtys, max_slot, excd. "
            "프리셋: board/data/workisus_learning/bot_settings_us_atr_musonsil_preset.json. "
            "동기젬마·카탈로그 시드로 카드와 JSON 키를 맞춘다."
        ),
    },
    {
        "title": "원키스US·ATR vs 고정 gap",
        "catalog_seed": "workisus_atr_vs_fixed_gap",
        "category": "atr_rl",
        "priority": 91,
        "body": (
            "고정 buy_gaps=[-5]*10: 변동성 무시—급등락 종목에 부적합. "
            "ATR 자동: 종목·시장 국면마다 gap/sell 재산출—무손실·세븐 스플릿 정본. "
            "atr_auto=false 종목은 수동 [3003] 유지—점검 시 카드와 불일치 주의. "
            "원히어로 KR ATR 스케줄(08:30~08:44)과 US 경로는 분리—US는 update_atr_settings_us."
        ),
    },
    {
        "title": "원키스US·ATR 젬마 점검 체크리스트",
        "catalog_seed": "workisus_atr_agent_checklist",
        "category": "atr_rl",
        "priority": 90,
        "body": (
            "매매규칙: atr_auto·buy_gaps·sell_pcts[0]==999·sell[1] 1.5~4%·atr_qty_amt. "
            "자동: ATR 갱신일·phase·15초 2차·buy_gaps 충족 여부. "
            "리스크: 무손실·합산평단·fee_buffer. "
            "오류: ATR 실패·갱신 안 됨·sell 4% 초과 수동편집 → workisus_trade_err_*·ATR 카드. "
            "pack 우선 시드: workisus_atr_* · wonkisus_atr_musonsil_policy."
        ),
    },
    {
        "title": "원키스US·ATR 오류·데이터 부족",
        "catalog_seed": "workisus_atr_error_data",
        "category": "atr_error",
        "priority": 85,
        "body": (
            "증상: [ATR-US] ATR 계산 실패(데이터 부족)—갱신 스킵, 이전 buy_gaps/sell 유지. "
            "원인: 상장 초기·거래정지·시세 API·excd 오타. "
            "해결: 시세 probe·티커 조사·excd 수정 후 update_atr_settings_us 재실행. "
            "무손실: ATR 없이 무리한 고정 -2% gap 금지—데이터 확보 후 자동화."
        ),
    },
    {
        "title": "원키스US·ATR 수동 편집 주의",
        "catalog_seed": "workisus_atr_manual_edit",
        "category": "atr_error",
        "priority": 84,
        "body": (
            "증상: [3003]에서 sell_pcts[1]=10% 등 과대 설정—2차 15초 순환 익절 안 됨. "
            "무손실 cap 4%·min 1.5% 범위 권장. "
            "buy_gaps -0.5보다 얕으면(-0.3) 과밀 분할·합산 방어 전 손실 구간 장기화. "
            "수동 변경 후 atr_auto=true면 다음 ATR 갱신 시 덮어씀—의도 보존 시 atr_auto OFF."
        ),
    },
]
