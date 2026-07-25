from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from monitor_comunitario.db.models import HermesEvent, HermesEventStatus, utc_now
from monitor_comunitario.notifications.telegram_provider import TelegramMessage
from monitor_comunitario.services.hermes_catalog import HERMES_ESCALATION_EVENTS


class HermesTelegramProvider(Protocol):
    """Minimal provider contract needed for Hermes operator escalation."""

    async def send_message(self, message: TelegramMessage) -> None:
        """Send one operator escalation message."""


@dataclass(frozen=True)
class HermesProcessingSummary:
    """Summary of one local Hermes processing pass."""

    events_checked: int
    events_processed: int
    events_escalated: int
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


def build_telegram_escalation_message(event: HermesEvent) -> TelegramMessage:
    """Build the operator-facing Telegram message for a Hermes escalation."""
    fields = [
        "Monitor Comunitario Hermes",
        f"Evento: {event.event_type}",
        f"ID: {event.id}",
        f"Canal: {event.channel or '-'}",
        f"Intent: {event.intent or '-'}",
        f"Template: {event.template_key or '-'}",
        f"Payload: {event.payload_json}",
    ]
    return TelegramMessage(text="\n".join(fields))


def process_created_hermes_events(
    session: Session,
    limit: int = 50,
    *,
    telegram_enabled: bool = False,
    telegram_provider: HermesTelegramProvider | None = None,
) -> HermesProcessingSummary:
    """Process created Hermes events locally, escalating selected events when enabled."""
    import asyncio

    events = list_created_hermes_events(session, limit=limit)

    processed = 0
    escalated = 0
    failed = 0

    for event in events:
        try:
            queued = mark_hermes_event_queued(session, event)
            should_escalate = (
                telegram_enabled
                and telegram_provider is not None
                and queued.event_type in HERMES_ESCALATION_EVENTS
            )
            if should_escalate:
                message = build_telegram_escalation_message(queued)
                provider = telegram_provider
                if provider is None:
                    raise RuntimeError("Telegram provider is required for escalation.")
                asyncio.run(provider.send_message(message))
                mark_hermes_event_escalated(session, queued)
                escalated += 1
            else:
                mark_hermes_event_processed(session, queued)
                processed += 1
        except Exception as exc:
            mark_hermes_event_failed(session, event, str(exc))
            failed += 1

    return HermesProcessingSummary(
        events_checked=len(events),
        events_processed=processed,
        events_escalated=escalated,
        events_failed=failed,
    )
