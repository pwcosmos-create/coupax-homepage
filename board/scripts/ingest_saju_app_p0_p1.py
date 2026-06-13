#!/usr/bin/env python3
"""saju-v2 앱 제목 규칙용 P0·P1 카드 일괄 제작·확정·위원회 검증.

  python scripts/ingest_saju_app_p0_p1.py --dry-run
  python scripts/ingest_saju_app_p0_p1.py
  python scripts/ingest_saju_app_p0_p1.py --rename-huisin-only
"""
from __future__ import annotations

import argparse
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


def _gyeok_specs() -> list[dict]:
    data = {
        "건록격": "월지 비견(比肩)이 격을 이룸. 자립·동료·경쟁·고집. 식상·재성으로 현실화.",
        "월겁격": "월지 겁재(劫財). 추진·파트너십·지분·계약 명시. 재성 약하면 현실화 필요.",
        "식신격": "월지 식신(食神). 생산·표현·교육·온화 창업. 과다 시 산만·규칙.",
        "상관격": "월지 상관(傷官). 돌파·마케팅·기술·말. 과다 시 규칙·집중 이슈.",
        "편재격": "월지 편재(偏財). 사업·프로젝트·변동 수입. 종목·대박 단정 금지.",
        "정재격": "월지 정재(正財). 월급·저축·가계·안정 수입.",
        "정관격": "월지 정관(正官). 조직·규율·책임·명분. 승진·시기 단정 금지.",
        "편인격": "월지 편인(偏印). 독학·직관·특수 지식·영성.",
        "정인격": "월지 정인(正印). 학습·자격·보호·전통.",
    }
    return [
        {
            "title": f"변수·격 {name}",
            "body": _seed("격국", text),
            "card_style": "variable",
            "tags": ["격국", "격", "십신", "명리"],
        }
        for name, text in data.items()
    ]


def _un_specs(prefix: str, label: str) -> list[dict]:
    els = ("목", "화", "토", "금", "수")
    hints = {
        "목": "성장·인연·학습·유연. 과다 시 고집·산만.",
        "화": "표현·활동·명예·감정. 과다 시 조급·번아웃.",
        "토": "안정·중재·재정·가정. 과다 시 우유부단·지체.",
        "금": "원칙·규율·결단·재물. 과다 시 냉정·완고.",
        "수": "지혜·이동·학습·직관. 과다 시 불안·생각 과다.",
    }
    return [
        {
            "title": f"변수·운 {label} {el}",
            "body": _seed(
                label,
                f"{el}行 {label} 방향. {hints[el]} 학파·신강신약에 따라 달라질 수 있음.",
            ),
            "card_style": "variable",
            "tags": [label, el, "용신", "오행", "대운", "세운"],
        }
        for el in els
    ]


def _stem_specs() -> list[dict]:
    stems = {
        "갑목": "큰 나무·개척·성장. 인성·재성과 조합.",
        "을목": "풀·유연·조율·인연. 겁재 과다 시 고집.",
        "병화": "태양·밝음·리더·표현. 수·목으로 조절.",
        "정화": "촛불·섬세·직관·예술. 토·목 보완.",
        "무토": "산·중재·신뢰·안정. 목·화로 활력.",
        "기토": "밭·실무·저축·배려. 수·목 보완.",
        "경금": "쇠·원칙·결단·규율. 화·수로 유연.",
        "신금": "보석·정밀·심미·기술. 수·토 보완.",
        "임수": "큰 물·지혜·이동·학습. 목·화로 방향.",
        "계수": "이슬·직관·기록·연구. 목·토 보완.",
    }
    return [
        {
            "title": f"변수·천간 {name}",
            "body": _seed("천간", text),
            "card_style": "variable",
            "tags": ["천간", "일간", name[:2], "오행"],
        }
        for name, text in stems.items()
    ]


def _branch_rel_specs() -> list[dict]:
    data = {
        "삼합": "寅午戌·申子辰·亥卯未·巳酉丑 — 인연·협력·결합. 겉 합 속 충 양면.",
        "방합": "寅卯辰·巳午未·申酉戌·亥子丑 — 계절·방위 기운.",
        "육합": "子丑·寅亥·卯戌·辰酉·巳申·午未 — 인연·결합·배우자궁.",
        "충": "子午·卯酉·寅申·巳亥·辰戌·丑未 — 변동·이동·관계 갈등.",
        "형": "寅巳申·丑戌未·子卯 — 압박·자기갈등·건강 리듬.",
        "파": "子酉·丑辰·寅亥·卯午·巳申·未戌 — 깨짐·재시작·재정비.",
        "해": "子未·丑午·寅巳·卯辰·申亥·酉戌 — 방해·소모·마찰.",
        "원진": "子未·丑午·寅酉·卯申·辰亥·巳戌 — 거리감·오해.",
        "반합": "子丑·午未 등 반쪽 합 — 미완성 인연·협력 키워드.",
    }
    return [
        {
            "title": f"변수·지지관계 {name}",
            "body": _seed("지지 관계", text + " 두 지지가 사주·운에서 성립할 때만."),
            "card_style": "variable",
            "tags": ["지지", "합", "충", "연애", "관계"],
        }
        for name, text in data.items()
    ]


def _ilju_specs() -> list[dict]:
    missing = ("을목", "기토", "경금", "신금", "임수")
    hints = {
        "을목": "유연·조율·인연. 겁재 과다 시 고집 주의.",
        "기토": "실무·배려·저축. 수·목 보완.",
        "경금": "원칙·결단·규율. 화·수로 유연.",
        "신금": "정밀·기술·심미. 수·토 보완.",
        "임수": "지혜·이동·학습. 목·화로 방향.",
    }
    return [
        {
            "title": f"해석·{name} 일주 성향",
            "body": _seed(
                "일주",
                f"{name} 일주(日柱) 성향. {hints[name]} 일지·월지·십신과 함께 본다.",
            ),
            "card_style": "interpretive",
            "tags": ["일주", "일간", name[:2], "성향", "인사"],
        }
        for name in missing
    ]


def _frame_specs() -> list[dict]:
    frames = [
        (
            "무료 사주 풀이 글 구조",
            "인사→팔자→오행→십신·격→용신→대운·세운→테마 1~2→실천→면책. 절당 2~4문장.",
            ["사주", "팔자", "무료", "풀이", "실천"],
        ),
        (
            "오행 상생·상극·균형",
            "목화토금수 상생상극. 과다=강점+과잉, 부족=보완 습관. 일간 생극 연결.",
            ["오행", "목", "화", "토", "금", "수", "상생"],
        ),
        (
            "격국·십신 핵심 프레임",
            "월지 격국과 두드러진 십신 2~3개로 큰 틀. 한 십신만으로 길흉 단정 금지.",
            ["격국", "격", "십신", "월지"],
        ),
        (
            "용신·기신 선정 원칙",
            "억부·통관·조후 학파별 상이. 용신=보완, 기신=조절. 「반드시」 단정 금지.",
            ["용신", "기신", "희신", "명리"],
        ),
        (
            "대운·세운·월운 읽는 순서",
            "대운 10년→세운 1년→월운 1~2문장. 충·합은 변동 키워드만.",
            ["대운", "세운", "월운", "운"],
        ),
    ]
    return [
        {
            "title": title,
            "body": _seed("프레임", detail),
            "card_style": "variable",
            "tags": tags,
        }
        for title, detail, tags in frames
    ]


def _interp_extra() -> list[dict]:
    extras = [
        (
            "해석·신강·신약 생활 패턴",
            "신강=자립·추진, 신약=협업·보완. 격·용신과 분리. 생활 습관만.",
            ["신강", "신약", "용신", "실천"],
        ),
        (
            "해석·희신·구신 활용",
            "희신=보완 방향, 구신=조절. 학파별 상이. 「반드시」 단정 금지.",
            ["희신", "용신", "기신", "구신"],
        ),
        (
            "해석·월운 12개월 흐름",
            "월운은 월별 십신 키워드 1~2문장. 세운·대운과 함께 보라고 안내.",
            ["월운", "세운", "대운", "운"],
        ),
    ]
    return [
        {
            "title": title,
            "body": _seed("해석", detail),
            "card_style": "interpretive",
            "tags": tags,
        }
        for title, detail, tags in extras
    ]


def all_specs() -> list[dict]:
    specs: list[dict] = []
    specs.extend(_gyeok_specs())
    specs.extend(_un_specs("용신", "용신"))
    specs.extend(_un_specs("기신", "기신"))
    specs.extend(_stem_specs())
    specs.extend(_branch_rel_specs())
    specs.extend(_ilju_specs())
    specs.extend(_frame_specs())
    specs.extend(_interp_extra())
    return specs


def cleanup_dup_huisin() -> int:
    """변수·운 희신 ○행·구형 변수·희신 ○행 중복 제거 (행당 최저 id 유지)."""
    groups: dict[str, list[dict]] = {}
    for c in learn.load_store().get("cards") or []:
        if not isinstance(c, dict):
            continue
        t = (c.get("title") or "").strip()
        el = ""
        if t.startswith("변수·운 희신 "):
            el = t.split()[-1]
        elif t.startswith("변수·희신 "):
            el = t.replace("변수·희신", "").strip()
        if el:
            groups.setdefault(el, []).append(c)
    removed = 0
    for el, items in groups.items():
        items.sort(key=lambda x: int(x.get("id") or 0))
        keep = items[0]
        for dup in items[1:]:
            cid = dup.get("id")
            if isinstance(cid, int) and cid != keep.get("id") and learn.delete_card(cid):
                removed += 1
    if removed:
        learn.export_pack()
    return removed


def fix_frame_titles() -> int:
    """해석· 접두가 붙은 공통 프레임 카드 제목을 앱 규격으로 복원."""
    frames = {
        "해석·무료 사주 풀이 글 구조": "무료 사주 풀이 글 구조",
        "해석·오행 상생·상극·균형": "오행 상생·상극·균형",
        "해석·격국·십신 핵심 프레임": "격국·십신 핵심 프레임",
        "해석·용신·기신 선정 원칙": "용신·기신 선정 원칙",
        "해석·대운·세운·월운 읽는 순서": "대운·세운·월운 읽는 순서",
    }
    n = 0
    for c in learn.load_store().get("cards") or []:
        if not isinstance(c, dict):
            continue
        t = (c.get("title") or "").strip()
        new = frames.get(t)
        if not new:
            continue
        cid = c.get("id")
        if isinstance(cid, int):
            learn.update_confirmed_card(cid, title=new)
            n += 1
    if n:
        learn.export_pack()
    return n


def existing_titles() -> set[str]:
    return {(c.get("title") or "").strip() for c in learn.list_cards(limit=2000)}


def rename_huisin() -> int:
    n = 0
    for c in learn.load_store().get("cards") or []:
        if not isinstance(c, dict):
            continue
        t = (c.get("title") or "").strip()
        if not t.startswith("변수·희신 ") or t.startswith("변수·운 희신"):
            continue
        el = t.replace("변수·희신", "").strip()
        new_title = f"변수·운 희신 {el}"
        cid = c.get("id")
        if not isinstance(cid, int):
            continue
        learn.update_confirmed_card(cid, title=new_title)
        try:
            import agent_office_wiki_store as ws

            fresh = learn.get_card(cid)
            if fresh:
                ws.save_saju_card_to_knowledge(fresh)
        except Exception:
            pass
        n += 1
    if n:
        learn.export_pack()
    return n


def ingest(*, sleep_sec: float = 0.3, dry_run: bool = False) -> dict:
    titles = existing_titles()
    pending = [s for s in all_specs() if s["title"] not in titles]
    added = 0
    ids: list[int] = []
    if dry_run:
        return {"dry_run": True, "would_add": len(pending), "titles": [s["title"] for s in pending]}
    for spec in pending:
        card = learn.add_card(
            body=spec["body"],
            title=spec["title"],
            source="app_p0_p1",
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
        added += 1
        if sleep_sec > 0:
            time.sleep(sleep_sec)
    if added:
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
    st = learn.stats()
    return {"added": added, "pending_titles": len(pending), "council": council, "stats": st}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--rename-huisin-only", action="store_true")
    p.add_argument("--sleep", type=float, default=0.3)
    args = p.parse_args()
    if args.rename_huisin_only:
        print({"renamed_huisin": rename_huisin()})
        return 0
    renamed = rename_huisin()
    removed = cleanup_dup_huisin()
    fixed = fix_frame_titles()
    result = ingest(sleep_sec=args.sleep, dry_run=args.dry_run)
    result["renamed_huisin"] = renamed
    result["fixed_frame_titles"] = fixed
    result["removed_dup_huisin"] = removed
    import json

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
