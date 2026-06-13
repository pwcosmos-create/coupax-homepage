"""
젬마 사무실 지식 ↔ GitHub pwcosmos-swiki 자동 동기화.

  SWIKI_SYNC_ENABLED=1
  SWIKI_GIT_URL=https://github.com/pwcosmos-create/pwcosmos-swiki.git
  SWIKI_GIT_TOKEN=ghp_...   (또는 GITHUB_TOKEN)
  SWIKI_REPO_PATH=board/data/pwcosmos-swiki  (기본: data/pwcosmos-swiki)

  python scripts/agent_office_swiki_sync.py sync
  python scripts/agent_office_swiki_sync.py push --wiki-id wiki_office_1
  python scripts/agent_office_swiki_sync.py pull
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import uuid
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
DEFAULT_REPO = BOARD / "data" / "pwcosmos-swiki"
STATE_PATH = BOARD / "data" / "swiki_sync_state.json"
COUPAX_WIKI_SUBDIR = Path("10_Wiki") / "Topics" / "Coupax"
SAJU_WIKI_SUBDIR = Path("10_Wiki") / "Topics" / "Saju"
GRAPH_PATH = Path("20_Meta") / "Graph.json"
INDEX_PATH = Path("20_Meta") / "Index.md"

DEFAULT_GIT_URL = "https://github.com/pwcosmos-create/pwcosmos-swiki.git"


def _enabled() -> bool:
    return os.getenv("SWIKI_SYNC_ENABLED", "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _repo_path() -> Path:
    raw = os.getenv("SWIKI_REPO_PATH", "").strip()
    if raw:
        p = Path(raw)
        return p if p.is_absolute() else BOARD / p
    return DEFAULT_REPO


def _git_url() -> str:
    return os.getenv("SWIKI_GIT_URL", DEFAULT_GIT_URL).strip() or DEFAULT_GIT_URL


def _git_branch() -> str:
    return os.getenv("SWIKI_GIT_BRANCH", "main").strip() or "main"


def _git_token() -> str:
    return (
        os.getenv("SWIKI_GIT_TOKEN", "").strip()
        or os.getenv("GITHUB_TOKEN", "").strip()
    )


def _git_env() -> dict[str, str]:
    import base64

    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    token = _git_token()
    if token:
        basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        env["GIT_CONFIG_COUNT"] = "1"
        env["GIT_CONFIG_KEY_0"] = "http.https://github.com/.extraheader"
        env["GIT_CONFIG_VALUE_0"] = f"AUTHORIZATION: basic {basic}"
    return env


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _ensure_git_identity(repo: Path) -> None:
    if not (_run_git(["config", "user.email"], repo).stdout or "").strip():
        _run_git(
            ["config", "user.email", os.getenv("SWIKI_GIT_EMAIL", "office@coupax.co.kr")],
            repo,
        )
    if not (_run_git(["config", "user.name"], repo).stdout or "").strip():
        _run_git(
            ["config", "user.name", os.getenv("SWIKI_GIT_NAME", "Coupax Agent Office")],
            repo,
        )


def _run_git(args: list[str], cwd: Path, *, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_git_env(),
        timeout=int(os.getenv("SWIKI_GIT_TIMEOUT", "120")),
    )


def load_state() -> dict:
    import json_store

    default = {"synced_wiki_ids": [], "last_pull": "", "last_push": "", "last_error": ""}
    try:
        data = json_store.load_json(STATE_PATH, default=default)
    except json_store.JsonStoreError:
        return default
    if isinstance(data, dict):
        data.setdefault("synced_wiki_ids", [])
        return data
    return default


def save_state(state: dict) -> None:
    import json_store

    json_store.save_json(STATE_PATH, state)


def ensure_repo() -> Path:
    repo = _repo_path()
    branch = _git_branch()
    url = _git_url()

    if not (repo / ".git").is_dir():
        repo.parent.mkdir(parents=True, exist_ok=True)
        if repo.exists() and any(repo.iterdir()):
            raise RuntimeError(f"repo path exists but is not a git clone: {repo}")
        r = subprocess.run(
            ["git", "clone", "--depth", "1", "-b", branch, url, str(repo)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=_git_env(),
            timeout=int(os.getenv("SWIKI_GIT_TIMEOUT", "120")),
        )
        if r.returncode != 0:
            raise RuntimeError(f"git clone failed: {r.stderr or r.stdout}")
        return repo

    _ensure_git_identity(repo)
    _run_git(["fetch", "origin", branch], repo)
    _run_git(["checkout", branch], repo)
    pull = _run_git(["pull", "--rebase", "origin", branch], repo)
    if pull.returncode != 0:
        err = (pull.stderr or pull.stdout or "").lower()
        if "uncommitted" in err or "unstaged" in err:
            st = _run_git(["status", "--porcelain"], repo)
            if (st.stdout or "").strip():
                _run_git(["add", "-A"], repo)
                _run_git(
                    ["commit", "-m", "sync: coupax office pending before pull"],
                    repo,
                )
                pull = _run_git(["pull", "--rebase", "origin", branch], repo)
        if pull.returncode != 0:
            raise RuntimeError(f"git pull failed: {pull.stderr or pull.stdout}")
    return repo


def _slug_title(title: str, wiki_id: str) -> str:
    base = re.sub(r"[^\w가-힣]+", "_", (title or wiki_id)).strip("_")[:60]
    return base or wiki_id


def pick_category(card: dict) -> str:
    agent = (card.get("agent_primary") or "").strip()
    tags = [str(t).lower() for t in (card.get("tags") or [])]
    title = (card.get("title") or "").lower()
    if agent == "creator" or "블로그" in title:
        return "Projects"
    if agent == "rl" or "우선" in title or "결론" in title:
        return "Decisions"
    if agent in ("structurer", "speaker", "listener"):
        return "Skills"
    if agent == "etf_sync" or "etf" in tags or "배당" in tags:
        return "Topics"
    return "Topics"


def wiki_to_markdown(card: dict, *, rel_path: str) -> str:
    wiki_id = card.get("id") or "wiki_unknown"
    title = (card.get("title") or wiki_id).replace(".md", "")
    summary = (card.get("summary") or "").strip()
    body = (card.get("body") or "").strip()
    tags = card.get("tags") or []
    category = pick_category(card)
    today = datetime.now().date().isoformat()
    task_id = card.get("task_id", "")
    doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, wiki_id))

    tag_str = json.dumps(tags, ensure_ascii=False)
    return f"""---
id: {doc_id}
coupax_wiki_id: {wiki_id}
task_id: {task_id}
category: "[[10_Wiki/{category}]]"
source: {card.get("source") or "coupax-agent-office"}
agent_primary: {card.get("agent_primary") or ""}
agent_synth: {card.get("agent_synth") or ""}
confidence_score: 0.85
tags: {tag_str}
last_reinforced: {today}
synced_at: {_now()}
---

# [[{title}]]

## 📌 한 줄 통찰
> {summary or "젬마24 사무실 작업 완료 보고"}

## 📖 구조화된 지식
{body}

## 🔗 지식 연결
- **Parent:** [[10_Wiki/Topics/Coupax/Index]]
- **Office Task:** #{task_id}
- **Agents:** {card.get("agent_primary")} → {card.get("agent_synth")}
- **Path:** [[{rel_path.replace(".md", "")}]]
"""


def _coupax_dir(repo: Path) -> Path:
    d = repo / COUPAX_WIKI_SUBDIR
    d.mkdir(parents=True, exist_ok=True)
    index = d / "Index.md"
    if not index.is_file():
        index.write_text(
            "# Coupax Agent Office\n\n젬마24 사무실에서 자동 동기화된 Wiki 카드입니다.\n",
            encoding="utf-8",
        )
    return d


def _update_graph(repo: Path, card: dict, rel_path: str) -> None:
    graph_file = repo / GRAPH_PATH
    if graph_file.is_file():
        try:
            graph = json.loads(graph_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            graph = {"nodes": [], "links": []}
    else:
        graph = {"nodes": [], "links": []}
    graph.setdefault("nodes", [])
    graph.setdefault("links", [])

    node_id = card.get("id") or Path(rel_path).stem
    nodes = graph["nodes"]
    if not any(isinstance(n, dict) and n.get("id") == node_id for n in nodes):
        nodes.append(
            {
                "id": node_id,
                "label": (card.get("title") or node_id)[:80],
                "category": pick_category(card),
                "path": rel_path.replace("\\", "/"),
                "source": "coupax-office",
            }
        )

    coupax_hub = "Coupax_Office_Hub"
    if not any(isinstance(n, dict) and n.get("id") == coupax_hub for n in nodes):
        nodes.append(
            {
                "id": coupax_hub,
                "label": "Coupax Agent Office",
                "category": "Topics",
                "path": str(COUPAX_WIKI_SUBDIR / "Index.md").replace("\\", "/"),
            }
        )
    links = graph["links"]
    if not any(
        isinstance(l, dict)
        and l.get("source") == coupax_hub
        and l.get("target") == node_id
        for l in links
    ):
        links.append(
            {"source": coupax_hub, "target": node_id, "type": "office_sync"}
        )

    graph["last_updated"] = datetime.now().date().isoformat()
    graph_file.parent.mkdir(parents=True, exist_ok=True)
    graph_file.write_text(
        json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _update_index(repo: Path, card: dict, rel_path: str) -> None:
    index_file = repo / INDEX_PATH
    link = f"- [[{rel_path.replace('.md', '')}]] — {card.get('title', '')} ({_now()})"
    section = "## Coupax Agent Office (자동 동기화)"
    if index_file.is_file():
        content = index_file.read_text(encoding="utf-8")
    else:
        content = "# Knowledge Index\n"
    if section not in content:
        content = content.rstrip() + f"\n\n{section}\n{link}\n"
    elif link not in content:
        content = content.rstrip() + f"\n{link}\n"
    index_file.parent.mkdir(parents=True, exist_ok=True)
    index_file.write_text(content, encoding="utf-8")


def _wiki_subdir(card: dict) -> Path:
    domain = (card.get("domain") or "finance").strip()
    if domain == "saju-learn":
        return SAJU_WIKI_SUBDIR
    return COUPAX_WIKI_SUBDIR


def _topic_dir(repo: Path, card: dict) -> Path:
    sub = _wiki_subdir(card)
    d = repo / sub
    d.mkdir(parents=True, exist_ok=True)
    index = d / "Index.md"
    label = "Saju" if sub == SAJU_WIKI_SUBDIR else "Coupax"
    if not index.is_file():
        index.write_text(
            f"# {label} Agent Office\n\n젬마24 사무실에서 자동 동기화된 Wiki 카드입니다.\n",
            encoding="utf-8",
        )
    return d


def push_wiki_card(card: dict, *, skip_pull: bool = False, force: bool = False) -> bool:
    if not _enabled():
        return False
    wiki_id = card.get("id")
    if not wiki_id:
        return False
    domain = (card.get("domain") or "finance").strip()
    if domain == "saju-learn" and os.getenv("SWIKI_PUSH_SAJU", "0").strip() not in (
        "1",
        "true",
        "yes",
    ):
        return False

    state = load_state()

    try:
        repo = _repo_path()
        if skip_pull:
            if not (repo / ".git").is_dir():
                repo = ensure_repo()
        else:
            repo = ensure_repo()

        topic = _topic_dir(repo, card)
        sub = _wiki_subdir(card)
        fname = f"{wiki_id}.md"
        rel = str(sub / fname).replace("\\", "/")
        out_path = topic / fname
        out_path.write_text(wiki_to_markdown(card, rel_path=rel), encoding="utf-8")

        _update_graph(repo, card, rel)
        _update_index(repo, card, rel)

        _run_git(["add", str(sub), str(GRAPH_PATH), str(INDEX_PATH)], repo)
        st = _run_git(["status", "--porcelain"], repo)
        if not (st.stdout or "").strip():
            return True

        _ensure_git_identity(repo)
        tag = "Saju" if domain == "saju-learn" else "Coupax"
        msg = f"reinforce: [{tag}] {card.get('title', wiki_id)[:60]}"
        commit = _run_git(["commit", "-m", msg], repo)
        if commit.returncode != 0:
            if "nothing to commit" in (commit.stdout or "") + (commit.stderr or ""):
                return True
            raise RuntimeError(commit.stderr or commit.stdout)

        push = _run_git(["push", "origin", _git_branch()], repo)
        if push.returncode != 0:
            raise RuntimeError(push.stderr or push.stdout)

        synced = set(state.get("synced_wiki_ids") or [])
        synced.add(wiki_id)
        state["synced_wiki_ids"] = sorted(synced)
        state["last_push"] = _now()
        state["last_error"] = ""
        save_state(state)

        try:
            import agent_office_log

            agent_office_log.append_message(
                from_id="structurer",
                kind="system",
                text=f"[GitHub swiki 동기화] {wiki_id} → {rel}",
            )
        except Exception:
            pass
        return True
    except Exception as e:
        state["last_error"] = str(e)[:300]
        save_state(state)
        try:
            import agent_office_log

            agent_office_log.append_message(
                from_id="structurer",
                kind="system",
                text=f"[GitHub swiki 동기화 실패] {wiki_id}: {e!s}"[:400],
            )
        except Exception:
            pass
        return False


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta: dict = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip().strip('"')
        if k in ("coupax_wiki_id", "task_id", "agent_primary", "agent_synth", "source"):
            meta[k] = v
        if k == "tags":
            try:
                meta["tags"] = json.loads(v.replace("'", '"'))
            except json.JSONDecodeError:
                meta["tags"] = []
    return meta, parts[2]


def _should_import_md_to_slim_json(meta: dict, wiki_id: str) -> bool:
    """① 사무실·예약 보고는 GitHub만 — 슬림 JSON pull 제외."""
    wid = (wiki_id or "").strip()
    if wid.startswith(("wiki_office_", "wiki_pulse_")):
        return False
    src = (meta.get("source") or "").strip()
    if src in ("office", "reserved", "coupax-agent-office"):
        return False
    return True


def pull_from_repo() -> int:
    """GitHub swiki → gemma_knowledge.json (공개·선별 Wiki만). import 개수 반환."""
    if not _enabled():
        return 0
    import agent_office_wiki_store

    repo = ensure_repo()
    coupax = repo / COUPAX_WIKI_SUBDIR
    if not coupax.is_dir():
        return 0

    imported = 0
    data = agent_office_wiki_store.load_knowledge()
    known_ids = {w.get("id") for w in data.get("wiki") or [] if isinstance(w, dict)}

    for md in coupax.glob("*.md"):
        if md.name == "Index.md":
            continue
        text = md.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(text)
        wiki_id = meta.get("coupax_wiki_id") or md.stem
        if not _should_import_md_to_slim_json(meta, wiki_id):
            continue
        if wiki_id in known_ids:
            continue

        title_m = re.search(r"^#\s*\[\[(.+?)\]\]", body, re.M)
        title = title_m.group(1) if title_m else md.stem
        insight_m = re.search(r"## 📌 한 줄 통찰\s*\n>\s*(.+)", body)
        summary = insight_m.group(1).strip() if insight_m else ""
        knowledge_m = re.search(
            r"## 📖 구조화된 지식\s*\n(.*?)(?=\n## |\Z)", body, re.S
        )
        knowledge = knowledge_m.group(1).strip() if knowledge_m else body[:4000]

        try:
            task_id = int(meta.get("task_id") or 0)
        except (TypeError, ValueError):
            task_id = None

        card = {
            "id": wiki_id,
            "layer": "10_Wiki",
            "title": title[:120],
            "summary": summary[:500],
            "body": knowledge[:8000],
            "task_id": task_id,
            "agent_primary": meta.get("agent_primary", ""),
            "agent_synth": meta.get("agent_synth", ""),
            "source": "swiki_pull",
            "ts": _now(),
            "tags": meta.get("tags") or [],
        }
        data["wiki"].append(card)
        known_ids.add(wiki_id)
        imported += 1

    if imported:
        agent_office_wiki_store.save_knowledge(data)

    state = load_state()
    state["last_pull"] = _now()
    state["last_error"] = ""
    save_state(state)
    return imported


def sync_all() -> dict:
    """pull → local wiki push (미동기분) → pull."""
    import agent_office_wiki_store

    result = {"pulled": 0, "pushed": 0, "errors": []}
    try:
        ensure_repo()
        result["pulled"] = pull_from_repo()
    except Exception as e:
        result["errors"].append(f"pull: {e}")

    state = load_state()
    synced = set(state.get("synced_wiki_ids") or [])

    for card in agent_office_wiki_store.load_knowledge().get("wiki") or []:
        if not isinstance(card, dict):
            continue
        wid = card.get("id")
        if not wid:
            continue
        if wid in synced:
            continue
        if push_wiki_card(card, skip_pull=True):
            result["pushed"] += 1
        else:
            result["errors"].append(f"push failed: {wid}")

    try:
        result["pulled"] += pull_from_repo()
    except Exception as e:
        result["errors"].append(f"final pull: {e}")

    return result


def sync_pending() -> int:
    import agent_office_wiki_store

    n = 0
    state = load_state()
    synced = set(state.get("synced_wiki_ids") or [])
    for card in agent_office_wiki_store.load_knowledge().get("wiki") or []:
        if not isinstance(card, dict):
            continue
        wid = card.get("id")
        if wid and wid not in synced:
            if push_wiki_card(card):
                n += 1
    return n


def main() -> int:
    import board_env

    board_env.load_board_env()
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pull")
    sub.add_parser("sync")
    pr = sub.add_parser("push")
    pr.add_argument("--wiki-id", required=True)
    sub.add_parser("ensure")

    args = p.parse_args()
    if args.cmd == "ensure":
        print(ensure_repo())
        return 0
    if args.cmd == "pull":
        print(f"imported={pull_from_repo()}")
        return 0
    if args.cmd == "sync":
        print(json.dumps(sync_all(), ensure_ascii=False))
        return 0
    if args.cmd == "push":
        import agent_office_wiki_store

        for w in agent_office_wiki_store.load_knowledge().get("wiki") or []:
            if isinstance(w, dict) and w.get("id") == args.wiki_id:
                ok = push_wiki_card(w)
                print("ok" if ok else "fail")
                return 0 if ok else 1
        print("wiki not found")
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
