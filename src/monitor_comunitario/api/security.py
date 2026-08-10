from secrets import compare_digest
from typing import Annotated

from fastapi import Cookie, Header, HTTPException, Request, status

from monitor_comunitario.core.config import get_settings
from monitor_comunitario.services.admin_session import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    verify_session_token,
)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def validate_admin_api_key(provided_api_key: str | None) -> None:
    """Validate the configured admin API key."""
    expected_api_key = get_settings().admin_api_key.strip()

    if not expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API key is not configured.",
        )

    if not provided_api_key or not compare_digest(provided_api_key.strip(), expected_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin API key.",
        )


def require_admin_api_key(
    request: Request,
    admin_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
    csrf_cookie: Annotated[str | None, Cookie(alias=CSRF_COOKIE_NAME)] = None,
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    """Require a valid admin session with CSRF protection."""
    settings = get_settings()
    expected_api_key = settings.admin_api_key.strip()

    if not expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API key is not configured.",
        )

    if not admin_session or not verify_session_token(expected_api_key, admin_session):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin API key.",
        )

    if request.method.upper() not in SAFE_METHODS and (
        not csrf_cookie or not csrf_header or not compare_digest(csrf_cookie, csrf_header)
    ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token is missing or invalid.",
            )


def require_admin_or_monitor_bot(
    request: Request,
    monitor_bot_key: Annotated[str | None, Header(alias="X-Monitor-Bot-Key")] = None,
    admin_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
    csrf_cookie: Annotated[str | None, Cookie(alias=CSRF_COOKIE_NAME)] = None,
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    """Allow the protected admin session or the dedicated internal bot key."""
    if monitor_bot_key is not None:
        expected_key = get_settings().monitor_bot_api_key.strip()
        if not expected_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Monitor bot API key is not configured.",
            )
        if not compare_digest(monitor_bot_key.strip(), expected_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid monitor bot API key.",
            )
        return

    require_admin_api_key(request, admin_session, csrf_cookie, csrf_header)


def require_monitor_bot_api_key(
    monitor_bot_key: Annotated[str | None, Header(alias="X-Monitor-Bot-Key")] = None,
) -> None:
    """Require the dedicated bot credential on internal bot-only routes."""
    expected_key = get_settings().monitor_bot_api_key.strip()
    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Monitor bot API key is not configured.",
        )
    if not monitor_bot_key or not compare_digest(monitor_bot_key.strip(), expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid monitor bot API key.",
        )
