from collections.abc import Generator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from monitor_comunitario.api.internal import app as internal_app
from monitor_comunitario.api.main import app
from monitor_comunitario.core.config import get_settings
from monitor_comunitario.db.init_db import init_db
from monitor_comunitario.db.models import InboundEmail
from monitor_comunitario.db.session import SessionLocal


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    monkeypatch.setenv("MONITOR_BOT_API_KEY", "dedicated-bot-key")
    get_settings.cache_clear()
    init_db()

    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()


def _create_email() -> int:
    raw_mime = b"\r\n".join(
        [
            b"From: Jarbas <jarbas@example.com>",
            b"To: monitor@monitor-mail.soberania.cloud",
            b"Subject: Duvida sobre aviso",
            b"MIME-Version: 1.0",
            b'Content-Type: text/html; charset="utf-8"',
            b"",
            b"<p>Ola <strong>Monitor</strong>. https://example.com/aviso</p>",
        ]
    )
    with SessionLocal() as session:
        email = InboundEmail(
            idempotency_key=uuid4().hex + uuid4().hex,
            sender="bounces-490616134-3512083692@mail.agents.soberania.cloud",
            recipient="monitor@monitor-mail.soberania.cloud",
            received_at=datetime(2026, 8, 11, 15, tzinfo=UTC),
            raw_mime=raw_mime,
        )
        session.add(email)
        session.commit()
        session.refresh(email)
        return email.id


def test_monitor_bot_mailbox_is_paginated_and_never_exposes_raw_mime(
    client: TestClient,
) -> None:
    email_id = _create_email()

    with TestClient(internal_app) as internal_client:
        response = internal_client.get(
            "/internal/monitor-bot/mailbox?page=1",
            headers={"X-Monitor-Bot-Key": "dedicated-bot-key"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert body["emails"][0]["id"] == email_id
    assert body["emails"][0]["subject"] == "Duvida sobre aviso"
    assert body["emails"][0]["sender"] == "Jarbas <jarbas@example.com>"
    assert "raw_mime" not in response.text
    assert "idempotency_key" not in response.text


def test_monitor_bot_reads_sanitized_email_text_by_id(client: TestClient) -> None:
    email_id = _create_email()

    with TestClient(internal_app) as internal_client:
        response = internal_client.get(
            f"/internal/monitor-bot/mailbox/{email_id}",
            headers={"X-Monitor-Bot-Key": "dedicated-bot-key"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == email_id
    assert body["sender"] == "Jarbas <jarbas@example.com>"
    assert body["body_text"] == "Ola Monitor. hxxps://example.com/aviso"
    assert "<strong>" not in response.text
    assert "https://" not in response.text
    assert "raw_mime" not in response.text


def test_monitor_bot_mailbox_requires_its_dedicated_key(client: TestClient) -> None:
    with TestClient(internal_app) as internal_client:
        response = internal_client.get("/internal/monitor-bot/mailbox")

    assert response.status_code == 401
