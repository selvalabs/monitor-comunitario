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


def test_hermes_can_consume_initial_access_code_only_once(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from monitor_comunitario.api import routes_hermes_internal

    class FakeDeliveryStore:
        def __init__(self) -> None:
            self.values = {"opaque-ref": {"access_code": "initial-code"}}

        def read(self, reference: str) -> dict[str, str] | None:
            return self.values.get(reference)

        def delete(self, reference: str) -> None:
            self.values.pop(reference, None)

    delivery_store = FakeDeliveryStore()
    monkeypatch.setattr(
        routes_hermes_internal,
        "get_ephemeral_delivery_store",
        lambda: delivery_store,
    )
    with SessionLocal() as session:
        event = HermesEvent(
            event_type="member_phone_confirmation_completed",
            channel="whatsapp",
            recipient_phone="5548999912345",
            intent="ACCESS_MEMBER_AREA",
            template_key="member_access_code_v1",
            payload_json='{"access_code_ref":"opaque-ref","name":"Carlos","url":"https://example.test/member"}',
            status=HermesEventStatus.QUEUED.value,
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        event_id = event.id

    headers = {"X-Hermes-Event-Secret": "event-secret"}
    first = client.post(f"/internal/hermes/events/{event_id}/access-code", headers=headers)
    assert first.status_code == 200
    assert first.json() == {"access_code": "initial-code"}

    second = client.post(f"/internal/hermes/events/{event_id}/access-code", headers=headers)
    assert second.status_code == 200

    acknowledged = client.patch(
        f"/internal/hermes/events/{event_id}",
        headers=headers,
        json={"status": "processed"},
    )
    assert acknowledged.status_code == 200

    third = client.post(f"/internal/hermes/events/{event_id}/access-code", headers=headers)
    assert third.status_code == 409


def test_hermes_cannot_consume_access_code_before_claiming_event(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from monitor_comunitario.api import routes_hermes_internal

    monkeypatch.setattr(routes_hermes_internal, "get_ephemeral_delivery_store", lambda: None)
    with SessionLocal() as session:
        event = HermesEvent(
            event_type="member_phone_confirmation_completed",
            payload_json='{"access_code_ref":"opaque-ref"}',
            status=HermesEventStatus.CREATED.value,
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        event_id = event.id

    response = client.post(
        f"/internal/hermes/events/{event_id}/access-code",
        headers={"X-Hermes-Event-Secret": "event-secret"},
    )
    assert response.status_code == 409
