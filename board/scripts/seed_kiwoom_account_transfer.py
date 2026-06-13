#!/usr/bin/env python3
"""계좌 차수거래·계좌 이동 학습 카드 추가·확정·구조 갱신."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_kiwoom_learn as learn  # noqa: E402
import agent_office_wiki_store as wiki  # noqa: E402

META_PATH = BOARD / "data" / "kiwoom_learning" / "knowledge_structure.json"

NEW_CARDS = [
    {
        "title": "계좌 차수거래 개념",
        "body": (
            "계좌 차수거래는 차수(1·2·3차) 분할 전략을 계좌 단위로 적용하는 운용이다. "
            "위탁·CMA·연금(IRP)·ISA 등 계좌마다 예수금·주문가능·보유·평단이 분리된다. "
            "동일 종목이라도 계좌가 다르면 포지션·손익·세금 처리가 각각 계산된다. "
            "전략 설계 시 「어느 계좌에서 몇 차수까지」를 먼저 정하고, 계좌별 자금 한도를 배분한다. "
            "한 계좌 안에서만 차수를 쌓는 것이 기본이며, 계좌를 넘는 차수는 「계좌 이동」 후 해당 계좌에서 다음 차수를 실행한다."
        ),
    },
    {
        "title": "계좌별 차수·자금 배분",
        "body": (
            "계좌별 목표 비중 예: 위탁 70% · CMA 30%. 각 계좌 내에서 1차 30%·2차 40%·3차 30% 식으로 차수 비율 적용. "
            "1차는 계좌 A만 사용, 2차 자금이 부족하면 B계좌에서 A로 이체 후 2차 진입. "
            "계좌별 최대 투입금·최대 종목 수·레버리지(신용) 한도를 카드에 명시한다. "
            "연금·ISA는 입출금·매매 제한이 있으므로 차수 규칙을 별도 카드로 둔다. "
            "점검: 계좌 A 주문가능 ≥ 2차 예상 금액 + 수수료, 이체 예정이면 이체 후 잔고 재확인."
        ),
    },
    {
        "title": "계좌 이동(이체·대체) 정의",
        "body": (
            "계좌 이동은 예수금·현금을 증권사 내 다른 계좌로 옮기는 것이다(주식 포지션 이전과 구분). "
            "키움 HTS/영웅문: 계좌간 이체, 대체, 출금·입금, 외화이체 등 메뉴로 처리. "
            "이동 목적을 기록한다 — 2·3차 매수 자금, 세금·이자, 계좌 정리, CMA→위탁 등. "
            "D+0·D+1·D+2 정산에 따라 당일·익일 반영 시점이 다르다. "
            "이체 직후 예수금·주문가능이 HTS와 일치하는지 스냅샷으로 남긴다(계좌번호 끝 4자리만)."
        ),
    },
    {
        "title": "계좌 이동 절차·리스크",
        "body": (
            "이체 전: 출금 계좌 주문가능·미체결 합계 확인 — 이체 금액이 주문·증거금과 겹치지 않게. "
            "이체 중: 장중 이체 가능 여부·한도·수수료(있을 경우) 확인. "
            "이체 후: 입금 계좌 예수금·주문가능 갱신, 2차 차수 주문 가능 여부 재계산. "
            "리스크: 이체 지연으로 2차 타이밍 놓침, 잘못된 계좌 선택, 이체 후에도 주문가능 부족, "
            "연금계좌 규정 위반 이체. 오류 시 즉시 HTS 잔고 화면 캡처 대신 금액·시각·목적만 텍스트 기록."
        ),
    },
    {
        "title": "차수거래×계좌 이동 시나리오",
        "body": (
            "시나리오 A: 1차 위탁계좌 매수 → 2차 전 CMA→위탁 이체 → 2·3차 위탁에서 추가. "
            "시나리오 B: 1·2차 완료 후 익절금 일부를 CMA로 이동(현금 대기·배당 재투자 분리). "
            "시나리오 C: 계좌별 차수 독립 — A는 1차만, B는 별도 종목 1차(상관 분산). "
            "규칙: 이체 완료 확인 전 2차 주문 금지. 미체결·예약주문 있으면 이체 금액에서 제외. "
            "학습 카드·계좌 젬마 스냅샷에 「이체 YYYY-MM-DD HH:MM · 금액 · A→B · 목적」 한 줄로 남긴다."
        ),
    },
]

# 계좌간 이동을 차수거래 수단으로 쓰는 통합 운용
INTEGRATED_CARDS = [
    {
        "title": "계좌간 이동으로 하는 차수거래 — 원칙",
        "body": (
            "차수거래를 하면서 계좌간 이동을 쓰는 방식은 「매매 계좌는 하나, 자금은 여러 계좌에서 모은다」는 구조다. "
            "1차: 매매 계좌(보통 위탁)에서 조건만 맞으면 시드 매수 — 이체 없이 주문가능만으로 실행. "
            "2차 전: 다른 계좌(CMA·별도 위탁 등)에 쌓아 둔 현금을 매매 계좌로 이체 → 이체 반영 확인 후 2차 매수. "
            "3차 전: 필요 시 동일 방식으로 추가 이체, 또는 1·2차 실현손익이 주문가능에 남으면 이체 생략. "
            "핵심 원칙: 이체는 차수의 일부이며, 이체가 끝나야 다음 차수 주문이 열린다. "
            "차수거래 로그 한 줄 형식: 「N차 | 계좌**** | 이체 Y/N | 출금계좌→입금계좌 | 금액 | 체결여부」."
        ),
    },
    {
        "title": "차수별 계좌간 이동 체크리스트",
        "body": (
            "【1차 — 이체 없음】 매매계좌 주문가능 ≥ 1차금액+수수료 · 종목·수량·가격 조건 충족 · 체결 기록. "
            "【1차→2차 사이 — 이체】 2차 예상금액 산출 → 출금계좌 잔고 확인 → HTS 계좌간 이체 실행 → "
            "입금계좌 주문가능 갱신 확인(스냅샷) → 2차 조건(눌림·시간) 재확인 → 2차 주문. "
            "【2차→3차 사이】 3차 필요 현금이 매매계좌에 있으면 이체 생략, 없으면 동일 이체 절차. "
            "이체 생략 가능 조건: 매매계좌 주문가능 ≥ 3차금액+미체결 합계+버퍼. "
            "장중: 이체 반영 전 급락·VI 시 2·3차 스킵 규칙 적용. 장마감 후 이체는 익일 2차로 연기할지 규칙에 명시."
        ),
    },
    {
        "title": "이체 타이밍·차수 스킵 규칙",
        "body": (
            "이체 지연·실패 시: 2차 조건이 당일만 유효하면 「이체 실패 → 2차 스킵」 기록 후 3차만 검토하거나 전략 중단. "
            "이체 후 주문가능이 여전히 부족하면: 이체 금액 재산정 또는 2차 수량 축소(차수 비율 하향). "
            "동시에 여러 계좌에서 한꺼번에 이체하지 않고, 한 번에 한 경로(A→B)만 — 실수 방지. "
            "익절·손절 청산 후: 현금이 매매계좌에 남으면 CMA 등으로 이동해 다음 종목 1차 자금으로 재배치(차수 사이클 분리). "
            "계좌간 이동으로 차수거래할 때 손절은 「통합 평단」 기준으로 유지하고, 이체는 매수 차수에만 사용(혼동 방지)."
        ),
    },
    {
        "title": "실전 예시 — CMA→위탁 3차 운용",
        "body": (
            "예시 종목 KODEX200, 목표 1000만 원 분할. CMA 400만·위탁 600만 배분. "
            "1차(위탁): 300만 시장가 또는 지정가 매수 — CMA 미사용. "
            "2차 전: CMA→위탁 400만 이체(목적: 2·3차 매수자금), 이체 완료 후 위탁 주문가능 확인. "
            "2차(위탁): 눌림 구간 400만 추가 매수. 3차: 위탁 잔여 주문가능 300만 또는 CMA 추가 이체 200만 후 300만. "
            "청산: 1차 익절 50% → 잔량 2·3차 트레일링. 전량 청산 후 CMA로 200만 이동(다음 전략 대기). "
            "기록 시 계좌번호 대신 CMA·위탁 라벨과 끝 4자리만. 이체·체결·차수 번호를 한 카드에 묶어 학습부에 붙여넣으면 계좌 젬마가 대조한다."
        ),
    },
]


def _layer_ids(confirmed: list[dict], pred) -> list[int]:
    return [c["id"] for c in confirmed if isinstance(c.get("id"), int) and pred(c)]


def write_meta_structure() -> None:
    confirmed = [
        c
        for c in learn.list_cards(limit=100)
        if isinstance(c, dict) and c.get("status") == "confirmed"
    ]

    def title(c: dict) -> str:
        return c.get("title") or ""

    layers_spec = [
        ("L0_concept", "차수·개념", lambda c: any(k in title(c) for k in ("정의", "프레임")) and "계좌" not in title(c)),
        ("L1_account_chasu", "계좌 차수거래", lambda c: "계좌 차수" in title(c) or "계좌별 차수" in title(c)),
        ("L2_transfer", "계좌 이동", lambda c: ("계좌 이동" in title(c) or "이동 절차" in title(c)) and "계좌간" not in title(c)),
        (
            "L2b_chasu_via_transfer",
            "계좌간 이동 차수거래",
            lambda c: "계좌간 이동" in title(c)
            or "이체 타이밍" in title(c)
            or ("실전 예시" in title(c) and "CMA" in title(c)),
        ),
        ("L3_risk", "손익·리스크", lambda c: "손절" in title(c)),
        ("L4_ops", "주문·예수금·연계", lambda c: any(k in title(c) for k in ("주문", "예수금", "시나리오", "체결")) and "계좌간" not in title(c)),
        ("L5_schema", "구조·pack", lambda c: "구조" in title(c)),
    ]
    seen: set[int] = set()
    layers: list[dict] = []
    for lid, lname, pred in layers_spec:
        cards = [i for i in _layer_ids(confirmed, pred) if i not in seen]
        for i in cards:
            seen.add(i)
        layers.append({"id": lid, "name": lname, "cards": cards})
    extra = [c["id"] for c in confirmed if c["id"] not in seen]
    if extra and layers:
        layers[-2]["cards"].extend(extra)

    tag_index: dict[str, list[int]] = {}
    for c in confirmed:
        for t in c.get("tags") or []:
            tag_index.setdefault(t, []).append(c["id"])

    structure = {
        "domain": "kiwoom-chasu",
        "layer": "20_Meta",
        "title": "차수거래·계좌 이동 지식 구조",
        "updated_at": learn._now(),
        "layers": layers,
        "tag_index": {k: sorted(set(v)) for k, v in sorted(tag_index.items())},
    }
    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(json.dumps(structure, ensure_ascii=False, indent=2), encoding="utf-8")


def _ingest_cards(cards: list[dict], source: str) -> int:
    titles = {c.get("title") for c in learn.list_cards(limit=120)}
    added = 0
    for s in cards:
        if s["title"] in titles:
            continue
        card = learn.add_card(body=s["body"], title=s["title"], source=source)
        cid = card.get("id")
        if isinstance(cid, int):
            learn.confirm_card(cid)
            store = learn.load_store()
            for c in store.get("cards") or []:
                if isinstance(c, dict) and c.get("id") == cid:
                    wiki.save_kiwoom_card_to_knowledge(c)
                    break
            titles.add(s["title"])
            added += 1
    return added


def main() -> int:
    added = _ingest_cards(NEW_CARDS, "account_transfer_seed")
    added += _ingest_cards(INTEGRATED_CARDS, "chasu_via_transfer")
    pack = learn.export_pack()
    write_meta_structure()
    st = learn.stats()
    print(f"new_confirmed={added} total={st['total']} pack={pack.get('card_count')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
