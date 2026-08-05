from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from monitor_comunitario.core.config import get_settings
from monitor_comunitario.db.models import Notification, User
from monitor_comunitario.db.session import get_session
from monitor_comunitario.schemas.member import MemberAccessRead, MemberAccessRequest
from monitor_comunitario.schemas.notifications import NotificationRead
from monitor_comunitario.schemas.users import UserRead
from monitor_comunitario.services.member_access import verify_access_code
from monitor_comunitario.services.rate_limit import (
    RateLimitExceeded,
    RateLimitUnavailable,
    enforce_rate_limit,
    rate_limit_key,
)

router = APIRouter(prefix="/member", tags=["member"])

SessionDep = Annotated[Session, Depends(get_session)]


def _list_member_notifications(session: Session, user_id: int) -> list[NotificationRead]:
    """Return frontend-safe notifications for a member."""
    query = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(50)
    )
    notifications = list(session.scalars(query).all())

    return [
        NotificationRead.model_validate(notification)
        for notification in notifications
    ]


@router.post("/access", response_model=MemberAccessRead)
def access_member_area(
    payload: MemberAccessRequest,
    request: Request,
    session: SessionDep,
) -> MemberAccessRead:
    """Return member data and notifications after phone + access code validation."""
    phone = payload.phone.strip()
    settings = get_settings()
    client_ip = request.headers.get(
        "x-forwarded-for",
        request.client.host if request.client else "unknown",
    )
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

    return MemberAccessRead(
        user=UserRead.model_validate(user),
        notifications=_list_member_notifications(session=session, user_id=user.id),
    )
