"""
Connect AI Lab connect-ai-brain.jsonl → gemma_knowledge.json (공개 Wiki).

  CONNECT_AI_LAB_PATH="C:\\Users\\...\\Desktop\\connect ai lab"
  PYTHONPATH=scripts python scripts/import_connect_brain_jsonl.py
  PYTHONPATH=scripts python scripts/import_connect_brain_jsonl.py --dry-run
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
_SCRIPTS = BOARD / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import agent_office_wiki_store as wiki_store  # noqa: E402

DEFAULT_LAB = Path(os.environ.get("USERPROFILE", "")) / "Desktop" / "connect ai lab"
SKIP_ANSWER_RE = re.compile(
    r"^💡\s*광장에서 배움\s*—\s*(주제|핵심)[:：]",
    re.M,
)
HIGH_VALUE_RE = re.compile(
    r"RAG|Connect AI|Coupax|Ollama|Antigravity|키움|연금|ETF|투자|"
    r"플레이북|MasterClass|브레인|지식|에이전트|SDK|파인튜닝|LM Studio",
    re.I,
)
DOMAIN_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"사주|명리|용신|일주|격국|대운", re.I), wiki_store.DOMAIN_SAJU),
    (re.compile(r"관상|관相|삼정|오관", re.I), wiki_store.DOMAIN_GWANSANG),
    (re.compile(r"디자인|토큰|레이아웃|style\.css|MasterClass|홈페이지", re.I), wiki_store.DOMAIN_DESIGN),
    (re.compile(r"키움|원키스|그리드|ATR|차수", re.I), wiki_store.DOMAIN_KIWOM),
    (re.compile(r"workisus|원키스", re.I), wiki_store.DOMAIN_WORKISUS),
]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _lab_path() -> Path:
    raw = os.environ.get("CONNECT_AI_LAB_PATH", "").strip()
    if raw:
        return Path(raw)
    return DEFAULT_LAB


def _brain_files(lab: Path) -> list[Path]:
    paths: list[Path] = []
    for name in ("connect-ai-brain.jsonl", "connect-ai-dpo.jsonl"):
        p = lab / name
        if p.is_file():
            paths.append(p)
    extra = os.environ.get("CONNECT_AI_BRAIN_JSONL", "").strip()
    if extra:
        ep = Path(extra)
        if ep.is_file() and ep not in paths:
            paths.append(ep)
    return paths


def _slug(text: str, n: int = 40) -> str:
    s = re.sub(r"[^\w가-힣]+", "_", (text or "").strip())[:n].strip("_")
    return s or "entry"


def _infer_domain(q: str, a: str) -> str:
    blob = f"{q}\n{a}"
    for rx, dom in DOMAIN_RULES:
        if rx.search(blob):
            return dom
    return wiki_store.DOMAIN_FINANCE


def _extract_title(q: str, a: str) -> str:
    for src in (a, q):
        m = re.search(r"^#\s*\[\[(.+?)\]\]", src, re.M)
        if m:
            return m.group(1).strip()[:120]
        m = re.search(r"^#\s+(.+)$", src, re.M)
        if m and len(m.group(1)) > 4:
            return m.group(1).strip()[:120]
    q1 = re.sub(r"\s+", " ", q.strip())[:80]
    return q1 or "Connect AI 지식"


def _should_skip(q: str, a: str) -> str | None:
    a = (a or "").strip()
    q = (q or "").strip()
    if len(a) < 80:
        return "short"
    if SKIP_ANSWER_RE.match(a) and len(a) < 200 and not HIGH_VALUE_RE.search(a):
        return "plaza_echo"
    if "회사 대화록" in a and len(a) > 2500:
        return "office_chat_log"
    if "자율 잡담" in a and "CEO" not in a and len(a) < 400:
        return "chatter"
    if not q or len(q) < 6:
        return "bad_question"
    return None


def _wiki_id(title: str, q: str) -> str:
    base = _slug(title, 32) or _slug(q, 32)
    h = hashlib.sha1(f"{title}\n{q}".encode()).hexdigest()[:8]
    return f"wiki_connect_{base}_{h}"


def _parse_row(obj: dict) -> tuple[str, str] | None:
    conv = obj.get("conversations")
    if not isinstance(conv, list) or len(conv) < 2:
        return None
    user = assistant = ""
    for turn in conv:
        if not isinstance(turn, dict):
            continue
        role = (turn.get("role") or "").strip().lower()
        content = (turn.get("content") or "").strip()
        if role == "user" and content:
            user = content
        elif role == "assistant" and content:
            assistant = content
    if user and assistant:
        return user, assistant
    return None


def import_jsonl(
    *,
    dry_run: bool = False,
    max_add: int = 150,
) -> dict:
    lab = _lab_path()
    files = _brain_files(lab)
    if not files:
        return {"ok": False, "error": f"brain jsonl not found under {lab}", "added": 0}

    data = wiki_store.load_knowledge()
    known_titles = {
        re.sub(r"\s+", " ", str(w.get("title") or "").strip().lower())
        for w in data.get("wiki") or []
        if isinstance(w, dict)
    }
    known_ids = {w.get("id") for w in data.get("wiki") or [] if isinstance(w, dict)}

    stats = {
        "ok": True,
        "lab": str(lab),
        "files": [str(p) for p in files],
        "scanned": 0,
        "skipped": 0,
        "added": 0,
        "updated": 0,
        "skip_reasons": {},
    }

    for path in files:
        with path.open(encoding="utf-8") as f:
            for line in f:
                if stats["added"] >= max_add:
                    break
                line = line.strip()
                if not line:
                    continue
                stats["scanned"] += 1
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    stats["skipped"] += 1
                    stats["skip_reasons"]["json"] = stats["skip_reasons"].get("json", 0) + 1
                    continue
                pair = _parse_row(obj)
                if not pair:
                    stats["skipped"] += 1
                    stats["skip_reasons"]["format"] = stats["skip_reasons"].get("format", 0) + 1
                    continue
                q, a = pair
                reason = _should_skip(q, a)
                if reason:
                    stats["skipped"] += 1
                    stats["skip_reasons"][reason] = stats["skip_reasons"].get(reason, 0) + 1
                    continue
                title = _extract_title(q, a)
                norm_title = re.sub(r"\s+", " ", title.lower())
                if norm_title in known_titles:
                    stats["skipped"] += 1
                    stats["skip_reasons"]["dup_title"] = stats["skip_reasons"].get("dup_title", 0) + 1
                    continue

                wid = _wiki_id(title, q)
                domain = _infer_domain(q, a)
                tags = wiki_store.extract_tags(title, a)
                summary_text = re.sub(r"\s+", " ", a[:500]).strip()
                card = {
                    "id": wid,
                    "domain": domain,
                    "layer": "10_Wiki",
                    "title": title[:120],
                    "summary": summary_text[:500],
                    "body": a[:8000],
                    "source": "connect_ai_lab",
                    "storage_tier": "slim_runtime",
                    "ts": _now(),
                    "tags": tags + ["ConnectAI", "brain"],
                }
                if dry_run:
                    stats["added"] += 1
                    known_titles.add(norm_title)
                    continue
                if wid in known_ids:
                    wiki_store._upsert_slim_wiki(data, card)
                    stats["updated"] += 1
                else:
                    wiki_store._upsert_slim_wiki(data, card)
                    known_ids.add(wid)
                    stats["added"] += 1
                known_titles.add(norm_title)

    if not dry_run and (stats["added"] or stats["updated"]):
        wiki_store.save_knowledge(data)
    return stats


def main() -> int:
    import board_env

    board_env.load_board_env()
    p = argparse.ArgumentParser(description="Import Connect AI brain jsonl into gemma wiki")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--max-add", type=int, default=150)
    args = p.parse_args()
    result = import_jsonl(dry_run=args.dry_run, max_add=args.max_add)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
