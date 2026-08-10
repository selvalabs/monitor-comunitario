from collections.abc import Generator

import pytest
from admin_test_helpers import admin_session_headers
from fastapi.testclient import TestClient
from sqlalchemy import select

from monitor_comunitario.api.main import app
from monitor_comunitario.core.config import get_settings
from monitor_comunitario.db.init_db import init_db
from monitor_comunitario.db.models import HermesEvent
from monitor_comunitario.db.session import SessionLocal

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


def admin_headers(client: TestClient) -> dict[str, str]:
    return admin_session_headers(client)


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
        headers=admin_headers(client),
    )

    assert admin_get_response.status_code == 200
    assert admin_get_response.json()["id"] == created["id"]


def test_create_user_emits_pending_approval_hermes_event(client: TestClient) -> None:
    response = client.post(
        "/users",
        json={
            "name": "Morador Pendente",
            "phone": "5548999999901",
            "municipality": "Florianópolis",
            "neighborhood": "Campeche",
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["notifications_approved"] is False

    with SessionLocal() as session:
        event = session.scalar(
            select(HermesEvent).where(
                HermesEvent.event_type == "admin_approval_pending",
                HermesEvent.payload_json.contains(f'"user_id":{created["id"]}'),
            )
        )

    assert event is not None
    assert event.status == "created"
    assert event.channel == "admin"
    assert event.intent == "UNKNOWN_ESCALATE"
    assert event.template_key == "human_escalation_v1"
    assert f'"user_id":{created["id"]}' in event.payload_json
    assert '"municipality":"Florian\\u00f3polis"' in event.payload_json


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
        headers=admin_headers(client),
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
        headers=admin_headers(client),
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
        headers=admin_headers(client),
    )

    assert admin_delete_response.status_code == 200
    assert admin_delete_response.json()["is_active"] is False


def test_email_and_whatsapp_verification_flow(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from monitor_comunitario.api import routes_users
    from monitor_comunitario.services import email_verification

    class FakeStore:
        def __init__(self) -> None:
            self.values: dict[str, dict[str, object]] = {}

        def save(
            self, email: str, phone: str, payload: dict[str, object], ttl_seconds: int
        ) -> None:
            self.values[email] = payload
            self.values[phone] = payload

        def load(self, email: str) -> dict[str, object] | None:
            return self.values.get(email)

        def load_by_phone(self, phone: str) -> dict[str, object] | None:
            return self.values.get(phone)

        def delete(self, email: str, phone: str) -> None:
            self.values.pop(email, None)
            self.values.pop(phone, None)

    store = FakeStore()
    delivered_emails: list[tuple[str, str]] = []
    monkeypatch.setenv("EMAIL_VERIFICATION_ENABLED", "true")
    monkeypatch.setenv("HERMES_CALLBACK_SECRET", "callback-secret")
    get_settings.cache_clear()

    monkeypatch.setattr(routes_users, "get_pending_registration_store", lambda: store)
    monkeypatch.setattr(
        email_verification,
        "send_verification_email",
        lambda *, email, otp: (delivered_emails.append((email, otp)) or "<brevo-id@example.com>"),
    )

    registration = client.post(
        "/users",
        json={
            "name": "Email Verified",
            "email": "person@example.com",
            "phone": "5548999912345",
            "municipality": "Florianopolis",
        },
    )
    assert registration.status_code == 202
    assert delivered_emails
    assert client.get("/admin/users").status_code == 401

    verify_email = client.post(
        "/users/verify-email",
        json={"email": delivered_emails[0][0], "otp": delivered_emails[0][1]},
    )
    assert verify_email.status_code == 200
    assert verify_email.json()["status"] == "pending_phone_verification"

    with SessionLocal() as session:
        request_event = session.scalar(
            select(HermesEvent).where(
                HermesEvent.event_type == "member_phone_confirmation_requested"
            )
        )
    assert request_event is not None
    assert request_event.channel == "whatsapp"
    assert request_event.recipient_phone == "5548999912345"
    assert request_event.template_key == "member_phone_confirmation_v1"

    callback = client.post(
        "/users/internal/hermes/phone-confirmation",
        headers={"X-Hermes-Callback-Secret": "callback-secret"},
        json={"phone": "5548999912345", "reply": "OK"},
    )
    assert callback.status_code == 200
    assert callback.json()["status"] == "confirmed"

    with SessionLocal() as session:
        completion_event = session.scalar(
            select(HermesEvent).where(
                HermesEvent.event_type == "member_phone_confirmation_completed"
            )
        )
    assert completion_event is not None
    assert completion_event.template_key == "member_access_code_v1"
    assert '"access_code"' in completion_event.payload_json

    access = client.post(
        "/member/access",
        json={"phone": "5548999912345", "access_code": "invalid"},
    )
    assert access.status_code == 401
    get_settings.cache_clear()


def test_admin_can_list_pending_registrations_without_otp(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from monitor_comunitario.api import routes_users

    class FakeStore:
        def list_pending(self) -> list[dict[str, object]]:
            return [
                {
                    "email": "pending@example.com",
                    "phone": "5548999912345",
                    "name": "Morador Pendente",
                    "email_verified": False,
                    "email_delivery_id": "<brevo-id@example.com>",
                    "otp_hash": "must-not-leak",
                }
            ]

    monkeypatch.setenv("EMAIL_VERIFICATION_ENABLED", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(routes_users, "get_pending_registration_store", lambda: FakeStore())

    response = client.get("/admin/registrations/pending", headers=admin_headers(client))

    assert response.status_code == 200
    body = response.json()
    assert body[0]["email"] == "pending@example.com"
    assert body[0]["email_delivery_id"] == "<brevo-id@example.com>"
    assert "otp" not in body[0]
    assert "otp_hash" not in body[0]


def test_monitor_bot_key_can_read_pending_registrations_without_admin_session(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from monitor_comunitario.api import routes_users

    class FakeStore:
        def list_pending(self) -> list[dict[str, object]]:
            return [
                {
                    "email": "bot@example.com",
                    "phone": "5548999912345",
                    "name": "Bot Teste",
                    "email_verified": False,
                }
            ]

    monkeypatch.setenv("MONITOR_BOT_API_KEY", "dedicated-bot-key")
    monkeypatch.setenv("EMAIL_VERIFICATION_ENABLED", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(routes_users, "get_pending_registration_store", lambda: FakeStore())

    response = client.get(
        "/admin/registrations/pending",
        headers={"X-Monitor-Bot-Key": "dedicated-bot-key"},
    )

    assert response.status_code == 200
    assert response.json()[0]["email"] == "bot@example.com"


def test_admin_can_resend_confirmation_email_with_cooldown(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from monitor_comunitario.api import routes_users
    from monitor_comunitario.services import email_verification

    class FakeStore:
        def __init__(self) -> None:
            self.pending: dict[str, object] = {
                "email": "pending@example.com",
                "phone": "5548999912345",
                "name": "Morador Pendente",
                "email_verified": False,
                "otp_hash": "old-hash",
            }

        def list_pending(self) -> list[dict[str, object]]:
            return [self.pending]

        def load(self, email: str) -> dict[str, object] | None:
            return self.pending if email == self.pending["email"] else None

        def save(
            self, email: str, phone: str, payload: dict[str, object], ttl_seconds: int
        ) -> None:
            self.pending = payload

    store = FakeStore()
    delivered: list[tuple[str, str]] = []
    monkeypatch.setenv("EMAIL_VERIFICATION_ENABLED", "true")
    monkeypatch.setenv("EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS", "60")
    get_settings.cache_clear()
    monkeypatch.setattr(routes_users, "get_pending_registration_store", lambda: store)
    monkeypatch.setattr(
        email_verification,
        "send_verification_email",
        lambda *, email, otp: (delivered.append((email, otp)) or "<new-id@example.com>"),
    )

    response = client.post(
        "/admin/registrations/pending/resend",
        headers=admin_headers(client),
        json={"email": "pending@example.com"},
    )

    assert response.status_code == 200
    assert response.json()["email_delivery_id"] == "<new-id@example.com>"
    assert delivered and delivered[0][0] == "pending@example.com"
    assert "otp" not in response.json()

    cooldown = client.post(
        "/admin/registrations/pending/resend",
        headers=admin_headers(client),
        json={"email": "pending@example.com"},
    )
    assert cooldown.status_code == 429
