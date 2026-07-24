from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from monitor_comunitario.db.models import HermesEvent, HermesEventStatus, utc_now


@dataclass(frozen=True)
class HermesProcessingSummary:
    """Summary of one local Hermes processing pass."""

    events_checked: int
    events_processed: int
    events_failed: int


def mark_hermes_event_queued(session: Session, event: HermesEvent) -> HermesEvent:
    """Mark a Hermes event as queued for local processing."""
    event.status = HermesEventStatus.QUEUED.value
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def mark_hermes_event_processed(session: Session, event: HermesEvent) -> HermesEvent:
    """Mark a Hermes event as processed without external delivery."""
    event.status = HermesEventStatus.PROCESSED.value
    event.processed_at = utc_now()
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def mark_hermes_event_failed(
    session: Session,
    event: HermesEvent,
    error_message: str,
) -> HermesEvent:
    """Mark a Hermes event as failed and persist the error reason."""
    event.status = HermesEventStatus.FAILED.value
    event.error_message = error_message
    event.processed_at = utc_now()
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def mark_hermes_event_escalated(session: Session, event: HermesEvent) -> HermesEvent:
    """Mark a Hermes event as escalated to an internal human/operator path."""
    event.status = HermesEventStatus.ESCALATED.value
    event.processed_at = utc_now()
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def list_created_hermes_events(session: Session, limit: int = 50) -> list[HermesEvent]:
    """Return pending Hermes events in creation order."""
    query = (
        select(HermesEvent)
        .where(HermesEvent.status == HermesEventStatus.CREATED.value)
        .order_by(HermesEvent.created_at.asc(), HermesEvent.id.asc())
        .limit(limit)
    )
    return list(session.scalars(query).all())


def process_created_hermes_events(session: Session, limit: int = 50) -> HermesProcessingSummary:
    """Process created Hermes events locally without external delivery."""
    events = list_created_hermes_events(session, limit=limit)

    processed = 0
    failed = 0

    for event in events:
        try:
            queued = mark_hermes_event_queued(session, event)
            mark_hermes_event_processed(session, queued)
            processed += 1
        except Exception as exc:
            mark_hermes_event_failed(session, event, str(exc))
            failed += 1

    return HermesProcessingSummary(
        events_checked=len(events),
        events_processed=processed,
        events_failed=failed,
    )
