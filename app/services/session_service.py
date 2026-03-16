"""Browser session helpers."""

from __future__ import annotations

import uuid

from fastapi import Request, Response


SESSION_COOKIE_NAME = "runzo_session_id"
SESSION_COOKIE_MAX_AGE = 60 * 60 * 24 * 30


def get_or_create_session_id(request: Request) -> tuple[str, bool]:
    """Read session id from cookie, or create one when missing."""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id:
        return session_id, False
    return str(uuid.uuid4()), True


def write_session_cookie(response: Response, session_id: str) -> None:
    """Write the session id back to browser cookie."""
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
