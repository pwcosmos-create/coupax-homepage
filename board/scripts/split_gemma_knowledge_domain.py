"""
통합 젬마 기억에서 domain 별로 파일 분리 (차후 물리 분리용).

  python scripts/split_gemma_knowledge_domain.py export saju-learn
  python scripts/split_gemma_knowledge_domain.py export saju-learn --remove
  python scripts/split_gemma_knowledge_domain.py export finance --out data/gemma_knowledge_finance.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_wiki_store


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("export")
    ex.add_argument("domain", choices=[agent_office_wiki_store.DOMAIN_FINANCE, agent_office_wiki_store.DOMAIN_SAJU])
    ex.add_argument("--out", default="")
    ex.add_argument(
        "--remove",
        action="store_true",
        help="통합 gemma_knowledge.json 에서 해당 domain 항목 제거",
    )
    sub.add_parser("stats")

    args = p.parse_args()
    if args.cmd == "stats":
        print(json.dumps(agent_office_wiki_store.knowledge_stats(), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "export":
        out = Path(args.out) if args.out else None
        result = agent_office_wiki_store.split_domain_to_file(
            args.domain, out, remove_from_unified=args.remove
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
