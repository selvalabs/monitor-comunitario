from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from monitor_comunitario.api.main import app
from monitor_comunitario.core.config import get_settings
from monitor_comunitario.db.init_db import init_db


@pytest.fixture()
def admin_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    get_settings.cache_clear()
    init_db()
    return TestClient(app)

def test_admin_login_sets_httponly_cookie_and_cookie_authenticates(
    admin_client: TestClient,
) -> None:
    get_settings.cache_clear()
    init_db()

    with admin_client as client:
        login = client.post(
            "/admin/session",
            headers={"X-Admin-API-Key": "test-admin-key"},
        )
        response = client.get("/admin/runs")

    assert login.status_code == 200
    assert "monitor_admin_session=" in login.headers["set-cookie"]
    assert "HttpOnly" in login.headers["set-cookie"]
    assert "SameSite=strict" in login.headers["set-cookie"]
    assert response.status_code == 200


def test_admin_login_rejects_invalid_key(admin_client: TestClient) -> None:
    get_settings.cache_clear()
    init_db()

    with admin_client as client:
        response = client.post(
            "/admin/session",
            headers={"X-Admin-API-Key": "wrong-key"},
        )

    assert response.status_code == 401


def test_admin_logout_clears_cookie(admin_client: TestClient) -> None:
    get_settings.cache_clear()
    init_db()

    with admin_client as client:
        response = client.delete("/admin/session")

    assert response.status_code == 204
    assert "monitor_admin_session=" in response.headers["set-cookie"]


def test_admin_frontend_does_not_use_session_storage() -> None:
    admin_js = (
        Path(__file__).parents[2]
        / "src"
        / "monitor_comunitario"
        / "web"
        / "static"
        / "admin.js"
    )

    assert "sessionStorage" not in admin_js.read_text(encoding="utf-8")
