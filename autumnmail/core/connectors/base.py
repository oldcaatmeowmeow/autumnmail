from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RawMail:
    """A normalized message returned by any mailbox connector."""

    uid: str
    message_id: str
    subject: str
    from_addr: str
    from_name: str
    received_at: str
    body_text: str
    snippet: str
    folder: str = "INBOX"
    size: int = 0
    has_attachments: bool = False


class ConnectorError(RuntimeError):
    """A user-facing connection or protocol error."""
