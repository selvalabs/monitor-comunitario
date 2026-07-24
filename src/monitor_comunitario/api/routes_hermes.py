from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from monitor_comunitario.api.security import require_admin_api_key
from monitor_comunitario.db.models import HermesEvent
from monitor_comunitario.db.session import get_session
from monitor_comunitario.schemas.hermes_events import HermesEventRead

admin_router = APIRouter(
    prefix="/admin/hermes",
    tags=["admin", "hermes"],
    dependencies=[Depends(require_admin_api_key)],
)

SessionDep = Annotated[Session, Depends(get_session)]


@admin_router.get("/events", response_model=list[HermesEventRead])
def list_hermes_events(
    session: SessionDep,
    limit: int = 50,
) -> list[HermesEvent]:
    """List Hermes event audit records for admin usage."""
    query = (
        select(HermesEvent)
        .order_by(HermesEvent.created_at.desc(), HermesEvent.id.desc())
        .limit(limit)
    )
    return list(session.scalars(query).all())


@admin_router.get("/events/{event_id}", response_model=HermesEventRead)
def get_hermes_event(
    event_id: int,
    session: SessionDep,
) -> HermesEvent:
    """Return one Hermes event audit record."""
    event = session.get(HermesEvent, event_id)

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hermes event not found.",
        )

    return event
