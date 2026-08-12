from secrets import compare_digest
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from monitor_comunitario.core.config import get_settings
from monitor_comunitario.db.models import Notification, User
from monitor_comunitario.db.session import get_session
from monitor_comunitario.schemas.member import (
    MemberAccessRead,
    MemberAccessRequest,
    MemberDeleteRequest,
)
from monitor_comunitario.schemas.notifications import NotificationRead
from monitor_comunitario.schemas.users import UserRead
from monitor_comunitario.services.data_retention import purge_user_data
from monitor_comunitario.services.member_access import verify_access_code
from monitor_comunitario.services.member_session import (
    MEMBER_CSRF_COOKIE_NAME,
    MEMBER_SESSION_COOKIE_NAME,
    MemberSessionUnavailable,
    generate_member_csrf_token,
    get_member_session_store,
)
from monitor_comunitario.services.rate_limit import (
    RateLimitExceeded,
    RateLimitUnavailable,
    enforce_rate_limit,
    rate_limit_key,
)
from monitor_comunitario.services.request_context import get_client_ip

router = APIRouter(prefix="/member", tags=["member"])

SessionDep = Annotated[Session, Depends(get_session)]


def _member_read(session: Session, user: User) -> MemberAccessRead:
    return MemberAccessRead(
        user=UserRead.model_validate(user),
        notifications=_list_member_notifications(session=session, user_id=user.id),
    )


def _authenticated_member(
    session: Session,
    member_session: str | None,
) -> User:
    store = get_member_session_store()
    if store is None or not member_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Member session is missing."
        )
    try:
        user_id = store.get_user_id(member_session)
    except MemberSessionUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Member session service temporarily unavailable.",
        ) from error
    user = (
        session.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
        if user_id
        else None
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Member session is invalid."
        )
    return user


def _require_member_csrf(
    csrf_cookie: str | None,
    csrf_header: str | None,
) -> None:
    if not csrf_cookie or not csrf_header or not compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token is missing or invalid."
        )


def _list_member_notifications(session: Session, user_id: int) -> list[NotificationRead]:
    """Return frontend-safe notifications for a member."""
    query = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(50)
    )
    notifications = list(session.scalars(query).all())

    return [NotificationRead.model_validate(notification) for notification in notifications]


@router.post("/access", response_model=MemberAccessRead)
def access_member_area(
    payload: MemberAccessRequest,
    request: Request,
    response: Response,
    session: SessionDep,
) -> MemberAccessRead:
    """Return member data and notifications after phone + access code validation."""
    phone = payload.phone.strip()
    settings = get_settings()
    client_ip = get_client_ip(request, trusted_proxy_ips=settings.trusted_proxy_ips)
    try:
        enforce_rate_limit(
            rate_limit_key("member-access", client_ip, phone),
            limit=settings.rate_limit_member_limit,
            window_seconds=settings.rate_limit_member_window_seconds,
        )
    except RateLimitExceeded as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many access attempts. Try again later.",
            headers={"Retry-After": str(error.retry_after)},
        ) from error
    except RateLimitUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Access service temporarily unavailable.",
        ) from error
    query = (
        select(User)
        .where(User.phone == phone, User.is_active.is_(True))
        .order_by(User.created_at.desc(), User.id.desc())
    )
    user = session.scalar(query)

    if user is None or not verify_access_code(payload.access_code, user.access_code_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone or access code.",
        )

    store = get_member_session_store()
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Member session service temporarily unavailable.",
        )
    try:
        member_session = store.create(user.id, get_settings().member_session_ttl_seconds)
    except MemberSessionUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Member session service temporarily unavailable.",
        ) from error
    response.set_cookie(
        key=MEMBER_SESSION_COOKIE_NAME,
        value=member_session,
        max_age=get_settings().member_session_ttl_seconds,
        httponly=True,
        secure=get_settings().app_env.lower() == "production",
        samesite="strict",
        path="/member",
    )
    response.set_cookie(
        key=MEMBER_CSRF_COOKIE_NAME,
        value=generate_member_csrf_token(),
        max_age=get_settings().member_session_ttl_seconds,
        httponly=False,
        secure=get_settings().app_env.lower() == "production",
        samesite="strict",
        path="/member",
    )
    return _member_read(session, user)


@router.get("/me", response_model=MemberAccessRead)
def get_member_area(
    session: SessionDep,
    member_session: Annotated[str | None, Cookie(alias=MEMBER_SESSION_COOKIE_NAME)] = None,
) -> MemberAccessRead:
    return _member_read(session, _authenticated_member(session, member_session))


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
def delete_member_session(
    response: Response,
    member_session: Annotated[str | None, Cookie(alias=MEMBER_SESSION_COOKIE_NAME)] = None,
    csrf_cookie: Annotated[str | None, Cookie(alias=MEMBER_CSRF_COOKIE_NAME)] = None,
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    _require_member_csrf(csrf_cookie, csrf_header)
    if member_session:
        store = get_member_session_store()
        if store:
            try:
                store.delete(member_session)
            except MemberSessionUnavailable as error:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Member session service temporarily unavailable.",
                ) from error
    settings = get_settings()
    response.delete_cookie(
        MEMBER_SESSION_COOKIE_NAME,
        path="/member",
        secure=settings.app_env.lower() == "production",
        samesite="strict",
    )
    response.delete_cookie(
        MEMBER_CSRF_COOKIE_NAME,
        path="/member",
        secure=settings.app_env.lower() == "production",
        samesite="strict",
    )


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_member_account(
    payload: MemberDeleteRequest,
    request: Request,
    response: Response,
    session: SessionDep,
    member_session: Annotated[str | None, Cookie(alias=MEMBER_SESSION_COOKIE_NAME)] = None,
    csrf_cookie: Annotated[str | None, Cookie(alias=MEMBER_CSRF_COOKIE_NAME)] = None,
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    """Permanently delete the authenticated member after re-authentication."""
    _require_member_csrf(csrf_cookie, csrf_header)
    user = _authenticated_member(session, member_session)
    phone = user.phone
    settings = get_settings()
    client_ip = get_client_ip(request, trusted_proxy_ips=settings.trusted_proxy_ips)
    try:
        enforce_rate_limit(
            rate_limit_key("member-delete", client_ip, phone),
            limit=settings.rate_limit_member_limit,
            window_seconds=settings.rate_limit_member_window_seconds,
        )
    except RateLimitExceeded as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many deletion attempts. Try again later.",
            headers={"Retry-After": str(error.retry_after)},
        ) from error
    except RateLimitUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Deletion service temporarily unavailable.",
        ) from error

    if not verify_access_code(payload.access_code, user.access_code_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone or access code.",
        )

    purge_user_data(session, user)
    session.commit()
    if member_session:
        store = get_member_session_store()
        if store:
            store.delete(member_session)
    settings = get_settings()
    response.delete_cookie(
        MEMBER_SESSION_COOKIE_NAME,
        path="/member",
        secure=settings.app_env.lower() == "production",
        samesite="strict",
    )
    response.delete_cookie(
        MEMBER_CSRF_COOKIE_NAME,
        path="/member",
        secure=settings.app_env.lower() == "production",
        samesite="strict",
    )
