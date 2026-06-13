"""
사주풀이 텍스트만 젬마24 학습부에 축적 (saju-v2 웹 무연동).

  python scripts/agent_office_saju_learn.py add --title "..." --text "..."
  python scripts/agent_office_saju_learn.py list
  python scripts/agent_office_saju_learn.py export
  python scripts/agent_office_saju_learn.py import-feedback /path/to/feedback.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path

import json_store

BOARD = Path(__file__).resolve().parents[1]
DATA_DIR = BOARD / "data" / "saju_learning"
CARDS_PATH = DATA_DIR / "cards.json"
PACK_PATH = DATA_DIR / "saju_knowledge_pack.json"
CURSOR_MD = BOARD.parent / "CURSOR_SAJU_LEARN.md"
MAX_CARDS = 500

# 위원회 검증 — 새 카드·병합·배포 시 절대 덮어쓰지 않음
COUNCIL_PRESERVE_FIELDS = (
    "council_status",
    "council_at",
    "council_pass",
    "council_report",
    "council_note",
)

_PII_PATTERNS = (
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    re.compile(r"01[0-9]-?\d{3,4}-?\d{4}"),
    re.compile(r"\d{6}-?\d{7}"),
    re.compile(r"(19|20)\d{2}\s*년?\s*\d{1,2}\s*월?\s*\d{1,2}\s*일?"),
)

_TAG_KW = (
    "오행",
    "십신",
    "일주",
    "대운",
    "세운",
    "용신",
    "기신",
    "격국",
    "신살",
    "재성",
    "관성",
    "식상",
    "비겁",
    "커버드콜",
    "명리",
    "사주",
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


def has_council_verification(card: dict | None) -> bool:
    if not isinstance(card, dict):
        return False
    return bool((card.get("council_at") or "").strip())


def preserve_council_fields(card: dict, donor: dict | None) -> dict:
    """donor에 검증 기록이 있으면 card에 유지(병합·덮어쓰기 방지)."""
    out = dict(card)
    if not isinstance(donor, dict) or not has_council_verification(donor):
        return out
    for key in COUNCIL_PRESERVE_FIELDS:
        if key in donor:
            out[key] = donor[key]
    return out


def merge_stores(
    base: dict,
    incoming: dict,
    *,
    add_new_only: bool = False,
) -> dict:
    """
    base(보통 서버)를 기준으로 incoming(로컬 신규) 병합.
    동일 id는 base의 위원회 검증 필드를 절대 지우지 않음.
    """
    base_cards = [
        c for c in (base.get("cards") or []) if isinstance(c, dict)
    ]
    by_id: dict[int, dict] = {}
    for c in base_cards:
        cid = c.get("id")
        if isinstance(cid, int):
            by_id[cid] = dict(c)

    next_id = max(by_id.keys(), default=0) + 1
    titles = {(c.get("title") or "").strip() for c in by_id.values() if c.get("title")}

    for inc in incoming.get("cards") or []:
        if not isinstance(inc, dict):
            continue
        cid = inc.get("id")
        title = (inc.get("title") or "").strip()

        if isinstance(cid, int) and cid in by_id:
            if add_new_only:
                continue
            merged = dict(inc)
            merged = preserve_council_fields(merged, by_id[cid])
            if (by_id[cid].get("wiki_id") or "") and not merged.get("wiki_id"):
                merged["wiki_id"] = by_id[cid]["wiki_id"]
            if by_id[cid].get("confirmed_at") and not merged.get("confirmed_at"):
                merged["confirmed_at"] = by_id[cid]["confirmed_at"]
            by_id[cid] = merged
            continue

        if title and title in titles:
            continue

        new_card = dict(inc)
        if not isinstance(new_card.get("id"), int) or new_card["id"] in by_id:
            new_card["id"] = next_id
            next_id += 1
        by_id[int(new_card["id"])] = new_card
        if title:
            titles.add(title)

    out = dict(base)
    out["cards"] = sorted(by_id.values(), key=lambda c: int(c.get("id") or 0))
    return out


def import_merge_cards_json(path: Path, *, add_new_only: bool = True) -> dict:
    """로컬 cards.json을 서버 store에 병합(위원회 검증 유지)."""
    incoming = json_store.load_json(path, default=_default_store())
    store = load_store()
    merged = merge_stores(store, incoming, add_new_only=add_new_only)
    save_store(merged)
    return {
        "before": len(store.get("cards") or []),
        "after": len(merged.get("cards") or []),
        "added": len(merged.get("cards") or []) - len(store.get("cards") or []),
        "council_preserved": sum(
            1 for c in merged.get("cards") or [] if has_council_verification(c)
        ),
    }


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
        verified = [c for c in cards if isinstance(c, dict) and has_council_verification(c)]
        rest = [c for c in cards if isinstance(c, dict) and not has_council_verification(c)]
        slots = max(0, MAX_CARDS - len(verified))
        data["cards"] = verified + rest[-slots:]
    json_store.save_json(CARDS_PATH, data)
    render_cursor_md(data)


def _extract_tags(text: str) -> list[str]:
    blob = (text or "")[:2000]
    tags = [k for k in _TAG_KW if k in blob]
    pillars = re.findall(r"[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]", blob)
    if pillars:
        tags.append("명식기호")
    return list(dict.fromkeys(tags))[:12]


def _summary(text: str, n: int = 160) -> str:
    t = re.sub(r"\s+", " ", (text or "")).strip()
    return t[:n] + ("…" if len(t) > n else "")


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").strip())[:120]


def title_taken(title: str) -> bool:
    t = normalize_title(title)
    return any(
        normalize_title(c.get("title") or "") == t
        for c in load_store().get("cards") or []
        if isinstance(c, dict)
    )


def find_card_by_seed(catalog_seed: str) -> dict | None:
    seed = (catalog_seed or "").strip()
    if not seed:
        return None
    for c in load_store().get("cards") or []:
        if isinstance(c, dict) and (c.get("catalog_seed") or "").strip() == seed:
            return c
    return None


def revise_card(
    card_id: int,
    *,
    body: str | None = None,
    title: str | None = None,
    catalog_seed: str | None = None,
    reconfirm: bool = True,
) -> dict | None:
    store = load_store()
    target = next(
        (c for c in store.get("cards") or [] if isinstance(c, dict) and c.get("id") == card_id),
        None,
    )
    if not target:
        return None
    if body is not None:
        target["body"] = _redact_pii((body or "").strip())[:24000]
        target["summary"] = _summary(target["body"])
        target["tags"] = _extract_tags(target["body"])
    if title is not None and normalize_title(title):
        if title_taken(title) and normalize_title(title) != normalize_title(target.get("title") or ""):
            raise ValueError("동일 제목의 카드가 이미 있습니다.")
        target["title"] = normalize_title(title)
    if catalog_seed is not None:
        target["catalog_seed"] = str(catalog_seed).strip()[:120]
    target["revised_at"] = _now()
    save_store(store)
    return target


def add_card(
    *,
    body: str,
    title: str = "",
    source: str = "paste",
    note: str = "",
    compose: bool | None = None,
    card_style: str | None = None,
    catalog_seed: str = "",
    category: str = "",
    use_council: bool = True,
    revise_if_seed_exists: bool = True,
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
                reconfirm=False,
            )
            if revised:
                revised["_revised"] = True
                return revised

    raw_body = _redact_pii((body or "").strip())
    if len(raw_body) < 8:
        raise ValueError("풀이 초안이 너무 짧습니다 (8자 이상).")

    title_in = normalize_title(title)
    if title_in and title_taken(title_in):
        raise ValueError("동일 제목의 카드가 이미 있습니다.")

    use_compose = compose
    if use_compose is None:
        try:
            import saju_card_reverify_enrich as enrich

            use_compose = enrich.compose_on_create_enabled()
        except Exception:
            use_compose = False

    if use_compose:
        try:
            import saju_card_reverify_enrich as enrich

            pkg = enrich.compose_new_card(
                title_in,
                raw_body,
                at_create=True,
                card_style=card_style,
                source=source,
            )
            title_in = pkg["title"]
            raw_body = pkg["body"]
            tags = pkg["tags"]
            summary = pkg["summary"]
            card_style = pkg.get("card_style") or card_style
        except Exception:
            use_compose = False

    if not use_compose:
        if len(raw_body) < 40:
            raise ValueError("풀이 본문이 너무 짧습니다 (40자 이상).")
        title_in = title_in or _summary(raw_body, 50)
        tags = _extract_tags(raw_body)
        summary = _summary(raw_body)
        if not card_style:
            try:
                import saju_card_reverify_enrich as enrich

                card_style = enrich.detect_card_style(
                    title_in, raw_body, source=source
                )
            except Exception:
                card_style = ""

    store = load_store()
    cards = store.get("cards") or []
    next_id = 1
    for c in cards:
        if isinstance(c, dict) and isinstance(c.get("id"), int):
            next_id = max(next_id, c["id"] + 1)

    card = {
        "id": next_id,
        "ts": _now(),
        "title": title_in,
        "body": raw_body[:24000],
        "summary": summary,
        "source": source[:40],
        "note": (note or "")[:300],
        "tags": tags,
        "status": "pending",
        "composed_at": _now() if use_compose else "",
        "card_style": (card_style or "")[:20],
    }
    if seed:
        card["catalog_seed"] = seed[:120]
    if category:
        card["category"] = category[:40]
    cards.append(card)
    store["cards"] = cards
    save_store(store)
    try:
        import agent_office_log

        agent_office_log.append_message(
            from_id="saju_reader",
            kind="task",
            text=f"[학습 카드 #{next_id}] {title_in}\n{_summary(raw_body, 120)}",
            division="saju-learn",
        )
    except Exception:
        pass
    return card


def confirm_card(card_id: int, *, export_pack_now: bool = True) -> dict | None:
    store = load_store()
    for c in store.get("cards") or []:
        if isinstance(c, dict) and c.get("id") == card_id:
            try:
                import saju_card_reverify_enrich as enrich

                if enrich.compose_on_create_enabled() and not (
                    c.get("composed_at") or ""
                ).strip():
                    enrich.compose_pending_card(card_id)
                    store = load_store()
                    for c2 in store.get("cards") or []:
                        if isinstance(c2, dict) and c2.get("id") == card_id:
                            c = c2
                            break
            except Exception:
                pass
            c["status"] = "confirmed"
            c["confirmed_at"] = _now()
            save_store(store)
            if export_pack_now:
                export_pack()
            wiki_id = None
            try:
                import agent_office_wiki_store

                wiki_row = agent_office_wiki_store.save_saju_card_to_knowledge(c)
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

                msg = f"[확정 #{card_id}] {c.get('title', '')} — pack 반영"
                if wiki_id:
                    msg += f" · 젬마기억 {wiki_id}"
                agent_office_log.append_message(
                    from_id="saju_curator",
                    kind="conclusion",
                    text=msg,
                    division="saju-learn",
                )
            except Exception:
                pass
            trigger_council_verify(card_id, mode="realtime")
            return get_card(card_id) or c
    return None


def trigger_council_verify(card_id: int, *, mode: str = "realtime") -> dict | None:
    """확정·신규 카드 즉시 위원회 검증 (실패해도 확정은 유지)."""
    try:
        import agent_office_saju_card_council as cc

        if cc.use_card_council():
            return cc.verify_card_by_id(card_id, mode=mode)
    except Exception:
        pass
    return None


def delete_card(card_id: int) -> bool:
    store = load_store()
    before = len(store.get("cards") or [])
    store["cards"] = [
        c
        for c in store.get("cards") or []
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
    return {
        "total": len(cards),
        "pending": pending,
        "confirmed": confirmed,
        "updated_at": load_store().get("updated_at") or "",
    }


def get_card(card_id: int) -> dict | None:
    for c in load_store().get("cards") or []:
        if isinstance(c, dict) and c.get("id") == card_id:
            return c
    return None


def set_card_council(card_id: int, **fields) -> bool:
    store = load_store()
    for c in store.get("cards") or []:
        if isinstance(c, dict) and c.get("id") == card_id:
            for k, v in fields.items():
                if v is not None:
                    c[k] = v
            save_store(store)
            return True
    return False


def update_confirmed_card(
    card_id: int,
    *,
    title: str | None = None,
    body: str | None = None,
    tags: list[str] | None = None,
    summary: str | None = None,
    note: str | None = None,
    **extra_fields,
) -> dict | None:
    """확정 카드 본문 수정 (위원회 FAIL 자동 보정·재인증용)."""
    store = load_store()
    for c in store.get("cards") or []:
        if not (isinstance(c, dict) and c.get("id") == card_id):
            continue
        if (c.get("status") or "") != "confirmed":
            return None
        if title is not None:
            c["title"] = _redact_pii(str(title).strip())[:120]
        if body is not None:
            c["body"] = _redact_pii(str(body).strip())[:24000]
            if summary is None:
                c["summary"] = _summary(c["body"])
        if summary is not None:
            c["summary"] = str(summary).strip()[:500]
        if tags is not None:
            c["tags"] = [str(t).strip() for t in tags if str(t).strip()][:12]
        if note is not None:
            c["note"] = str(note).strip()[:500]
        for k, v in extra_fields.items():
            if v is not None:
                c[k] = v
        c["updated_at"] = _now()
        save_store(store)
        export_pack()
        try:
            import agent_office_wiki_store

            agent_office_wiki_store.save_saju_card_to_knowledge(c)
        except Exception:
            pass
        return dict(c)
    return None


def list_cards(*, status: str | None = None, limit: int = 50) -> list[dict]:
    cards = [c for c in load_store().get("cards") or [] if isinstance(c, dict)]
    if status:
        cards = [c for c in cards if c.get("status") == status]
    cards.sort(key=lambda c: c.get("id") or 0, reverse=True)
    return cards[:limit]


def export_pack() -> dict:
    confirmed = [c for c in load_store().get("cards") or [] if isinstance(c, dict) and c.get("status") == "confirmed"]
    pack = {
        "version": 1,
        "purpose": "offline_saju_interpretation",
        "exported_at": _now(),
        "card_count": len(confirmed),
        "cards": [
            {
                "id": c.get("id"),
                "title": c.get("title"),
                "body": c.get("body"),
                "tags": c.get("tags") or [],
                "summary": c.get("summary"),
                "council_status": c.get("council_status") or "",
                "council_pass": bool(c.get("council_pass")),
                "council_at": c.get("council_at") or "",
            }
            for c in confirmed
        ],
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    json_store.save_json(PACK_PATH, pack)
    return pack


def import_feedback_jsonl(path: Path, *, limit: int = 50) -> int:
    """saju-v2 feedback.jsonl 에서 response(풀이)만 가져오기 — saju 앱 코드 변경 없음."""
    if not path.is_file():
        raise FileNotFoundError(path)
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = (row.get("response") or row.get("content") or "").strip()
        if len(text) < 80:
            continue
        rating = row.get("rating")
        title = f"피드백 풀이"
        if rating is not None:
            title += f" (평점 {rating})"
        try:
            add_card(body=text, title=title[:120], source="feedback_import")
            n += 1
        except ValueError:
            continue
        if n >= limit:
            break
    return n


def render_cursor_md(data: dict | None = None) -> str:
    data = data or load_store()
    st = stats()
    lines = [
        "# Cursor — 사주 학습부 (풀이 텍스트만)",
        "",
        f"갱신: **{data.get('updated_at', '—')}** · 전체 {st['total']} · 검수대기 {st['pending']} · 확정 {st['confirmed']}",
        "",
        "saju-v2 웹과 **연동되지 않습니다**. 풀이 본문만 붙여 넣거나 feedback.jsonl을 수동 import합니다.",
        "",
        f"보내기: `board/data/saju_learning/saju_knowledge_pack.json` ({st['confirmed']}건 확정)",
        "",
        "---",
        "",
    ]
    cards = [c for c in data.get("cards") or [] if isinstance(c, dict)]
    if not cards:
        lines.append("_아직 학습 카드가 없습니다._")
    else:
        for c in reversed(cards[-25:]):
            icon = "✅" if c.get("status") == "confirmed" else "🔴"
            lines.append(f"## {icon} #{c.get('id')} · {c.get('title', '')}")
            lines.append("")
            lines.append(f"- 상태: {c.get('status')} · 출처: {c.get('source')} · {c.get('ts')}")
            if c.get("tags"):
                lines.append(f"- 태그: {', '.join(c['tags'])}")
            lines.append("")
            lines.append((c.get("body") or "")[:3000])
            lines.append("")
            lines.append("---")
            lines.append("")
    CURSOR_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--title", default="")
    a.add_argument("--text", required=True)
    a.add_argument("--source", default="cli")
    sub.add_parser("list")
    sub.add_parser("stats")
    sub.add_parser("export")
    c = sub.add_parser("confirm")
    c.add_argument("id", type=int)
    imp = sub.add_parser("import-feedback")
    imp.add_argument("path")
    imp.add_argument("--limit", type=int, default=30)
    mrg = sub.add_parser(
        "import-merge",
        help="cards.json 병합 — 기존 위원회 검증 필드 유지",
    )
    mrg.add_argument("path", type=Path)
    mrg.add_argument(
        "--add-new-only",
        action="store_true",
        help="신규 카드만 추가(동일 id 본문 갱신 안 함)",
    )

    args = p.parse_args()
    if args.cmd == "add":
        card = add_card(body=args.text, title=args.title, source=args.source)
        print(json.dumps(card, ensure_ascii=False, indent=2))
    elif args.cmd == "list":
        for c in list_cards(limit=20):
            print(c["id"], c["status"], c["title"][:50])
    elif args.cmd == "stats":
        print(json.dumps(stats(), ensure_ascii=False))
    elif args.cmd == "export":
        pack = export_pack()
        print(f"exported {pack['card_count']} -> {PACK_PATH}")
    elif args.cmd == "confirm":
        print(confirm_card(args.id))
    elif args.cmd == "import-feedback":
        n = import_feedback_jsonl(Path(args.path), limit=args.limit)
        print(f"imported={n}")
    elif args.cmd == "import-merge":
        info = import_merge_cards_json(
            Path(args.path), add_new_only=bool(args.add_new_only)
        )
        print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
