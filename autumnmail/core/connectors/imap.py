from __future__ import annotations

import html
import imaplib
import re
import socket
from datetime import date, datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr, parsedate_to_datetime
from html.parser import HTMLParser

from .base import ConnectorError, RawMail

TZ = timezone(timedelta(hours=8))
MAX_BODY = 200_000
_MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def imap_date(value: date) -> str:
    """IMAP wants 18-Oct-2026, independent of the Windows locale."""
    return f"{value.day:02d}-{_MONTHS[value.month - 1]}-{value.year}"


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif tag in ("br", "p", "div", "li", "tr", "h1", "h2", "h3"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        elif tag in ("p", "div", "li", "tr", "h1", "h2", "h3"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def _strip_html(value: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(value)
    except Exception:
        return html.unescape(re.sub(r"<[^>]+>", " ", value))
    return html.unescape("".join(parser.parts))


def _payload_text(part) -> str:
    try:
        content = part.get_content()
        if isinstance(content, str):
            return content
        return content.decode(part.get_content_charset() or "utf-8", errors="replace")
    except Exception:
        payload = part.get_payload(decode=True)
        if not payload:
            return ""
        return payload.decode(part.get_content_charset() or "utf-8", errors="replace")


def _extract_body(message) -> tuple[str, bool]:
    plain: list[str] = []
    rich: list[str] = []
    has_attachments = False

    if message.is_multipart():
        for part in message.walk():
            if part.get_filename():
                has_attachments = True
                continue
            content_type = part.get_content_type()
            if content_type == "text/plain":
                plain.append(_payload_text(part))
            elif content_type == "text/html":
                rich.append(_payload_text(part))
    else:
        if message.get_content_type() == "text/html":
            rich.append(_payload_text(message))
        else:
            plain.append(_payload_text(message))

    text = "\n".join(piece for piece in plain if piece.strip())
    if not text.strip() and rich:
        text = _strip_html("\n".join(rich))
    return text.strip()[:MAX_BODY], has_attachments


def _snippet(text: str, subject: str) -> str:
    value = re.sub(r"[\u200b-\u200d\ufeff]", "", text)
    value = re.sub(r"\s+", " ", value).strip()
    return (value or subject)[:220]


def parse_message(raw: bytes, uid: str, folder: str = "INBOX") -> RawMail:
    message = BytesParser(policy=policy.default).parsebytes(raw)
    subject = str(message.get("Subject", "")).strip()
    from_name, from_addr = parseaddr(str(message.get("From", "")))
    message_id = str(message.get("Message-ID", "")).strip()

    received = None
    header_date = message.get("Date")
    if header_date:
        try:
            received = parsedate_to_datetime(str(header_date))
        except (TypeError, ValueError, OverflowError):
            received = None
    if received is None:
        received = datetime.now(TZ)
    if received.tzinfo is None:
        received = received.replace(tzinfo=TZ)
    received_iso = received.astimezone(TZ).isoformat(timespec="minutes")

    body, has_attachments = _extract_body(message)
    return RawMail(
        uid=str(uid),
        message_id=message_id,
        subject=subject or "(无主题)",
        from_addr=from_addr,
        from_name=from_name or from_addr,
        received_at=received_iso,
        body_text=body,
        snippet=_snippet(body, subject),
        folder=folder,
        size=len(raw),
        has_attachments=has_attachments,
    )


def friendly_error(exc: Exception) -> str:
    text = str(exc)
    lower = text.lower()
    if "unsafe login" in lower:
        return "网易邮箱拒绝登录：请在网页版开启 IMAP，并使用客户端授权码。"
    if (
        "authenticationfailed" in lower
        or "login fail" in lower
        or "invalid credentials" in lower
        or "authentication failed" in lower
    ):
        return "登录失败：请确认使用的是邮箱授权码（不是登录密码），并已开启 IMAP 服务。"
    if "too many" in lower or "rate" in lower:
        return "登录过于频繁，请稍后再试。"
    if "select" in lower and "fail" in lower:
        return "无法打开收件箱：请确认邮箱已开启 IMAP 服务。"
    return f"IMAP 操作失败：{text}"


def _fetch_payload(data) -> bytes:
    for item in data or []:
        if isinstance(item, tuple) and len(item) >= 2:
            payload = item[1]
            if isinstance(payload, (bytes, bytearray)):
                return bytes(payload)
    return b""


class ImapConnector:
    """Read-only IMAP connector.

    Uses BODY.PEEK[] and a read-only mailbox so messages are never marked as
    seen, moved, or deleted.
    """

    def __init__(
        self,
        host: str,
        port: int = 993,
        user: str = "",
        password: str = "",
        timeout: float = 30.0,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.user = user
        self.password = password
        self.timeout = timeout
        self.conn: imaplib.IMAP4_SSL | None = None

    def __enter__(self) -> "ImapConnector":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def connect(self) -> None:
        try:
            self.conn = imaplib.IMAP4_SSL(self.host, self.port, timeout=self.timeout)
            self.conn.login(self.user, self.password)
        except imaplib.IMAP4.error as exc:
            raise ConnectorError(friendly_error(exc)) from exc
        except (OSError, socket.timeout) as exc:
            raise ConnectorError(
                f"无法连接 {self.host}:{self.port}，请检查网络或服务器地址。"
            ) from exc

        self._send_id()
        try:
            self.conn.select("INBOX", readonly=True)
        except imaplib.IMAP4.error as exc:
            raise ConnectorError(friendly_error(exc)) from exc

    def _send_id(self) -> None:
        """NetEase (163/126) requires the IMAP ID command before SELECT."""
        if not self.conn:
            return
        try:
            self.conn._simple_command(
                "ID",
                '("name" "AutumnMail" "version" "0.1.0" "vendor" "AutumnMail")',
            )
            self.conn._untagged_response("OK", [None], "ID")
        except Exception:
            # QQ and some servers do not implement ID; it is safe to continue.
            pass

    def close(self) -> None:
        if not self.conn:
            return
        try:
            self.conn.logout()
        except Exception:
            pass
        finally:
            self.conn = None

    def test(self) -> dict:
        with self:
            status, data = self.conn.status("INBOX", "(MESSAGES UIDNEXT)")
            if status != "OK":
                raise ConnectorError("无法读取收件箱状态。")
            text = data[0].decode(errors="replace") if data else ""
            count = re.search(r"MESSAGES\s+(\d+)", text)
            uidnext = re.search(r"UIDNEXT\s+(\d+)", text)
            return {
                "ok": True,
                "mailbox": "INBOX",
                "messages": int(count.group(1)) if count else None,
                "uidnext": int(uidnext.group(1)) if uidnext else None,
            }

    def fetch(self, since: date, limit: int = 200) -> list[RawMail]:
        with self:
            status, data = self.conn.uid("search", None, "SINCE", imap_date(since))
            if status != "OK":
                raise ConnectorError("搜索邮件失败，请稍后再试。")
            uids = data[0].split() if data and data[0] else []
            if limit:
                uids = uids[-limit:]

            messages: list[RawMail] = []
            for raw_uid in uids:
                uid = raw_uid.decode(errors="replace")
                status, payload = self.conn.uid("fetch", uid, "(BODY.PEEK[])")
                if status != "OK":
                    continue
                raw = _fetch_payload(payload)
                if raw:
                    messages.append(parse_message(raw, uid))
            return messages
