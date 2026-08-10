from collections.abc import Generator

import pytest
from admin_test_helpers import admin_session_headers
from fastapi.testclient import TestClient

from monitor_comunitario.api.main import app
from monitor_comunitario.core.config import get_settings
from monitor_comunitario.db.init_db import init_db
from monitor_comunitario.db.models import HermesEvent, HermesEventStatus
from monitor_comunitario.db.session import SessionLocal


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    get_settings.cache_clear()
    init_db()

    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()


def test_admin_hermes_events_requires_api_key(client: TestClient) -> None:
    response = client.get("/admin/hermes/events")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing admin API key."


def test_monitor_bot_receives_redacted_registration_events_only(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MONITOR_BOT_API_KEY", "dedicated-bot-key")
    get_settings.cache_clear()
    with SessionLocal() as session:
        session.add_all(
            [
                HermesEvent(
                    event_type="member_phone_confirmation_completed",
                    status="processed",
                    channel="whatsapp",
                    template_key="member_access_code_v1",
                    payload_json='{"access_code":"must-not-reach-bot"}',
                ),
                HermesEvent(
                    event_type="notification_ready",
                    status="created",
                    payload_json='{"notification_id":1}',
                ),
            ]
        )
        session.commit()

    response = client.get(
        "/internal/monitor-bot/registration-events",
        headers={"X-Monitor-Bot-Key": "dedicated-bot-key"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body
    assert all(
        item["event_type"]
        in {"member_phone_confirmation_requested", "member_phone_confirmation_completed"}
        for item in body
    )
    assert any(item["event_type"] == "member_phone_confirmation_completed" for item in body)
    assert all("payload_json" not in item for item in body)
    assert "access_code" not in response.text


def test_monitor_bot_cannot_read_full_admin_hermes_payload(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MONITOR_BOT_API_KEY", "dedicated-bot-key")
    get_settings.cache_clear()

    response = client.get(
        "/admin/hermes/events",
        headers={"X-Monitor-Bot-Key": "dedicated-bot-key"},
    )

    assert response.status_code == 401


def test_admin_hermes_events_lists_events(client: TestClient) -> None:
    with SessionLocal() as session:
        event = HermesEvent(
            event_type="notification_ready",
            status="created",
            channel="app",
            recipient_phone="5548999999999",
            intent="ALERT_EXPLANATION",
            template_key="alert_explanation_v1",
            payload_json='{"notification_id":1}',
        )
        session.add(event)
        session.commit()
        session.refresh(event)

    response = client.get(
        "/admin/hermes/events",
        headers=admin_session_headers(client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body[0]["id"] == event.id
    assert body[0]["event_type"] == "notification_ready"
    assert body[0]["status"] == "created"
    assert body[0]["recipient_phone"] == "5548999999999"
    assert body[0]["llm_allowed"] is False


def test_admin_hermes_event_detail_returns_404(client: TestClient) -> None:
    response = client.get(
        "/admin/hermes/events/999999",
        headers=admin_session_headers(client),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Hermes event not found."


def test_admin_hermes_event_status_update_requires_api_key(client: TestClient) -> None:
    response = client.patch(
        "/admin/hermes/events/1/status",
        json={"status": "processed"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing admin API key."


def test_admin_hermes_event_status_update_persists_terminal_status(
    client: TestClient,
) -> None:
    with SessionLocal() as session:
        event = HermesEvent(
            event_type="admin_approval_pending",
            status=HermesEventStatus.CREATED.value,
            payload_json='{"user_id":1}',
        )
        session.add(event)
        session.commit()
        session.refresh(event)

    response = client.patch(
        f"/admin/hermes/events/{event.id}/status",
        headers=admin_session_headers(client),
        json={"status": "escalated"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == event.id
    assert body["status"] == "escalated"
    assert body["processed_at"] is not None

    with SessionLocal() as session:
        persisted = session.get(HermesEvent, event.id)

    assert persisted is not None
    assert persisted.status == HermesEventStatus.ESCALATED.value
    assert persisted.processed_at is not None


def test_admin_hermes_event_status_update_returns_404(client: TestClient) -> None:
    response = client.patch(
        "/admin/hermes/events/999999/status",
        headers=admin_session_headers(client),
        json={"status": "processed"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Hermes event not found."


def test_admin_hermes_event_status_update_rejects_invalid_status(
    client: TestClient,
) -> None:
    with SessionLocal() as session:
        event = HermesEvent(event_type="notification_ready", payload_json="{}")
        session.add(event)
        session.commit()
        session.refresh(event)

    response = client.patch(
        f"/admin/hermes/events/{event.id}/status",
        headers=admin_session_headers(client),
        json={"status": "sent"},
    )

    assert response.status_code == 422
