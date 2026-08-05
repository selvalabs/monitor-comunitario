from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from monitor_comunitario.db.models import Base, HermesEvent, MonitoringRunStatus
from monitor_comunitario.services import monitoring


def test_failed_monitoring_cycle_creates_hermes_worker_failed_event(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session_local = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    async def fail_fetch(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("scraper unavailable")

    monkeypatch.setattr(monitoring, "SessionLocal", testing_session_local)
    monkeypatch.setattr(monitoring, "fetch_celesc_municipality_pages", fail_fetch)

    result = monitoring.run_monitoring_cycle(limit=1)

    with testing_session_local() as session:
        hermes_event = session.scalar(select(HermesEvent))

    assert result.run.status == MonitoringRunStatus.FAILED.value
    assert result.run.finished_at is not None
    assert result.run.error_message == "RuntimeError: scraper unavailable"
    assert hermes_event is not None
    assert session.scalar(select(HermesEvent).limit(2).offset(1)) is None
    assert hermes_event.event_type == "worker_failed"
    assert hermes_event.status == "created"
    assert hermes_event.intent == "UNKNOWN_ESCALATE"
    assert hermes_event.template_key == "human_escalation_v1"
    assert "scraper unavailable" in hermes_event.payload_json
