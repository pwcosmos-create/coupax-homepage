#!/usr/bin/env python3
"""서버 cards.json 점검 후 부족한 변수·띠·십신·오행·지지·격 카드 추가.

  python scripts/ingest_saju_app_gaps.py --dry-run
  python scripts/ingest_saju_app_gaps.py
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import board_env

board_env.load_board_env()

import agent_office_saju_learn as learn  # noqa: E402

_FOOTER = " 본 내용은 명리 참고용이며 확정 예언·의학·투자·법률 단정은 하지 않습니다."

_ZODIAC: list[tuple[str, str, str]] = [
    ("자", "鼠", "子"),
    ("축", "牛", "丑"),
    ("인", "虎", "寅"),
    ("묘", "兔", "卯"),
    ("진", "龙", "辰"),
    ("사", "蛇", "巳"),
    ("오", "马", "午"),
    ("미", "羊", "未"),
    ("신", "猴", "申"),
    ("유", "鸡", "酉"),
    ("술", "狗", "戌"),
    ("해", "猪", "亥"),
]

_BRANCHES: list[tuple[str, str, str]] = [
    ("자수", "子", "亥子丑 수·겨울·밤. 지혜·잠재력·시작·비밀. 이동·유통."),
    ("축토", "丑", "습토·한겨울. 끈기·저장·노력·완성 지연. 부모·전통."),
    ("인목", "寅", "봄초·새벽. 도전·용기·성장·리더. 변화 시작·활동."),
    ("묘목", "卯", "봄·동트는. 표현·인연·부드러운 힘. 예술·교육·협력."),
    ("진토", "辰", "봄말·습토. 전환·야망·저장·권력. 변동·이동·조직."),
    ("사화", "巳", "초여름. 지혜·열정·전략·표현. 재물·학습·예민."),
    ("오화", "午", "여름·정오. 명예·속도·경쟁·체면. 활동·여행·리더."),
    ("미토", "未", "여름말·조토. 돌봄·예술·완성·인내. 관계·가정·재정 정리."),
    ("신금", "申", "초가을. 실행·변화·이동·법칙. 기술·금융·경쟁."),
    ("유금", "酉", "가을·수확. 완성·미감·말·브랜드. 정리·계약·품질."),
    ("술토", "戌", "가을말·조토. 의리·원칙·저장·권위. 방어·부동산·마무리."),
    ("해수", "亥", "겨울초·밤. 포용·종교·직관·잠재. 준비·연구·휴식."),
]

_SHISHEN: list[tuple[str, str]] = [
    ("비견", "나와 같은 오행·형제·동료·자아·독립. 협력과 경쟁 공존."),
    ("겁재", "강한 비겁·경쟁·분재·충동. 기회와 손실 동시."),
    ("식신", "내가 생함·표현·생산·먹고살림. 안정 창작·요리·교육."),
    ("상관", "설기·돌파·말·비판·마케팅. 규칙 거부·창업·예술."),
    ("편재", "유동 재물·사업·프로젝트·외부 기회. 변동 수입·실행."),
    ("정재", "안정 재물·월급·저축·가정·현실. 성실·계약·물건 관리."),
    ("편관", "압박·권위·변동·경쟁·법규. 도전·스트레스·리더십 시험."),
    ("정관", "명분·직장·책임·규율·결혼(전통). 안정·신뢰·사회적 역할."),
    ("편인", "독학·직관·특수 지식·영성. 변동 학습."),
    ("정인", "학교·자격·보호·문서·어머니 기운. 안정 학습·인성·전통."),
]

_ELEMENTS: list[tuple[str, str]] = [
    ("목", "생장·인·봄·동. 시작·육성·표현의 원천. 과다 시 고집·산만."),
    ("화", "확장·여·여름·남. 명예·인정·속도. 과다 시 조급·번아웃."),
    ("토", "중재·信·환절·중앙. 저장·완충·신뢰. 과다 시 우유부단."),
    ("금", "수렴·義·가을·서. 결단·정리·원칙. 과다 시 냉정·완고."),
    ("수", "저장·智·겨울·북. 지혜·이동·잠재. 과다 시 불안·생각 과다."),
]


def _seed(topic: str, detail: str) -> str:
    return (
        f"【{topic}】{detail} "
        "일간·월지·격국·용신·대운·세운과 함께 「경향」으로만 서술한다."
        + _FOOTER
    )


def daily_fortune_specs() -> list[dict]:
    return [
        {
            "title": "변수·일운 참고",
            "body": _seed(
                "일운",
                "당일 천간·지지를 일간 십신으로 환산해 「오늘의 톤」 1~2문장. "
                "월운·세운보다 가볍게. 중요 결정은 세운·대운과 함께 보라고 안내. "
                "날짜·사건 단정 금지.",
            ),
            "card_style": "variable",
            "tags": ["일운", "오늘", "운", "십신", "당일"],
        },
        {
            "title": "해석·오늘의 운세",
            "body": _seed(
                "오늘의 운세",
                "오늘 하루는 일운(日運) 천·지를 일간 기준 십신으로 읽는다. "
                "재물·연애·직업 전체 풀이가 아니라 당일 컨디션·말·행동·만남 톤만 2~4문장. "
                "대운·세운·월운은 한 줄 맥락만 선택적으로.",
            ),
            "card_style": "interpretive",
            "tags": ["일운", "오늘", "운", "당일", "십신"],
        },
    ]


def gap_specs() -> list[dict]:
    specs: list[dict] = []
    specs.extend(daily_fortune_specs())

    for ko, han, ji in _ZODIAC:
        specs.append(
            {
                "title": f"변수·띠 {ko}({han})",
                "body": _seed(
                    "띠·지지",
                    f"{ko}띠 — 지지 {ji}({han}). 년지·일지에 있으면 성향·인연·가족 "
                    "테마에 투영. 띠만으로 길흉·직업·결혼 시기 단정 금지.",
                ),
                "card_style": "variable",
                "tags": ["띠", "지지", ko, "년지", "인연"],
            }
        )

    specs.extend(
        [
            {
                "title": "변수·격 비겁격",
                "body": _seed(
                    "격국",
                    "월지 비견·겁재(比肩·劫財)가 격을 이룸. 자립·동료·경쟁·협업·지분. "
                    "식상·재성으로 현실화·수입화. 과다 시 고집·분재 주의.",
                ),
                "card_style": "variable",
                "tags": ["격국", "격", "비견", "겁재", "십신"],
            },
            {
                "title": "변수·격 종격(從格) 참고",
                "body": _seed(
                    "격국",
                    "일간이 극약해 월지·사주 기세를 따르는 격. "
                    "종재·종살·종아·종왕 등 학파별 분류. 「반드시」 단정 금지.",
                ),
                "card_style": "variable",
                "tags": ["격국", "격", "종격", "신약"],
            },
            {
                "title": "변수·격 잡격·무격 참고",
                "body": _seed(
                    "격국",
                    "월지 본기가 불명확하거나 여러 십신이 겹칠 때. "
                    "일간·오행·대운으로 주제를 잡고 한 격만 고집하지 않는다.",
                ),
                "card_style": "variable",
                "tags": ["격국", "격", "잡격", "무격"],
            },
            {
                "title": "변수·조후(寒暖燥濕) 참고",
                "body": _seed(
                    "조후",
                    "한난·조습·건조로 사주 균형 방향을 보는 견해. "
                    "억부·통관과 충돌할 수 있어 학파·환경에 따라 다름을 명시.",
                ),
                "card_style": "variable",
                "tags": ["조후", "용신", "오행", "한열"],
            },
        ]
    )

    for name, hanja, desc in _BRANCHES:
        specs.append(
            {
                "title": f"변수·지지 {name}",
                "body": _seed(
                    "지지",
                    f"{name}({hanja}). {desc} "
                    "월지·일지·시지·년지 위치에 따라 의미가 달라진다.",
                ),
                "card_style": "variable",
                "tags": ["지지", hanja, name[:2], "충", "합"],
            }
        )

    for name, desc in _SHISHEN:
        specs.append(
            {
                "title": f"변수·십신 {name}",
                "body": _seed(
                    "십신",
                    f"{name}. {desc} "
                    "월지·천간·지지에서 도출. 한 십신만 강조하지 말고 조합으로 풀이.",
                ),
                "card_style": "variable",
                "tags": ["십신", name, "격국", "용신"],
            }
        )

    for name, desc in _ELEMENTS:
        specs.append(
            {
                "title": f"변수·오행 {name}",
                "body": _seed(
                    "오행",
                    f"{name}({name}行). {desc} "
                    "사주 전체 개수로 과다·부족 판단. 상생상극으로 용신 방향 연결.",
                ),
                "card_style": "variable",
                "tags": ["오행", name, "상생", "용신"],
            }
        )

    return specs


def existing_titles() -> set[str]:
    return {(c.get("title") or "").strip() for c in learn.list_cards(limit=3000)}


def ingest(*, sleep_sec: float = 0.2, dry_run: bool = False) -> dict:
    titles = existing_titles()
    pending = [s for s in gap_specs() if s["title"] not in titles]
    if dry_run:
        return {
            "dry_run": True,
            "would_add": len(pending),
            "titles": [s["title"] for s in pending],
        }
    ids: list[int] = []
    for spec in pending:
        card = learn.add_card(
            body=spec["body"],
            title=spec["title"],
            source="app_gaps",
            card_style=spec.get("card_style"),
        )
        cid = card.get("id")
        if not isinstance(cid, int):
            continue
        learn.confirm_card(cid, export_pack_now=False)
        tags = spec.get("tags") or []
        if tags:
            fresh = learn.get_card(cid) or card
            learn.update_confirmed_card(
                cid,
                tags=list(dict.fromkeys(list(fresh.get("tags") or []) + tags))[:12],
            )
        ids.append(cid)
        titles.add(spec["title"])
        if sleep_sec > 0:
            time.sleep(sleep_sec)
    if ids:
        learn.export_pack()
    council: dict = {}
    if ids:
        try:
            import agent_office_saju_card_council as cc

            council = cc.run_batch(min(len(ids) + 5, 80))
        except Exception as e:
            council = {"error": str(e)[:200]}
        try:
            import sync_saju_wiki_council as swc

            swc.main()
        except Exception:
            pass
        learn.export_pack()
    return {
        "added": len(ids),
        "pending_titles": len(pending),
        "council": council,
        "stats": learn.stats(),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--sleep", type=float, default=0.2)
    args = p.parse_args()
    print(json.dumps(ingest(sleep_sec=args.sleep, dry_run=args.dry_run), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
