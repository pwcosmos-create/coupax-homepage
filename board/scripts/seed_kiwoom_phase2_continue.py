#!/usr/bin/env python3
"""차수거래 2단계 심화 학습 카드 추가·확정·구조·Wiki 반영."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_kiwoom_learn as learn  # noqa: E402
import agent_office_wiki_store as wiki  # noqa: E402

META_PATH = BOARD / "data" / "kiwoom_learning" / "knowledge_structure.json"

PHASE2_CARDS = [
    {
        "title": "월배당 ETF × 차수거래",
        "body": (
            "월배당 ETF는 배당락·분배금 지급일 전후 변동성이 커 차수 규칙을 별도 둔다. "
            "1차: 배당락 N일 전·후 진입 금지 또는 축소 규칙. 2차: 락 이후 가격 안정·거래량 회복 확인 후. "
            "3차: 월배당 수익률·분배금 추이가 학습 카드·ETF 허브 데이터와 일치하는지 대조. "
            "차수별 목표는 가격 차익과 분배금 현금흐름을 분리 기록한다. "
            "동일 ETF라도 계좌(위탁·연금)별 세금·분배 처리가 다르면 계좌 차수 카드와 함께 본다."
        ),
    },
    {
        "title": "장전·장중·장후 차수 타이밍",
        "body": (
            "장전(08:00~09:00): 예상체결·호가 확인만, 1차 신규 진입은 원칙적으로 장중 개시 후. "
            "장중: 1·2·3차 실행 구간 — VI·급등락 구간은 2·3차 스킵. "
            "장후 시간외: 유동성·스프레드 리스크로 3차 금지 또는 수량 50% 축소 규칙. "
            "차수 로그에 「장전/장중/장후 + 시각」을 남긴다. "
            "전일 미체결이 있으면 장 시작 전 정정·취소 후 차수 재계산."
        ),
    },
    {
        "title": "다종목 포트폴리오 차수·자금 캡",
        "body": (
            "동시에 여러 종목에 차수를 열 때 계좌 단위 총 투입 상한(예: 예수금의 80%)을 둔다. "
            "종목 A 1차 진행 중이면 종목 B 2차는 B 전용 자금 한도 내에서만. "
            "상관 높은 ETF(예: KODEX200·TIGER200)는 동시 3차 금지 또는 한쪽만 차수 허용. "
            "우선순위: 손절 임박 종목 > 2차 조건 충족 종목 > 신규 1차. "
            "학습부에 「종목·차수·계좌·투입금」 표 한 줄로 남기면 구조 젬마가 태그·pack에 반영한다."
        ),
    },
    {
        "title": "신용·미수·레버리지 차수 리스크",
        "body": (
            "신용·미수 매수는 2·3차 추가 시 증거금·반대매매 리스크가 커진다. "
            "차수별 최대 레버리지 배수·추가매수 한도를 카드에 고정한다. "
            "이체로 자금을 모은 뒤에도 신용 한도 초과 시 2차 스킵. "
            "금리·이자 비용을 통합 평단 손익에 포함해 손절선을 상향 조정할지 규칙화. "
            "연금·ISA는 신용 불가인 경우가 많으므로 계좌 유형별 차수 규칙과 분리한다."
        ),
    },
    {
        "title": "급락·VI·거래정지 시 차수 중단",
        "body": (
            "VI 발동·급락(예: 5분 -3% 이상)·거래정지·관리종목 시 2·3차 자동 중단. "
            "1차만 보유 중이면 손절 규칙 우선 적용 후 신규 차수 금지. "
            "중단 사유·시각·종목을 카드에 기록 — 이후 재개는 「재개 조건」 카드에 맞출 것. "
            "계좌간 이체로 2차 자금을 맞춘 직후 VI면 이체는 완료했으나 주문은 스킵(자금은 매매계좌 대기). "
            "뉴스·공시는 HTS 확인, 본 학습부에는 출처·요지만 텍스트."
        ),
    },
    {
        "title": "조건부지정가·예약주문과 차수",
        "body": (
            "1차: 지정가 또는 시장가 — 체결 확인 후 2차 조건 설정. "
            "2차: 조건부지정가(가격 도달 시) — 미체결 시 장 마감 전 정정 규칙. "
            "3차: 예약주문·시간외는 유동성 리스크 검토 후. "
            "차수 N마다 주문 유형을 카드에 명시; 미체결이 다음 차수 주문가능을 잠식하지 않게 합산 점검. "
            "계좌간 이체 직후 예약주문 넣기 전 주문가능 갱신 필수."
        ),
    },
    {
        "title": "연금·ISA·세금이 차수에 미치는 제약",
        "body": (
            "연금(IRP)·ISA는 입출금·매매 횟수·대상 종목 제한이 있어 차수 횟수·이체 경로가 위탁과 다르다. "
            "매도 차익·분배금 세금은 계좌별로 달라 3차 청산 시 세후 목표가를 별도 계산. "
            "연금계좌에서 CMA→위탁 이체가 불가하면 차수는 해당 계좌 내 자금만으로 설계. "
            "세금 최적화를 이유로 차수 순서를 바꾸지 않고, 손절·리스크 규칙이 우선. "
            "확정 카드·계좌 젬마에 「계좌유형·제한」 태그를 붙인다."
        ),
    },
    {
        "title": "학습 카드·체결 로그 대조(피드백)",
        "body": (
            "실전 체결 후 HTS 체결내역과 학습 카드의 차수 번호·가격·수량을 대조한다. "
            "불일치 시: 카드 수정 또는 「오차 메모」 카드 추가 — 구조 젬마·회간이 pack에 반영. "
            "계좌 젬마 스냅샷 시각과 체결 시각이 30분 이상 어긋나면 stale로 표시. "
            "피드백 우선순위: 손절 미준수 > 이체 후 미주문 > 태그 누락 > 요약 오타. "
            "대기 카드는 주 1회 검수·확정; 확정은 kiwoom_knowledge_pack·Wiki 동시 갱신."
        ),
    },
    {
        "title": "차수 실패·오류 복구 절차",
        "body": (
            "실패 유형: 이체 지연, 미체결 과다, 주문가능 부족, HTS 오류, 잘못된 계좌 선택. "
            "복구: 1) 미체결·예약 전량 정리 2) 잔고·주문가능 스냅샷 3) 해당 차수 스킵 또는 수량 축소 재시도. "
            "동일 종목 당일 2차 재시도는 1회로 제한. "
            "오류 젬마 job과 연동 — health·대기 25건 초과 시 알림. "
            "복구 완료 후 「N차 스킵/재시도 Y/N · 사유」 한 줄을 학습 카드에 남긴다."
        ),
    },
]


def _layer_ids(confirmed: list[dict], pred) -> list[int]:
    return [c["id"] for c in confirmed if isinstance(c.get("id"), int) and pred(c)]


def write_meta_structure() -> None:
    confirmed = [
        c
        for c in learn.list_cards(limit=120)
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
        ("L3_risk", "손익·리스크", lambda c: "손절" in title(c) or "신용" in title(c) or "급락" in title(c)),
        (
            "L4_ops",
            "주문·예수금·연계",
            lambda c: any(k in title(c) for k in ("주문", "예수금", "시나리오", "체결", "조건부", "장전"))
            and "계좌간" not in title(c),
        ),
        ("L5_schema", "구조·pack", lambda c: "구조" in title(c) or "피드백" in title(c)),
        ("L6_etf", "ETF·배당", lambda c: "ETF" in title(c) or "배당" in title(c)),
        ("L7_portfolio", "포트폴리오", lambda c: "다종목" in title(c) or "포트폴리오" in title(c)),
        ("L8_tax_account", "세금·연금·ISA", lambda c: any(k in title(c) for k in ("연금", "ISA", "세금"))),
        ("L9_recovery", "복구·오류", lambda c: "복구" in title(c) or "오류" in title(c)),
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
        layers[-3]["cards"].extend(extra)

    tag_index: dict[str, list[int]] = {}
    for c in confirmed:
        for t in c.get("tags") or []:
            tag_index.setdefault(t, []).append(c["id"])

    structure = {
        "domain": "kiwoom-chasu",
        "layer": "20_Meta",
        "title": "차수거래·계좌·심화 지식 구조",
        "updated_at": learn._now(),
        "phase": 2,
        "layers": layers,
        "tag_index": {k: sorted(set(v)) for k, v in sorted(tag_index.items())},
    }
    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(json.dumps(structure, ensure_ascii=False, indent=2), encoding="utf-8")


def _ingest_cards(cards: list[dict], source: str) -> int:
    titles = {c.get("title") for c in learn.list_cards(limit=150)}
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
    added = _ingest_cards(PHASE2_CARDS, "phase2_continue")
    pack = learn.export_pack()
    write_meta_structure()
    st = learn.stats()
    print(f"new_confirmed={added} total={st['total']} pack={pack.get('card_count')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
