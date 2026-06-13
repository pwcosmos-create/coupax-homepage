"""원히어로 차수거래 — 카드 기반 매매 방법 학습 경로.

확정 카드(catalog_seed)와 1:1 매칭 · 단계별 HTS·대시보드 실습 체크리스트.
"""
from __future__ import annotations

import json
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
STATE_PATH = BOARD / "data" / "kiwoom_learning" / "learn_path_state.json"

# 순서 = 실제 매매 흐름 (이 카드 순서로 학습)
TRADING_LEARN_STEPS: list[dict] = [
    {
        "step": 1,
        "catalog_seed": "wonhero_def",
        "title": "원히어로·차수 구조 이해",
        "practice": [
            "stock.coupax.co.kr/wonhero 대시보드 접속",
            "종목·슬롯(차수)·ATR buy_gaps/sell_pcts 위치 확인",
            "coupax 학습부는 규칙 문서, 실주문은 원히어로 봇 담당임을 구분",
        ],
    },
    {
        "step": 2,
        "catalog_seed": "wonhero_slot1_manual",
        "title": "1차 — HTS 수동 매수·잔고 인식",
        "practice": [
            "1번 계좌에서 HTS로 1차만 수동 매수(시장가·지정가)",
            "원히어로에서 잔고 인식·register 로그 확인",
            "같은 15초 루프에 2차가 바로 나가지 않는지 확인(newly_registered)",
        ],
    },
    {
        "step": 3,
        "catalog_seed": "wonhero_instant_2nd",
        "title": "2차 — 등록 15초 후 즉시 매수",
        "practice": [
            "register 후 15초 이상 경과 시 2차 주문 가능 여부 관찰",
            "스캘프·다계좌(account_tag)면 instant 2차가 꺼짐을 확인",
            "bot_log reason에 경과 초·슬롯 번호가 남는지 확인",
        ],
    },
    {
        "step": 4,
        "catalog_seed": "wonhero_buy_gaps",
        "title": "3차+ — ATR buy_gaps 추가매수",
        "practice": [
            "3차부터는 하락률(buy_gaps) 충족 시에만 추가매수",
            "대시보드 cascade 표·buy_gaps %와 로그 대조",
            "장중·쿨다운·잔고 부족 시 스킵되는지 확인",
        ],
    },
    {
        "step": 5,
        "catalog_seed": "wonhero_atr_schedule",
        "title": "ATR 갱신·설정 반영",
        "practice": [
            "국내 08:30~08:44 ATR 자동 갱신 구간 인지",
            "필요 시 POST /api/update_atr 또는 대시보드 ATR 버튼",
            "갱신 후 buy_gaps·sell_pcts가 종목 행에 반영됐는지 확인",
        ],
    },
    {
        "step": 6,
        "catalog_seed": "wonhero_sell_pcts",
        "title": "익절 — 무조건·sell_pcts·버퍼",
        "practice": [
            "최상위 원칙: sell_pcts+게이트 충족 시 반드시 익절(미루기·임의 취소 금지)",
            "슬롯별 익절 %·버퍼·합산 이익 게이트 동작 확인",
            "1차 999% 패턴 등 대시보드 sell_pcts와 bot_log 익절 대조",
            "손절 자동매도는 없음 — 이익 구간에서는 무조건 익절로 리스크 관리",
        ],
    },
    {
        "step": 7,
        "catalog_seed": "wonhero_loop",
        "title": "15초 루프·장중 감시",
        "practice": [
            "auto_bot 15초 주기로 잔고·익절·추가매수 반복함을 관찰",
            "평일 08:00~15:40 장중 매매·장외 reconcile 구분",
            "당일 was_sold_today·재진입 규칙과 충돌 없는지 확인",
        ],
    },
    {
        "step": 8,
        "catalog_seed": "wonhero_reconcile",
        "title": "reconcile·잔고 맞추기",
        "practice": [
            "HTS 잔고와 봇 슬롯 수량 불일치 시 reconcile 절차",
            "학습 카드에 주문번호·계좌 전체 넣지 않기",
            "오류 시 monitor_live_* 카드·meta_err 가이드 참고",
        ],
    },
    {
        "step": 9,
        "catalog_seed": "wonhero_dashboard_atr",
        "title": "대시보드 운영·설정 저장",
        "practice": [
            "saveAutoSettings·cascade 행 보존 여부 확인",
            "reloadBotSettingsFromServer 후 표·localStorage 일치",
            "실전 전 소액·1종목으로 1→2→3차 흐름 리허설",
        ],
    },
]


def _load_state() -> dict:
    if not STATE_PATH.is_file():
        return {"completed_steps": [], "updated_at": ""}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"completed_steps": [], "updated_at": ""}


def save_state(data: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def mark_step_done(step: int) -> dict:
    st = _load_state()
    done = set(int(x) for x in st.get("completed_steps") or [] if str(x).isdigit())
    done.add(int(step))
    st["completed_steps"] = sorted(done)
    from datetime import datetime

    st["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_state(st)
    return st


def build_path_report() -> dict:
    import agent_office_kiwoom_learn as learn

    by_seed: dict[str, dict] = {}
    for c in learn.load_store().get("cards") or []:
        if not isinstance(c, dict):
            continue
        seed = (c.get("catalog_seed") or "").strip()
        if seed:
            by_seed[seed] = c

    st = _load_state()
    done_steps = set(int(x) for x in st.get("completed_steps") or [] if str(x).isdigit())

    steps_out: list[dict] = []
    ready = 0
    for spec in TRADING_LEARN_STEPS:
        seed = spec["catalog_seed"]
        card = by_seed.get(seed)
        step_n = int(spec["step"])
        has_card = card is not None
        confirmed = has_card and card.get("status") == "confirmed"
        if confirmed:
            ready += 1
        manual_done = step_n in done_steps
        status = "done" if (manual_done or confirmed) else ("ready" if has_card else "missing_card")
        steps_out.append(
            {
                "step": step_n,
                "catalog_seed": seed,
                "title": spec["title"],
                "practice": spec.get("practice") or [],
                "status": status,
                "card_id": card.get("id") if card else None,
                "card_title": (card.get("title") or "") if card else "",
                "card_status": (card.get("status") or "") if card else "",
                "summary": (card.get("summary") or "")[:280] if card else "",
                "body_preview": (card.get("body") or "")[:600] if card else "",
            }
        )

    total = len(TRADING_LEARN_STEPS)
    next_step = None
    for s in steps_out:
        if s["status"] != "done":
            next_step = s["step"]
            break

    return {
        "steps": steps_out,
        "total": total,
        "cards_ready": ready,
        "completed_manual": len(done_steps),
        "progress_pct": int(100 * (sum(1 for s in steps_out if s["status"] == "done") / total)) if total else 0,
        "next_step": next_step,
        "wonhero_url": "https://stock.coupax.co.kr/wonhero",
        "updated_at": st.get("updated_at") or "",
    }
