PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS accounts (
    id            TEXT PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    provider      TEXT NOT NULL,
    auth_type     TEXT NOT NULL,
    display_name  TEXT,
    scan_since    TEXT,
    last_sync_at  TEXT,
    enabled       INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS applications (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    company       TEXT NOT NULL,
    company_norm  TEXT,
    position      TEXT,
    location      TEXT,
    status        TEXT NOT NULL DEFAULT '投递中',
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id  INTEGER NOT NULL,
    category        TEXT NOT NULL,
    title           TEXT,
    event_time      TEXT,
    deadline        TEXT,
    duration_min    INTEGER,
    location        TEXT,
    link            TEXT,
    platform        TEXT,
    needs_reply     INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'pending',
    evidence        TEXT,
    message_id      TEXT,
    decided_by      TEXT NOT NULL DEFAULT 'demo',
    confidence      REAL,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (application_id) REFERENCES applications (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS messages (
    id          TEXT PRIMARY KEY,
    account_id  TEXT,
    subject     TEXT,
    from_addr   TEXT,
    from_name   TEXT,
    received_at TEXT,
    snippet     TEXT,
    body_text   TEXT,
    raw_link    TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS feedback (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id   INTEGER,
    message_id TEXT,
    old_value  TEXT,
    new_value  TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_app ON events (application_id);
CREATE INDEX IF NOT EXISTS idx_events_time ON events (event_time);
CREATE INDEX IF NOT EXISTS idx_events_status ON events (status);
CREATE INDEX IF NOT EXISTS idx_messages_account ON messages (account_id);
CREATE INDEX IF NOT EXISTS idx_apps_status ON applications (status);
