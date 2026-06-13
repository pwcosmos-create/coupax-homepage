"""
원히어로(MagicSplit) 매매 규칙 학습 카드 축적.

  python scripts/agent_office_kiwoom_learn.py add --title "..." --text "..."
  python scripts/seed_kiwoom_wonhero_rules.py --reset   # 전면 교체 시드
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import json_store

BOARD = Path(__file__).resolve().parents[1]
DATA_DIR = BOARD / "data" / "kiwoom_learning"
CARDS_PATH = DATA_DIR / "cards.json"
PACK_PATH = DATA_DIR / "kiwoom_knowledge_pack.json"
CURSOR_MD = BOARD.parent / "CURSOR_KIWOM_LEARN.md"
DIVISION = "kiwoom-chasu"
# 원히어로 카탈로그(~70) + 오류·RL 메타 — 500 상한 시 --add 시 오래된 카드가 잘림
MAX_CARDS = 1200

_PII_PATTERNS = (
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    re.compile(r"01[0-9]-?\d{3,4}-?\d{4}"),
    re.compile(r"\d{6}-?\d{7}"),
    re.compile(r"\d{10,}"),
)

_TAG_KW = (
    "원히어로",
    "슬롯",
    "ATR",
    "buy_gaps",
    "sell_pcts",
    "cascade",
    "MagicSplit",
    "차수",
    "1차",
    "2차",
    "3차",
    "매수",
    "매도",
    "손절",
    "익절",
    "분할",
    "체결",
    "미체결",
    "종목",
    "티커",
    "수량",
    "호가",
    "VI",
    "ETF",
    "코스피",
    "코스닥",
    "키움",
    "예수금",
    "잔고",
    "주문가능",
    "계좌",
    "계좌이동",
    "이체",
    "계좌간",
    "계좌간이동",
    "대체",
    "CMA",
    "위탁",
    "연금",
    "ISA",
    "IRP",
    "입금",
    "출금",
    "API",
    "수수료",
    "슬리피지",
    "레버리지",
    "공매도",
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
    codes = re.findall(r"\b[0-9]{6}\b", blob)
    if codes:
        tags.append("종목코드")
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


def find_card_by_id(card_id: int) -> dict | None:
    for c in load_store().get("cards") or []:
        if isinstance(c, dict) and c.get("id") == card_id:
            return c
    return None


def ensure_unique_title(title: str, taken: set[str] | None = None) -> str:
    """제목 중복 시 · v2 / 날짜 접미."""
    titles = taken if taken is not None else existing_titles()
    base = normalize_title(title)
    if not base:
        return base
    if base not in titles:
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
    """기존 카드 본문·제목 갱신(합친 내용 반영). 확정 카드는 Wiki·pack 동일 id로 upsert."""
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
                raise ValueError("다른 카드와 제목이 겹칩니다. 제목을 바꾸세요.")
            target["title"] = new_title

    if catalog_seed is not None:
        seed = str(catalog_seed).strip()[:120]
        if seed:
            other = find_card_by_seed(seed)
            if other and other.get("id") != card_id:
                raise ValueError(
                    f"catalog_seed '{seed}'는 카드 #{other.get('id')}에 사용 중입니다."
                )
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

            agent_office_wiki_store.save_kiwoom_card_to_knowledge(target)
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
        try:
            import kiwoom_learning_errors as kerr

            kerr.record("duplicate", "제목 중복 — 저장하지 않음", title=title)
        except Exception:
            pass
        raise ValueError("동일 제목의 카드가 이미 있습니다. 제목을 바꾸거나 기존 카드를 수정하세요.")
    contributors: list[dict] = []
    if use_council is None:
        use_council = source in ("paste", "office_paste", "manual")
    if use_council:
        try:
            import kiwoom_card_council as kc

            if kc.council_enabled():
                body, contributors = kc.compose_card_body(
                    {"title": title, "body": body, "category": "manual"}
                )
        except Exception:
            pass
    if len(body) < 30:
        try:
            import kiwoom_learning_errors as kerr

            kerr.record("too_short", "학습 본문 30자 미만", title=title)
        except Exception:
            pass
        raise ValueError("학습 본문이 너무 짧습니다 (30자 이상).")
    try:
        import kiwoom_card_validate as kval

        ok, kind, hint = kval.validate_spec(title, body)
        if not ok and source not in ("paste", "manual"):
            import kiwoom_learning_errors as kerr

            kerr.record(kind, hint, title=title)
    except Exception:
        pass

    store = load_store()
    cards = store.get("cards") or []
    next_id = 1
    for c in cards:
        if isinstance(c, dict) and isinstance(c.get("id"), int):
            next_id = max(next_id, c["id"] + 1)

    if not title:
        try:
            import kiwoom_card_title_compose as kt

            title = kt.generate_title(
                body=body,
                category=str(note or source or ""),
                taken=existing_titles(),
            )
        except Exception:
            title = normalize_title(_summary(body, 50))
    title = ensure_unique_title(title or normalize_title(_summary(body, 50)))
    if title_taken(title):
        try:
            import kiwoom_learning_errors as kerr

            kerr.record("duplicate", "제목 중복(자동 제목)", title=title)
        except Exception:
            pass
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
        card["catalog_seed"] = str(catalog_seed).strip()[:120]
    if contributors:
        card["council"] = contributors
        card["council_agents"] = [x.get("agent_id") for x in contributors if x.get("agent_id")]
    cards.append(card)
    store["cards"] = cards
    save_store(store)
    try:
        import agent_office_log

        if contributors:
            import kiwoom_card_council as kc

            kc.log_council_feed(title, contributors, card_id=next_id)
        else:
            agent_office_log.append_message(
                from_id="kiwoom_reader",
                kind="task",
                text=f"[원히어로 차수거래 카드 #{next_id}] {title}\n{_summary(body, 120)}",
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

                wiki_row = agent_office_wiki_store.save_kiwoom_card_to_knowledge(c)
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
                import kiwoom_card_rl_engine as rle

                rle.record_confirm_success(c)
            except Exception:
                pass
            try:
                import agent_office_log

                msg = f"[확정 #{card_id}] {c.get('title', '')} — pack 반영"
                if wiki_id:
                    msg += f" · 젬마기억 {wiki_id}"
                agent_office_log.append_message(
                    from_id="kiwoom_curator",
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
    return {
        "total": len(cards),
        "pending": pending,
        "confirmed": confirmed,
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
        "purpose": "kiwoom_chasu_trading_learn",
        "exported_at": _now(),
        "card_count": len(confirmed),
        "cards": [
            {
                "id": c.get("id"),
                "title": c.get("title"),
                "summary": c.get("summary"),
                "tags": c.get("tags") or [],
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
        "# Cursor — 원히어로 차수거래 학습부",
        "",
        f"갱신: {data.get('updated_at') or '—'} · 확정 {len(confirmed)}건",
        "",
        "확정 카드 요약 (PII 제거됨). 투자 자문 아님.",
        "",
    ]
    for c in confirmed[-40:]:
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
