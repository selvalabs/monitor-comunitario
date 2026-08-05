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
    x_admin_api_key: Annotated[str | None, Header(alias="X-Admin-API-Key")] = None,
    admin_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
    csrf_cookie: Annotated[str | None, Cookie(alias=CSRF_COOKIE_NAME)] = None,
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    """Require the legacy header or a valid session with CSRF protection."""
    settings = get_settings()
    expected_api_key = settings.admin_api_key.strip()

    if not expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API key is not configured.",
        )

    if x_admin_api_key and compare_digest(x_admin_api_key.strip(), expected_api_key):
        return

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