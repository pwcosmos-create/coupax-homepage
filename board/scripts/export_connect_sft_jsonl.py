"""
Connect AI Lab + Coupax gemma 지식 → SFT 학습용 JSONL (Unsloth / 장기 기억 탭).

  PYTHONPATH=scripts python scripts/export_connect_sft_jsonl.py
  PYTHONPATH=scripts python scripts/export_connect_sft_jsonl.py --tag pwcosmos-v591
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
_SCRIPTS = BOARD / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import agent_office_wiki_store as wiki_store  # noqa: E402
import import_connect_brain_jsonl as brain_imp  # noqa: E402

DEFAULT_LAB = Path(os.environ.get("USERPROFILE", "")) / "Desktop" / "connect ai lab"
PLAZA_RE = re.compile(r"^💡\s*광장에서 배움", re.M)
MIN_ANSWER = 120


def _lab() -> Path:
    raw = os.environ.get("CONNECT_AI_LAB_PATH", "").strip()
    return Path(raw) if raw else DEFAULT_LAB


def _key(q: str, a: str) -> str:
    return hashlib.sha1(f"{q.strip()}\n{a.strip()[:500]}".encode()).hexdigest()


def _from_brain_row(obj: dict) -> tuple[str, str] | None:
    pair = brain_imp._parse_row(obj)
    if not pair:
        return None
    q, a = pair
    if brain_imp._should_skip(q, a):
        return None
    return q, a


def _from_dpo_row(obj: dict) -> tuple[str, str] | None:
    q = (obj.get("prompt") or "").strip()
    a = (obj.get("chosen") or "").strip()
    if not q or not a:
        return None
    if brain_imp._should_skip(q, a):
        return None
    return q, a


def _from_wiki(card: dict) -> tuple[str, str] | None:
    title = (card.get("title") or "").strip()
    body = ((card.get("summary") or "") + "\n" + (card.get("body") or "")).strip()
    if len(body) < MIN_ANSWER:
        return None
    q = f"{title}에 대해 알려줘" if title else "이 지식을 설명해줘"
    return q, body[:8000]


def _record(q: str, a: str) -> dict:
    return {
        "conversations": [
            {"role": "user", "content": q},
            {"role": "assistant", "content": a},
        ]
    }


def export_sft(*, tag: str, include_wiki: bool = True) -> dict:
    lab = _lab()
    seen: set[str] = set()
    rows: list[dict] = []

    for path in brain_imp._brain_files(lab):
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "conversations" in obj:
                    pair = _from_brain_row(obj)
                else:
                    pair = _from_dpo_row(obj)
                if not pair:
                    continue
                q, a = pair
                k = _key(q, a)
                if k in seen:
                    continue
                seen.add(k)
                rows.append(_record(q, a))

    wiki_added = 0
    if include_wiki:
        data = wiki_store.load_knowledge()
        for card in data.get("wiki") or []:
            if not isinstance(card, dict):
                continue
            pair = _from_wiki(card)
            if not pair:
                continue
            q, a = pair
            k = _key(q, a)
            if k in seen:
                continue
            seen.add(k)
            rows.append(_record(q, a))
            wiki_added += 1

    out_name = f"{tag}-sft.jsonl"
    out_paths = [
        lab / out_name,
        BOARD / "data" / "pwcosmos-swiki" / "connect-ai" / out_name,
    ]
    for op in out_paths:
        op.parent.mkdir(parents=True, exist_ok=True)
        with op.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return {
        "tag": tag,
        "total": len(rows),
        "wiki_added": wiki_added,
        "outputs": [str(p) for p in out_paths],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tag", default="", help="모델 태그 (기본: pwcosmos-v{N})")
    p.add_argument("--no-wiki", action="store_true")
    args = p.parse_args()
    tag = (args.tag or "").strip()
    if not tag:
        # 장기 기억 UI 기본 규칙: pwcosmos-v{지식수}
        n = len(wiki_store.load_knowledge().get("wiki") or [])
        tag = f"pwcosmos-v{n}"
    out = export_sft(tag=tag, include_wiki=not args.no_wiki)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
