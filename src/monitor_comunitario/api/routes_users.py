import asyncio
import contextlib
import hmac
from datetime import UTC, datetime
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from monitor_comunitario.api.security import require_admin_api_key
from monitor_comunitario.core.config import get_settings
from monitor_comunitario.db.models import User
from monitor_comunitario.db.session import get_session
from monitor_comunitario.notifications.evolution_provider import (
    EvolutionMessage,
    EvolutionNotificationProvider,
)
from monitor_comunitario.schemas.users import (
    EmailVerificationRequest,
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
from monitor_comunitario.services.hermes_catalog import get_template
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

SessionDep = Annotated[Session, Depends(get_session)]


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


def _normalize_phone(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def _send_whatsapp(phone: str, text: str) -> None:
    settings = get_settings()
    if not settings.evolution_enabled:
        raise EmailVerificationUnavailable("Evolution provider is disabled")
    provider = EvolutionNotificationProvider(
        base_url=settings.evolution_base_url,
        api_key=settings.evolution_api_key,
        instance=settings.evolution_instance,
    )
    asyncio.run(provider.send_text(EvolutionMessage(phone=phone, text=text)))


def _create_verified_user(session: Session, data: dict[str, Any]) -> tuple[User, str]:
    access_code = generate_access_code()
    user_data = {
        key: value
        for key, value in data.items()
        if key not in {"email", "otp_hash", "attempts", "email_verified"}
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

        send_verification_email(email=email, otp=otp)
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
    request: Request,
    session: SessionDep,
) -> RegistrationPendingRead:
    """Verify email OTP and send the deterministic WhatsApp confirmation."""
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
    template = get_template("member_phone_confirmation_v1")
    text = template.body.format(name=pending["name"], url=settings.member_area_url)
    try:
        _send_whatsapp(pending["phone"], text)
    except (EmailVerificationUnavailable, ValueError, OSError, httpx.HTTPError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Phone verification is temporarily unavailable.",
        ) from error
    return RegistrationPendingRead(
        status="pending_phone_verification",
        message="E-mail confirmado. Responda OK à mensagem no WhatsApp para ativar o cadastro.",
    )


@router.post("/webhooks/evolution", include_in_schema=False)
def evolution_webhook(
    payload: dict[str, Any],
    request: Request,
    session: SessionDep,
) -> dict[str, str]:
    """Consume only signed Evolution messages for pending phone confirmation."""
    settings = get_settings()
    provided_secret = request.headers.get("X-Hermes-Webhook-Secret", "")
    if not settings.evolution_webhook_secret or not hmac.compare_digest(
        provided_secret, settings.evolution_webhook_secret
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret."
        )
    data = payload.get("data", payload)
    key = data.get("key", {}) if isinstance(data, dict) else {}
    remote_jid = str(key.get("remoteJid", ""))
    if key.get("fromMe") or "@s.whatsapp.net" not in remote_jid:
        return {"status": "ignored"}
    phone = _normalize_phone(remote_jid.split("@", 1)[0].split(":", 1)[0])
    message = data.get("message", {}) if isinstance(data, dict) else {}
    text = (
        str(
            message.get("conversation", "")
            or message.get("extendedTextMessage", {}).get("text", "")
        )
        .strip()
        .upper()
    )
    store = get_pending_registration_store()
    if store is None or not phone:
        return {"status": "ignored"}
    pending = store.load_by_phone(phone)
    if pending is None or not pending.get("email_verified"):
        return {"status": "ignored"}
    if text == "CANCELAR":
        store.delete(pending["email"], phone)
        return {"status": "cancelled"}
    if text != "OK":
        return {"status": "ignored"}
    user, access_code = _create_verified_user(session, pending)
    store.delete(pending["email"], phone)
    with contextlib.suppress(EmailVerificationUnavailable, ValueError, OSError, httpx.HTTPError):
        _send_whatsapp(
            phone,
            f"Cadastro confirmado, {user.name}! Seu código privado é {access_code}. "
            f"Acesse {settings.member_area_url}",
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
