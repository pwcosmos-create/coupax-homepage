"""홈페이지 디자인 — 토론 주제 자동 생성 (정적 6건 소진 후에도 계속).

  python scripts/homepage_design_debate_generator.py propose --limit 3
  python scripts/homepage_design_debate_generator.py run --max 1
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

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

REGISTRY_PATH = BOARD / "data" / "homepage_design_learning" / "debate_topic_registry.json"

# (id, 주제축, A안, B안, 결론 가이드 한 줄)
_DEBATE_AXES: list[tuple[str, str, str, str, str]] = [
    ("footer_sticky", "푸터", "하단 sticky CTA 바", "정적 푸터만", "전환 중심 랜딩만 sticky, 정보형 사이트는 정적."),
    ("logo_size", "헤더 로고", "큰 워드마크", "컴팩트 아이콘+텍스트", "모바일은 컴팩트, 데스크톱은 브랜드 여유 허용."),
    ("nav_hamburger", "모바일 네비", "햄버거 드로어", "하단 탭 바", "탭 3~4개면 하단 탭, 그 외 드로어."),
    ("search_prominent", "검색", "헤더 검색창 노출", "검색 아이콘만", "콘텐츠 허브는 노출, 단순 랜딩은 아이콘."),
    ("breadcrumb", "경로", "breadcrumb 항상 표시", "뒤로가기만", "3단계 이상 깊으면 breadcrumb."),
    ("sidebar_office", "사무실", "좌측 고정 roster", "상단 탭만", "3열 Office는 roster 고정 유지."),
    ("feed_density", "대화 로그", "메시지 카드 넓게", "타임라인 좁게", "긴 로그는 좁은 타임라인+요약."),
    ("form_labels", "폼", "라벨 상단", "플로팅 라벨", "짧은 2~3필드는 플로팅, 복잡 폼은 상단 라벨."),
    ("error_inline", "에러", "필드 인라인 에러", "폼 상단 요약", "접근성은 둘 다: 상단 요약+인라인."),
    ("loading_skeleton", "로딩", "스켈레톤 UI", "스피너만", "카드·피드는 스켈레톤, 단발 액션은 스피너."),
    ("image_hero_photo", "히어로", "실사 배경", "일러스트·그라데이션", "금융 신뢰는 실사/추상, 장식 과다 금지."),
    ("video_hero", "히어로", "짧은 루프 영상", "정적 이미지", "LCP·모바일 데이터 고려 시 정적 우선."),
    ("icon_style", "아이콘", "라인 아이콘", "필드 아이콘", "UI는 라인, 강조 배지만 필."),
    ("table_mobile", "표", "가로 스크롤", "카드형 행 변환", "ETF·데이터 표는 스크롤+sticky 열."),
    ("pagination", "목록", "무한 스크롤", "페이지네이션", "블로그·아카이브는 페이지네이션."),
    ("tag_chips", "태그", "채우기 색 칩", "테두리 칩", "다크 배경은 테두리 칩."),
    ("modal_vs_drawer", "패널", "모달 중앙", "하단 드로어", "모바일 편집·필터는 드로어."),
    ("toast_position", "알림", "하단 토스트", "상단 배너", "치명 오류만 상단, 성공은 하단 토스트."),
    ("dark_mode_toggle", "테마", "사용자 다크 토글", "시스템만", "공개 홈은 시스템+토글 선택 제공 검토."),
    ("font_serif_head", "타이포", "제목 세리프", "전부 산세리프", "coupax 기본은 산세리프, 프리미엄 섹션만 세리프."),
    ("link_underline", "링크", "본문 링크 밑줄", "색만 구분", "본문 링크는 밑줄 또는 명확한 색."),
    ("focus_ring", "포커스", "두꺼운 focus ring", "미세 outline", "키보드는 ring 2px Accent."),
    ("anim_hover", "모션", "호버 스케일", "호버 색만", "motion-reduce 시 색만."),
    ("grid_masonry", "그리드", "메이슨리", "균일 행 높이", "블로그 타일은 균일, 이미지 갤러리만 메이슨리."),
    ("price_color", "데이터", "상승 빨강", "상승 초록", "한국 시세 관습(빨강 상승) 유지 시 문서화."),
    ("chart_palette", "차트", "브랜드 Accent 차트", "중립 그레이", "장식 차트는 그레이, 강조 1색."),
    ("avatar_style", "아바타", "젬마 이모지", "이니셜 원", "Agent Office는 이모지 유지."),
    ("divider_style", "구분", "선 divider", "여백만", "섹션 간 여백 32px+ 우선."),
    ("sticky_header", "헤더", "스크롤 시 축소 sticky", "비고정", "긴 문서만 sticky+축소."),
    ("tooltip_density", "도움말", "아이콘 ? 툴팁", "인라인 설명", "금융 지표는 인라인 한 줄."),
    ("print_styles", "인쇄", "print CSS 제공", "미제공", "리포트·학습 카드 export는 print 고려."),
    ("code_block", "코드", "다크 코드 블록", "라이트 인라인", "문서 내 code는 라이트 배경."),
    ("ads_slot", "광고", "본문 중간 슬롯", "사이드만", "가독성 우선 사이드/하단."),
    ("cookie_banner", "동의", "하단 배너", "중앙 모달", "최소 방해 하단 슬림."),
    ("lang_switch", "다국어", "헤더 언어 토글", "푸터만", "2언어 이하면 헤더."),
    ("empty_state", "빈 상태", "일러스트+CTA", "텍스트만", "온보딩 필요 화면은 일러스트."),
    ("progress_steps", "진행", "스텝퍼 UI", "퍼센트 바", "3단계 이상 폼은 스텝퍼."),
    ("trust_badges", "신뢰", "로고 띠 배지", "한 줄 문구", "금융은 문구+최소 로고."),
    ("share_buttons", "공유", "상단 공유", "하단만", "콘텐츠 페이지 하단."),
    ("office_feed_order", "사무실 피드", "최신순 고정", "중요도 핀", "운영 알림만 핀, 나머지 최신순."),
    ("wiki_panel", "위키 패널", "우측 항상 열림", "접기 기본", "넓은 화면만 우측 위키, 모바일은 탭."),
    ("card_preview", "카드 미리보기", "호버 확장", "클릭 모달", "학습 카드 목록은 클릭 모달."),
    ("unit_tab_color", "유닛 탭", "색상 구분 탭", "아이콘만", "사주·키움·관상 등 유닛은 색+라벨."),
    ("login_gate", "로그인", "전면 모달", "인라인 배너", "Agent Office만 게이트, 공개 홈은 배너 없음."),
    ("data_refresh", "데이터 갱신", "자동 폴링 배지", "수동 새로고침", "실시간 피드만 폴링 표시."),
    ("seo_snippet", "SEO 스니펫", "200자 요약 카드", "키워드 리스트", "학습 카드 상단 200자+ 요약 필수."),
    ("mobile_bottom_bar", "모바일 바", "하단 액션 바", "FAB 하나", "2개 이상 액션은 바, 단일은 FAB."),
]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def auto_enabled() -> bool:
    return os.getenv("HOMEPAGE_DESIGN_DEBATE_AUTO", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def max_per_run() -> int:
    return max(1, min(5, int(os.getenv("HOMEPAGE_DESIGN_DEBATE_MAX_PER_RUN", "1") or "1")))


def _slug(text: str) -> str:
    t = re.sub(r"[^\w가-힣]+", "_", (text or "").strip().lower())
    t = re.sub(r"_+", "_", t).strip("_")
    return (t[:48] or "topic")


def used_seeds() -> set[str]:
    import agent_office_homepage_design_learn as learn

    out: set[str] = set()
    for c in learn.load_store().get("cards") or []:
        if not isinstance(c, dict):
            continue
        seed = (c.get("catalog_seed") or "").strip()
        if seed:
            out.add(seed)
    reg = load_registry()
    for row in reg.get("topics") or []:
        if isinstance(row, dict) and row.get("catalog_seed"):
            out.add(str(row["catalog_seed"]).strip())
    return out


def load_registry() -> dict:
    try:
        import json_store

        return json_store.load_json(REGISTRY_PATH, default={"topics": [], "updated_at": ""})
    except Exception:
        return {"topics": [], "updated_at": ""}


def save_registry(data: dict) -> None:
    import json_store

    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _now()
    json_store.save_json(REGISTRY_PATH, data)


def _build_body(axis: str, opt_a: str, opt_b: str, guide: str) -> str:
    return (
        f"【주제】 {axis}: {opt_a} vs {opt_b}\n"
        f"【브랜드】 Midnight / Copper / Accent 토큰 유지.\n"
        f"【재사용】 다음 홈페이지 제작 시 동일 축을 catalog_seed로 참조.\n"
        f"【결론 가이드】 {guide}"
    )


def spec_from_axis(axis_id: str, variant: int = 0) -> dict:
    row = next((r for r in _DEBATE_AXES if r[0] == axis_id), None)
    if not row:
        raise ValueError(f"unknown axis {axis_id}")
    _, topic, opt_a, opt_b, guide = row
    seed = f"debate_auto_{axis_id}" if variant <= 0 else f"debate_auto_{axis_id}_v{variant}"
    title = f"토론·{topic} — {opt_a} vs {opt_b}"
    if variant > 0:
        title += f" (v{variant + 1})"
    return {
        "catalog_seed": seed,
        "title": title,
        "category": "debate",
        "priority": 50 - variant,
        "body": _build_body(topic, opt_a, opt_b, guide),
        "auto_generated": True,
        "axis_id": axis_id,
        "variant": variant,
    }


def propose_next_specs(*, limit: int = 5) -> list[dict]:
    """아직 카드가 없는 다음 토론 스펙 (정적·자동 통합)."""
    from homepage_design_card_catalog import debate_specs

    used = used_seeds()
    out: list[dict] = []

    for spec in debate_specs():
        seed = (spec.get("catalog_seed") or "").strip()
        if not seed or seed in used:
            continue
        import agent_office_homepage_design_learn as learn

        existing = learn.find_card_by_seed(seed)
        if existing and existing.get("status") == "confirmed":
            used.add(seed)
            continue
        out.append(dict(spec))
        if len(out) >= limit:
            return out

    if not auto_enabled():
        return out

    # 축 × variant 순회
    for variant in range(0, 12):
        for axis_id, *_ in _DEBATE_AXES:
            seed = f"debate_auto_{axis_id}" if variant <= 0 else f"debate_auto_{axis_id}_v{variant}"
            if seed in used:
                continue
            out.append(spec_from_axis(axis_id, variant))
            if len(out) >= limit:
                return out

    # 풀 소진 시: 날짜+축 해시로 신규 조합 주제
    day = datetime.now().strftime("%Y%m%d")
    for n in range(200):
        axis = _DEBATE_AXES[n % len(_DEBATE_AXES)]
        axis_id = axis[0]
        h = hashlib.sha1(f"{day}:{n}:{axis_id}".encode()).hexdigest()[:6]
        seed = f"debate_auto_{axis_id}_{h}"
        if seed in used:
            continue
        spec = spec_from_axis(axis_id, 0)
        spec["catalog_seed"] = seed
        spec["title"] = f"토론·{axis[1]} 재검토 ({h}) — {axis[2]} vs {axis[3]}"
        out.append(spec)
        if len(out) >= limit:
            return out
    return out


def register_topic(spec: dict, *, card_id: int | None = None) -> None:
    data = load_registry()
    topics = [t for t in data.get("topics") or [] if isinstance(t, dict)]
    seed = (spec.get("catalog_seed") or "").strip()
    row = {
        "catalog_seed": seed,
        "title": spec.get("title"),
        "ts": _now(),
        "card_id": card_id,
        "auto": bool(spec.get("auto_generated")),
    }
    topics = [t for t in topics if t.get("catalog_seed") != seed]
    topics.append(row)
    data["topics"] = topics[-500:]
    save_registry(data)


def list_recent_topics(*, limit: int = 12) -> list[dict]:
    reg = load_registry()
    topics = [t for t in reg.get("topics") or [] if isinstance(t, dict)]
    topics.sort(key=lambda t: t.get("ts") or "", reverse=True)
    return topics[:limit]


def run_auto_topics(*, max_n: int | None = None) -> dict:
    """신규 주제 생성 → 위원회 토론 → 확정 (1~max_n건)."""
    import homepage_design_council as hdc

    n = max_n if max_n is not None else max_per_run()
    created: list[dict] = []
    errors: list[str] = []

    for spec in propose_next_specs(limit=n):
        try:
            out = hdc.run_debate_for_spec(spec, auto_confirm=True)
            if out.get("created"):
                register_topic(spec, card_id=out.get("card_id"))
                created.append(
                    {
                        "seed": spec.get("catalog_seed"),
                        "title": spec.get("title"),
                        "card_id": out.get("card_id"),
                    }
                )
        except Exception as e:
            errors.append(f"{spec.get('catalog_seed')}: {e!s}")

    return {
        "ok": not errors or bool(created),
        "created": len(created),
        "items": created,
        "errors": errors[:5],
        "pending_specs": len(propose_next_specs(limit=20)),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    prop = sub.add_parser("propose")
    prop.add_argument("--limit", type=int, default=5)
    run = sub.add_parser("run")
    run.add_argument("--max", type=int, default=0)
    lst = sub.add_parser("list")
    args = p.parse_args()
    if args.cmd == "propose":
        print(json.dumps(propose_next_specs(limit=args.limit), ensure_ascii=False, indent=2))
    elif args.cmd == "run":
        mx = args.max or max_per_run()
        print(json.dumps(run_auto_topics(max_n=mx), ensure_ascii=False, indent=2))
    elif args.cmd == "list":
        print(json.dumps(list_recent_topics(), ensure_ascii=False, indent=2))
    else:
        p.print_help()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
