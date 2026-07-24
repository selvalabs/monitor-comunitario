from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from monitor_comunitario.api.main import app
from monitor_comunitario.core.config import get_settings
from monitor_comunitario.db.init_db import init_db
from monitor_comunitario.db.models import HermesEvent
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
        headers={"X-Admin-API-Key": "test-admin-key"},
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
        headers={"X-Admin-API-Key": "test-admin-key"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Hermes event not found."
