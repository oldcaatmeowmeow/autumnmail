from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "AutumnMail"


def data_dir() -> Path:
    """Return the per-user local data directory.

    Overridable with AUTUMNMAIL_DATA_DIR (used by tests and portable mode).
    """
    override = os.environ.get("AUTUMNMAIL_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / f".{APP_NAME.lower()}"


def ensure_dirs() -> dict[str, Path]:
    root = data_dir()
    dirs = {name: root / name for name in ("logs", "exports", "cache", "backups")}
    root.mkdir(parents=True, exist_ok=True)
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return {"root": root, **dirs}


def db_path() -> Path:
    return data_dir() / "data.db"


def secrets_path() -> Path:
    return data_dir() / "secrets.json"
