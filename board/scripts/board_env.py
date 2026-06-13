"""Load board/.env into os.environ (cron/CLI; systemd uses EnvironmentFile)."""
from __future__ import annotations

import os
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]


def load_board_env(*, board: Path | None = None) -> None:
    path = (board or BOARD) / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if key:
            os.environ.setdefault(key, val)


def resolve_db_path(*, board: Path | None = None) -> Path:
    """`.env`의 BOARD_DB_PATH가 있어도 파일이 없으면 board/board.db로 폴백."""
    b = board or BOARD
    load_board_env(board=b)
    raw = (os.environ.get("BOARD_DB_PATH") or "").strip()
    if raw:
        p = Path(raw)
        if p.is_file():
            return p
    return b / "board.db"
