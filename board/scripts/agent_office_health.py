"""
에이전트 사무실·지식 동기화 상태 점검.

  python scripts/agent_office_health.py
  python scripts/agent_office_health.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))


def run_checks() -> dict:
    import board_env

    board_env.load_board_env()
    report: dict = {"ok": True, "checks": []}

    def add(name: str, ok: bool, detail: str = ""):
        report["checks"].append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            report["ok"] = False

    # JSON files
    for label, path in (
        ("tasks", BOARD / "data" / "agent_office_tasks.json"),
        ("feed", BOARD / "data" / "agent_office_feed.json"),
        ("registry", BOARD / "data" / "agent_registry.json"),
        ("knowledge", BOARD / "data" / "gemma_knowledge.json"),
    ):
        if path.is_file():
            try:
                json.loads(path.read_text(encoding="utf-8"))
                add(f"json:{label}", True, str(path))
            except json.JSONDecodeError as e:
                add(f"json:{label}", False, str(e))
        else:
            add(f"json:{label}", False, "missing")

    try:
        import agent_office_tasks

        tasks = agent_office_tasks.load_tasks().get("tasks") or []
        queued = sum(1 for t in tasks if isinstance(t, dict) and t.get("status") == "queued")
        in_prog = sum(1 for t in tasks if isinstance(t, dict) and t.get("status") == "in_progress")
        done = sum(1 for t in tasks if isinstance(t, dict) and t.get("status") == "done")
        add("tasks", True, f"total={len(tasks)} queued={queued} in_progress={in_prog} done={done}")
    except Exception as e:
        add("tasks", False, str(e))

    try:
        import agent_office_reserved_tasks

        rq = agent_office_reserved_tasks.count_reserved_queued()
        ra = agent_office_reserved_tasks.count_reserved_active()
        add("reserved_queue", ra <= 4, f"active={ra} queued_only={rq} (target 3)")
    except Exception as e:
        add("reserved_queue", False, str(e))

    try:
        import agent_office_saju_reserved_tasks

        rq = agent_office_saju_reserved_tasks.count_reserved_queued()
        ra = agent_office_saju_reserved_tasks.count_reserved_active()
        add("saju_reserved_queue", ra <= 4, f"active={ra} queued_only={rq} (target 3)")
    except Exception as e:
        add("saju_reserved_queue", False, str(e))

    try:
        import agent_office_wiki_store

        st = agent_office_wiki_store.knowledge_stats()
        add("wiki_local", True, f"wiki={st['wiki_count']} meta={st['meta_count']}")
    except Exception as e:
        add("wiki_local", False, str(e))

    try:
        import agent_office_web_search as ws

        add("web_search", ws.web_search_enabled(), ws.provider_status())
    except Exception as e:
        add("web_search", False, str(e))

    try:
        import blog_publish_scheduler as bps

        st = bps.status()
        detail = (
            f"enabled={st.get('enabled')} drafts={st.get('draft_count')} "
            f"scheduled={((st.get('scheduled') or {}).get('publish_at')) or '—'}"
        )
        add("blog_publish_scheduler", True, detail)
    except Exception as e:
        add("blog_publish_scheduler", False, str(e))

    swiki_enabled = os.getenv("SWIKI_SYNC_ENABLED", "0").strip() in ("1", "true", "yes")
    token = bool(os.getenv("SWIKI_GIT_TOKEN") or os.getenv("GITHUB_TOKEN"))
    repo = BOARD / "data" / "pwcosmos-swiki"
    add("swiki_config", True, f"enabled={swiki_enabled} token={'yes' if token else 'no'}")

    try:
        import agent_office_swiki_sync

        st = agent_office_swiki_sync.load_state()
        detail = (
            f"synced={len(st.get('synced_wiki_ids') or [])} "
            f"last_push={st.get('last_push') or '—'} "
            f"last_pull={st.get('last_pull') or '—'}"
        )
        if not swiki_enabled:
            add("swiki_sync", True, "disabled (set SWIKI_SYNC_ENABLED=1 + token to enable)")
        elif swiki_enabled and not token:
            add("swiki_sync", False, "SWIKI_SYNC_ENABLED but SWIKI_GIT_TOKEN missing")
        elif st.get("last_error"):
            add("swiki_sync", False, detail + f" err={st['last_error'][:80]}")
        elif (repo / ".git").is_dir():
            add("swiki_repo", True, str(repo))
        else:
            add("swiki_repo", False, "clone not present")
    except Exception as e:
        add("swiki_sync", False, str(e))

    db = Path(os.environ.get("BOARD_DB_PATH", str(BOARD / "board.db")))
    add("database", db.is_file(), str(db))

    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    report = run_checks()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=== Agent Office Health ===")
        print("OK" if report["ok"] else "ISSUES FOUND")
        for c in report["checks"]:
            mark = "OK" if c["ok"] else "FAIL"
            print(f"  [{mark}] {c['name']}: {c['detail']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
