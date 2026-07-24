from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from monitor_comunitario.db.models import Base, HermesEvent, HermesEventStatus


def test_hermes_event_model_records_auditable_payload() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        event = HermesEvent(
            event_type="notification_ready",
            status=HermesEventStatus.CREATED.value,
            channel="app",
            recipient_phone="+5548999999999",
            intent="ALERT_EXPLANATION",
            template_key="alert_explanation_v1",
            payload_json='{"municipality":"Florianopolis"}',
            source="monitor_comunitario",
        )
        session.add(event)
        session.commit()

        persisted = session.scalar(select(HermesEvent))

    assert persisted is not None
    assert persisted.event_type == "notification_ready"
    assert persisted.status == "created"
    assert persisted.llm_allowed is False
    assert persisted.payload_json == '{"municipality":"Florianopolis"}'


def test_hermes_event_status_values_are_explicit() -> None:
    assert HermesEventStatus.CREATED.value == "created"
    assert HermesEventStatus.QUEUED.value == "queued"
    assert HermesEventStatus.PROCESSED.value == "processed"
    assert HermesEventStatus.FAILED.value == "failed"
    assert HermesEventStatus.ESCALATED.value == "escalated"
