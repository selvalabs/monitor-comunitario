from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from monitor_comunitario.api.security import require_monitor_bot_api_key
from monitor_comunitario.db.models import HermesEvent
from monitor_comunitario.db.session import get_session
from monitor_comunitario.schemas.hermes_events import HermesEventBotRead

router = APIRouter(
    prefix="/internal/monitor-bot",
    tags=["internal", "monitor-bot"],
    dependencies=[Depends(require_monitor_bot_api_key)],
)
SessionDep = Annotated[Session, Depends(get_session)]
REGISTRATION_EVENT_TYPES = frozenset(
    {"member_phone_confirmation_requested", "member_phone_confirmation_completed"}
)


@router.get("/registration-events", response_model=list[HermesEventBotRead])
def list_registration_events(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[HermesEvent]:
    """Return registration event metadata without resident payloads."""
    query = (
        select(HermesEvent)
        .where(HermesEvent.event_type.in_(REGISTRATION_EVENT_TYPES))
        .order_by(HermesEvent.created_at.desc(), HermesEvent.id.desc())
        .limit(limit)
    )
    return list(session.scalars(query).all())
