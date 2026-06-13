"""홈페이지 디자인 위원회 — 토론 주제별 다중 젬마 관점 합성.

  python scripts/homepage_design_council.py run
  python scripts/homepage_design_council.py run --seed debate_cta_copper_vs_accent
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

DIVISION = "homepage-design"

# (agent_id, 역할 라벨)
DEBATE_PANEL: list[tuple[str, str]] = [
    ("design_token", "토큰·색"),
    ("design_typography", "타이포"),
    ("design_layout", "레이아웃"),
    ("design_component", "컴포넌트"),
    ("design_a11y", "접근성"),
    ("design_handoff", "핸드오프"),
    ("design_ux_writer", "UX 카피"),
    ("design_researcher", "레퍼런스"),
]

_ROLE_STANCE: dict[str, str] = {
    "design_token": "브랜드 토큰 일관성을 최우선. CSS 변수로 고정하고 섹션마다 임의 hex 금지.",
    "design_typography": "가독성·계층. 제목 clamp, 본문 16px·line-height 1.6 권장.",
    "design_layout": "8px 그리드·반응형 브레이크포인트. 모바일 375px 터치 44px.",
    "design_component": "버튼·카드·폼 패턴 재사용. Primary CTA는 페이지당 하나.",
    "design_a11y": "대비 4.5:1, focus, aria-label. 장식만 색으로 정보 전달 금지.",
    "design_handoff": "결정은 style.css·:root 변수. 인라인 style 최소.",
    "design_ux_writer": "짧은 동사 CTA, placeholder 예시, 에러는 다음 행동 포함.",
    "design_researcher": "동종 랜딩·대시보드 벤치마크 후 coupax 토큰에 맞게 축소 적용.",
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def council_enabled() -> bool:
    return os.getenv("HOMEPAGE_DESIGN_COUNCIL_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _stance_for_topic(agent_id: str, topic_title: str, seed: str) -> str:
    base = _ROLE_STANCE.get(agent_id, "사용자·브랜드 일관성 관점.")
    t = (topic_title or "").lower()
    if "cta" in seed or "copper" in t:
        if agent_id == "design_token":
            return "Primary CTA는 Deep Copper, 링크·보조는 Accent #4f6ef7 분리."
        if agent_id == "design_component":
            return ".btn-primary=Copper, .btn-gray=보조. 한 화면 Primary 1개."
    if "mobile" in seed or "탭" in topic_title:
        if agent_id == "design_layout":
            return "탭 5개↑: 가로 스크롤+sticky. 4개↓: 2열 그리드·min-height 44px."
    if "hero" in seed or "히어로" in topic_title:
        if agent_id == "design_layout":
            return "B2C 랜딩: 히어로 여백·단일 메시지. 데이터 허브만 밀도 허용."
    if "typography" in seed or "15px" in topic_title or "font" in seed:
        if agent_id == "design_typography":
            return "공개 장문 16px, 대시보드 메타 14–15px. 모바일 최소 15px."
    if "footer" in seed or "sticky" in topic_title:
        if agent_id == "design_layout":
            return "sticky는 전환 목적 섹션만. 본문 가독성 해치지 않게."
    if "a11y" in seed or "focus" in seed or "tooltip" in seed:
        if agent_id == "design_a11y":
            return "키보드·스크린리더 경로를 시각 스타일과 분리하지 말 것."
    if "loading" in seed or "skeleton" in seed:
        if agent_id == "design_component":
            return "레이아웃 시프트 없는 스켈레톤 우선."
    if seed.startswith("debate_web_"):
        if agent_id == "design_researcher":
            return "【웹 리서치】 본문 출처·스니펫을 coupax 토큰·그리드에 맞게 축소·재해석. 원문 URL은 카드에만 보관."
        if agent_id == "design_token":
            return "외부 레퍼런스 색은 Midnight/Copper/Accent로 치환, 임의 hex 금지."
    return base


def enrich_body_with_panel(
    topic: str,
    base_body: str,
    *,
    catalog_seed: str = "",
) -> tuple[str, list[dict]]:
    """규칙 기반 패널 코멘트를 본문에 붙임 (Gemini 없이도 동작)."""
    contributors: list[dict] = []
    parts = [base_body.strip(), "", "——— 위원회 토론 ———", ""]
    for aid, role in DEBATE_PANEL:
        stance = _stance_for_topic(aid, topic, catalog_seed)
        contributors.append({"agent_id": aid, "role": role, "summary": stance[:200]})
        parts.append(f"【{role} · {aid}】")
        parts.append(stance)
        parts.append("")
    parts.append(
        f"【합의 초안 · design_curator】 위 관점을 반영해 style.css 변수·컴포넌트 클래스로 "
        f"고정하고, 다음 사이트 제작 시 동일 catalog_seed({catalog_seed or '—'})를 참조한다."
    )
    return "\n".join(parts).strip(), contributors


def next_debate_spec() -> dict | None:
    """다음 1건: 정적 미완료 → 자동 생성 대기열."""
    import homepage_design_debate_generator as gen

    pending = gen.propose_next_specs(limit=1)
    return pending[0] if pending else None


def run_debate_for_spec(spec: dict, *, auto_confirm: bool = True) -> dict:
    """주어진 스펙으로 위원회 토론 카드 1장."""
    import agent_office_homepage_design_learn as learn

    if not council_enabled():
        return {"ok": True, "skipped": True, "message": "위원회 비활성"}

    seed = (spec.get("catalog_seed") or "").strip()
    if not seed:
        return {"ok": False, "created": 0, "message": "catalog_seed 없음"}

    title = spec.get("title") or seed
    body = spec.get("body") or ""
    enriched, panel = enrich_body_with_panel(title, body, catalog_seed=seed)

    existing = learn.find_card_by_seed(seed)
    if existing and isinstance(existing.get("id"), int):
        if existing.get("status") == "confirmed" and existing.get("council_agents"):
            return {
                "ok": True,
                "created": 0,
                "seed": seed,
                "card_id": existing.get("id"),
                "message": "이미 확정됨",
            }
        card = learn.revise_card(
            int(existing["id"]),
            body=enriched,
            title=title,
            catalog_seed=seed,
            reconfirm=False,
        )
    else:
        card = learn.add_card(
            body=enriched,
            title=title,
            source="council_debate",
            catalog_seed=seed,
            category="debate",
            use_council=False,
            revise_if_seed_exists=False,
        )

    if card:
        store = learn.load_store()
        for c in store.get("cards") or []:
            if isinstance(c, dict) and c.get("id") == card.get("id"):
                c["council"] = panel
                c["council_agents"] = [p["agent_id"] for p in panel]
                c["category"] = "debate"
                if spec.get("auto_generated"):
                    c["auto_generated"] = True
        learn.save_store(store)

    confirmed = None
    if auto_confirm and card and isinstance(card.get("id"), int):
        confirmed = learn.confirm_card(int(card["id"]))

    try:
        import agent_office_log

        tag = "자동" if spec.get("auto_generated") else "정적"
        agent_office_log.append_message(
            from_id="design_council",
            kind="conclusion",
            text=f"[디자인 토론·{tag}] {title} · 패널 {len(panel)}명",
            division=DIVISION,
        )
    except Exception:
        pass

    try:
        import homepage_design_debate_generator as gen

        gen.register_topic(spec, card_id=(confirmed or card or {}).get("id"))
    except Exception:
        pass

    return {
        "ok": True,
        "created": 1,
        "seed": seed,
        "card_id": (confirmed or card or {}).get("id"),
        "panel": len(panel),
        "auto": bool(spec.get("auto_generated")),
    }


def run_one_debate(*, auto_confirm: bool = True) -> dict:
    if not council_enabled():
        return {"ok": True, "skipped": True, "message": "위원회 비활성"}

    spec = next_debate_spec()
    if not spec:
        return {"ok": True, "created": 0, "message": "토론할 미완료 주제 없음"}

    return run_debate_for_spec(spec, auto_confirm=auto_confirm)


def run_debate_cycle(*, max_auto: int | None = None) -> dict:
    """주기 job·cron: 최대 N건 연속 토론(자동 주제 포함)."""
    import homepage_design_debate_generator as gen

    n = max_auto if max_auto is not None else gen.max_per_run()
    if gen.auto_enabled() and n > 0:
        return gen.run_auto_topics(max_n=n)
    return run_one_debate()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", default="", help="특정 debate catalog_seed")
    p.add_argument("--no-confirm", action="store_true")
    args = p.parse_args()
    if args.seed:
        from homepage_design_card_catalog import debate_specs

        spec = next((s for s in debate_specs() if s.get("catalog_seed") == args.seed), None)
        if not spec:
            print('{"ok": false, "error": "unknown seed"}')
            return 1
        import agent_office_homepage_design_learn as learn

        body, panel = enrich_body_with_panel(spec["title"], spec["body"], catalog_seed=args.seed)
        card = learn.add_card(
            body=body,
            title=spec["title"],
            source="council_debate",
            catalog_seed=args.seed,
            category="debate",
            use_council=False,
        )
        if not args.no_confirm and card.get("id"):
            learn.confirm_card(int(card["id"]))
        print('{"ok": true}')
        return 0
    import homepage_design_debate_generator as gen

    out = gen.run_auto_topics(max_n=gen.max_per_run()) if gen.auto_enabled() else run_one_debate(
        auto_confirm=not args.no_confirm
    )
    import json

    print(json.dumps(out, ensure_ascii=False))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
