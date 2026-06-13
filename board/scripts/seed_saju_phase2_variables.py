#!/usr/bin/env python3
"""사주 명리 2차 변수 카드 — 음양·십이운성·지장간·천간합·납음·특수격·신강 등."""
from __future__ import annotations

import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_saju_learn as learn  # noqa: E402
import agent_office_wiki_store as wiki  # noqa: E402

FOOTER = " 참고용 서술이며 확정 예언·의학·법률 단정은 금지한다."

# 십이운성 12
TWELVE_STAGES: list[tuple[str, str]] = [
    ("장생", "시작·성장·희망. 새 출발·학습·씨앗 단계. 과다 시 산만."),
    ("목욕", "매력·감정·노출. 인연·표현·예술. 과다 시 산만·스캔들 톤만."),
    ("관대", "성장·자립·사회 진출. 역할 확대·자격. 과다 시 과시."),
    ("건록", "왕성·안정·성숙. 실력·자원 축적. 과다 시 고집."),
    ("제왕", "정점·권위·집중. 리더·완성. 과다 시 독선·압박."),
    ("쇠", "전환·조정·내려놓음. 휴식·정리. 과다 시 무기력 톤만."),
    ("병", "약화·주의·컨디션. 건강 리듬·부담. 의학 단정 금지."),
    ("사", "정지·변화·재시작 전. 내면·종교·연구. 공포 조장 금지."),
    ("묘", "저장·잠재·준비. 비밀·계획. 과다 시 은둔."),
    ("절", "단절·새 사이클 직전. 이동·이직 키워드만."),
    ("태", "잉태·가능성·미완. 학습·프로젝트 초기."),
    ("양", "양육·보호·성장 기반. 멘토·가정·인성 기운."),
]

# 지지별 지장간 (본기·중기·여기 요약)
HIDDEN_STEMS: list[tuple[str, str, str]] = [
    ("자수", "癸", "壬癸 잠재·지혜·유통"),
    ("축토", "己", "己辛癸 습토·저장·노력"),
    ("인목", "甲", "甲丙戊 봄초·도전·리더"),
    ("묘목", "乙", "乙 목 기운·표현·인연"),
    ("진토", "戊", "戊乙癸 습토·전환·야망"),
    ("사화", "丙", "丙庚戊 화·전략·표현"),
    ("오화", "丁", "丁己 화 정점·명예·속도"),
    ("미토", "己", "己丁乙 조토·돌봄·완성"),
    ("신금", "庚", "庚壬戊 금·실행·변화"),
    ("유금", "辛", "辛 정밀·완성·미감"),
    ("술토", "戊", "戊辛丁 조토·의리·저장"),
    ("해수", "壬", "壬甲 수·포용·직관"),
]

STEM_COMBINE: list[tuple[str, str]] = [
    ("甲己合土", "갑기 합토 — 중재·현실·신뢰. 합이 깨지면 내적 갈등."),
    ("乙庚合金", "을경 합금 — 규율·결단·정리. 예술+원칙 조합."),
    ("丙辛合水", "병신 합수 — 감성·직관·표현 정제."),
    ("丁壬合木", "정임 합목 — 성장·학습·인연 확장."),
    ("戊癸合火", "무계 합화 — 열정·추진·체면."),
]


def _card(title: str, body: str) -> dict:
    return {"title": title, "body": body}


def build_phase2_cards() -> list[dict]:
    cards: list[dict] = []

    cards.append(
        _card(
            "변수·음양 원리",
            "【음양 변수】양(陽)은 확장·밝음·추진·건조, 음(陰)은 수용·내면·유연·습润. "
            "천간 양: 갑병무경임, 음: 을정기신계. 지지 양: 인진오신술, 음: 축묘미유자해. "
            "일간 음양으로 겉·속 성향을 나누고, 오행과 함께 용신 방향을 잡는다." + FOOTER,
        )
    )
    cards.append(
        _card(
            "변수·일간 음양 판별",
            "【음양 변수】양일간은 드러내는 추진·리더·속도, 음일간은 섬세·인내·내면·협상. "
            "양일간+관성 과다: 압박·완고, 음일간+식상: 표현·창작. "
            "궁합·직장에서는 음양 보완(양↔음)을 「역할 분담」으로만 서술." + FOOTER,
        )
    )

    for name, desc in TWELVE_STAGES:
        cards.append(
            _card(
                f"변수·십이운성 {name}",
                f"【십이운성 변수】{name}. {desc} "
                "일간·대운·세운 지지에 따라 단계가 달라진다. "
                "한 단계만으로 길흉 단정하지 말고 십신·용신과 함께 본다." + FOOTER,
            )
        )

    cards.append(
        _card(
            "변수·지장간 개요",
            "【지장간 변수】지지 안에 숨은 천간(본기·중기·여기). 격국·십신의 뿌리. "
            "월지 본기가 격의 핵심, 일지 본기는 배우자·내면. "
            "지장간이 강하면 겉과 속이 다를 수 있음 — 「겉 격 vs 속 십신」 분리 서술." + FOOTER,
        )
    )
    for branch, main, desc in HIDDEN_STEMS:
        cards.append(
            _card(
                f"변수·지장간 {branch}",
                f"【지장간 변수】{branch} — 본기 {main} 중심. {desc}. "
                "월지·일지·시지에 있을 때 해당 궁에 투영." + FOOTER,
            )
        )

    for name, desc in STEM_COMBINE:
        cards.append(
            _card(
                f"변수·천간합 {name}",
                f"【천간합 변수】{name}. {desc} "
                "합이 성립하면 해당 오행 기운이 강해짐. 충·극과 겹치면 「합 속 갈등」 톤." + FOOTER,
            )
        )

    cards.append(
        _card(
            "변수·납음 개요",
            "【납음 변수】60갑자 각각의 오행·음성(海中金·炉中火 등). "
            "년주·일주 납음으로 조상·본인 기질 보조. "
            "납음만으로 용신 단정 금지 — 오행 개수·월지 격이 우선." + FOOTER,
        )
    )

    for title, body in [
        (
            "변수·특수격 종격",
            "【특수격】일간 극약·비겁·인성 편중 시 종(從)격 검토. "
            "종재격·종살격·종儿격 등 — 강한 기운에 순응하는 풀이. 확정 단정 금지.",
        ),
        (
            "변수·특수격 화격",
            "【특수격】화(化) 기운이 명확할 때 — 합화·化神. "
            "甲己化土·丙辛化水 등 천간합화와 연계. 학파별 차이 명시.",
        ),
        (
            "변수·특수격 신강",
            "【신강신약】일간 득령·득지·득시·비겁으로 강약 판단. "
            "신강: 설기·극·泄 필요, 신약: 생·扶 필요. "
            "용신은 「억부」— 강하면 설, 약하면 생.",
        ),
        (
            "변수·특수격 신약",
            "【신강신약】신약 일간은 인성·비겁 보호·학습·멘토가 도움. "
            "관성·재성 과다 시 압박·재물 부담 — 「보완·휴식」 톤.",
        ),
        (
            "변수·득령득지득시",
            "【득령득지득시】월지=득령(계절), 일지=득지(배우자궁), 시지=득시(말년·자녀). "
            "세 개 중 2개 이상이면 일간 강한 편. "
            "득령 없으면 격국·용신 해석에 주의.",
        ),
        (
            "변수·원진",
            "【원진】子未·丑午·寅酉·卯申·辰亥·巳戌 — 거리·오해·소통 비용. "
            "충·합과 별도. 「이별·불화」 단정 금지, 「조율 필요」 톤.",
        ),
        (
            "변수·조후 한열",
            "【조후】한(寒) 사주는 화·목 보완, 열(熱) 사주는 수·금 보완. "
            "계절(월지)과 함께 본다. 의학·질병 단정 금지.",
        ),
        (
            "변수·공망 활용",
            "【공망】해공·자공 등 — 「기대 조절·공허」 톤. "
            "인연·재물·프로젝트에서 「채워지지 않음」 표현만. 불길·파산 단정 금지.",
        ),
    ]:
        cards.append(_card(title, body + FOOTER))

    return cards


def ingest(cards: list[dict]) -> int:
    titles = {c.get("title") for c in learn.list_cards(limit=500)}
    added = 0
    for s in cards:
        if s["title"] in titles:
            continue
        card = learn.add_card(body=s["body"], title=s["title"], source="phase2_variables")
        cid = card.get("id")
        if not isinstance(cid, int):
            continue
        learn.confirm_card(cid)
        store = learn.load_store()
        for c in store.get("cards") or []:
            if isinstance(c, dict) and c.get("id") == cid:
                wiki.save_saju_card_to_knowledge(c)
                break
        titles.add(s["title"])
        added += 1
    return added


def main() -> int:
    pool = build_phase2_cards()
    added = ingest(pool)
    learn.export_pack()
    st = learn.stats()
    print(f"pool={len(pool)} new={added} total={st['total']} confirmed={st['confirmed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
