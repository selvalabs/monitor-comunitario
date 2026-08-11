from collections.abc import Generator

import pytest
from admin_test_helpers import admin_session_headers
from fastapi.testclient import TestClient

from monitor_comunitario.api.main import app
from monitor_comunitario.core.config import get_settings
from monitor_comunitario.db.init_db import init_db
from monitor_comunitario.services.member_access import hash_access_code, verify_access_code

ADMIN_API_KEY = "test-admin-key"


def unique_phone(suffix: str) -> str:
    return f"55489999{suffix}"


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("ADMIN_API_KEY", ADMIN_API_KEY)
    get_settings.cache_clear()
    init_db()

    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()


def admin_headers(client: TestClient) -> dict[str, str]:
    return admin_session_headers(client)


def test_access_code_hash_verification() -> None:
    code_hash = hash_access_code("ABCDE-23456")

    assert code_hash != "ABCDE-23456"
    assert verify_access_code("abcde 23456", code_hash) is True
    assert verify_access_code("wrong-code", code_hash) is False


def test_create_user_returns_one_time_access_code(client: TestClient) -> None:
    response = client.post(
        "/users",
        json={
            "name": "Member Access User",
            "phone": unique_phone("0001"),
            "municipality": "Florianópolis",
            "neighborhood": "Campeche",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["id"] >= 1
    assert body["access_code"]
    assert "access_code_hash" not in body

    public_read_response = client.get(f"/users/{body['id']}")

    assert public_read_response.status_code == 404

    admin_read_response = client.get(
        f"/admin/users/{body['id']}",
        headers=admin_headers(client),
    )

    assert admin_read_response.status_code == 200
    assert "access_code" not in admin_read_response.json()
    assert "access_code_hash" not in admin_read_response.json()


def test_member_access_succeeds_with_phone_and_access_code(client: TestClient) -> None:
    phone = unique_phone("0002")
    create_response = client.post(
        "/users",
        json={
            "name": "Member Login User",
            "phone": phone,
            "municipality": "São José",
        },
    )
    created_user = create_response.json()

    access_response = client.post(
        "/member/access",
        json={
            "phone": phone,
            "access_code": created_user["access_code"],
        },
    )

    assert access_response.status_code == 200

    body = access_response.json()

    assert body["user"]["id"] == created_user["id"]
    assert body["user"]["phone"] == phone
    assert body["notifications"] == []


def test_member_access_rejects_invalid_code(client: TestClient) -> None:
    phone = unique_phone("0003")
    client.post(
        "/users",
        json={
            "name": "Invalid Member User",
            "phone": phone,
            "municipality": "Palhoça",
        },
    )

    response = client.post(
        "/member/access",
        json={
            "phone": phone,
            "access_code": "wrong-code",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid phone or access code."


def test_member_can_permanently_delete_account_with_private_code(client: TestClient) -> None:
    phone = unique_phone("0004")
    create_response = client.post(
        "/users",
        json={"name": "Delete Me", "phone": phone, "municipality": "Palhoça"},
    )
    created_user = create_response.json()

    response = client.request(
        "DELETE",
        "/member/account",
        json={"phone": phone, "access_code": created_user["access_code"]},
    )

    assert response.status_code == 204
    assert client.post(
        "/member/access",
        json={"phone": phone, "access_code": created_user["access_code"]},
    ).status_code == 401



def test_member_account_deletion_requires_private_code(client: TestClient) -> None:
    phone = unique_phone("0005")
    create_response = client.post(
        "/users",
        json={"name": "Keep Me", "phone": phone, "municipality": "Palhoça"},
    )

    response = client.request(
        "DELETE",
        "/member/account",
        json={"phone": phone, "access_code": "wrong-code"},
    )

    assert response.status_code == 401
    assert client.post(
        "/member/access",
        json={"phone": phone, "access_code": create_response.json()["access_code"]},
    ).status_code == 200


def test_member_page_and_static_assets_are_served() -> None:
    with TestClient(app) as test_client:
        page_response = test_client.get("/member")
        script_response = test_client.get("/static/member.js")
        style_response = test_client.get("/static/member.css")

    assert page_response.status_code == 200
    assert "Seus avisos" in page_response.text
    assert "Entrar" in page_response.text
    assert "theme-selector" in page_response.text
    assert "confirm-delete-member" in page_response.text
    assert "language-selector" in page_response.text
    assert "/static/preferences.js" in page_response.text

    assert script_response.status_code == 200
    assert "sessionStorage" in script_response.text
    assert "/member/access" in script_response.text
    assert "/member/account" in script_response.text

    assert style_response.status_code == 200
    assert "member-main" in style_response.text


def test_member_javascript_renders_alert_summary_with_original_details() -> None:
    with TestClient(app) as test_client:
        response = test_client.get("/static/member.js")

    assert response.status_code == 200
    assert "/member/access" in response.text
    assert "buildNotificationSummary" in response.text
    assert "notification-summary" in response.text
    assert "Ver aviso original da Celesc" in response.text
    assert "Não encontramos avisos para seu endereço." in response.text
    assert 'document.createElement("details")' in response.text


def test_member_stylesheet_supports_readable_notification_details() -> None:
    with TestClient(app) as test_client:
        response = test_client.get("/static/member.css")

    assert response.status_code == 200
    assert ".notification-summary" in response.text
    assert ".notification-original" in response.text
