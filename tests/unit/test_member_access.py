from collections.abc import Generator

import pytest
from admin_test_helpers import admin_session_headers
from fastapi.testclient import TestClient

from monitor_comunitario.api import routes_member
from monitor_comunitario.api.main import app
from monitor_comunitario.core.config import get_settings
from monitor_comunitario.db.init_db import init_db
from monitor_comunitario.services.member_access import hash_access_code, verify_access_code
from monitor_comunitario.services.member_session import MEMBER_CSRF_COOKIE_NAME

ADMIN_API_KEY = "test-admin-key"


def unique_phone(suffix: str) -> str:
    return f"55489999{suffix}"


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    class FakeMemberSessionStore:
        def __init__(self) -> None:
            self.values: dict[str, int] = {}
            self.counter = 0

        def create(self, user_id: int, ttl_seconds: int = 3600) -> str:
            self.counter += 1
            token = f"member-session-{self.counter}"
            self.values[token] = user_id
            return token

        def get_user_id(self, token: str) -> int | None:
            return self.values.get(token)

        def delete(self, token: str) -> None:
            self.values.pop(token, None)

    member_session_store = FakeMemberSessionStore()
    monkeypatch.setattr(routes_member, "get_member_session_store", lambda: member_session_store)
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
    assert body["preferences"] == {
        "celesc_scheduled": True,
        "celesc_emergency": True,
        "casan_water": True,
        "defesa_civil_sc": False,
    }
    assert "monitor_member_session=" in access_response.headers["set-cookie"]
    assert "HttpOnly" in access_response.headers["set-cookie"]
    assert "SameSite=strict" in access_response.headers["set-cookie"]

    restored = client.get("/member/me")
    assert restored.status_code == 200
    assert restored.json()["user"]["id"] == created_user["id"]


def test_member_can_update_alert_source_preferences(client: TestClient) -> None:
    phone = unique_phone("0008")
    create_response = client.post(
        "/users",
        json={
            "name": "Preference Member",
            "phone": phone,
            "municipality": "FlorianÃ³polis",
        },
    )
    access_code = create_response.json()["access_code"]
    client.post("/member/access", json={"phone": phone, "access_code": access_code})

    response = client.patch(
        "/member/preferences",
        headers={"X-CSRF-Token": client.cookies.get(MEMBER_CSRF_COOKIE_NAME)},
        json={
            "celesc_scheduled": True,
            "celesc_emergency": False,
            "casan_water": False,
            "defesa_civil_sc": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["preferences"] == {
        "celesc_scheduled": True,
        "celesc_emergency": False,
        "casan_water": False,
        "defesa_civil_sc": True,
    }


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

    client.post(
        "/member/access",
        json={"phone": phone, "access_code": created_user["access_code"]},
    )
    csrf_token = client.cookies.get(MEMBER_CSRF_COOKIE_NAME)
    response = client.request(
        "DELETE",
        "/member/account",
        headers={"X-CSRF-Token": csrf_token},
        json={"access_code": created_user["access_code"]},
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

    client.post(
        "/member/access",
        json={"phone": phone, "access_code": create_response.json()["access_code"]},
    )
    response = client.request(
        "DELETE",
        "/member/account",
        headers={"X-CSRF-Token": client.cookies.get(MEMBER_CSRF_COOKIE_NAME)},
        json={"access_code": "wrong-code"},
    )

    assert response.status_code == 401
    assert client.post(
        "/member/access",
        json={"phone": phone, "access_code": create_response.json()["access_code"]},
    ).status_code == 200


def test_member_account_deletion_requires_csrf(client: TestClient) -> None:
    phone = unique_phone("0006")
    create_response = client.post(
        "/users",
        json={"name": "CSRF Member", "phone": phone, "municipality": "PalhoÃ§a"},
    )
    access_code = create_response.json()["access_code"]
    client.post("/member/access", json={"phone": phone, "access_code": access_code})

    response = client.request(
        "DELETE",
        "/member/account",
        json={"access_code": access_code},
    )

    assert response.status_code == 403


def test_member_logout_requires_csrf_and_invalidates_session(client: TestClient) -> None:
    phone = unique_phone("0007")
    create_response = client.post(
        "/users",
        json={"name": "Logout Member", "phone": phone, "municipality": "PalhoÃ§a"},
    )
    client.post(
        "/member/access",
        json={"phone": phone, "access_code": create_response.json()["access_code"]},
    )

    without_csrf = client.delete("/member/session")
    assert without_csrf.status_code == 403

    csrf_token = client.cookies.get(MEMBER_CSRF_COOKIE_NAME)
    logout = client.delete(
        "/member/session",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert logout.status_code == 204
    assert client.get("/member/me").status_code == 401


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
    assert "sessionStorage" not in script_response.text
    assert "/member/me" in script_response.text
    assert "/member/session" in script_response.text
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
