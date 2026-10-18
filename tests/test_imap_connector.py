from __future__ import annotations

from datetime import date

from autumnmail.core.connectors import imap as imap_module
from autumnmail.core.connectors.imap import ImapConnector


class FakeImap:
    instances: list["FakeImap"] = []

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.commands: list[tuple] = []
        self.selected = None
        self.logged_out = False
        FakeImap.instances.append(self)

    def login(self, user, password):
        self.user = user
        self.password = password
        return "OK", [b"ok"]

    def _simple_command(self, *args):
        self.commands.append(args)
        return "OK", [b"ok"]

    def _untagged_response(self, *args):
        return "OK", [b"ok"]

    def select(self, mailbox, readonly=False):
        self.selected = (mailbox, readonly)
        return "OK", [b"1"]

    def status(self, mailbox, what):
        return "OK", [b"INBOX (MESSAGES 3 UIDNEXT 4)"]

    def uid(self, command, *args):
        self.commands.append(("uid", command, args))
        if command.lower() == "search":
            return "OK", [b"1 2 3"]
        if command.lower() == "fetch":
            uid = args[0]
            raw = (
                "From: HR <hr@example.com>\r\n"
                f"Subject: 面试邀请 {uid}\r\n"
                "Date: Sun, 18 Oct 2026 10:00:00 +0800\r\n"
                f"Message-ID: <m{uid}@example.com>\r\n"
                "Content-Type: text/plain; charset=utf-8\r\n"
                "\r\n"
                f"邀请 {uid}\r\n"
            ).encode("utf-8")
            return "OK", [(b"header", raw)]
        return "OK", [b""]

    def logout(self):
        self.logged_out = True
        return "BYE", [b"bye"]


def test_fetch_is_read_only(monkeypatch):
    FakeImap.instances.clear()
    monkeypatch.setattr(imap_module.imaplib, "IMAP4_SSL", FakeImap)

    connector = ImapConnector("imap.qq.com", 993, "me@qq.com", "secret")
    mails = connector.fetch(date(2026, 10, 18), limit=2)

    assert len(mails) == 2
    assert mails[0].subject == "面试邀请 2"
    assert mails[1].subject == "面试邀请 3"

    instance = FakeImap.instances[0]
    assert instance.selected == ("INBOX", True)
    assert instance.logged_out is True

    fetch_calls = [
        call for call in instance.commands if call[0] == "uid" and call[1].lower() == "fetch"
    ]
    assert fetch_calls
    assert all("BODY.PEEK[]" in call[2][1] for call in fetch_calls)

    search_calls = [
        call for call in instance.commands if call[0] == "uid" and call[1].lower() == "search"
    ]
    assert search_calls
    assert "SINCE" in search_calls[0][2]


def test_connection_reports_counts(monkeypatch):
    FakeImap.instances.clear()
    monkeypatch.setattr(imap_module.imaplib, "IMAP4_SSL", FakeImap)

    result = ImapConnector("imap.qq.com", 993, "me@qq.com", "secret").test()
    assert result == {
        "ok": True,
        "mailbox": "INBOX",
        "messages": 3,
        "uidnext": 4,
    }
