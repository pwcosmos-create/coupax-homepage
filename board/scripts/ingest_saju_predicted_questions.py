#!/usr/bin/env python3
"""예측 가능한 사용자 질문(의도 분류)별 해석 카드 추가.

saju_reading_intent.py 의 daily | monthly | summary | topic | full 유형과
자주 쓰는 질문 문구(나의 운세, 재물운, 연애운 등)에 맞춘 전용 카드.

  python scripts/ingest_saju_predicted_questions.py --dry-run
  python scripts/ingest_saju_predicted_questions.py
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


def _seed(topic: str, detail: str) -> str:
    return (
        f"【{topic}】{detail} "
        "일간·월지·격국·용신·대운·세운과 함께 「경향」으로만 서술한다."
        + _FOOTER
    )


def predicted_question_specs() -> list[dict]:
    """의도 추론·앱 추천 질문 칩과 1:1 대응."""
    return [
        {
            "title": "해석·나의 운세",
            "body": _seed(
                "나의 운세",
                "「나의 운세」「내 운세」「운세 보기」 질문용 요약 풀이. "
                "인사·성향(일주)·용신·대운·세운을 3~4절로 짧게 연결. "
                "재물·연애·직업 전 테마는 한 줄씩만 언급하고, "
                "세부는 「재물운」「연애운」 등 테마 질문으로 안내. "
                "날짜·합격·이혼·투자 종목 단정 금지.",
            ),
            "card_style": "interpretive",
            "tags": ["나의운세", "내운세", "운세", "사주", "요약", "인사", "용신", "대운"],
        },
        {
            "title": "해석·사주 풀이",
            "body": _seed(
                "사주 풀이",
                "「사주 풀이」「사주 보기」「내 사주」 종합 질문용. "
                "팔자 네 기둥·월지 격국·두드러진 십신·용신·기신을 순서대로 짚고, "
                "심층 10절 전체가 아닌 「한 번에 읽는 중간 길이」 톤. "
                "시주 미상 시 일주·월주 중심 안내.",
            ),
            "card_style": "interpretive",
            "tags": ["사주풀이", "사주보기", "내사주", "종합운", "팔자", "격국", "용신"],
        },
        {
            "title": "해석·재물운",
            "body": _seed(
                "재물운",
                "「재물운」「돈운」「금전」 테마 질문 전용. "
                "정재·편재·식상생재·대운·세운 재성 흐름만 4~6문장. "
                "수입·지출·계약·저축은 「가능성·톤」으로, 종목·대박·날짜 단정 금지. "
                "다른 테마(연애·직업)는 한 줄로 구분 안내.",
            ),
            "card_style": "interpretive",
            "tags": ["재물운", "재물", "정재", "편재", "재성", "수입", "투자"],
        },
        {
            "title": "해석·연애운",
            "body": _seed(
                "연애운",
                "「연애운」「애정」「결혼」「배우자」 질문 전용. "
                "일지·배우자궁·도화·합·충·관성·재성으로 관계 톤만 서술. "
                "만남·이혼·불륜·자녀 시기 단정 금지. 궁합은 별도 「궁합」 질문으로 안내.",
            ),
            "card_style": "interpretive",
            "tags": ["연애운", "연애", "애정", "결혼", "배우자", "도화", "합", "충"],
        },
        {
            "title": "해석·직업운",
            "body": _seed(
                "직업운",
                "「직업운」「직장」「이직」「사업」「취업」 질문 전용. "
                "관성·식신·상관·역마·대운·세운으로 일터·이동·창업 톤. "
                "승진·합격·입사 날짜 단정 금지. 재물·연애와 구분해 한 테마만.",
            ),
            "card_style": "interpretive",
            "tags": ["직업운", "직업", "직장", "이직", "사업", "취업", "관성", "식신"],
        },
        {
            "title": "해석·건강운",
            "body": _seed(
                "건강운",
                "「건강운」「컨디션」「번아웃」 질문 전용. "
                "오행 과다·부족·신강신약·휴식 리듬·스트레스 톤만. "
                "질병명·수술 시기·약 처방 단정 금지. 의학 진단 대체 문구 금지.",
            ),
            "card_style": "interpretive",
            "tags": ["건강운", "건강", "컨디션", "번아웃", "오행", "실천", "주의"],
        },
        {
            "title": "해석·궁합",
            "body": _seed(
                "궁합",
                "「궁합」「연인 비교」「두 명식」 질문 전용. "
                "일간·일지·용신 방향·합·충·형만 비교 톤. "
                "결혼·이혼·자녀·불륜 시기 단정 금지. 한 명식 풀이와 구분.",
            ),
            "card_style": "interpretive",
            "tags": ["궁합", "연인", "비교", "합", "충", "배우자", "관계"],
        },
        {
            "title": "해석·심층 풀이 안내",
            "body": _seed(
                "심층 풀이",
                "「심층 풀이」「10절」「전체 풀이」「풀 리딩」 질문용 안내. "
                "심층·[1]~[10] 순서(인사→팔자→오행→격→용신→대운→재물→연애→직업→실천)를 요약하고, "
                "채팅 요약(나의 운세)과 구분. 각 절은 인증 카드 조합으로 제공됨을 안내.",
            ),
            "card_style": "interpretive",
            "tags": ["심층풀이", "10절", "전체풀이", "풀리딩", "심층사주", "10섹션"],
        },
        {
            "title": "해석·이번 달 운세",
            "body": _seed(
                "이번 달 운세",
                "「이번 달」「내달」「월운」 질문 전용. "
                "당월 천·지를 일간 십신으로 읽고 재물·연애·직업은 1문장씩만. "
                "세운·대운은 맥락 1줄. 날짜·사건 단정 금지.",
            ),
            "card_style": "interpretive",
            "tags": ["이번달", "월운", "다음달", "당월", "운", "세운"],
        },
    ]


def existing_titles() -> set[str]:
    return {(c.get("title") or "").strip() for c in learn.list_cards(limit=5000)}


def ingest(*, sleep_sec: float = 0.25, dry_run: bool = False) -> dict:
    titles = existing_titles()
    pending = [s for s in predicted_question_specs() if s["title"] not in titles]
    if dry_run:
        return {
            "dry_run": True,
            "would_add": len(pending),
            "titles": [s["title"] for s in pending],
            "skip_existing": [s["title"] for s in predicted_question_specs() if s["title"] in titles],
        }
    ids: list[int] = []
    for spec in pending:
        card = learn.add_card(
            body=spec["body"],
            title=spec["title"],
            source="predicted_questions",
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
                tags=list(dict.fromkeys(list(fresh.get("tags") or []) + tags))[:16],
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

            council = cc.run_batch(min(len(ids) + 5, 40))
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
        "card_ids": ids,
        "pending_titles": [s["title"] for s in pending],
        "council": council,
        "stats": learn.stats(),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--sleep", type=float, default=0.25)
    args = p.parse_args()
    print(json.dumps(ingest(sleep_sec=args.sleep, dry_run=args.dry_run), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
