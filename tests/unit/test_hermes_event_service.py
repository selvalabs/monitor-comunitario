from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from monitor_comunitario.db.models import Base, HermesEventStatus
from monitor_comunitario.services.hermes_events import create_hermes_event


def test_create_hermes_event_persists_created_event() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        event = create_hermes_event(
            session=session,
            event_type="notification_ready",
            channel="app",
            recipient_phone="+5548999999999",
            intent="ALERT_EXPLANATION",
            template_key="alert_explanation_v1",
            payload={"municipality": "Florianopolis"},
        )

        assert event.id is not None
        assert event.status == HermesEventStatus.CREATED.value
        assert event.llm_allowed is False
        assert '"municipality":"Florianopolis"' in event.payload_json


def test_create_hermes_event_rejects_user_facing_llm() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        try:
            create_hermes_event(
                session=session,
                event_type="notification_ready",
                channel="whatsapp",
                recipient_phone="+5548999999999",
                intent="HELP",
                template_key="explain_project_v1",
                payload={},
                llm_allowed=True,
            )
        except ValueError as exc:
            assert "LLM is not allowed for user-facing Hermes templates" in str(exc)
        else:
            raise AssertionError("Expected ValueError")
