from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from admin_test_helpers import admin_session_headers
from fastapi.testclient import TestClient

from monitor_comunitario.api.main import app
from monitor_comunitario.core.config import get_settings
from monitor_comunitario.db.init_db import init_db
from monitor_comunitario.db.models import MonitoringRun, MonitoringRunStatus
from monitor_comunitario.db.session import SessionLocal


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """Create a test client with an explicit admin API key."""
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    get_settings.cache_clear()
    init_db()

    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()


def test_health_remains_public(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_checks_database_connectivity(client: TestClient) -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_admin_diagnostics_requires_api_key(client: TestClient) -> None:
    response = client.get("/admin/diagnostics")

    assert response.status_code == 401


def test_admin_diagnostics_returns_operational_metadata(client: TestClient) -> None:
    response = client.get(
        "/admin/diagnostics",
        headers=admin_session_headers(client),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["environment"]
    assert data["timezone"]
    assert data["database"] == {"status": "ok"}
    assert set(data["scheduler"]) == {"enabled", "hour", "minute"}
    assert set(data["notifications"]) == {"provider", "evolution_enabled"}
    assert "latest_run" in data


def test_admin_latest_run_requires_api_key(client: TestClient) -> None:
    response = client.get("/admin/runs/latest")

    assert response.status_code == 401


def test_admin_latest_run_returns_most_recent_run(client: TestClient) -> None:
    with SessionLocal() as session:
        run = MonitoringRun(
            started_at=datetime(2099, 1, 1, tzinfo=UTC),
            status=MonitoringRunStatus.SUCCESS.value,
            municipalities_found=10,
            municipalities_captured=2,
            notices_found=5,
            notices_persisted=5,
            notices_created=3,
            users_checked=4,
            matches_created=2,
            notifications_created=2,
            raw_snapshot_path="snapshots/latest-test.json",
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    response = client.get(
        "/admin/runs/latest",
        headers=admin_session_headers(client),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == run_id
    assert data["status"] == "success"
    assert data["notices_found"] == 5
    assert data["matches_created"] == 2
    assert data["notifications_created"] == 2
