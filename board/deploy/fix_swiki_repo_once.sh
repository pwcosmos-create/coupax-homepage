#!/usr/bin/env bash
set -euo pipefail
REPO="/home/ubuntu/coupax-homepage/board/data/pwcosmos-swiki"
BOARD="/home/ubuntu/coupax-homepage/board"

# Load board secrets for git HTTPS auth (SWIKI_GIT_TOKEN)
set -a
# shellcheck disable=SC1091
source "${BOARD}/.env"
set +a

rm -f "${REPO}/.git/index.lock"
cd "${REPO}"
git add -A
git commit -m "sync: coupax office pending before pull" || true

cd "${BOARD}"
PYTHONPATH=scripts SWIKI_SYNC_ENABLED=1 .venv/bin/python scripts/agent_office_swiki_sync.py pull

# Rebase onto origin and push consolidated local commit (auth via board_env)
PYTHONPATH=scripts SWIKI_SYNC_ENABLED=1 .venv/bin/python - <<'PY'
import board_env
board_env.load_board_env()
from agent_office_swiki_sync import ensure_repo, _run_git, _git_branch, load_state, save_state

repo = ensure_repo()
st = _run_git(["status", "-sb"], repo)
print(st.stdout or st.stderr)
push = _run_git(["push", "origin", _git_branch()], repo)
if push.returncode != 0:
    raise SystemExit(push.stderr or push.stdout)
print("bulk push OK")
state = load_state()
state["last_error"] = ""
save_state(state)
PY

PYTHONPATH=scripts SWIKI_SYNC_ENABLED=1 .venv/bin/python scripts/agent_office_swiki_sync.py sync 2>&1 | tail -1
