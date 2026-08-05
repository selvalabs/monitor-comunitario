from secrets import token_urlsafe
from typing import Annotated

from fastapi import APIRouter, Cookie, Header, Response, status

from monitor_comunitario.api.security import validate_admin_api_key
from monitor_comunitario.core.config import get_settings
from monitor_comunitario.services.admin_session import (
    CSRF_COOKIE_NAME,
    CSRF_TOKEN_LENGTH,
    SESSION_COOKIE_NAME,
    SESSION_TTL_SECONDS,
    create_session_token,
)

router = APIRouter(prefix="/admin", tags=["admin", "session"])


@router.post("/session")
def create_admin_session(
    response: Response,
    x_admin_api_key: Annotated[str | None, Header(alias="X-Admin-API-Key")] = None,
) -> dict[str, bool]:
    """Exchange the admin key for a short-lived HttpOnly session cookie."""
    validate_admin_api_key(x_admin_api_key)
    settings = get_settings()
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token_urlsafe(CSRF_TOKEN_LENGTH),
        max_age=SESSION_TTL_SECONDS,
        httponly=False,
        secure=settings.app_env.lower() == "production",
        samesite="strict",
        path="/",
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_token(settings.admin_api_key),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=settings.app_env.lower() == "production",
        samesite="strict",
        path="/",
    )
    return {"authenticated": True}


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_session(
    response: Response,
    _: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> None:
    """Clear the current admin session cookie."""
    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        path="/",
        secure=get_settings().app_env.lower() == "production",
        samesite="strict",
    )
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=get_settings().app_env.lower() == "production",
        samesite="strict",
    )
