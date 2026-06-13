"""
홈페이지 디자인 학습 카드 — 재사용 플레이북 축적.

  python scripts/agent_office_homepage_design_learn.py add --title "..." --text "..."
  python scripts/seed_homepage_design_cards.py --add
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import json_store

BOARD = Path(__file__).resolve().parents[1]
DATA_DIR = BOARD / "data" / "homepage_design_learning"
CARDS_PATH = DATA_DIR / "cards.json"
PACK_PATH = DATA_DIR / "homepage_design_knowledge_pack.json"
CURSOR_MD = BOARD.parent / "CURSOR_HOMEPAGE_DESIGN_LEARN.md"
DIVISION = "homepage-design"
MAX_CARDS = 800

_PII_PATTERNS = (
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    re.compile(r"01[0-9]-?\d{3,4}-?\d{4}"),
    re.compile(r"\d{6}-?\d{7}"),
)

_TAG_KW = (
    "토큰",
    "타이포",
    "레이아웃",
    "그리드",
    "반응형",
    "375",
    "컴포넌트",
    "CTA",
    "Copper",
    "Midnight",
    "Accent",
    "style.css",
    "핸드오프",
    "접근성",
    "WCAG",
    "Agent Office",
    "토론",
    "플레이북",
    "카드",
    "히어로",
    "네비",
    "푸터",
)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _redact_pii(text: str) -> str:
    out = text or ""
    for rx in _PII_PATTERNS:
        out = rx.sub("[제거됨]", out)
    return out


def _default_store() -> dict:
    return {"updated_at": "", "cards": []}


def load_store() -> dict:
    try:
        data = json_store.load_json(CARDS_PATH, default=_default_store())
    except json_store.JsonStoreError:
        return _default_store()
    if not isinstance(data, dict):
        return _default_store()
    data.setdefault("cards", [])
    return data


def save_store(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _now()
    cards = data.get("cards")
    if isinstance(cards, list) and len(cards) > MAX_CARDS:
        data["cards"] = cards[-MAX_CARDS:]
    json_store.save_json(CARDS_PATH, data)
    render_cursor_md(data)


def _extract_tags(text: str) -> list[str]:
    blob = (text or "")[:2000]
    tags = [k for k in _TAG_KW if k in blob]
    if "토론" in blob or "debate" in blob.lower():
        tags.append("토론")
    if "플레이북" in blob:
        tags.append("플레이북")
    return list(dict.fromkeys(tags))[:12]


def _summary(text: str, n: int = 160) -> str:
    t = re.sub(r"\s+", " ", (text or "")).strip()
    return t[:n] + ("…" if len(t) > n else "")


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").strip())[:120]


def existing_titles() -> set[str]:
    return {
        normalize_title(c.get("title") or "")
        for c in load_store().get("cards") or []
        if isinstance(c, dict) and normalize_title(c.get("title") or "")
    }


def title_taken(title: str) -> bool:
    return normalize_title(title) in existing_titles()


def find_card_by_seed(catalog_seed: str) -> dict | None:
    seed = (catalog_seed or "").strip()
    if not seed:
        return None
    for c in load_store().get("cards") or []:
        if isinstance(c, dict) and (c.get("catalog_seed") or "").strip() == seed:
            return c
    return None


def ensure_unique_title(title: str, taken: set[str] | None = None) -> str:
    titles = taken if taken is not None else existing_titles()
    base = normalize_title(title)
    if not base or base not in titles:
        return base
    for n in range(2, 30):
        cand = normalize_title(f"{base} · v{n}")
        if cand not in titles:
            return cand
    return normalize_title(f"{base} · {_now()}")


def revise_card(
    card_id: int,
    *,
    body: str | None = None,
    title: str | None = None,
    catalog_seed: str | None = None,
    reconfirm: bool = True,
) -> dict | None:
    store = load_store()
    target: dict | None = None
    for c in store.get("cards") or []:
        if isinstance(c, dict) and c.get("id") == card_id:
            target = c
            break
    if not target:
        return None
    new_body = _redact_pii((body if body is not None else target.get("body") or "").strip())
    if len(new_body) < 30:
        raise ValueError("학습 본문이 너무 짧습니다 (30자 이상).")
    if title is not None:
        new_title = normalize_title(title)
        if new_title:
            taken = {
                normalize_title(c.get("title") or "")
                for c in store.get("cards") or []
                if isinstance(c, dict)
                and c.get("id") != card_id
                and normalize_title(c.get("title") or "")
            }
            if new_title in taken:
                raise ValueError("다른 카드와 제목이 겹칩니다.")
            target["title"] = new_title
    if catalog_seed is not None:
        seed = str(catalog_seed).strip()[:120]
        if seed:
            other = find_card_by_seed(seed)
            if other and other.get("id") != card_id:
                raise ValueError(f"catalog_seed '{seed}'는 카드 #{other.get('id')}에 사용 중.")
            target["catalog_seed"] = seed
    target["body"] = new_body[:24000]
    target["summary"] = _summary(new_body)
    target["tags"] = _extract_tags(new_body)
    target["ts"] = _now()
    target["revised_at"] = _now()
    save_store(store)
    if target.get("status") == "confirmed" and reconfirm:
        export_pack()
        try:
            import agent_office_wiki_store

            agent_office_wiki_store.save_design_card_to_knowledge(target)
        except Exception:
            pass
    return target


def add_card(
    *,
    body: str,
    title: str = "",
    source: str = "paste",
    note: str = "",
    catalog_seed: str = "",
    use_council: bool | None = None,
    revise_if_seed_exists: bool = True,
    category: str = "",
) -> dict:
    seed = (catalog_seed or "").strip()
    if revise_if_seed_exists and seed:
        existing = find_card_by_seed(seed)
        if existing and isinstance(existing.get("id"), int):
            revised = revise_card(
                int(existing["id"]),
                body=body,
                title=title or None,
                catalog_seed=seed,
                reconfirm=existing.get("status") == "confirmed",
            )
            if revised:
                revised["_revised"] = True
                return revised

    body = _redact_pii((body or "").strip())
    title = normalize_title(title)
    if title and title_taken(title):
        raise ValueError("동일 제목의 카드가 이미 있습니다.")

    contributors: list[dict] = []
    if use_council is None:
        use_council = source in ("council_debate", "catalog_seed")
    if use_council:
        try:
            import homepage_design_council as hdc

            if hdc.council_enabled():
                body, contributors = hdc.enrich_body_with_panel(
                    title or seed,
                    body,
                    catalog_seed=seed,
                )
        except Exception:
            pass

    if len(body) < 30:
        raise ValueError("학습 본문이 너무 짧습니다 (30자 이상).")

    store = load_store()
    cards = store.get("cards") or []
    next_id = 1
    for c in cards:
        if isinstance(c, dict) and isinstance(c.get("id"), int):
            next_id = max(next_id, c["id"] + 1)

    if not title:
        title = normalize_title(_summary(body, 50))
    title = ensure_unique_title(title)
    if title_taken(title):
        raise ValueError("동일 제목의 카드가 이미 있습니다.")

    card = {
        "id": next_id,
        "ts": _now(),
        "title": title,
        "body": body[:24000],
        "summary": _summary(body),
        "source": source[:40],
        "note": (note or "")[:300],
        "tags": _extract_tags(body),
        "status": "pending",
    }
    if catalog_seed:
        card["catalog_seed"] = seed[:120]
    if category:
        card["category"] = category[:40]
    if contributors:
        card["council"] = contributors
        card["council_agents"] = [x.get("agent_id") for x in contributors if x.get("agent_id")]

    cards.append(card)
    store["cards"] = cards
    save_store(store)
    try:
        import agent_office_log

        if contributors:
            agent_office_log.append_message(
                from_id="design_council",
                kind="task",
                text=f"[디자인 토론 카드 #{next_id}] {title}\n{_summary(body, 200)}",
                division=DIVISION,
            )
        else:
            agent_office_log.append_message(
                from_id="design_curator",
                kind="task",
                text=f"[디자인 카드 #{next_id}] {title}\n{_summary(body, 120)}",
                division=DIVISION,
            )
    except Exception:
        pass
    return card


def confirm_card(card_id: int, *, export_pack_now: bool = True) -> dict | None:
    store = load_store()
    for c in store.get("cards") or []:
        if isinstance(c, dict) and c.get("id") == card_id:
            c["status"] = "confirmed"
            c["confirmed_at"] = _now()
            save_store(store)
            if export_pack_now:
                export_pack()
            wiki_id = None
            try:
                import agent_office_wiki_store

                wiki_row = agent_office_wiki_store.save_design_card_to_knowledge(c)
                if wiki_row:
                    wiki_id = wiki_row.get("id")
                    c["wiki_id"] = wiki_id
                    store2 = load_store()
                    for c2 in store2.get("cards") or []:
                        if isinstance(c2, dict) and c2.get("id") == card_id:
                            c2["wiki_id"] = wiki_id
                            break
                    save_store(store2)
            except Exception:
                pass
            try:
                import agent_office_log

                msg = f"[확정 #{card_id}] {c.get('title', '')} — pack·재사용 플레이북 반영"
                if wiki_id:
                    msg += f" · {wiki_id}"
                agent_office_log.append_message(
                    from_id="design_curator",
                    kind="conclusion",
                    text=msg,
                    division=DIVISION,
                )
            except Exception:
                pass
            return c
    return None


def delete_card(card_id: int) -> bool:
    store = load_store()
    before = len(store.get("cards") or [])
    store["cards"] = [
        c for c in store.get("cards") or []
        if not (isinstance(c, dict) and c.get("id") == card_id)
    ]
    if len(store["cards"]) == before:
        return False
    save_store(store)
    return True


def stats() -> dict:
    cards = [c for c in load_store().get("cards") or [] if isinstance(c, dict)]
    pending = sum(1 for c in cards if c.get("status") == "pending")
    confirmed = sum(1 for c in cards if c.get("status") == "confirmed")
    debate = sum(1 for c in cards if (c.get("category") or "") == "debate" or "토론" in (c.get("title") or ""))
    return {
        "total": len(cards),
        "pending": pending,
        "confirmed": confirmed,
        "debate_cards": debate,
        "updated_at": load_store().get("updated_at") or "",
    }


def list_cards(*, status: str | None = None, limit: int = 50) -> list[dict]:
    cards = [c for c in load_store().get("cards") or [] if isinstance(c, dict)]
    if status:
        cards = [c for c in cards if c.get("status") == status]
    cards.sort(key=lambda c: c.get("id") or 0, reverse=True)
    return cards[:limit]


def export_pack() -> dict:
    confirmed = [
        c for c in load_store().get("cards") or []
        if isinstance(c, dict) and c.get("status") == "confirmed"
    ]
    pack = {
        "version": 1,
        "purpose": "homepage_design_reusable_playbook",
        "exported_at": _now(),
        "card_count": len(confirmed),
        "cards": [
            {
                "id": c.get("id"),
                "title": c.get("title"),
                "summary": c.get("summary"),
                "tags": c.get("tags") or [],
                "catalog_seed": c.get("catalog_seed"),
                "category": c.get("category"),
                "body": (c.get("body") or "")[:8000],
            }
            for c in confirmed
        ],
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PACK_PATH.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    render_cursor_md()
    return pack


def render_cursor_md(data: dict | None = None) -> str:
    data = data or load_store()
    confirmed = [
        c for c in data.get("cards") or []
        if isinstance(c, dict) and c.get("status") == "confirmed"
    ]
    lines = [
        "# Cursor — 홈페이지 디자인 학습부",
        "",
        f"갱신: {data.get('updated_at') or '—'} · 확정 {len(confirmed)}건",
        "",
        "다음 홈페이지 제작 시 재사용할 디자인·핸드오프 카드 요약.",
        "",
    ]
    for c in confirmed[-50:]:
        lines.append(f"## #{c.get('id')} {c.get('title', '')}")
        lines.append("")
        lines.append((c.get("summary") or "")[:500])
        if c.get("tags"):
            lines.append("")
            lines.append("태그: " + ", ".join(c.get("tags") or []))
        lines.append("")
    CURSOR_MD.write_text("\n".join(lines), encoding="utf-8")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    add = sub.add_parser("add")
    add.add_argument("--title", default="")
    add.add_argument("--text", required=True)
    lst = sub.add_parser("list")
    sub.add_parser("export")
    args = p.parse_args()
    if args.cmd == "add":
        c = add_card(body=args.text, title=args.title)
        print(json.dumps(c, ensure_ascii=False, indent=2))
    elif args.cmd == "list":
        print(json.dumps(list_cards(), ensure_ascii=False, indent=2))
    elif args.cmd == "export":
        print(json.dumps(export_pack(), ensure_ascii=False, indent=2))
    else:
        p.print_help()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
