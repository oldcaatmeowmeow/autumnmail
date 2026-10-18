from __future__ import annotations

from fastapi import Header, HTTPException, Request

from ..security.token import token_matches


def require_token(
    request: Request, x_app_token: str | None = Header(default=None)
) -> None:
    expected = getattr(request.app.state, "token", "")
    if not expected:
        return
    if not token_matches(expected, x_app_token or ""):
        raise HTTPException(
            status_code=401,
            detail="本地访问令牌无效，请从桌面应用启动秋信。",
        )
