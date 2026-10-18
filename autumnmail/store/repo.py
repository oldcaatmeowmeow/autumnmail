from __future__ import annotations

import csv
import io
import re
import uuid
from datetime import datetime, timedelta, timezone

from .. import __version__, paths
from ..core import presets
from ..core.ics import build_ics
from ..security.dpapi import SecretStore
from . import db

TZ = timezone(timedelta(hours=8))
SECRET_LLM = "llm_api_key"
SECRET_ACCOUNT_PREFIX = "account:"

DEFAULT_SETTINGS: dict[str, str] = {
    "initialized": "false",
    "onboarded": "false",
    "demo_mode": "true",
    "scan_interval_min": "15",
    "scan_since_days": "90",
    "notify_enabled": "true",
    "quiet_hours": "22:00-08:00",
    "llm_provider": "deepseek",
    "llm_model": "deepseek-chat",
    "llm_base_url": "https://api.deepseek.com/v1",
    "llm_rules_only": "false",
    "theme": "light",
}

EVENT_SELECT = """
SELECT e.*, a.company, a.position, a.location AS app_location, a.status AS app_status
FROM events e
JOIN applications a ON a.id = e.application_id
"""

_secret_store: SecretStore | None = None


def secret_store() -> SecretStore:
    global _secret_store
    if _secret_store is None:
        _secret_store = SecretStore()
    return _secret_store


def reset_secret_store() -> None:
    global _secret_store
    _secret_store = None


def _event(row) -> dict:
    data = dict(row)
    data["needs_reply"] = bool(data.get("needs_reply"))
    return data


def _now() -> str:
    return datetime.now(TZ).isoformat(timespec="minutes")


def get_setting(key: str, default: str | None = None) -> str | None:
    conn = db.connect()
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default
    finally:
        conn.close()


def set_setting(key: str, value: str) -> None:
    conn = db.connect()
    try:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()


def get_settings() -> dict:
    raw = dict(DEFAULT_SETTINGS)
    conn = db.connect()
    try:
        for row in conn.execute("SELECT key, value FROM settings"):
            raw[row["key"]] = row["value"]
    finally:
        conn.close()

    key = secret_store().get(SECRET_LLM)
    return {
        "onboarded": raw.get("onboarded") == "true",
        "demo_mode": raw.get("demo_mode") == "true",
        "scan_interval_min": int(raw.get("scan_interval_min", "15")),
        "scan_since_days": int(raw.get("scan_since_days", "90")),
        "notify_enabled": raw.get("notify_enabled") == "true",
        "quiet_hours": raw.get("quiet_hours", "22:00-08:00"),
        "llm_provider": raw.get("llm_provider", "deepseek"),
        "llm_model": raw.get("llm_model", "deepseek-chat"),
        "llm_base_url": raw.get("llm_base_url", "https://api.deepseek.com/v1"),
        "llm_rules_only": raw.get("llm_rules_only") == "true",
        "theme": raw.get("theme", "light"),
        "llm_api_key_set": bool(key),
        "llm_api_key_preview": f"••••{key[-4:]}" if key else "",
    }


def update_settings(payload: dict) -> dict:
    bool_keys = {"onboarded", "notify_enabled", "llm_rules_only", "demo_mode"}
    int_keys = {"scan_interval_min", "scan_since_days"}
    str_keys = {"quiet_hours", "llm_provider", "llm_model", "llm_base_url", "theme"}

    conn = db.connect()
    try:
        for key in bool_keys:
            if key in payload and payload[key] is not None:
                conn.execute(
                    "INSERT INTO settings(key, value) VALUES(?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, "true" if payload[key] else "false"),
                )
        for key in int_keys:
            if key in payload and payload[key] is not None:
                value = max(1, int(payload[key]))
                if key == "scan_interval_min":
                    value = min(value, 1440)
                conn.execute(
                    "INSERT INTO settings(key, value) VALUES(?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, str(value)),
                )
        for key in str_keys:
            if key in payload and payload[key] is not None:
                conn.execute(
                    "INSERT INTO settings(key, value) VALUES(?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, str(payload[key])),
                )
        conn.commit()
    finally:
        conn.close()

    if payload.get("clear_api_key"):
        secret_store().delete(SECRET_LLM)
    elif payload.get("llm_api_key"):
        secret_store().set(SECRET_LLM, str(payload["llm_api_key"]))

    return get_settings()


def _public_account(row) -> dict:
    data = dict(row)
    data["enabled"] = bool(data.get("enabled"))
    return data


def list_accounts() -> list[dict]:
    conn = db.connect()
    try:
        rows = conn.execute(
            "SELECT a.id, a.email, a.provider, a.auth_type, a.display_name,"
            " a.imap_host, a.imap_port, a.scan_since, a.last_sync_at, a.enabled,"
            " a.created_at,"
            " (SELECT COUNT(*) FROM messages m WHERE m.account_id = a.id) AS message_count"
            " FROM accounts a ORDER BY a.created_at"
        ).fetchall()
        return [_public_account(row) for row in rows]
    finally:
        conn.close()


def get_account_raw(account_id: str) -> dict | None:
    conn = db.connect()
    try:
        row = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def add_account(
    email: str,
    auth_code: str,
    display_name: str | None = None,
    imap_host: str | None = None,
    imap_port: int | None = None,
) -> dict:
    email = email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise ValueError("邮箱地址格式不正确")

    provider_key = presets.detect_provider(email)
    provider = presets.provider_info(provider_key)
    if not provider.available:
        raise ValueError(provider.hint)
    if provider_key in {"qq", "163"} and not auth_code.strip():
        raise ValueError("请填写邮箱授权码（不是登录密码）")
    if provider_key == "imap" and not (imap_host or provider.imap_host):
        raise ValueError("请填写 IMAP 服务器地址")

    account_id = uuid.uuid4().hex[:12]
    now = _now()
    scan_since = (datetime.now(TZ) - timedelta(days=90)).isoformat(timespec="minutes")
    host = (imap_host or provider.imap_host or "").strip() or None
    port = int(imap_port or provider.imap_port)

    conn = db.connect()
    try:
        exists = conn.execute(
            "SELECT 1 FROM accounts WHERE email = ?", (email,)
        ).fetchone()
        if exists:
            raise ValueError("该邮箱已添加")
        conn.execute(
            """INSERT INTO accounts
               (id, email, provider, auth_type, display_name, imap_host, imap_port,
                scan_since, last_sync_at, enabled, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
            (
                account_id,
                email,
                provider_key,
                provider.auth_type,
                display_name or provider.label,
                host,
                port,
                scan_since,
                None,
                now,
            ),
        )
        conn.execute(
            "INSERT INTO settings(key, value) VALUES('onboarded', 'true') "
            "ON CONFLICT(key) DO UPDATE SET value = 'true'"
        )
        conn.commit()
    finally:
        conn.close()

    if auth_code:
        secret_store().set(SECRET_ACCOUNT_PREFIX + account_id, auth_code)
    return public_account(account_id)


def public_account(account_id: str) -> dict:
    conn = db.connect()
    try:
        row = conn.execute(
            "SELECT a.id, a.email, a.provider, a.auth_type, a.display_name,"
            " a.imap_host, a.imap_port, a.scan_since, a.last_sync_at, a.enabled,"
            " a.created_at,"
            " (SELECT COUNT(*) FROM messages m WHERE m.account_id = a.id) AS message_count"
            " FROM accounts a WHERE a.id = ?",
            (account_id,),
        ).fetchone()
        if not row:
            raise ValueError("账户不存在")
        return _public_account(row)
    finally:
        conn.close()


def delete_account(account_id: str) -> None:
    conn = db.connect()
    try:
        conn.execute("DELETE FROM messages WHERE account_id = ?", (account_id,))
        conn.execute("DELETE FROM sync_runs WHERE account_id = ?", (account_id,))
        conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        conn.commit()
    finally:
        conn.close()
    secret_store().delete(SECRET_ACCOUNT_PREFIX + account_id)


def upsert_messages(account_id: str, mails) -> int:
    """Store fetched messages. Returns the number of newly inserted rows."""
    now = _now()
    inserted = 0
    conn = db.connect()
    try:
        for mail in mails:
            message_key = f"{account_id}:{mail.uid}"
            exists = conn.execute(
                "SELECT 1 FROM messages WHERE id = ?", (message_key,)
            ).fetchone()
            values = (
                mail.uid,
                mail.folder or "INBOX",
                mail.message_id,
                mail.subject,
                mail.from_addr,
                mail.from_name,
                mail.received_at,
                mail.snippet,
                mail.body_text,
                mail.size,
                1 if mail.has_attachments else 0,
                now,
            )
            if exists:
                conn.execute(
                    """UPDATE messages SET uid = ?, folder = ?, message_id = ?,
                       subject = ?, from_addr = ?, from_name = ?, received_at = ?,
                       snippet = ?, body_text = ?, size = ?, has_attachments = ?,
                       synced_at = ? WHERE id = ?""",
                    values + (message_key,),
                )
            else:
                conn.execute(
                    """INSERT INTO messages
                       (uid, folder, message_id, subject, from_addr, from_name,
                        received_at, snippet, body_text, size, has_attachments,
                        synced_at, id, account_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    values + (message_key, account_id),
                )
                inserted += 1
        conn.commit()
    finally:
        conn.close()
    return inserted


def mark_synced(account_id: str, when: str | None = None) -> None:
    conn = db.connect()
    try:
        conn.execute(
            "UPDATE accounts SET last_sync_at = ? WHERE id = ?",
            (when or _now(), account_id),
        )
        conn.commit()
    finally:
        conn.close()


def start_sync_run(account_id: str) -> int:
    conn = db.connect()
    try:
        cursor = conn.execute(
            "INSERT INTO sync_runs(account_id, started_at, status) VALUES (?, ?, 'running')",
            (account_id, _now()),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def finish_sync_run(
    run_id: int,
    status: str,
    scanned: int = 0,
    inserted: int = 0,
    error: str | None = None,
) -> None:
    conn = db.connect()
    try:
        conn.execute(
            """UPDATE sync_runs SET finished_at = ?, status = ?, scanned = ?,
               inserted = ?, error = ? WHERE id = ?""",
            (_now(), status, scanned, inserted, error, run_id),
        )
        conn.commit()
    finally:
        conn.close()


def recent_messages(limit: int = 50, account_id: str | None = None) -> list[dict]:
    sql = (
        "SELECT id, account_id, subject, from_addr, from_name, received_at,"
        " snippet, has_attachments FROM messages"
    )
    params: list = []
    if account_id:
        sql += " WHERE account_id = ?"
        params.append(account_id)
    sql += " ORDER BY received_at DESC LIMIT ?"
    params.append(max(1, min(int(limit), 500)))

    conn = db.connect()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [
            {**dict(row), "has_attachments": bool(row["has_attachments"])}
            for row in rows
        ]
    finally:
        conn.close()


def counts() -> dict:
    conn = db.connect()
    try:
        return {
            "applications": conn.execute(
                "SELECT COUNT(*) AS c FROM applications"
            ).fetchone()["c"],
            "events": conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()["c"],
            "accounts": conn.execute("SELECT COUNT(*) AS c FROM accounts").fetchone()["c"],
            "messages": conn.execute("SELECT COUNT(*) AS c FROM messages").fetchone()["c"],
        }
    finally:
        conn.close()


def dashboard() -> dict:
    now = datetime.now(TZ)
    now_s = now.isoformat(timespec="minutes")
    week_s = (now + timedelta(days=7)).isoformat(timespec="minutes")
    week_ago_s = (now - timedelta(days=7)).isoformat(timespec="minutes")
    today = now.strftime("%Y-%m-%d")

    conn = db.connect()
    try:
        upcoming = [
            _event(row)
            for row in conn.execute(
                EVENT_SELECT
                + " WHERE e.event_time >= ? AND e.event_time <= ?"
                " AND e.status != 'skipped' ORDER BY e.event_time LIMIT 12",
                (now_s, week_s),
            )
        ]
        today_events = [
            _event(row)
            for row in conn.execute(
                EVENT_SELECT
                + " WHERE substr(e.event_time, 1, 10) = ?"
                " AND e.status != 'skipped' ORDER BY e.event_time",
                (today,),
            )
        ]
        needs_reply = [
            _event(row)
            for row in conn.execute(
                EVENT_SELECT
                + " WHERE e.needs_reply = 1 AND e.status = 'pending'"
                " ORDER BY COALESCE(e.event_time, e.deadline)",
            )
        ]
        rejections = [
            _event(row)
            for row in conn.execute(
                EVENT_SELECT
                + " WHERE e.category = '拒信' AND e.created_at >= ?"
                " ORDER BY e.created_at DESC",
                (week_ago_s,),
            )
        ]
        recent = [
            _event(row)
            for row in conn.execute(
                EVENT_SELECT + " ORDER BY e.created_at DESC, e.id DESC LIMIT 8"
            )
        ]
        active = conn.execute(
            "SELECT COUNT(*) AS c FROM applications WHERE status NOT IN ('已拒绝', '已结束')"
        ).fetchone()["c"]

        return {
            "stats": {
                "upcoming_7d": len(upcoming),
                "needs_reply": len(needs_reply),
                "new_rejections_7d": len(rejections),
                "active_applications": active,
            },
            "today": today_events,
            "upcoming": upcoming,
            "action_items": needs_reply,
            "recent": recent,
        }
    finally:
        conn.close()


def list_applications(status: str | None = None, q: str | None = None) -> list[dict]:
    now = datetime.now(TZ).isoformat(timespec="minutes")
    sql = """
    SELECT a.*,
      (SELECT COUNT(*) FROM events e WHERE e.application_id = a.id) AS event_count,
      (SELECT e.event_time FROM events e
         WHERE e.application_id = a.id AND e.event_time IS NOT NULL
           AND e.status != 'skipped' AND e.event_time >= ?
         ORDER BY e.event_time LIMIT 1) AS next_event_time,
      (SELECT e.category FROM events e
         WHERE e.application_id = a.id AND e.event_time IS NOT NULL
           AND e.status != 'skipped' AND e.event_time >= ?
         ORDER BY e.event_time LIMIT 1) AS next_category,
      (SELECT e.title FROM events e
         WHERE e.application_id = a.id AND e.event_time IS NOT NULL
           AND e.status != 'skipped' AND e.event_time >= ?
         ORDER BY e.event_time LIMIT 1) AS next_title
    FROM applications a
    WHERE 1 = 1
    """
    params: list = [now, now, now]
    if status and status != "全部":
        sql += " AND a.status = ?"
        params.append(status)
    if q:
        sql += " AND (a.company LIKE ? OR a.position LIKE ?)"
        like = f"%{q.strip()}%"
        params.extend([like, like])
    sql += (
        " ORDER BY CASE WHEN next_event_time IS NULL THEN 1 ELSE 0 END,"
        " next_event_time ASC, a.updated_at DESC"
    )

    conn = db.connect()
    try:
        return [dict(row) for row in conn.execute(sql, params)]
    finally:
        conn.close()


def get_application(app_id: int) -> dict | None:
    conn = db.connect()
    try:
        app_row = conn.execute(
            "SELECT * FROM applications WHERE id = ?", (app_id,)
        ).fetchone()
        if not app_row:
            return None
        events = [
            _event(row)
            for row in conn.execute(
                EVENT_SELECT
                + " WHERE e.application_id = ?"
                " ORDER BY COALESCE(e.event_time, e.deadline, e.created_at)",
                (app_id,),
            )
        ]
        message_ids = [e["message_id"] for e in events if e.get("message_id")]
        messages: dict[str, dict] = {}
        if message_ids:
            placeholders = ",".join("?" for _ in message_ids)
            for row in conn.execute(
                f"SELECT * FROM messages WHERE id IN ({placeholders})", message_ids
            ):
                messages[row["id"]] = dict(row)
        return {"application": dict(app_row), "events": events, "messages": messages}
    finally:
        conn.close()


def get_event(event_id: int) -> dict | None:
    conn = db.connect()
    try:
        row = conn.execute(EVENT_SELECT + " WHERE e.id = ?", (event_id,)).fetchone()
        return _event(row) if row else None
    finally:
        conn.close()


def list_events(from_iso: str, to_iso: str) -> list[dict]:
    conn = db.connect()
    try:
        rows = conn.execute(
            EVENT_SELECT
            + " WHERE (e.event_time BETWEEN ? AND ?)"
            " OR (e.deadline BETWEEN ? AND ?)"
            " ORDER BY COALESCE(e.event_time, e.deadline)",
            (from_iso, to_iso, from_iso, to_iso),
        ).fetchall()
        return [_event(row) for row in rows]
    finally:
        conn.close()


def _sync_app_status(conn, app_id: int) -> None:
    categories = [
        row["category"]
        for row in conn.execute(
            "SELECT category FROM events WHERE application_id = ? AND status != 'skipped'",
            (app_id,),
        )
    ]
    if any("拒" in c for c in categories):
        status = "已拒绝"
    elif any("Offer" in c or "录用" in c for c in categories):
        status = "已Offer"
    elif any("面" in c for c in categories):
        status = "面试中"
    elif any("测评" in c or "笔试" in c for c in categories):
        status = "测评中"
    else:
        status = "投递中"
    conn.execute(
        "UPDATE applications SET status = ?, updated_at = ? WHERE id = ?",
        (status, _now(), app_id),
    )


def update_event_status(event_id: int, status: str) -> dict | None:
    allowed = {"pending", "confirmed", "done", "skipped"}
    if status not in allowed:
        raise ValueError("无效的事件状态")
    conn = db.connect()
    try:
        row = conn.execute(
            "SELECT application_id FROM events WHERE id = ?", (event_id,)
        ).fetchone()
        if not row:
            return None
        conn.execute("UPDATE events SET status = ? WHERE id = ?", (status, event_id))
        _sync_app_status(conn, int(row["application_id"]))
        conn.commit()
    finally:
        conn.close()
    return get_event(event_id)


def review_queue() -> list[dict]:
    conn = db.connect()
    try:
        rows = conn.execute(
            EVENT_SELECT
            + " WHERE e.confidence < 0.8 AND e.status = 'pending'"
            " AND e.decided_by != 'human'"
            " ORDER BY e.confidence ASC, e.event_time"
        ).fetchall()
        return [_event(row) for row in rows]
    finally:
        conn.close()


def resolve_review(event_id: int, action: str, category: str | None = None) -> dict | None:
    conn = db.connect()
    try:
        current = conn.execute(
            "SELECT * FROM events WHERE id = ?", (event_id,)
        ).fetchone()
        if not current:
            return None
        app_id = int(current["application_id"])

        if action == "skip":
            conn.execute(
                "UPDATE events SET status = 'skipped', decided_by = 'human' WHERE id = ?",
                (event_id,),
            )
        else:
            if category:
                conn.execute(
                    "UPDATE events SET category = ? WHERE id = ?", (category, event_id)
                )
            conn.execute(
                "UPDATE events SET confidence = 1.0, decided_by = 'human' WHERE id = ?",
                (event_id,),
            )

        conn.execute(
            """INSERT INTO feedback(event_id, message_id, old_value, new_value, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                event_id,
                current["message_id"],
                f"{current['category']}|{current['confidence']}",
                f"{category or current['category']}|{action}",
                _now(),
            ),
        )
        _sync_app_status(conn, app_id)
        conn.commit()
    finally:
        conn.close()
    return get_event(event_id)


def export_csv() -> str:
    conn = db.connect()
    try:
        rows = conn.execute(EVENT_SELECT + " ORDER BY COALESCE(e.event_time, e.deadline)").fetchall()
    finally:
        conn.close()

    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(
        ["公司", "岗位", "阶段", "事件时间", "截止时间", "平台", "地点", "待回复", "状态", "置信度", "依据"]
    )
    for row in rows:
        event = _event(row)
        writer.writerow(
            [
                event.get("company", ""),
                event.get("position", ""),
                event.get("category", ""),
                event.get("event_time", ""),
                event.get("deadline", ""),
                event.get("platform", ""),
                event.get("location", ""),
                "是" if event.get("needs_reply") else "否",
                event.get("status", ""),
                event.get("confidence", ""),
                event.get("evidence", ""),
            ]
        )
    return buffer.getvalue()


def export_ics() -> str:
    conn = db.connect()
    try:
        rows = conn.execute(
            EVENT_SELECT
            + " WHERE e.event_time IS NOT NULL OR e.deadline IS NOT NULL"
            " ORDER BY COALESCE(e.event_time, e.deadline)"
        ).fetchall()
    finally:
        conn.close()
    return build_ics([_event(row) for row in rows])


def sync_mock() -> dict:
    now = _now()
    conn = db.connect()
    try:
        conn.execute("UPDATE accounts SET last_sync_at = ?", (now,))
        conn.commit()
    finally:
        conn.close()
    return {
        "ok": True,
        "scanned": 0,
        "new_events": 0,
        "message": "M0 骨架：同步任务已模拟完成，真实 IMAP 拉取将在 M1 接入。",
    }


def meta() -> dict:
    return {
        "version": __version__,
        "app": "秋信 AutumnMail",
        "data_dir": str(paths.data_dir()),
        "db_path": str(db.path()),
        "providers": [
            {
                "key": p.key,
                "label": p.label,
                "auth_type": p.auth_type,
                "imap_host": p.imap_host,
                "available": p.available,
                "hint": p.hint,
            }
            for p in presets.PROVIDERS.values()
        ],
    }


def reset_demo() -> bool:
    from ..core.seed import reset_demo as _reset

    ok = _reset()
    reset_secret_store()
    return ok


def initialize() -> None:
    """Seed demo data on first run only."""
    if get_setting("initialized") == "true":
        return
    from ..core.seed import seed_demo

    seed_demo(force=False)
