from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")
_db_path: Path | None = None


def configure(path: str | Path) -> Path:
    global _db_path
    _db_path = Path(path)
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    return _db_path


def path() -> Path:
    if _db_path is None:
        raise RuntimeError("Database is not configured")
    return _db_path


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(path(), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init() -> Path:
    conn = connect()
    try:
        conn.executescript(_SCHEMA_PATH.read_text("utf-8"))
        conn.commit()
    finally:
        conn.close()
    return path()
