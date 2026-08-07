from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from monitor_comunitario.api.main import app
from monitor_comunitario.core.config import get_settings
from monitor_comunitario.db.models import HermesEvent, HermesEventStatus
from monitor_comunitario.db.session import SessionLocal


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("HERMES_EVENT_API_SECRET", "event-secret")
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


def test_hermes_event_polling_requires_dedicated_secret(client: TestClient) -> None:
    response = client.get("/internal/hermes/events")

    assert response.status_code == 401


def test_hermes_event_polling_claims_and_acknowledges_event(client: TestClient) -> None:
    with SessionLocal() as session:
        event = HermesEvent(
            event_type="member_phone_confirmation_requested",
            channel="whatsapp",
            recipient_phone="5548999912345",
            intent="ACCESS_MEMBER_AREA",
            template_key="member_phone_confirmation_v1",
            payload_json='{"name":"Carlos","url":"https://example.test/member"}',
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        event_id = event.id

    headers = {"X-Hermes-Event-Secret": "event-secret"}
    response = client.get(
        "/internal/hermes/events?event_type=member_phone_confirmation_requested",
        headers=headers,
    )

    assert response.status_code == 200
    claimed_events = response.json()
    assert any(item["id"] == event_id for item in claimed_events)
    claimed_payload = next(item["payload"] for item in claimed_events if item["id"] == event_id)
    assert claimed_payload["name"] == "Carlos"

    with SessionLocal() as session:
        claimed = session.get(HermesEvent, event_id)
        assert claimed is not None
        assert claimed.status == HermesEventStatus.QUEUED.value

    second_poll = client.get("/internal/hermes/events", headers=headers)
    assert second_poll.status_code == 200
    assert all(item["id"] != event_id for item in second_poll.json())

    acknowledged = client.patch(
        f"/internal/hermes/events/{event_id}",
        headers=headers,
        json={"status": "processed"},
    )
    assert acknowledged.status_code == 200
    assert acknowledged.json()["status"] == "processed"


def test_hermes_event_polling_does_not_expose_other_event_types(client: TestClient) -> None:
    with SessionLocal() as session:
        session.add(HermesEvent(event_type="admin_approval_pending", payload_json="{}"))
        session.commit()

    response = client.get(
        "/internal/hermes/events?event_type=admin_approval_pending",
        headers={"X-Hermes-Event-Secret": "event-secret"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_failed_hermes_event_is_available_for_retry(client: TestClient) -> None:
    with SessionLocal() as session:
        event = HermesEvent(
            event_type="member_phone_confirmation_completed",
            channel="whatsapp",
            recipient_phone="5548999912345",
            intent="ACCESS_MEMBER_AREA",
            template_key="member_access_code_v1",
            payload_json='{"name":"Carlos","access_code":"code","url":"https://example.test/member"}',
            status=HermesEventStatus.FAILED.value,
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        event_id = event.id

    response = client.get(
        "/internal/hermes/events?event_type=member_phone_confirmation_completed",
        headers={"X-Hermes-Event-Secret": "event-secret"},
    )

    assert response.status_code == 200
    claimed_events = response.json()
    claimed = next(item for item in claimed_events if item["id"] == event_id)
    assert claimed["status"] == "queued"
