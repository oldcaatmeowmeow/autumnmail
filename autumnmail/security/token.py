from __future__ import annotations

import hmac
import secrets


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_matches(expected: str, provided: str) -> bool:
    return bool(expected) and bool(provided) and hmac.compare_digest(expected, provided)
