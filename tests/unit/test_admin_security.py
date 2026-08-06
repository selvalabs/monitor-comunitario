from collections.abc import Generator

import pytest
from admin_test_helpers import admin_session_headers
from fastapi.testclient import TestClient

from monitor_comunitario.api.main import app
from monitor_comunitario.core.config import get_settings
from monitor_comunitario.db.init_db import init_db


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """Create a test client with an explicit admin API key."""
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    get_settings.cache_clear()
    init_db()

    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()


def test_admin_runs_returns_503_when_api_key_is_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    get_settings.cache_clear()
    init_db()

    with TestClient(app) as test_client:
        response = test_client.get(
            "/admin/runs",
            headers={"X-Admin-API-Key": "any-key"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "Admin API key is not configured."

    get_settings.cache_clear()


def test_admin_runs_requires_api_key(client: TestClient) -> None:
    response = client.get("/admin/runs")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing admin API key."


def test_admin_runs_rejects_invalid_api_key(client: TestClient) -> None:
    response = client.get(
        "/admin/runs",
        headers={"X-Admin-API-Key": "wrong-key"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing admin API key."


def test_admin_runs_accepts_valid_session(client: TestClient) -> None:
    response = client.get(
        "/admin/runs",
        headers=admin_session_headers(client),
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_public_health_does_not_require_admin_api_key(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
