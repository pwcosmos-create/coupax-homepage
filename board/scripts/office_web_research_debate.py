"""사업부 공통 — 웹 검색 → 위원회 토론 → 학습 카드.

  python scripts/office_web_research_debate.py run --unit gwansang-learn
  python scripts/office_web_research_debate.py run --unit all --max 2
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
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

from office_web_research_units import UnitWebResearchConfig, all_unit_ids, get_config

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


def _slug(text: str) -> str:
    t = re.sub(r"[^\w가-힣]+", "_", (text or "").strip().lower())
    t = re.sub(r"_+", "_", t).strip("_")
    return (t[:32] or "topic")


def _load_learn(module_name: str):
    return importlib.import_module(module_name)


def enabled(cfg: UnitWebResearchConfig) -> bool:
    key = f"{cfg.env_prefix}_WEB_RESEARCH_ENABLED"
    return os.getenv(key, os.getenv("OFFICE_WEB_RESEARCH_ENABLED", "1")).strip().lower() in (
        "1",
        "true",
        "yes",
    )


def max_per_run(cfg: UnitWebResearchConfig) -> int:
    key = f"{cfg.env_prefix}_WEB_RESEARCH_MAX"
    try:
        n = int(os.getenv(key, os.getenv("OFFICE_WEB_RESEARCH_MAX", "1")) or "1")
    except ValueError:
        n = 1
    return max(1, min(3, n))


def council_enabled(cfg: UnitWebResearchConfig) -> bool:
    key = f"{cfg.env_prefix}_WEB_COUNCIL_ENABLED"
    return os.getenv(key, os.getenv("OFFICE_WEB_COUNCIL_ENABLED", "1")).strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _domain_ok(url: str) -> bool:
    try:
        host = (urlparse(url).netloc or "").lower().replace("www.", "")
    except ValueError:
        return False
    if not host:
        return False
    return not any(host == d or host.endswith("." + d) for d in _NOISE_DOMAINS)


def search_refs(query: str, *, limit: int = 5) -> list[dict]:
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


def _used_web_seeds(cfg: UnitWebResearchConfig) -> set[str]:
    learn = _load_learn(cfg.learn_module)
    out: set[str] = set()
    for c in learn.load_store().get("cards") or []:
        if not isinstance(c, dict):
            continue
        seed = (c.get("catalog_seed") or "").strip()
        if seed.startswith("debate_web_"):
            out.add(seed)
    return out


def _pick_axes(cfg: UnitWebResearchConfig, *, count: int) -> list[tuple[str, str, str, str, str]]:
    used = _used_web_seeds(cfg)
    ranked: list[tuple[int, tuple[str, str, str, str, str]]] = []
    for i, row in enumerate(cfg.query_axes):
        query, topic, *_ = row
        penalty = 1000 if any(s.startswith(f"debate_web_{_slug(topic)}_") for s in used) else 0
        ranked.append((penalty + i, row))
    ranked.sort(key=lambda x: x[0])
    return [r[1] for r in ranked[:count]]


def _web_research_block(refs: list[dict], query: str, cfg: UnitWebResearchConfig) -> str:
    lines = [f"【웹 리서치 · {_now()[:10]}】 검색: {query[:80]}", ""]
    if not refs:
        lines.append("외부 검색 결과 없음 — 내장 축·위원회 규칙만으로 토론.")
    else:
        for i, r in enumerate(refs[:5], 1):
            lines.append(f"{i}. {r.get('title') or '(제목 없음)'}")
            if r.get("snippet"):
                lines.append(f"   요약: {r['snippet'][:220]}")
            lines.append(f"   출처: {r.get('url')}")
            lines.append("")
    lines.append(f"【coupax 적용】 {cfg.apply_note}")
    return "\n".join(lines).strip()


def _stance_for_topic(
    cfg: UnitWebResearchConfig, agent_id: str, topic_title: str, seed: str
) -> str:
    base = cfg.role_stances.get(agent_id, "도메인 일관성·사용자 안전 관점.")
    if seed.startswith("debate_web_"):
        if "researcher" in agent_id or agent_id.endswith("_seo"):
            return base + " 【웹 리서치】 출처 스니펫은 카드에만 보관, 과장 차용 금지."
    return base


def enrich_body_with_panel(
    cfg: UnitWebResearchConfig,
    topic: str,
    base_body: str,
    *,
    catalog_seed: str = "",
) -> tuple[str, list[dict]]:
    contributors: list[dict] = []
    parts = [base_body.strip(), "", "——— 위원회 토론 ———", ""]
    for aid, role in cfg.debate_panel:
        stance = _stance_for_topic(cfg, aid, topic, catalog_seed)
        contributors.append({"agent_id": aid, "role": role, "summary": stance[:200]})
        parts.append(f"【{role} · {aid}】")
        parts.append(stance)
        parts.append("")
    parts.append(
        f"【합의 초안】 위 관점을 반영해 확정하고, catalog_seed({catalog_seed or '—'})로 재사용한다."
    )
    return "\n".join(parts).strip(), contributors


def spec_from_axis_and_refs(
    cfg: UnitWebResearchConfig,
    axis: tuple[str, str, str, str, str],
    refs: list[dict],
) -> dict:
    query, topic, opt_a, opt_b, guide = axis
    h = hashlib.sha1(f"{cfg.unit_id}:{query}:{datetime.now().strftime('%Y%m%d%H%M')}".encode()).hexdigest()[:8]
    seed = f"debate_web_{_slug(topic)}_{h}"
    title = f"웹리서치·{topic} — {opt_a} vs {opt_b}"
    body = (
        _web_research_block(refs, query, cfg)
        + "\n\n"
        + f"【주제】 {topic}: {opt_a} vs {opt_b}\n"
        + f"【결론 가이드】 {guide}\n"
        + f"【재사용】 catalog_seed={seed}"
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


def _add_card(learn, spec: dict, enriched: str):
    import inspect

    sig = inspect.signature(learn.add_card)
    params = sig.parameters
    kwargs = {
        "body": enriched,
        "title": spec.get("title") or "",
        "source": "council_debate",
        "catalog_seed": spec.get("catalog_seed") or "",
    }
    if "category" in params:
        kwargs["category"] = "debate"
    if "use_council" in params:
        kwargs["use_council"] = False
    if "revise_if_seed_exists" in params:
        kwargs["revise_if_seed_exists"] = False
    if "compose" in params:
        kwargs["compose"] = False
    return learn.add_card(**kwargs)


def _revise_card(learn, card_id: int, spec: dict, enriched: str):
    kwargs = dict(
        card_id=card_id,
        body=enriched,
        title=spec.get("title") or "",
        catalog_seed=spec.get("catalog_seed") or "",
        reconfirm=False,
    )
    return learn.revise_card(**kwargs)


def run_debate_for_spec(
    cfg: UnitWebResearchConfig, spec: dict, *, auto_confirm: bool = True
) -> dict:
    learn = _load_learn(cfg.learn_module)
    if not council_enabled(cfg):
        return {"ok": True, "skipped": True, "message": "위원회 비활성"}

    seed = (spec.get("catalog_seed") or "").strip()
    if not seed:
        return {"ok": False, "created": 0, "message": "catalog_seed 없음"}

    title = spec.get("title") or seed
    body = spec.get("body") or ""
    enriched, panel = enrich_body_with_panel(cfg, title, body, catalog_seed=seed)

    find_seed = getattr(learn, "find_card_by_seed", None)
    existing = find_seed(seed) if callable(find_seed) else None
    if not existing and getattr(learn, "title_taken", None):
        if learn.title_taken(title):
            return {"ok": False, "created": 0, "message": "동일 제목 존재", "seed": seed}

    if existing and isinstance(existing.get("id"), int):
        if existing.get("status") == "confirmed" and existing.get("council_agents"):
            return {
                "ok": True,
                "created": 0,
                "seed": seed,
                "card_id": existing.get("id"),
                "message": "이미 확정됨",
            }
        revise = getattr(learn, "revise_card", None)
        if callable(revise):
            card = revise(int(existing["id"]), body=enriched, title=title, catalog_seed=seed, reconfirm=False)
        else:
            card = existing
    else:
        card = _add_card(learn, spec, enriched)

    if card:
        store = learn.load_store()
        for c in store.get("cards") or []:
            if isinstance(c, dict) and c.get("id") == card.get("id"):
                c["council"] = panel
                c["council_agents"] = [p["agent_id"] for p in panel]
                c["category"] = "debate"
                c["catalog_seed"] = seed
                if spec.get("auto_generated"):
                    c["auto_generated"] = True
                if spec.get("web_research"):
                    c["web_research"] = True
                if spec.get("refs"):
                    c["refs"] = spec.get("refs")
        learn.save_store(store)

    confirmed = None
    if auto_confirm and card and isinstance(card.get("id"), int):
        confirmed = learn.confirm_card(int(card["id"]))

    try:
        import agent_office_log

        tag = "자동" if spec.get("auto_generated") else "정적"
        agent_office_log.append_message(
            from_id=cfg.log_from_id,
            kind="conclusion",
            text=f"[웹리서치 토론·{tag}] {title} · 패널 {len(panel)}명",
            division=cfg.division,
        )
    except Exception:
        pass

    return {
        "ok": True,
        "created": 1,
        "seed": seed,
        "card_id": (confirmed or card or {}).get("id"),
        "panel": len(panel),
        "unit": cfg.unit_id,
    }


def run_web_research_debate(
    unit_id: str, *, max_n: int | None = None
) -> dict:
    cfg = get_config(unit_id)
    if not cfg:
        return {"ok": False, "error": f"unknown unit {unit_id}"}
    if not enabled(cfg):
        return {"ok": True, "skipped": True, "message": "웹 리서치 비활성", "unit": unit_id}

    learn = _load_learn(cfg.learn_module)
    n = max_n if max_n is not None else max_per_run(cfg)
    created: list[dict] = []
    errors: list[str] = []

    for axis in _pick_axes(cfg, count=n):
        query = axis[0]
        try:
            refs = search_refs(query, limit=5)
            spec = spec_from_axis_and_refs(cfg, axis, refs)
            seed = spec.get("catalog_seed") or ""
            find_seed = getattr(learn, "find_card_by_seed", None)
            if callable(find_seed) and find_seed(seed):
                continue
            out = run_debate_for_spec(cfg, spec, auto_confirm=True)
            if out.get("created"):
                created.append(
                    {
                        "seed": seed,
                        "title": spec.get("title"),
                        "card_id": out.get("card_id"),
                        "refs": len(refs),
                        "query": query[:60],
                        "unit": unit_id,
                    }
                )
        except Exception as e:
            errors.append(f"{query[:40]}: {e!s}")

    stats = learn.stats() if hasattr(learn, "stats") else {}
    return {
        "ok": not errors or bool(created),
        "unit": unit_id,
        "created": len(created),
        "items": created,
        "errors": errors[:5],
        "stats": stats,
    }


def run_all_units(*, max_n: int = 1) -> dict:
    results: list[dict] = []
    total = 0
    for uid in all_unit_ids():
        if uid == "homepage-design":
            try:
                import homepage_design_web_research as hdwr

                out = hdwr.run_web_research_debate(max_n=max_n)
            except Exception as e:
                out = run_web_research_debate(uid, max_n=max_n)
                out["fallback_error"] = str(e)
        else:
            out = run_web_research_debate(uid, max_n=max_n)
        total += int(out.get("created") or 0)
        results.append(out)
    return {"ok": True, "total_created": total, "units": results}


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    run = sub.add_parser("run")
    run.add_argument("--unit", default="all")
    run.add_argument("--max", type=int, default=0)
    args = p.parse_args()
    if args.cmd == "run":
        mx = args.max or 1
        if args.unit == "all":
            out = run_all_units(max_n=mx)
        else:
            out = run_web_research_debate(args.unit, max_n=mx)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    p.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
