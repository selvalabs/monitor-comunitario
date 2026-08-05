from secrets import compare_digest
from typing import Annotated

from fastapi import Cookie, Header, HTTPException, status

from monitor_comunitario.core.config import get_settings
from monitor_comunitario.services.admin_session import SESSION_COOKIE_NAME, verify_session_token


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
    x_admin_api_key: Annotated[str | None, Header(alias="X-Admin-API-Key")] = None,
    admin_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> None:
    """Require the legacy header or a valid HttpOnly admin session."""
    settings = get_settings()
    expected_api_key = settings.admin_api_key.strip()

    if not expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API key is not configured.",
        )

    if x_admin_api_key and compare_digest(x_admin_api_key.strip(), expected_api_key):
        return

    if admin_session and verify_session_token(expected_api_key, admin_session):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing admin API key.",
    )
