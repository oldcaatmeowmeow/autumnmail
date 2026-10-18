"""Provider presets: turn an email address into connection defaults.

M0 only ships QQ / 163 (IMAP + authorization code). Outlook is recognized but
reported as a phase-2 provider.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    key: str
    label: str
    auth_type: str
    imap_host: str | None = None
    imap_port: int = 993
    available: bool = True
    hint: str = ""


PROVIDERS: dict[str, Provider] = {
    "qq": Provider(
        key="qq",
        label="QQ 邮箱",
        auth_type="app_password",
        imap_host="imap.qq.com",
        hint="设置 → 账户 → 开启 IMAP/SMTP 服务，生成授权码",
    ),
    "163": Provider(
        key="163",
        label="网易邮箱",
        auth_type="app_password",
        imap_host="imap.163.com",
        hint="设置 → POP3/SMTP/IMAP → 开启 IMAP/SMTP，获取客户端授权密码",
    ),
    "outlook": Provider(
        key="outlook",
        label="Outlook",
        auth_type="oauth",
        available=False,
        hint="Outlook 支持将在二期（M5）通过 Microsoft Graph 提供",
    ),
    "imap": Provider(
        key="imap",
        label="通用 IMAP",
        auth_type="app_password",
        imap_host=None,
        hint="在高级设置中填写 IMAP 服务器地址",
    ),
}

_QQ_DOMAINS = {"qq.com", "foxmail.com"}
_NETEASE_DOMAINS = {"163.com", "126.com", "yeah.net"}
_OUTLOOK_DOMAINS = {"outlook.com", "hotmail.com", "live.com", "msn.com"}


def detect_provider(email: str) -> str:
    domain = email.rsplit("@", 1)[-1].strip().lower() if "@" in email else ""
    if domain in _QQ_DOMAINS:
        return "qq"
    if domain in _NETEASE_DOMAINS:
        return "163"
    if domain in _OUTLOOK_DOMAINS:
        return "outlook"
    return "imap"


def provider_info(key: str) -> Provider:
    return PROVIDERS.get(key, PROVIDERS["imap"])
