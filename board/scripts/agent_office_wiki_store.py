"""
작업 완료 보고 → 젬마24 지식망 (10_Wiki / 20_Meta) 저장.

  python scripts/agent_office_wiki_store.py list
  python scripts/agent_office_wiki_store.py save --task-id 1
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import json_store

BOARD = Path(__file__).resolve().parents[1]
KNOWLEDGE_PATH = BOARD / "data" / "gemma_knowledge.json"
SAJU_KNOWLEDGE_PATH = BOARD / "data" / "gemma_knowledge_saju.json"
# 슬림 JSON(공개 RAG) 상한 — 사무실 보고는 GitHub만 (①)
MAX_WIKI = 400
MAX_META = 2000

DOMAIN_FINANCE = "finance"
DOMAIN_SAJU = "saju-learn"
DOMAIN_KIWOM = "kiwoom-chasu"
DOMAIN_DESIGN = "homepage-design"
DOMAIN_WORKISUS = "workisus-chasu"
DOMAIN_GWANSANG = "gwansang-learn"

SOURCE_RESERVED = "reserved"
OFFICE_SOURCES = frozenset({"office", "reserved", "coupax-agent-office"})
GITHUB_ONLY_PREFIXES = ("wiki_office_", "wiki_pulse_")

_PII_PATTERNS = (
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    re.compile(r"01[0-9]-?\d{3,4}-?\d{4}"),
    re.compile(r"\d{6}-?\d{7}"),
)

_TAG_STOP = {
    "해주세요",
    "주세요",
    "관련",
    "정리",
    "조사",
    "작업",
    "지시",
    "완료",
    "보고",
    "다음",
    "단계",
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _redact_pii(text: str) -> str:
    out = text or ""
    for rx in _PII_PATTERNS:
        out = rx.sub("[PII]", out)
    return out


def _default_knowledge() -> dict:
    return {"updated_at": "", "wiki": [], "meta": []}


def wiki_domain(entry: dict | None, default: str = DOMAIN_FINANCE) -> str:
    if not isinstance(entry, dict):
        return default
    d = (entry.get("domain") or default).strip()
    return d if d in (
        DOMAIN_FINANCE,
        DOMAIN_SAJU,
        DOMAIN_KIWOM,
        DOMAIN_DESIGN,
        DOMAIN_WORKISUS,
        DOMAIN_GWANSANG,
    ) else default


def _migrate_domains(data: dict) -> None:
    """구 카드에 domain 없으면 finance 로 태깅."""
    id_dom: dict[str, str] = {}
    for w in data.get("wiki") or []:
        if isinstance(w, dict):
            w.setdefault("domain", DOMAIN_FINANCE)
            wid = w.get("id")
            if wid:
                id_dom[str(wid)] = wiki_domain(w)
    for m in data.get("meta") or []:
        if isinstance(m, dict):
            m.setdefault("domain", id_dom.get(str(m.get("wiki_id") or ""), DOMAIN_FINANCE))


def _normalize_knowledge(data: dict) -> dict:
    if not isinstance(data, dict):
        return _default_knowledge()
    data.setdefault("wiki", [])
    data.setdefault("meta", [])
    data.setdefault("schema_version", 2)
    if not isinstance(data["wiki"], list):
        data["wiki"] = []
    if not isinstance(data["meta"], list):
        data["meta"] = []
    _migrate_domains(data)
    return data


def load_knowledge() -> dict:
    try:
        data = json_store.load_json(KNOWLEDGE_PATH, default=_default_knowledge())
    except json_store.JsonStoreError:
        return _default_knowledge()
    return _normalize_knowledge(data)


def save_knowledge(data: dict) -> None:
    data = _normalize_knowledge(data)
    wiki = data.get("wiki")
    if isinstance(wiki, list):
        data["wiki"] = [
            w for w in wiki if isinstance(w, dict) and not is_github_archive_card(w)
        ]
        keep_ids = {w.get("id") for w in data["wiki"]}
        meta = data.get("meta")
        if isinstance(meta, list):
            data["meta"] = [
                m
                for m in meta
                if isinstance(m, dict) and m.get("wiki_id") in keep_ids
            ]
    wiki = data.get("wiki")
    meta = data.get("meta")
    if isinstance(wiki, list) and len(wiki) > MAX_WIKI:
        data["wiki"] = wiki[-MAX_WIKI:]
    if isinstance(meta, list) and len(meta) > MAX_META:
        data["meta"] = meta[-MAX_META:]
    data["updated_at"] = _now()
    json_store.save_json(KNOWLEDGE_PATH, data)


def extract_tags(title: str, body: str, limit: int = 8) -> list[str]:
    blob = f"{title} {body}".lower()
    tags: list[str] = []
    for m in re.finditer(r"[가-힣]{2,6}", blob):
        w = m.group(0)
        if w not in _TAG_STOP and w not in tags:
            tags.append(w)
        if len(tags) >= limit:
            break
    for m in re.finditer(r"\b(etf|faq|pii|wiki|배당|금리|블로그)\b", blob, re.I):
        t = m.group(0).lower()
        if t == "etf":
            t = "ETF"
        elif t == "faq":
            t = "FAQ"
        elif t == "pii":
            t = "PII"
        elif t == "wiki":
            t = "Wiki"
        if t not in tags:
            tags.append(t)
    return tags[:limit]


def _summary_from_result(result: str, max_len: int = 220) -> str:
    text = (result or "").strip()
    for marker in ("■ 취합 결론", "■ 연구 수집", "■ 지시"):
        if marker in text:
            part = text.split(marker, 1)[-1].strip()
            if marker == "■ 취합 결론" and part:
                text = part
                break
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("■")]
    summary = " ".join(lines[:4]) if lines else text
    summary = re.sub(r"\s+", " ", summary)
    if len(summary) > max_len:
        return summary[: max_len - 1] + "…"
    return summary


def find_wiki_by_task(task_id: int) -> dict | None:
    for w in load_knowledge().get("wiki") or []:
        if isinstance(w, dict) and w.get("task_id") == task_id:
            return w
    return None


def find_wiki_by_id(wiki_id: str) -> dict | None:
    wid = (wiki_id or "").strip()
    if not wid:
        return None
    for w in load_knowledge().get("wiki") or []:
        if isinstance(w, dict) and w.get("id") == wid:
            return w
    return None


def is_github_archive_card(card: dict | None) -> bool:
    """사무실·예약 작업 보고 — GitHub md 전용, 슬림 JSON 제외 (①)."""
    if not isinstance(card, dict):
        return False
    wid = str(card.get("id") or "")
    if wid.startswith(GITHUB_ONLY_PREFIXES):
        return True
    src = (card.get("source") or "").strip()
    return src in OFFICE_SOURCES


def should_persist_in_slim_json(task: dict, wiki_card: dict) -> bool:
    """블로그 RAG용 gemma_knowledge.json 에 넣을 카드인지."""
    if is_github_archive_card(wiki_card):
        return False
    domain = wiki_domain(wiki_card)
    if domain == DOMAIN_SAJU:
        return True
    wid = str(wiki_card.get("id") or "")
    if wid.startswith("wiki_saju_"):
        return True
    src = (wiki_card.get("source") or task.get("source") or "").strip()
    if src in OFFICE_SOURCES:
        return False
    return not wid.startswith(GITHUB_ONLY_PREFIXES)


def resolve_task_wiki_id(task: dict) -> str:
    """③ 예약 작업: 제목별 고정 id · 그 외: 작업번호 id."""
    source = (task.get("source") or "").strip()
    if source == SOURCE_RESERVED:
        try:
            import agent_office_reserved_tasks as reserved

            return reserved.pulse_wiki_id_for_title(task.get("title") or "")
        except Exception:
            pass
        title = (task.get("title") or "").strip()
        slug = re.sub(r"[^\w가-힣]+", "_", title).strip("_")[:40] or "reserved"
        return f"wiki_pulse_{slug}"
    tid = task.get("id")
    if isinstance(tid, int):
        return f"wiki_office_{tid}"
    return "wiki_office_unknown"


def _upsert_slim_wiki(data: dict, wiki_card: dict) -> None:
    """슬림 JSON에 Wiki 1건 upsert + Meta 갱신."""
    wiki_id = wiki_card.get("id")
    tid = wiki_card.get("task_id")
    domain = wiki_domain(wiki_card)
    tags = wiki_card.get("tags") or []
    ts = wiki_card.get("ts") or _now()
    primary_id = wiki_card.get("agent_primary") or ""
    synth_id = wiki_card.get("agent_synth") or ""

    replaced = False
    for i, w in enumerate(data.get("wiki") or []):
        if isinstance(w, dict) and w.get("id") == wiki_id:
            data["wiki"][i] = wiki_card
            replaced = True
            break
    if not replaced:
        data["wiki"].append(wiki_card)

    meta = [m for m in (data.get("meta") or []) if not (isinstance(m, dict) and m.get("wiki_id") == wiki_id)]
    data["meta"] = meta

    for tag in tags:
        slug = re.sub(r"[^\w가-힣]+", "_", tag).strip("_")[:40]
        if not slug:
            continue
        meta.append(
            {
                "id": f"meta_tag_{wiki_id}_{slug}",
                "domain": domain,
                "layer": "20_Meta",
                "kind": "tag",
                "key": tag,
                "wiki_id": wiki_id,
                "task_id": tid,
                "ts": ts,
            }
        )
    saju_cid = wiki_card.get("saju_card_id")
    if saju_cid is not None:
        meta.append(
            {
                "id": f"meta_index_saju_{saju_cid}",
                "domain": domain,
                "layer": "20_Meta",
                "kind": "index",
                "key": f"saju_card:{saju_cid}",
                "wiki_id": wiki_id,
                "ts": ts,
            }
        )
    elif tid is not None:
        meta.append(
            {
                "id": f"meta_index_task_{tid}",
                "domain": domain,
                "layer": "20_Meta",
                "kind": "index",
                "key": f"task:{tid}",
                "wiki_id": wiki_id,
                "agent_primary": primary_id,
                "ts": ts,
            }
        )
    for aid in {primary_id, synth_id, wiki_card.get("resolved_to")}:
        if not aid or not isinstance(aid, str):
            continue
        meta.append(
            {
                "id": f"meta_agent_{wiki_id}_{aid}",
                "domain": domain,
                "layer": "20_Meta",
                "kind": "agent_link",
                "key": aid,
                "wiki_id": wiki_id,
                "task_id": tid,
                "ts": ts,
            }
        )
    data["meta"] = meta


def prune_office_from_slim_json(*, dry_run: bool = False) -> dict:
    """슬림 JSON에서 사무실·예약 Wiki/Meta 제거 (① 정리). GitHub 원본은 유지."""
    data = load_knowledge()
    wiki_before = len(data.get("wiki") or [])
    meta_before = len(data.get("meta") or [])

    keep_wiki = [
        w
        for w in (data.get("wiki") or [])
        if isinstance(w, dict) and not is_github_archive_card(w)
    ]
    keep_ids = {w.get("id") for w in keep_wiki}
    keep_meta = [
        m
        for m in (data.get("meta") or [])
        if isinstance(m, dict) and m.get("wiki_id") in keep_ids
    ]

    removed = {
        "wiki": wiki_before - len(keep_wiki),
        "meta": meta_before - len(keep_meta),
        "wiki_remaining": len(keep_wiki),
        "meta_remaining": len(keep_meta),
    }
    if not dry_run:
        data["wiki"] = keep_wiki
        data["meta"] = keep_meta
        save_knowledge(data)
    return removed


def save_task_to_knowledge(
    task: dict,
    result: str,
    *,
    primary_id: str,
    synth_id: str,
) -> dict | None:
    """완료 작업을 10_Wiki 카드 + 20_Meta 태그·색인으로 저장. 저장된 wiki dict 반환."""
    tid = task.get("id")
    if not isinstance(tid, int):
        return None

    title = (task.get("title") or "").strip() or f"작업 #{tid} 보고"
    body_raw = result or task.get("result") or ""
    body = _redact_pii(body_raw)[:8000]
    summary = _redact_pii(_summary_from_result(body))
    tags = extract_tags(title, f"{task.get('body') or ''} {body}")
    domain = (task.get("division") or DOMAIN_FINANCE).strip()
    if domain not in (
        DOMAIN_FINANCE,
        DOMAIN_SAJU,
        DOMAIN_KIWOM,
        DOMAIN_DESIGN,
        DOMAIN_WORKISUS,
        DOMAIN_GWANSANG,
    ):
        domain = DOMAIN_FINANCE
    wiki_id = resolve_task_wiki_id(task)
    ts = task.get("finished_at") or _now()
    task_source = (task.get("source") or "office").strip()

    wiki_card = {
        "id": wiki_id,
        "domain": domain,
        "layer": "10_Wiki",
        "title": title[:120],
        "summary": summary,
        "body": body,
        "task_id": tid,
        "assign_to": task.get("assign_to"),
        "resolved_to": task.get("resolved_to") or primary_id,
        "agent_primary": primary_id,
        "agent_synth": synth_id,
        "source": task_source,
        "storage_tier": "github_archive",
        "priority": task.get("priority") or "normal",
        "ts": ts,
        "tags": tags,
    }

    # ① GitHub 마스터 — 사무실·예약 보고는 항상 push (③ 예약은 동일 md 덮어쓰기)
    try:
        import agent_office_swiki_sync

        agent_office_swiki_sync.push_wiki_card(wiki_card, force=True)
    except Exception:
        pass

    if not should_persist_in_slim_json(task, wiki_card):
        return wiki_card

    wiki_card = {**wiki_card, "storage_tier": "slim_runtime"}
    data = load_knowledge()
    _upsert_slim_wiki(data, wiki_card)
    save_knowledge(data)
    return wiki_card


def save_kiwoom_card_to_knowledge(card: dict) -> dict | None:
    """확정된 차수거래 학습 카드 → 10_Wiki (domain=kiwoom-chasu)."""
    cid = card.get("id")
    if cid is None:
        return None
    title = (card.get("title") or "").strip() or f"차수거래 #{cid}"
    body = _redact_pii((card.get("body") or ""))[:8000]
    summary = _redact_pii((card.get("summary") or _summary_from_result(body))[:220])
    tags = list(card.get("tags") or [])
    for t in extract_tags(title, body):
        if t not in tags:
            tags.append(t)
    tags = tags[:12]
    wiki_id = f"wiki_kiwoom_{cid}"
    ts = card.get("confirmed_at") or card.get("ts") or _now()
    wiki_card = {
        "id": wiki_id,
        "domain": DOMAIN_KIWOM,
        "layer": "10_Wiki",
        "title": title[:120],
        "summary": summary,
        "body": body,
        "kiwoom_card_id": cid,
        "source": card.get("source") or "kiwoom_learn",
        "storage_tier": "slim_runtime",
        "agent_primary": "kiwoom_curator",
        "agent_synth": "kiwoom_structurer",
        "ts": ts,
        "tags": tags,
    }
    data = load_knowledge()
    _upsert_slim_wiki(data, wiki_card)
    save_knowledge(data)
    try:
        import agent_office_swiki_sync

        agent_office_swiki_sync.push_wiki_card(wiki_card)
    except Exception:
        pass
    return wiki_card


def save_design_card_to_knowledge(card: dict) -> dict | None:
    """확정된 홈페이지 디자인 학습 카드 → 10_Wiki (domain=homepage-design)."""
    cid = card.get("id")
    if cid is None:
        return None
    title = (card.get("title") or "").strip() or f"디자인 #{cid}"
    body = _redact_pii((card.get("body") or ""))[:8000]
    summary = _redact_pii((card.get("summary") or _summary_from_result(body))[:220])
    tags = list(card.get("tags") or [])
    for t in extract_tags(title, body):
        if t not in tags:
            tags.append(t)
    tags = tags[:12]
    wiki_id = f"wiki_design_{cid}"
    ts = card.get("confirmed_at") or card.get("ts") or _now()
    wiki_card = {
        "id": wiki_id,
        "domain": DOMAIN_DESIGN,
        "layer": "10_Wiki",
        "title": title[:120],
        "summary": summary,
        "body": body,
        "design_card_id": cid,
        "catalog_seed": card.get("catalog_seed"),
        "source": card.get("source") or "design_learn",
        "storage_tier": "slim_runtime",
        "agent_primary": "design_curator",
        "agent_synth": "design_council",
        "ts": ts,
        "tags": tags,
    }
    data = load_knowledge()
    _upsert_slim_wiki(data, wiki_card)
    save_knowledge(data)
    return wiki_card


def save_gwansang_card_to_knowledge(card: dict) -> dict | None:
    """확정된 관상 학습 카드 → 10_Wiki (domain=gwansang-learn)."""
    cid = card.get("id")
    if cid is None:
        return None
    title = (card.get("title") or "").strip() or f"관상 #{cid}"
    body = _redact_pii((card.get("body") or ""))[:8000]
    summary = _redact_pii((card.get("summary") or _summary_from_result(body))[:220])
    tags = list(card.get("tags") or [])
    for t in extract_tags(title, body):
        if t not in tags:
            tags.append(t)
    tags = tags[:12]
    wiki_id = f"wiki_gwansang_{cid}"
    ts = card.get("confirmed_at") or card.get("ts") or _now()
    wiki_card = {
        "id": wiki_id,
        "domain": DOMAIN_GWANSANG,
        "layer": "10_Wiki",
        "title": title[:120],
        "summary": summary,
        "body": body,
        "gwansang_card_id": cid,
        "catalog_seed": card.get("catalog_seed"),
        "source": card.get("source") or "gwansang_learn",
        "storage_tier": "slim_runtime",
        "agent_primary": card.get("agent_primary") or "gwansang_curator",
        "agent_synth": "gwansang_seo",
        "ts": ts,
        "tags": tags,
    }
    data = load_knowledge()
    _upsert_slim_wiki(data, wiki_card)
    save_knowledge(data)
    return wiki_card


def save_workisus_card_to_knowledge(card: dict) -> dict | None:
    """확정된 원키스 US 차수 학습 카드 → 10_Wiki (domain=workisus-chasu)."""
    cid = card.get("id")
    if cid is None:
        return None
    title = (card.get("title") or "").strip() or f"원키스US #{cid}"
    body = _redact_pii((card.get("body") or ""))[:8000]
    summary = _redact_pii((card.get("summary") or _summary_from_result(body))[:220])
    tags = list(card.get("tags") or [])
    for t in extract_tags(title, body):
        if t not in tags:
            tags.append(t)
    tags = tags[:12]
    wiki_id = f"wiki_workisus_{cid}"
    ts = card.get("confirmed_at") or card.get("ts") or _now()
    wiki_card = {
        "id": wiki_id,
        "domain": DOMAIN_WORKISUS,
        "layer": "10_Wiki",
        "title": title[:120],
        "summary": summary,
        "body": body,
        "workisus_card_id": cid,
        "catalog_seed": card.get("catalog_seed"),
        "source": card.get("source") or "workisus_learn",
        "storage_tier": "slim_runtime",
        "agent_primary": "workisus_curator",
        "agent_synth": "workisus_slots",
        "ts": ts,
        "tags": tags,
    }
    data = load_knowledge()
    _upsert_slim_wiki(data, wiki_card)
    save_knowledge(data)
    return wiki_card


def save_saju_card_to_knowledge(card: dict) -> dict | None:
    """확정된 사주 풀이 카드 → 10_Wiki (domain=saju-learn). pack 과 병행."""
    cid = card.get("id")
    if cid is None:
        return None
    title = (card.get("title") or "").strip() or f"사주 풀이 #{cid}"
    body = _redact_pii((card.get("body") or ""))[:8000]
    summary = _redact_pii((card.get("summary") or _summary_from_result(body))[:220])
    tags = list(card.get("tags") or [])
    for t in extract_tags(title, body):
        if t not in tags:
            tags.append(t)
    tags = tags[:12]
    wiki_id = f"wiki_saju_{cid}"
    ts = card.get("confirmed_at") or card.get("ts") or _now()

    try:
        import saju_knowledge_tier as skt

        ct = skt.council_tier(card)
    except Exception:
        ct = "review"
        skt = None

    wiki_card = {
        "id": wiki_id,
        "domain": DOMAIN_SAJU,
        "layer": "10_Wiki",
        "title": title[:120],
        "summary": summary,
        "body": body,
        "saju_card_id": cid,
        "source": card.get("source") or "saju_learn",
        "storage_tier": "slim_runtime",
        "agent_primary": "saju_curator",
        "agent_synth": "saju_structurer",
        "ts": ts,
        "tags": tags,
        "council_status": (card.get("council_status") or "")[:16],
        "council_pass": bool(card.get("council_pass")),
        "council_at": (card.get("council_at") or "")[:32],
        "council_tier": ct,
        "rag_eligible": ct != "excluded" if skt else True,
        "compose_eligible": ct == "certified" if skt else False,
    }

    data = load_knowledge()
    _upsert_slim_wiki(data, wiki_card)
    save_knowledge(data)

    try:
        import agent_office_swiki_sync

        agent_office_swiki_sync.push_wiki_card(wiki_card)
    except Exception:
        pass
    return wiki_card


def save_stock_pulse_to_knowledge(wiki_card: dict) -> dict | None:
    """주식 시황 일지 → finance 10_Wiki (wiki_stock_pulse, 덮어쓰기 갱신)."""
    wid = (wiki_card.get("id") or "").strip()
    if wid != "wiki_stock_pulse":
        wiki_card = {**wiki_card, "id": "wiki_stock_pulse"}
    title = (wiki_card.get("title") or "").strip() or f"주식 시황 일지 {_now()[:10]}"
    body = _redact_pii((wiki_card.get("body") or ""))[:8000]
    summary = _redact_pii((wiki_card.get("summary") or _summary_from_result(body))[:220])
    tags = list(wiki_card.get("tags") or [])
    for t in extract_tags(title, body):
        if t not in tags:
            tags.append(t)
    ts = wiki_card.get("ts") or wiki_card.get("stock_snapshot_at") or _now()
    out = {
        "id": "wiki_stock_pulse",
        "domain": DOMAIN_FINANCE,
        "layer": "10_Wiki",
        "title": title[:120],
        "summary": summary,
        "body": body,
        "source": (wiki_card.get("source") or "stock_watch").strip(),
        "storage_tier": "slim_runtime",
        "agent_primary": wiki_card.get("agent_primary") or "stock_radar",
        "agent_synth": wiki_card.get("agent_synth") or "stock_chart",
        "ts": ts,
        "tags": tags[:12],
        "stock_snapshot_at": wiki_card.get("stock_snapshot_at") or ts,
    }
    data = load_knowledge()
    _upsert_slim_wiki(data, out)
    save_knowledge(data)
    return out


def filter_by_domain(data: dict, domain: str | None) -> tuple[list, list]:
    wiki = [w for w in data.get("wiki") or [] if isinstance(w, dict)]
    meta = [m for m in data.get("meta") or [] if isinstance(m, dict)]
    if not domain:
        return wiki, meta
    wiki = [w for w in wiki if wiki_domain(w) == domain]
    wiki_ids = {w.get("id") for w in wiki}
    meta = [m for m in meta if wiki_domain(m) == domain or m.get("wiki_id") in wiki_ids]
    return wiki, meta


def export_domain_slice(domain: str) -> dict:
    """차후 분리용: 한 domain 만 잘라낸 스냅샷."""
    data = load_knowledge()
    wiki, meta = filter_by_domain(data, domain)
    return {
        "schema_version": 2,
        "domain": domain,
        "exported_at": _now(),
        "wiki": wiki,
        "meta": meta,
    }


def split_domain_to_file(
    domain: str,
    out_path: Path | None = None,
    *,
    remove_from_unified: bool = False,
) -> dict:
    """
    domain 을 별도 JSON 으로보내기. remove_from_unified=True 면 통합본에서 제거.
    """
    out_path = out_path or (
        SAJU_KNOWLEDGE_PATH if domain == DOMAIN_SAJU else BOARD / f"data/gemma_knowledge_{domain}.json"
    )
    slice_data = export_domain_slice(domain)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_store.save_json(out_path, slice_data)

    removed = {"wiki": 0, "meta": 0}
    if remove_from_unified:
        data = load_knowledge()
        before_w = len(data.get("wiki") or [])
        before_m = len(data.get("meta") or [])
        data["wiki"] = [
            w
            for w in data.get("wiki") or []
            if not (isinstance(w, dict) and wiki_domain(w) == domain)
        ]
        data["meta"] = [
            m
            for m in data.get("meta") or []
            if not (isinstance(m, dict) and wiki_domain(m) == domain)
        ]
        removed["wiki"] = before_w - len(data["wiki"])
        removed["meta"] = before_m - len(data["meta"])
        save_knowledge(data)

    return {
        "ok": True,
        "domain": domain,
        "out_path": str(out_path),
        "wiki_count": len(slice_data.get("wiki") or []),
        "meta_count": len(slice_data.get("meta") or []),
        "removed_from_unified": removed,
    }


def enrich_saju_wiki_entries(wiki: list) -> list:
    """cards.json 위원회 상태를 Wiki 항목에 병합."""
    try:
        import saju_knowledge_tier as skt

        by_id = skt.load_cards_by_id()
    except Exception:
        return wiki
    out = []
    for w in wiki:
        if not isinstance(w, dict):
            continue
        sid = w.get("saju_card_id")
        card = by_id.get(int(sid)) if sid is not None else None
        out.append(skt.enrich_wiki_from_card(w, card))
    return out


def knowledge_stats(domain: str | None = None) -> dict:
    data = load_knowledge()
    wiki, meta = filter_by_domain(data, domain)
    if domain == DOMAIN_SAJU:
        wiki = enrich_saju_wiki_entries(wiki)
    finance_wiki, finance_meta = filter_by_domain(data, DOMAIN_FINANCE)
    saju_wiki, saju_meta = filter_by_domain(data, DOMAIN_SAJU)
    slim_wiki = [w for w in (data.get("wiki") or []) if isinstance(w, dict) and not is_github_archive_card(w)]
    archive_n = len(data.get("wiki") or []) - len(slim_wiki)
    return {
        "updated_at": data.get("updated_at") or "",
        "schema_version": data.get("schema_version", 1),
        "wiki_count": len(wiki),
        "meta_count": len(meta),
        "slim_wiki_count": len(slim_wiki),
        "github_archive_in_json": archive_n,
        "recent_wiki": wiki[-8:],
        "council_certified": sum(
            1 for w in wiki if isinstance(w, dict) and w.get("council_tier") == "certified"
        ),
        "council_review": sum(
            1 for w in wiki if isinstance(w, dict) and w.get("council_tier") == "review"
        ),
        "by_domain": {
            DOMAIN_FINANCE: {
                "wiki_count": len(finance_wiki),
                "meta_count": len(finance_meta),
            },
            DOMAIN_SAJU: {
                "wiki_count": len(saju_wiki),
                "meta_count": len(saju_meta),
            },
        },
    }


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    pr = sub.add_parser("prune-office")
    pr.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("save")
    s.add_argument("--task-id", type=int, required=True)

    args = p.parse_args()
    if args.cmd == "prune-office":
        print(json.dumps(prune_office_from_slim_json(dry_run=args.dry_run), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "list":
        st = knowledge_stats()
        print(json.dumps(st, ensure_ascii=False, indent=2))
        for w in reversed(st.get("recent_wiki") or []):
            print(f"  - {w.get('id')}: {w.get('title')}")
        return 0
    if args.cmd == "save":
        import agent_office_tasks

        task = agent_office_tasks.find_task(args.task_id)
        if not task or task.get("status") != "done":
            print("task not found or not done")
            return 1
        row = save_task_to_knowledge(
            task,
            task.get("result") or "",
            primary_id=task.get("handled_by") or "researcher",
            synth_id=task.get("synthesized_by") or "structurer",
        )
        print(json.dumps(row, ensure_ascii=False))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
