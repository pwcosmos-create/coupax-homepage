"""
JSON 파일 원자적 읽기/쓰기 + 프로세스 간 잠금.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

try:
    import fcntl  # Unix

    _HAS_FCNTL = True
except ImportError:
    _HAS_FCNTL = False

try:
    import msvcrt  # Windows

    _HAS_MSVCRT = True
except ImportError:
    _HAS_MSVCRT = False


class JsonStoreError(Exception):
    pass


@contextmanager
def file_lock(path: Path, *, timeout: float = 10.0):
    path = Path(path)
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + timeout
    fp = open(lock_path, "a+b")
    try:
        while True:
            try:
                if _HAS_FCNTL:
                    fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                elif _HAS_MSVCRT:
                    fp.seek(0)
                    msvcrt.locking(fp.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    break
                break
            except (OSError, BlockingIOError):
                if time.time() >= deadline:
                    raise JsonStoreError(f"lock timeout: {lock_path}")
                time.sleep(0.05)
        yield
    finally:
        try:
            if _HAS_FCNTL:
                fcntl.flock(fp.fileno(), fcntl.LOCK_UN)
            elif _HAS_MSVCRT:
                fp.seek(0)
                msvcrt.locking(fp.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        fp.close()


def load_json(path: Path, *, default: Any) -> Any:
    path = Path(path)
    if not path.is_file():
        return default
    with file_lock(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise JsonStoreError(f"invalid JSON: {path}: {e}") from e


def save_json(path: Path, data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(path):
        fd, tmp_name = tempfile.mkstemp(
            prefix=path.name + ".",
            suffix=".tmp",
            dir=str(path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write("\n")
            os.replace(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise


def update_json(path: Path, *, default: Any, mutator: Callable[[Any], Any]) -> Any:
    path = Path(path)
    with file_lock(path):
        if path.is_file():
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                raise JsonStoreError(f"invalid JSON: {path}: {e}") from e
        else:
            data = default() if callable(default) else default

        data = mutator(data)
        fd, tmp_name = tempfile.mkstemp(
            prefix=path.name + ".",
            suffix=".tmp",
            dir=str(path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write("\n")
            os.replace(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
        return data
