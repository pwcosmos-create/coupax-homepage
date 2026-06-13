#!/usr/bin/env python3
"""사주 학습 카드 전수 점검 — 제목 누락·위원회·본문 품질·구조."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_saju_learn as learn  # noqa: E402
import saju_knowledge_tier as tier  # noqa: E402
import saju_reading_engine as eng  # noqa: E402
from saju_card_reverify_enrich import _has_rich_structure, _strip_footer  # noqa: E402
from saju_reading_display import body_has_quality_issues  # noqa: E402

ABSOLUTE_CLAIMS = re.compile(r"반드시|100%|무조건|절대\s*길|절대\s*흉|이혼\s*확정|파산\s*확정")

DEEP = [
    f"심층·[{i}] {t}"
    for i, t in enumerate(
        [
            "인사·성향",
            "사주팔자",
            "오행 균형",
            "십신·격국",
            "용신·기신",
            "대운·세운",
            "재물",
            "연애·관계",
            "직업",
            "실천·주의",
        ],
        1,
    )
]

CATALOG = {
    "십신": [f"변수·십신 {n}" for n in "비견 겁재 식신 상관 편재 정재 편관 정관 편인 정인".split()],
    "오행": [f"변수·오행 {e}" for e in "목 화 토 금 수".split()],
    "격국": [
        "변수·격 건록격",
        "변수·격 월겁격",
        "변수·격 비겁격",
        "변수·격 식신격",
        "변수·격 상관격",
        "변수·격 편재격",
        "변수·격 정재격",
        "변수·격 편관격",
        "변수·격 정관격",
        "변수·격 편인격",
        "변수·격 정인격",
        "변수·격 칠살격",
        "변수·격 종격(從格) 참고",
        "변수·격 잡격·무격 참고",
    ],
    "천간(일간)": [f"변수·천간 {n}" for n in "갑목 을목 병화 정화 무토 기토 경금 신금 임수 계수".split()],
    "지지": [f"변수·지지 {n}" for n in "자수 축토 인목 묘목 진토 사화 오화 미토 신금 유금 술토 해수".split()],
    "신살": [f"변수·신살 {n}" for n in "역마 도화 화개 문창 천을".split()],
    "띠": [f"변수·띠 {n}" for n in "쥐 소 호랑이 토끼 용 뱀 말 양 원숭이 닭 개 돼지".split()],
}


def body_len(card: dict) -> int:
    return len(_strip_footer(card.get("body") or ""))


def main() -> int:
    store = learn.load_store()
    cards = [c for c in store.get("cards") or [] if isinstance(c, dict)]
    confirmed = [c for c in cards if c.get("status") == "confirmed"]
    by_title: dict[str, list[dict]] = defaultdict(list)
    for c in cards:
        by_title[(c.get("title") or "").strip()].append(c)

    print("=== 사주 학습 카드 전수 점검 ===")
    print(f"전체 {len(cards)} · 확정 {len(confirmed)} · 대기 {len(cards) - len(confirmed)}")

    # 위원회
    council = Counter((c.get("council_status") or "none").strip() or "none" for c in confirmed)
    pass_n = sum(1 for c in confirmed if tier.is_council_pass(c))
    fail_n = sum(1 for c in confirmed if tier.is_council_fail(c))
    print(f"\n[위원회] PASS {pass_n} · FAIL {fail_n} · 미검 {council.get('none', 0)} · 기타 {sum(council.values()) - pass_n - fail_n - council.get('none', 0)}")

    # 제목 중복
    dupes = {t: cs for t, cs in by_title.items() if t and len(cs) > 1}
    if dupes:
        print(f"\n[오류] 제목 중복 {len(dupes)}건")
        for t, cs in sorted(dupes.items())[:15]:
            print(f"  {t} -> ids {[c.get('id') for c in cs]}")
    else:
        print("\n[OK] 제목 중복 없음")

    # 카탈로그 누락
    print("\n[필수 제목 카탈로그]")
    titles = {(c.get("title") or "").strip() for c in confirmed}
    all_miss: list[str] = []
    for label, want in CATALOG.items():
        miss = [t for t in want if t not in titles]
        all_miss.extend(miss)
        st = "OK" if not miss else f"누락 {len(miss)}"
        print(f"  {label}: {len(want) - len(miss)}/{len(want)} {st}")
        for m in miss:
            print(f"    - {m}")

    # 심층 10섹션
    print("\n[심층 10섹션]")
    deep_miss = []
    for t in DEEP:
        hit = [c for c in confirmed if (c.get("title") or "").strip() == t]
        if not hit:
            deep_miss.append(t)
            print(f"  MISSING  {t}")
        else:
            ln = body_len(hit[0])
            flag = " (짧음)" if ln < 800 else ""
            print(f"  OK       {t} ({ln}자){flag}")
    if not deep_miss:
        print("  -> 10섹션 모두 존재")

    # 버킷
    inv = eng.pass_inventory()
    print("\n[버킷 PASS 수]")
    for k, n in sorted(inv.get("buckets", {}).items(), key=lambda x: -x[1]):
        print(f"  {k}: {n}")

    # 본문 길이
    lens = [body_len(c) for c in confirmed]
    if lens:
        under400 = sum(1 for x in lens if x < 400)
        under800 = sum(1 for x in lens if x < 800)
        print(f"\n[본문 길이] min={min(lens)} max={max(lens)} avg={sum(lens)//len(lens)} median={sorted(lens)[len(lens)//2]}")
        print(f"  400자 미만 {under400} · 800자 미만 {under800}")

    # 품질 이슈
    q_issues: list[tuple] = []
    short: list[tuple] = []
    no_footer: list[tuple] = []
    absolute: list[tuple] = []
    thin: list[tuple] = []
    no_wiki: list[tuple] = []
    not_rich: list[tuple] = []

    for c in confirmed:
        cid = c.get("id")
        title = (c.get("title") or "")[:50]
        body = c.get("body") or ""
        bl = body_len(c)
        if bl < 400:
            short.append((cid, title, bl))
        qi = body_has_quality_issues(body)
        if qi:
            q_issues.append((cid, title, qi))
        if "본 내용은 명리" not in body:
            no_footer.append((cid, title))
        if ABSOLUTE_CLAIMS.search(body):
            absolute.append((cid, title))
        if body == (c.get("summary") or "")[: len(body)] and bl < 120:
            thin.append((cid, title, bl))
        if not (c.get("wiki_id") or "").strip():
            no_wiki.append((cid, title))
        if not _has_rich_structure(body):
            not_rich.append((cid, title, bl))

    def show(label: str, rows: list, limit: int = 20) -> None:
        print(f"\n[{label}] {len(rows)}건")
        for row in rows[:limit]:
            print(f"  #{row[0]} {row[1]}" + (f" ({row[2]})" if len(row) > 2 else ""))
        if len(rows) > limit:
            print(f"  ... 외 {len(rows) - limit}건")

    show("품질 이슈(empty_bracket·broken_phrase 등)", q_issues)
    show("본문 400자 미만", short)
    show("면책 문구 없음", no_footer)
    show("단정 표현 의심", absolute)
    show("요약=본문 단편", thin)
    show("wiki_id 없음", no_wiki)
    show("구조 미풍부(_has_rich_structure=False)", not_rich, 25)

    # 버킷별 짧은 카드
    print("\n[버킷별 400자 미만]")
    bucket_short: dict[str, int] = defaultdict(int)
    for c in confirmed:
        if body_len(c) >= 400:
            continue
        b = eng.card_bucket(c)
        bucket_short[b] += 1
    for b, n in sorted(bucket_short.items(), key=lambda x: -x[1]):
        print(f"  {b}: {n}")

    # 요약
    err = len(dupes) + len(all_miss) + len(deep_miss)
    warn = len(q_issues) + len(short) + len(absolute) + len(thin)
    print("\n=== 요약 ===")
    print(f"  오류(중복·누락): {err}건")
    print(f"  품질 경고: {warn}건 (짧은본문·이슈·단정·단편)")
    print(f"  구조 보강 대상: {len(not_rich)}건")
    print(f"  PASS 풀: {pass_n}장 (풀 운영 200+: {'OK' if pass_n >= 200 else '부족'})")
    return 1 if err else 0


if __name__ == "__main__":
    raise SystemExit(main())
