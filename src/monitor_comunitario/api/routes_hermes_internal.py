import json
from secrets import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from monitor_comunitario.core.config import get_settings
from monitor_comunitario.db.models import HermesEvent, HermesEventStatus, utc_now
from monitor_comunitario.db.session import get_session
from monitor_comunitario.schemas.hermes_events import (
    HermesEventDeliveryRead,
    HermesEventDeliveryUpdate,
)
from monitor_comunitario.services.email_verification import (
    EmailVerificationUnavailable,
    get_pending_registration_store,
)

router = APIRouter(prefix="/internal/hermes", tags=["internal", "hermes"])
SessionDep = Annotated[Session, Depends(get_session)]
DELIVERABLE_EVENT_TYPES = frozenset(
    {"member_phone_confirmation_requested", "member_phone_confirmation_completed"}
)


def require_hermes_event_secret(
    provided_secret: Annotated[str | None, Header(alias="X-Hermes-Event-Secret")] = None,
) -> None:
    """Authenticate Hermes event polling without exposing the admin session."""
    expected_secret = get_settings().hermes_event_api_secret
    if not expected_secret or not provided_secret or not compare_digest(
        provided_secret, expected_secret
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Hermes event API secret.",
        )


def _to_delivery_event(event: HermesEvent) -> HermesEventDeliveryRead:
    try:
        payload = json.loads(event.payload_json)
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hermes event payload is invalid.",
        ) from error
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hermes event payload must be an object.",
        )
    return HermesEventDeliveryRead(
        id=event.id,
        status=event.status,
        event_type=event.event_type,
        channel=event.channel,
        recipient_phone=event.recipient_phone,
        intent=event.intent,
        template_key=event.template_key,
        payload=payload,
        created_at=event.created_at,
    )


def _delivery_reference(event: HermesEvent) -> str | None:
    try:
        payload = json.loads(event.payload_json)
    except json.JSONDecodeError:
        return None
    reference = payload.get("delivery_ref") if isinstance(payload, dict) else None
    return reference if isinstance(reference, str) and reference else None


@router.get(
    "/events",
    response_model=list[HermesEventDeliveryRead],
    dependencies=[Depends(require_hermes_event_secret)],
)
def claim_hermes_events(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    event_type: Annotated[list[str] | None, Query()] = None,
) -> list[HermesEventDeliveryRead]:
    """Claim deliverable events for Hermes with an atomic status transition."""
    requested_types = set(event_type or DELIVERABLE_EVENT_TYPES)
    allowed_types = requested_types & DELIVERABLE_EVENT_TYPES
    if not allowed_types:
        return []
    query = (
        select(HermesEvent)
        .where(
            HermesEvent.status.in_(
                {HermesEventStatus.CREATED.value, HermesEventStatus.FAILED.value}
            ),
            HermesEvent.event_type.in_(allowed_types),
        )
        .order_by(HermesEvent.created_at.asc(), HermesEvent.id.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    events = list(session.scalars(query).all())
    for event in events:
        event.status = HermesEventStatus.QUEUED.value
    session.commit()
    return [_to_delivery_event(event) for event in events]


@router.get(
    "/events/{event_id}/access-code",
    dependencies=[Depends(require_hermes_event_secret)],
)
def get_delivery_access_code(event_id: int, session: SessionDep) -> dict[str, str]:
    """Return an ephemeral member code only to the Hermes delivery worker."""
    event = session.get(HermesEvent, event_id)
    if (
        event is None
        or event.event_type != "member_phone_confirmation_completed"
        or event.status != HermesEventStatus.QUEUED.value
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found.")
    reference = _delivery_reference(event)
    store = get_pending_registration_store()
    if reference is None or store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Delivery code not found."
        )
    try:
        access_code = store.load_delivery_access_code(reference)
    except EmailVerificationUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Delivery code is temporarily unavailable.",
        ) from error
    if not access_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Delivery code not found."
        )
    return {"access_code": access_code}


@router.patch(
    "/events/{event_id}",
    response_model=HermesEventDeliveryRead,
    dependencies=[Depends(require_hermes_event_secret)],
)
def acknowledge_hermes_event(
    event_id: int,
    update: HermesEventDeliveryUpdate,
    session: SessionDep,
) -> HermesEventDeliveryRead:
    """Persist Hermes delivery success or failure for a claimed event."""
    event = session.get(HermesEvent, event_id)
    if event is None or event.event_type not in DELIVERABLE_EVENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Hermes event not found."
        )
    if event.status not in {
        HermesEventStatus.QUEUED.value,
        HermesEventStatus.FAILED.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hermes event is not available for acknowledgement.",
        )
    if update.status == HermesEventStatus.PROCESSED.value:
        reference = _delivery_reference(event)
        if reference:
            store = get_pending_registration_store()
            if store is None:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Delivery code is temporarily unavailable.",
                )
            try:
                store.delete_delivery_access_code(reference)
            except EmailVerificationUnavailable as error:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Delivery code is temporarily unavailable.",
                ) from error
    event.status = update.status
    event.error_message = update.error_message[:2000]
    event.processed_at = utc_now() if update.status == HermesEventStatus.PROCESSED.value else None
    session.add(event)
    session.commit()
    session.refresh(event)
    return _to_delivery_event(event)
