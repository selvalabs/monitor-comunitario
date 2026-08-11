from fastapi.testclient import TestClient

from monitor_comunitario.api.internal import app as internal_app
from monitor_comunitario.api.main import app as public_app


def test_public_app_does_not_mount_internal_routes() -> None:
    with TestClient(public_app) as client:
        assert client.get("/internal/hermes/events").status_code == 404
        assert client.post("/internal/email/inbound").status_code == 404
        assert client.get("/internal/monitor-bot/registration-events").status_code == 404


def test_internal_app_recognizes_internal_routes() -> None:
    with TestClient(internal_app) as client:
        assert client.get("/internal/hermes/events").status_code == 401
        assert client.get("/internal/monitor-bot/registration-events").status_code != 404


def test_internal_app_exposes_private_health_checks() -> None:
    with TestClient(internal_app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 200
