"""홈페이지 디자인 — 외부 사이트 웹 검색 → 위원회 토론 → 학습 카드.

  python scripts/homepage_design_web_research.py run
  python scripts/homepage_design_web_research.py run --max 2
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

# (query, 주제축, A안, B안, coupax 결론 가이드)
_DESIGN_QUERY_AXES: list[tuple[str, str, str, str, str]] = [
    (
        "landing page design trends 2025 dark mode typography",
        "랜딩 히어로",
        "다크 풀블리드 히어로",
        "라이트 카드형 히어로",
        "coupax 공개 홈은 히어로 다크+본문 라이트 혼합 유지.",
    ),
    (
        "dashboard UI design best practices spacing grid",
        "대시보드 밀도",
        "정보 밀집 테이블",
        "여백·카드 분리",
        "Agent Office·데이터 허브만 밀도 허용, 블로그는 여백 우선.",
    ),
    (
        "mobile navigation UX hamburger vs bottom tab bar",
        "모바일 네비",
        "햄버거 드로어",
        "하단 탭 바",
        "탭 5개 이상이면 스크롤 칩, 4개 이하면 2열 그리드.",
    ),
    (
        "web design color contrast WCAG accessibility CTA",
        "접근성 CTA",
        "고대비 단색 버튼",
        "아웃라인+보조 텍스트",
        "Primary CTA Copper, 대비 4.5:1 검증 후 style.css 고정.",
    ),
    (
        "design system CSS variables tokens documentation",
        "디자인 토큰",
        "JSON 토큰 단일 소스",
        "CSS :root 직접",
        "coupax는 :root 변수+Design_System_Spec 병행.",
    ),
    (
        "skeleton loading UI vs spinner UX research",
        "로딩 UX",
        "스켈레톤 플레이스홀더",
        "중앙 스피너",
        "카드·피드는 스켈레톤, 단발 액션은 스피너.",
    ),
    (
        "breadcrumb navigation UX deep site structure",
        "경로 표시",
        "breadcrumb 항상",
        "뒤로가기만",
        "3단계 이상 깊으면 breadcrumb.",
    ),
    (
        "form design label placement floating vs top",
        "폼 라벨",
        "상단 고정 라벨",
        "플로팅 라벨",
        "짧은 2~3필드는 플로팅, 복잡 폼은 상단 라벨.",
    ),
    (
        "sticky header shrink on scroll UX",
        "헤더 sticky",
        "스크롤 축소 sticky",
        "비고정 헤더",
        "긴 문서·블로그만 sticky+축소.",
    ),
    (
        "finance website trust design credibility layout",
        "금융 신뢰 UI",
        "데이터·수치 강조",
        "여백·카피 중심",
        "금융 블로그는 수치+출처, 과장 비주얼 금지.",
    ),
    (
        "responsive typography clamp fluid web design",
        "반응형 타이포",
        "clamp 유동 스케일",
        "고정 px 스텝",
        "제목 clamp, 본문 16px, 캡션 14px.",
    ),
    (
        "card UI shadow vs border dark theme",
        "다크 카드",
        "1px border",
        "soft shadow",
        "Midnight 배경은 border rgba(255,255,255,.08) 우선.",
    ),
    (
        "AI agent dashboard office UI design multi panel",
        "에이전트 사무실",
        "3열 패널 고정",
        "단일 피드 집중",
        "Agent Office는 좌 roster·중 피드·우 위키 3열 유지.",
    ),
    (
        "comment thread UI nested replies design",
        "댓글 스레드",
        "중첩 들여쓰기",
        "플랫 타임라인",
        "블로그 댓글은 1단 들여쓰기, 깊은 중첩 금지.",
    ),
    (
        "tab navigation design accessibility keyboard",
        "탭 네비",
        "언더라인 탭",
        "필드 세그먼트",
        "Office 유닛 전환은 세그먼트, 긴 문서는 언더라인.",
    ),
    (
        "microinteractions button feedback UX hover active",
        "버튼 피드백",
        "호버·액티브 모션",
        "색상 변화만",
        "motion-reduce 시 색만, Primary는 Copper 고정.",
    ),
    (
        "open graph social preview card design meta",
        "OG 카드",
        "대형 타이틀+로고",
        "미니멀 텍스트",
        "썸네일 1200×630, Midnight 배경+Copper 포인트.",
    ),
    (
        "table of contents sticky sidebar documentation",
        "문서 목차",
        "우측 sticky TOC",
        "본문 인라인 앵커",
        "긴 학습 카드·가이드만 sticky TOC.",
    ),
    (
        "search results page UI design filters layout",
        "검색 결과",
        "좌측 필터 패널",
        "상단 칩 필터",
        "모바일은 칩, 데스크톱 ETF 허브는 좌 패널.",
    ),
    (
        "knowledge graph network visualization UI dark",
        "지식 네트워크",
        "노드·엣지 그래프",
        "리스트+태그",
        "gemma 지식망은 그래프+리스트 토글.",
    ),
]

_NOISE_DOMAINS = frozenset(
    {
        "pinterest.com",
        "facebook.com",
        "instagram.com",
        "tiktok.com",
        "amazon.com",
        "coupang.com",
    }
)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def enabled() -> bool:
    return os.getenv("HOMEPAGE_DESIGN_WEB_RESEARCH_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def max_per_run() -> int:
    return max(1, min(3, int(os.getenv("HOMEPAGE_DESIGN_WEB_RESEARCH_MAX", "1") or "1")))


def _used_web_seeds() -> set[str]:
    import agent_office_homepage_design_learn as learn

    out: set[str] = set()
    for c in learn.load_store().get("cards") or []:
        if not isinstance(c, dict):
            continue
        seed = (c.get("catalog_seed") or "").strip()
        if seed.startswith("debate_web_"):
            out.add(seed)
    return out


def _pick_axes(*, count: int) -> list[tuple[str, str, str, str, str]]:
    used = _used_web_seeds()
    day = datetime.now().strftime("%Y%m%d")
    ranked: list[tuple[int, tuple[str, str, str, str, str]]] = []
    for i, row in enumerate(_DESIGN_QUERY_AXES):
        query, topic, a, b, guide = row
        penalty = 1000 if any(s.startswith(f"debate_web_{_slug(topic)}_") for s in used) else 0
        ranked.append((penalty + i, row))
    ranked.sort(key=lambda x: x[0])
    return [r[1] for r in ranked[:count]]


def _slug(text: str) -> str:
    t = re.sub(r"[^\w가-힣]+", "_", (text or "").strip().lower())
    t = re.sub(r"_+", "_", t).strip("_")
    return (t[:32] or "topic")


def _domain_ok(url: str) -> bool:
    try:
        host = (urlparse(url).netloc or "").lower().replace("www.", "")
    except ValueError:
        return False
    if not host:
        return False
    return not any(host == d or host.endswith("." + d) for d in _NOISE_DOMAINS)


def search_design_refs(query: str, *, limit: int = 5) -> list[dict]:
    import agent_office_web_search as ws

    if not ws.web_search_enabled():
        return []
    hits = ws.search_web(query, limit=limit)
    out: list[dict] = []
    seen: set[str] = set()
    for h in hits:
        url = (h.url or "").strip()
        if not url or not _domain_ok(url):
            continue
        key = urlparse(url).netloc.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "title": (h.title or "")[:120],
                "url": url[:500],
                "snippet": (h.snippet or "")[:400],
                "provider": h.provider or "web",
            }
        )
    return out


def _web_research_block(refs: list[dict], query: str) -> str:
    lines = [
        f"【웹 리서치 · { _now()[:10] }】 검색: {query[:80]}",
        "",
    ]
    if not refs:
        lines.append("외부 검색 결과 없음 — 내장 축·위원회 규칙만으로 토론.")
        return "\n".join(lines)
    for i, r in enumerate(refs[:5], 1):
        lines.append(f"{i}. {r.get('title') or '(제목 없음)'}")
        if r.get("snippet"):
            lines.append(f"   요약: {r['snippet'][:220]}")
        lines.append(f"   출처: {r.get('url')}")
        lines.append("")
    lines.append(
        "【coupax 적용】 위 레퍼런스는 브랜드 토큰(Midnight/Copper/Accent)과 "
        "8px 그리드·375px 터치·WCAG 대비를 깨지 않는 범위에서만 차용한다."
    )
    return "\n".join(lines).strip()


def spec_from_axis_and_refs(
    axis: tuple[str, str, str, str, str],
    refs: list[dict],
    *,
    variant: int = 0,
) -> dict:
    query, topic, opt_a, opt_b, guide = axis
    h = hashlib.sha1(
        f"{query}:{variant}:{datetime.now().strftime('%Y%m%d%H%M')}".encode()
    ).hexdigest()[:8]
    seed = f"debate_web_{_slug(topic)}_{h}"
    title = f"웹리서치·{topic} — {opt_a} vs {opt_b}"
    body = (
        _web_research_block(refs, query)
        + "\n\n"
        + f"【주제】 {topic}: {opt_a} vs {opt_b}\n"
        + f"【브랜드】 Midnight #0A1931 / Copper #B8860B / Accent #4f6ef7 유지.\n"
        + f"【결론 가이드】 {guide}\n"
        + f"【재사용】 catalog_seed={seed} · 외부 사이트 벤치마크 반영."
    )
    return {
        "catalog_seed": seed,
        "title": title,
        "category": "debate",
        "priority": 55,
        "body": body,
        "auto_generated": True,
        "web_research": True,
        "search_query": query,
        "refs": refs[:5],
        "axis_id": _slug(topic),
    }


def run_web_research_debate(*, max_n: int | None = None) -> dict:
    """웹 검색 1~N건 → 위원회 토론 → 확정 카드."""
    import homepage_design_council as hdc

    if not enabled():
        return {"ok": True, "skipped": True, "message": "웹 리서치 비활성"}

    n = max_n if max_n is not None else max_per_run()
    created: list[dict] = []
    errors: list[str] = []

    for axis in _pick_axes(count=n):
        query = axis[0]
        try:
            refs = search_design_refs(query, limit=5)
            spec = spec_from_axis_and_refs(axis, refs)
            seed = spec.get("catalog_seed") or ""
            import agent_office_homepage_design_learn as learn

            if learn.find_card_by_seed(seed):
                continue
            out = hdc.run_debate_for_spec(spec, auto_confirm=True)
            if out.get("created"):
                try:
                    import homepage_design_debate_generator as gen

                    gen.register_topic(spec, card_id=out.get("card_id"))
                except Exception:
                    pass
                created.append(
                    {
                        "seed": seed,
                        "title": spec.get("title"),
                        "card_id": out.get("card_id"),
                        "refs": len(refs),
                        "query": query[:60],
                    }
                )
        except Exception as e:
            errors.append(f"{query[:40]}: {e!s}")

    return {
        "ok": not errors or bool(created),
        "created": len(created),
        "items": created,
        "errors": errors[:5],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    run = sub.add_parser("run")
    run.add_argument("--max", type=int, default=0)
    probe = sub.add_parser("probe")
    probe.add_argument("--query", default=_DESIGN_QUERY_AXES[0][0])
    args = p.parse_args()
    if args.cmd == "run":
        mx = args.max or max_per_run()
        out = run_web_research_debate(max_n=mx)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if args.cmd == "probe":
        refs = search_design_refs(args.query, limit=5)
        print(json.dumps(refs, ensure_ascii=False, indent=2))
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
