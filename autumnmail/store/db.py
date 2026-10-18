from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")
_db_path: Path | None = None

# Columns added after the first release. Keep migrations additive so an
# existing local database is never dropped or recreated.
_ADDITIVE_COLUMNS: dict[str, dict[str, str]] = {
    "accounts": {
        "imap_host": "TEXT",
        "imap_port": "INTEGER",
    },
    "messages": {
        "uid": "TEXT",
        "folder": "TEXT",
        "message_id": "TEXT",
        "size": "INTEGER",
        "has_attachments": "INTEGER NOT NULL DEFAULT 0",
        "synced_at": "TEXT",
    },
}


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


def _migrate(conn: sqlite3.Connection) -> None:
    for table, columns in _ADDITIVE_COLUMNS.items():
        existing = {
            row["name"] for row in conn.execute(f"PRAGMA table_info({table})")
        }
        for name, ddl in columns.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_uid ON messages (account_id, uid)"
    )


def init() -> Path:
    conn = connect()
    try:
        conn.executescript(_SCHEMA_PATH.read_text("utf-8"))
        _migrate(conn)
        conn.commit()
    finally:
        conn.close()
    return path()
