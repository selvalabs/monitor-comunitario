from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from monitor_comunitario.api.security import require_admin_api_key
from monitor_comunitario.core.config import get_settings
from monitor_comunitario.db.models import User
from monitor_comunitario.db.session import get_session
from monitor_comunitario.schemas.users import UserCreate, UserCreatedRead, UserRead, UserUpdate
from monitor_comunitario.services.hermes_events import create_hermes_event
from monitor_comunitario.services.member_access import generate_access_code, hash_access_code
from monitor_comunitario.services.rate_limit import (
    RateLimitExceeded,
    RateLimitUnavailable,
    enforce_rate_limit,
    rate_limit_key,
)

router = APIRouter(prefix="/users", tags=["users"])
admin_router = APIRouter(
    prefix="/admin/users",
    tags=["admin", "users"],
    dependencies=[Depends(require_admin_api_key)],
)

SessionDep = Annotated[Session, Depends(get_session)]


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


@router.post("", response_model=UserCreatedRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    request: Request,
    session: SessionDep,
) -> UserCreatedRead:
    """Create a monitored user/address record and return a one-time access code."""
    settings = get_settings()
    client_ip = request.headers.get(
        "x-forwarded-for",
        request.client.host if request.client else "unknown",
    )
    try:
        enforce_rate_limit(
            rate_limit_key("user-registration", client_ip),
            limit=settings.rate_limit_register_limit,
            window_seconds=settings.rate_limit_register_window_seconds,
        )
    except RateLimitExceeded as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Try again later.",
            headers={"Retry-After": str(error.retry_after)},
        ) from error
    except RateLimitUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration service temporarily unavailable.",
        ) from error

    access_code = generate_access_code()
    user = User(
        **payload.model_dump(),
        access_code_hash=hash_access_code(access_code),
        access_code_created_at=utc_now(),
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    if not user.notifications_approved:
        create_hermes_event(
            session=session,
            event_type="admin_approval_pending",
            channel="admin",
            recipient_phone="",
            intent="UNKNOWN_ESCALATE",
            template_key="human_escalation_v1",
            payload={
                "user_id": user.id,
                "municipality": user.municipality,
                "neighborhood": user.neighborhood,
            },
        )

    return UserCreatedRead(
        **UserRead.model_validate(user).model_dump(),
        access_code=access_code,
    )


@admin_router.get("", response_model=list[UserRead])
def list_users(
    session: SessionDep,
    include_inactive: bool = False,
) -> list[User]:
    """List registered users for admin usage.

    Inactive users are hidden by default because they should not receive
    outage notifications.
    """
    query = select(User).order_by(User.created_at.desc())

    if not include_inactive:
        query = query.where(User.is_active.is_(True))

    return list(session.scalars(query).all())


@admin_router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: int,
    session: SessionDep,
) -> User:
    """Return a single user by ID for admin usage."""
    user = session.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return user


@admin_router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    session: SessionDep,
) -> User:
    """Update a user record partially for admin usage."""
    user = session.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(user, field, value)

    user.updated_at = utc_now()

    session.add(user)
    session.commit()
    session.refresh(user)

    return user


@admin_router.delete("/{user_id}", response_model=UserRead)
def deactivate_user(
    user_id: int,
    session: SessionDep,
) -> User:
    """Deactivate a user without deleting historical records for admin usage."""
    user = session.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    user.is_active = False
    user.updated_at = utc_now()

    session.add(user)
    session.commit()
    session.refresh(user)

    return user
