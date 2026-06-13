"""젬마 지식망 → force-graph용 nodes/links JSON."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]

CATEGORY_COLORS = {
    "00_Raw": "#3b82f6",
    "10_Wiki": "#10b981",
    "20_Meta": "#f97316",
    "40_템플릿": "#a855f7",
    "_company": "#eab308",
    "_root": "#14b8a6",
    "Topics": "#8b5cf6",
    "Coupax": "#10b981",
    "Saju": "#a78bfa",
    "office": "#06b6d4",
    "default": "#64748b",
}

HUB_ID = "gemma24_hub"


def _category(entry: dict) -> str:
    layer = str(entry.get("layer") or "")
    if layer.startswith("00"):
        return "00_Raw"
    if layer.startswith("10"):
        return "10_Wiki"
    if layer.startswith("20"):
        return "20_Meta"
    if layer.startswith("40"):
        return "40_템플릿"
    cat = str(entry.get("category") or "").strip()
    if cat in CATEGORY_COLORS:
        return cat
    if cat.startswith("_"):
        return cat
    path = str(entry.get("path") or "")
    if "/Saju/" in path or entry.get("domain") == "saju-learn":
        return "Saju"
    if "/Coupax/" in path:
        return "Coupax"
    if "company" in path.lower() or "_company" in path:
        return "_company"
    return "10_Wiki"


def _color(cat: str) -> str:
    return CATEGORY_COLORS.get(cat, CATEGORY_COLORS["default"])


def _size_for(cat: str, base: int = 12) -> int:
    if cat == "office" or cat == "_root":
        return 28
    if cat == "10_Wiki":
        return 18
    if cat == "_company":
        return 10
    if cat == "20_Meta":
        return 11
    return base


def _link_key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


def _swiki_graph_path() -> Path:
    custom = os.environ.get("SWIKI_REPO_PATH", "").strip()
    if custom:
        return Path(custom) / "20_Meta" / "Graph.json"
    return BOARD / "data" / "pwcosmos-swiki" / "20_Meta" / "Graph.json"


def build_knowledge_graph(
    *,
    max_nodes: int = 1200,
    max_links: int = 6000,
    include_swiki: bool = True,
) -> dict:
    import agent_office_wiki_store as wiki_store

    nodes: list[dict] = []
    links: list[dict] = []
    node_ids: set[str] = set()
    link_keys: set[tuple[str, str]] = set()
    folder_counts: dict[str, int] = {}

    def add_node(nid: str, label: str, cat: str, desc: str = "", size: int | None = None):
        if not nid or nid in node_ids or len(nodes) >= max_nodes:
            return
        node_ids.add(nid)
        folder_counts[cat] = folder_counts.get(cat, 0) + 1
        nodes.append(
            {
                "id": nid,
                "name": (label or nid)[:80],
                "group": cat,
                "color": _color(cat),
                "size": size if size is not None else _size_for(cat),
                "desc": (desc or "")[:500],
            }
        )

    def add_link(src: str, tgt: str, val: float = 1.0):
        if not src or not tgt or src == tgt:
            return
        key = _link_key(src, tgt)
        if key in link_keys or len(links) >= max_links:
            return
        if src not in node_ids or tgt not in node_ids:
            return
        link_keys.add(key)
        links.append({"source": src, "target": tgt, "value": val})

    add_node(
        HUB_ID,
        "젬마24 지식 허브",
        "office",
        "coupax 사무실 Wiki·Meta·swiki 통합 허브",
        32,
    )

    for path_fn in (wiki_store.KNOWLEDGE_PATH, wiki_store.SAJU_KNOWLEDGE_PATH):
        if not path_fn.is_file():
            continue
        try:
            data = json.loads(path_fn.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for w in data.get("wiki") or []:
            if not isinstance(w, dict):
                continue
            wid = str(w.get("id") or "").strip()
            if not wid:
                continue
            cat = _category(w)
            add_node(
                wid,
                w.get("title") or wid,
                cat,
                w.get("summary") or "",
            )
            add_link(HUB_ID, wid, 2.0)

        for m in data.get("meta") or []:
            if not isinstance(m, dict):
                continue
            wiki_id = str(m.get("wiki_id") or "").strip()
            if not wiki_id or wiki_id not in node_ids:
                continue
            tag = str(m.get("key") or m.get("id") or "").strip()
            if not tag:
                continue
            mid = f"meta_{wiki_id}_{re.sub(r'[^a-zA-Z0-9_가-힣-]', '_', tag)[:40]}"
            add_node(mid, tag[:60], "20_Meta", f"Wiki {wiki_id} 메타", 10)
            add_link(wiki_id, mid, 1.0)

    if include_swiki:
        gf = _swiki_graph_path()
        if gf.is_file():
            try:
                raw = json.loads(gf.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                raw = {}
            for n in raw.get("nodes") or []:
                if not isinstance(n, dict):
                    continue
                nid = str(n.get("id") or "").strip()
                if not nid:
                    continue
                cat = _category(n)
                add_node(
                    nid,
                    n.get("label") or nid,
                    cat,
                    n.get("path") or "",
                )
                if len(nodes) >= max_nodes:
                    break
            for l in raw.get("links") or []:
                if not isinstance(l, dict):
                    continue
                src = str(l.get("source") or "").strip()
                tgt = str(l.get("target") or "").strip()
                add_link(src, tgt, float(l.get("value") or 1))
                if len(links) >= max_links:
                    break
            if HUB_ID in node_ids:
                coupax_hub = "Coupax_Office_Hub"
                if coupax_hub in node_ids:
                    add_link(HUB_ID, coupax_hub, 3.0)

    updated = datetime.now().strftime("%Y-%m-%d %H:%M")
    return {
        "updated_at": updated,
        "nodes": nodes,
        "links": links,
        "stats": {
            "node_count": len(nodes),
            "link_count": len(links),
            "folders": folder_counts,
        },
    }
