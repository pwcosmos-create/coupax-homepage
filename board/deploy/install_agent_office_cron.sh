#!/usr/bin/env bash
# 에이전트 사무실 worker — mode_on 인 에이전트 주기 작업 (15분마다)
set -euo pipefail
BOARD="${BOARD_DIR:-/home/ubuntu/coupax-homepage/board}"
PY="${BOARD}/.venv/bin/python"
WORKER_LINE="*/5 * * * * cd ${BOARD} && AGENT_OFFICE_WORKER_ENABLED=1 ${PY} scripts/agent_office_worker.py >> logs/agent_office_worker.log 2>&1"
TASK_LINE="*/5 * * * * cd ${BOARD} && ${PY} scripts/agent_office_task_runner.py process --max 4 >> logs/agent_office_tasks.log 2>&1"

mkdir -p "${BOARD}/logs"
( crontab -l 2>/dev/null | grep -v "agent_office_worker.py" | grep -v "agent_office_task_runner.py" || true
  echo "${WORKER_LINE}"
  echo "${TASK_LINE}"
) | crontab -
echo "Installed:"
echo "${WORKER_LINE}"
echo "${TASK_LINE}"
