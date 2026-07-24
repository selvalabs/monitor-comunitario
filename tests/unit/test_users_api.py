from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from monitor_comunitario.api.main import app
from monitor_comunitario.core.config import get_settings
from monitor_comunitario.db.init_db import init_db

ADMIN_API_KEY = "test-admin-key"


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """Create database tables and provide a FastAPI test client."""
    monkeypatch.setenv("ADMIN_API_KEY", ADMIN_API_KEY)
    get_settings.cache_clear()
    init_db()

    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()


def admin_headers() -> dict[str, str]:
    return {"X-Admin-API-Key": ADMIN_API_KEY}


def test_create_and_get_user(client: TestClient) -> None:
    payload = {
        "name": "Carlos Selva",
        "phone": "5548999999999",
        "municipality": "Florianópolis",
        "neighborhood": "Campeche",
        "street": "Avenida Pequeno Príncipe",
        "number": "100",
        "zipcode": "88063-000",
        "accept_municipality_wide_alerts": True,
    }

    create_response = client.post("/users", json=payload)

    assert create_response.status_code == 201

    created = create_response.json()

    assert created["id"] >= 1
    assert created["name"] == payload["name"]
    assert created["municipality"] == payload["municipality"]
    assert created["notifications_approved"] is False
    assert created["is_active"] is True

    public_get_response = client.get(f"/users/{created['id']}")

    assert public_get_response.status_code == 404

    admin_get_response = client.get(
        f"/admin/users/{created['id']}",
        headers=admin_headers(),
    )

    assert admin_get_response.status_code == 200
    assert admin_get_response.json()["id"] == created["id"]


def test_admin_user_routes_require_api_key(client: TestClient) -> None:
    list_response = client.get("/admin/users")

    assert list_response.status_code == 401
    assert list_response.json()["detail"] == "Invalid or missing admin API key."


def test_update_user(client: TestClient) -> None:
    create_response = client.post(
        "/users",
        json={
            "name": "Teste Update",
            "phone": "5548999999998",
            "municipality": "São José",
        },
    )

    user_id = create_response.json()["id"]

    public_update_response = client.patch(
        f"/users/{user_id}",
        json={"neighborhood": "Kobrasol", "street": "Rua Koesa"},
    )

    assert public_update_response.status_code == 404

    admin_update_response = client.patch(
        f"/admin/users/{user_id}",
        headers=admin_headers(),
        json={"neighborhood": "Kobrasol", "street": "Rua Koesa"},
    )

    assert admin_update_response.status_code == 200
    assert admin_update_response.json()["neighborhood"] == "Kobrasol"
    assert admin_update_response.json()["street"] == "Rua Koesa"


def test_admin_can_approve_user_notifications(client: TestClient) -> None:
    create_response = client.post(
        "/users",
        json={
            "name": "Teste Aprovação",
            "phone": "5548999999996",
            "municipality": "Florianópolis",
        },
    )
    user_id = create_response.json()["id"]

    assert create_response.json()["notifications_approved"] is False

    admin_update_response = client.patch(
        f"/admin/users/{user_id}",
        headers=admin_headers(),
        json={"notifications_approved": True},
    )

    assert admin_update_response.status_code == 200
    assert admin_update_response.json()["notifications_approved"] is True


def test_deactivate_user(client: TestClient) -> None:
    create_response = client.post(
        "/users",
        json={
            "name": "Teste Delete",
            "phone": "5548999999997",
            "municipality": "Palhoça",
        },
    )

    user_id = create_response.json()["id"]

    public_delete_response = client.delete(f"/users/{user_id}")

    assert public_delete_response.status_code == 404

    admin_delete_response = client.delete(
        f"/admin/users/{user_id}",
        headers=admin_headers(),
    )

    assert admin_delete_response.status_code == 200
    assert admin_delete_response.json()["is_active"] is False
