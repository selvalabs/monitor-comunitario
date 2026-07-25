from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from monitor_comunitario.db.models import Base, HermesEvent, HermesEventStatus
from monitor_comunitario.notifications.telegram_provider import TelegramMessage
from monitor_comunitario.services.hermes_processing import (
    mark_hermes_event_failed,
    mark_hermes_event_processed,
    mark_hermes_event_queued,
    process_created_hermes_events,
)


class FakeTelegramProvider:
    def __init__(self) -> None:
        self.messages: list[TelegramMessage] = []

    async def send_message(self, message: TelegramMessage) -> None:
        self.messages.append(message)


def test_hermes_event_status_transitions_are_persisted() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        event = HermesEvent(event_type="notification_ready", payload_json="{}")
        session.add(event)
        session.commit()
        session.refresh(event)

        queued = mark_hermes_event_queued(session, event)
        processed = mark_hermes_event_processed(session, queued)

        assert processed.status == HermesEventStatus.PROCESSED.value
        assert processed.processed_at is not None


def test_hermes_event_failure_records_error_message() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        event = HermesEvent(event_type="gateway_down", payload_json="{}")
        session.add(event)
        session.commit()
        session.refresh(event)

        failed = mark_hermes_event_failed(session, event, "gateway timeout")

        assert failed.status == HermesEventStatus.FAILED.value
        assert failed.error_message == "gateway timeout"
        assert failed.processed_at is not None


def test_process_created_hermes_events_processes_without_external_delivery() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(HermesEvent(event_type="notification_ready", payload_json="{}"))
        session.add(HermesEvent(event_type="notification_ready", payload_json="{}"))
        session.commit()

        summary = process_created_hermes_events(session, limit=10)
        events = list(session.scalars(select(HermesEvent)).all())

    assert summary.events_checked == 2
    assert summary.events_processed == 2
    assert summary.events_escalated == 0
    assert summary.events_failed == 0
    assert {event.status for event in events} == {HermesEventStatus.PROCESSED.value}


def test_process_created_hermes_events_escalates_enabled_events_to_telegram() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    provider = FakeTelegramProvider()

    with Session(engine) as session:
        event = HermesEvent(
            event_type="admin_approval_pending",
            payload_json='{"user_id":1}',
        )
        session.add(event)
        session.commit()

        summary = process_created_hermes_events(
            session,
            limit=10,
            telegram_enabled=True,
            telegram_provider=provider,
        )
        persisted = session.get(HermesEvent, event.id)

    assert summary.events_checked == 1
    assert summary.events_processed == 0
    assert summary.events_escalated == 1
    assert summary.events_failed == 0
    assert persisted is not None
    assert persisted.status == HermesEventStatus.ESCALATED.value
    assert len(provider.messages) == 1
    assert "admin_approval_pending" in provider.messages[0].text
    assert f"ID: {event.id}" in provider.messages[0].text


def test_process_created_hermes_events_keeps_escalation_local_when_telegram_disabled() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    provider = FakeTelegramProvider()

    with Session(engine) as session:
        event = HermesEvent(event_type="admin_approval_pending", payload_json="{}")
        session.add(event)
        session.commit()

        summary = process_created_hermes_events(
            session,
            limit=10,
            telegram_enabled=False,
            telegram_provider=provider,
        )
        persisted = session.get(HermesEvent, event.id)

    assert summary.events_checked == 1
    assert summary.events_processed == 1
    assert summary.events_escalated == 0
    assert summary.events_failed == 0
    assert persisted is not None
    assert persisted.status == HermesEventStatus.PROCESSED.value
    assert provider.messages == []
