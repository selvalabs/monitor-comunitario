import hmac
import time
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from monitor_comunitario.api.security import require_admin_api_key, require_admin_or_monitor_bot
from monitor_comunitario.core.config import get_settings
from monitor_comunitario.db.models import User
from monitor_comunitario.db.session import get_session
from monitor_comunitario.schemas.users import (
    EmailVerificationRequest,
    PendingRegistrationAdminRead,
    PendingRegistrationResendRequest,
    RegistrationPendingRead,
    UserCreate,
    UserCreatedRead,
    UserRead,
    UserUpdate,
)
from monitor_comunitario.services.email_verification import (
    EmailVerificationUnavailable,
    generate_otp,
    get_pending_registration_store,
    hash_otp,
    normalize_email,
)
from monitor_comunitario.services.hermes_events import create_hermes_event
from monitor_comunitario.services.member_access import generate_access_code, hash_access_code
from monitor_comunitario.services.rate_limit import (
    RateLimitExceeded,
    RateLimitUnavailable,
    enforce_rate_limit,
    rate_limit_key,
)
from monitor_comunitario.services.request_context import get_client_ip

router = APIRouter(prefix="/users", tags=["users"])
admin_router = APIRouter(
    prefix="/admin/users",
    tags=["admin", "users"],
    dependencies=[Depends(require_admin_api_key)],
)
registration_admin_router = APIRouter(
    prefix="/admin/registrations",
    tags=["admin", "registrations"],
    dependencies=[Depends(require_admin_or_monitor_bot)],
)

SessionDep = Annotated[Session, Depends(get_session)]


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


def _normalize_phone(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def _create_verified_user(session: Session, data: dict[str, Any]) -> tuple[User, str]:
    access_code = generate_access_code()
    user_data = {
        key: value
        for key, value in data.items()
        if key
        not in {
            "email",
            "otp_hash",
            "attempts",
            "email_verified",
            "email_delivery_id",
            "email_last_sent_at",
        }
    }
    user = User(
        **user_data,
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
    return user, access_code


@router.post(
    "",
    response_model=UserCreatedRead | RegistrationPendingRead,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    payload: UserCreate,
    request: Request,
    response: Response,
    session: SessionDep,
) -> UserCreatedRead | RegistrationPendingRead:
    """Create a user locally or start verified registration in production."""
    settings = get_settings()
    client_ip = get_client_ip(request, trusted_proxy_ips=settings.trusted_proxy_ips)
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

    if not settings.email_verification_enabled:
        user, access_code = _create_verified_user(
            session,
            {**payload.model_dump(exclude={"email"}), "phone": _normalize_phone(payload.phone)},
        )
        return UserCreatedRead(
            **UserRead.model_validate(user).model_dump(), access_code=access_code
        )

    email = normalize_email(payload.email)
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A valid email is required."
        )
    store = get_pending_registration_store()
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration verification is temporarily unavailable.",
        )
    phone = _normalize_phone(payload.phone)
    otp = generate_otp()
    pending = {
        **payload.model_dump(exclude={"email", "phone"}),
        "email": email,
        "phone": phone,
        "otp_hash": hash_otp(otp),
        "attempts": 0,
        "email_verified": False,
    }
    try:
        store.save(email, phone, pending, settings.email_verification_ttl_seconds)
        from monitor_comunitario.services.email_verification import send_verification_email

        delivery_id = send_verification_email(email=email, otp=otp)
        pending["email_last_sent_at"] = time.time()
        if delivery_id:
            pending["email_delivery_id"] = delivery_id
        store.save(email, phone, pending, settings.email_verification_ttl_seconds)
    except EmailVerificationUnavailable as error:
        store.delete(email, phone)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration verification is temporarily unavailable.",
        ) from error
    response.status_code = status.HTTP_202_ACCEPTED
    return RegistrationPendingRead(message="Confira seu e-mail para continuar o cadastro.")


@router.post("/verify-email", response_model=RegistrationPendingRead)
def verify_email(
    payload: EmailVerificationRequest,
    session: SessionDep,
) -> RegistrationPendingRead:
    """Verify email OTP and enqueue the deterministic WhatsApp confirmation for Hermes."""
    settings = get_settings()
    if not settings.email_verification_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Email verification is disabled."
        )
    email = normalize_email(payload.email)
    store = get_pending_registration_store()
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration verification is temporarily unavailable.",
        )
    try:
        pending = store.load(email)
    except EmailVerificationUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration verification is temporarily unavailable.",
        ) from error
    if pending is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification request expired or not found.",
        )
    if pending.get("attempts", 0) >= settings.email_verification_max_attempts:
        store.delete(email, pending["phone"])
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many verification attempts."
        )
    if not hmac.compare_digest(str(pending.get("otp_hash", "")), hash_otp(payload.otp)):
        pending["attempts"] = int(pending.get("attempts", 0)) + 1
        store.save(email, pending["phone"], pending, settings.email_verification_ttl_seconds)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code."
        )
    pending["email_verified"] = True
    store.save(email, pending["phone"], pending, settings.email_verification_ttl_seconds)
    create_hermes_event(
        session=session,
        event_type="member_phone_confirmation_requested",
        channel="whatsapp",
        recipient_phone=pending["phone"],
        intent="ACCESS_MEMBER_AREA",
        template_key="member_phone_confirmation_v1",
        payload={"name": pending["name"], "url": settings.member_area_url},
    )
    return RegistrationPendingRead(
        status="pending_phone_verification",
        message="E-mail confirmado. Responda OK à mensagem no WhatsApp para ativar o cadastro.",
    )


def _pending_registration_read(payload: dict[str, Any]) -> PendingRegistrationAdminRead:
    email_verified = bool(payload.get("email_verified", False))
    return PendingRegistrationAdminRead(
        email=normalize_email(str(payload.get("email", ""))),
        phone=str(payload.get("phone", "")),
        name=str(payload.get("name", "")),
        email_verified=email_verified,
        email_delivery_id=str(payload.get("email_delivery_id", "")),
        status=("pending_phone_verification" if email_verified else "pending_email_verification"),
    )


@registration_admin_router.get("/pending", response_model=list[PendingRegistrationAdminRead])
def list_pending_registrations() -> list[PendingRegistrationAdminRead]:
    """List registration state for the operator without OTP material."""
    store = get_pending_registration_store()
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration verification is temporarily unavailable.",
        )
    try:
        return [_pending_registration_read(item) for item in store.list_pending()]
    except EmailVerificationUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration verification is temporarily unavailable.",
        ) from error


@registration_admin_router.post(
    "/pending/resend",
    response_model=PendingRegistrationAdminRead,
)
def resend_pending_registration_email(
    payload: PendingRegistrationResendRequest,
) -> PendingRegistrationAdminRead:
    """Resend the approved email OTP without returning the OTP to the operator."""
    settings = get_settings()
    store = get_pending_registration_store()
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration verification is temporarily unavailable.",
        )
    email = normalize_email(payload.email)
    try:
        pending = store.load(email)
    except EmailVerificationUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration verification is temporarily unavailable.",
        ) from error
    if pending is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending registration not found.",
        )
    if pending.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already verified for this registration.",
        )

    last_sent_at = float(pending.get("email_last_sent_at", 0))
    retry_after = int(
        last_sent_at + settings.email_verification_resend_cooldown_seconds - time.time()
    )
    if retry_after > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Confirmation email resend is temporarily rate limited.",
            headers={"Retry-After": str(retry_after)},
        )

    otp = generate_otp()
    pending["otp_hash"] = hash_otp(otp)
    pending["attempts"] = 0
    try:
        from monitor_comunitario.services.email_verification import send_verification_email

        delivery_id = send_verification_email(email=email, otp=otp)
        pending["email_last_sent_at"] = time.time()
        pending["email_delivery_id"] = delivery_id or ""
        store.save(
            email,
            str(pending["phone"]),
            pending,
            settings.email_verification_ttl_seconds,
        )
    except EmailVerificationUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registration verification is temporarily unavailable.",
        ) from error
    return _pending_registration_read(pending)


@router.post("/internal/hermes/phone-confirmation", include_in_schema=False)
def hermes_phone_confirmation(
    payload: dict[str, Any],
    request: Request,
    session: SessionDep,
) -> dict[str, str]:
    """Apply a signed phone-confirmation result received from Hermes."""
    settings = get_settings()
    provided_secret = request.headers.get("X-Hermes-Callback-Secret", "")
    if not settings.hermes_callback_secret or not hmac.compare_digest(
        provided_secret, settings.hermes_callback_secret
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Hermes callback secret.",
        )

    phone = _normalize_phone(str(payload.get("phone", "")))
    reply = str(payload.get("reply", "")).strip().upper()
    store = get_pending_registration_store()
    if store is None or not phone:
        return {"status": "ignored"}
    pending = store.load_by_phone(phone)
    if pending is None or not pending.get("email_verified"):
        return {"status": "ignored"}
    if reply == "CANCELAR":
        store.delete(pending["email"], phone)
        return {"status": "cancelled"}
    if reply != "OK":
        return {"status": "ignored"}

    user, access_code = _create_verified_user(session, pending)
    store.delete(pending["email"], phone)
    create_hermes_event(
        session=session,
        event_type="member_phone_confirmation_completed",
        channel="whatsapp",
        recipient_phone=phone,
        intent="ACCESS_MEMBER_AREA",
        template_key="member_access_code_v1",
        payload={"name": user.name, "access_code": access_code, "url": settings.member_area_url},
    )
    return {"status": "confirmed"}


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
