from __future__ import annotations

from datetime import date
from email.header import Header

import pytest

from autumnmail import paths
from autumnmail.core import sync
from autumnmail.core.connectors.base import RawMail
from autumnmail.core.connectors.imap import friendly_error, imap_date, parse_message
from autumnmail.store import db, repo


@pytest.fixture()
def database(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTUMNMAIL_DATA_DIR", str(tmp_path))
    paths.ensure_dirs()
    db.configure(paths.db_path())
    db.init()
    repo.reset_secret_store()
    yield
    repo.reset_secret_store()


class FakeConnector:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def fetch(self, since, limit=200):
        return [
            RawMail(
                uid="101",
                message_id="<demo-101@example.com>",
                subject="面试邀请",
                from_addr="campus@example.com",
                from_name="校园招聘",
                received_at="2026-10-18T10:00+08:00",
                body_text="邀请您参加 10 月 20 日 14:00 的二面。",
                snippet="邀请您参加 10 月 20 日 14:00 的二面。",
            )
        ]

    def test(self):
        return {"ok": True, "mailbox": "INBOX", "messages": 1, "uidnext": 102}


def test_sync_inserts_and_dedupes(database):
    account = repo.add_account("me@qq.com", "auth-code")
    first = sync.sync_account(account["id"], connector_factory=FakeConnector)
    assert first["ok"] is True
    assert first["new"] == 1

    second = sync.sync_account(account["id"], connector_factory=FakeConnector)
    assert second["ok"] is True
    assert second["new"] == 0

    messages = repo.recent_messages(account_id=account["id"])
    assert len(messages) == 1
    assert messages[0]["subject"] == "面试邀请"
    stored = repo.get_account_raw(account["id"])
    assert stored["last_sync_at"] is not None


def test_demo_account_is_skipped(database):
    from autumnmail.core.seed import seed_demo

    seed_demo(force=True)
    result = sync.sync_account("demo-account")
    assert result["ok"] is False
    assert "演示账户" in result["message"]


def test_sync_all_without_real_accounts(database):
    from autumnmail.core.seed import seed_demo

    seed_demo(force=True)
    result = sync.sync_all()
    assert result["ok"] is False
    assert result["message"] == "还没有添加真实邮箱"


def test_parse_message_plain():
    subject = Header("面试邀请", "utf-8").encode()
    raw = (
        "From: 校园招聘 <campus@example.com>\r\n"
        "To: me@qq.com\r\n"
        f"Subject: {subject}\r\n"
        "Date: Sun, 18 Oct 2026 10:00:00 +0800\r\n"
        "Message-ID: <abc@example.com>\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        "\r\n"
        "邀请您参加面试。\r\n"
    ).encode("utf-8")

    mail = parse_message(raw, "42")
    assert mail.subject == "面试邀请"
    assert mail.from_addr == "campus@example.com"
    assert mail.message_id == "<abc@example.com>"
    assert "邀请您参加面试" in mail.body_text
    assert mail.received_at.startswith("2026-10-18T10:00")


def test_parse_message_html():
    raw = (
        "From: HR <hr@example.com>\r\n"
        "Subject: 测评通知\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        "\r\n"
        "<html><body><p>请在 10 月 20 日前完成测评。</p></body></html>\r\n"
    ).encode("utf-8")

    mail = parse_message(raw, "43")
    assert "请在 10 月 20 日前完成测评" in mail.body_text
    assert "<p>" not in mail.body_text


def test_friendly_error():
    assert "授权码" in friendly_error(Exception("AUTHENTICATIONFAILED"))
    assert "网易" in friendly_error(Exception("Unsafe Login. Please contact"))


def test_imap_date():
    assert imap_date(date(2026, 10, 18)) == "18-Oct-2026"
