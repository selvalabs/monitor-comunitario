from collections.abc import Generator
from typing import Any

import httpx
import pytest

from monitor_comunitario.core.config import get_settings
from monitor_comunitario.services import email_verification


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, str]:
        return {"messageId": "<brevo-message-id@example.com>"}


class FakeClient:
    def __init__(self, **kwargs: Any) -> None:
        self.options = kwargs

    requests: list[dict[str, Any]] = []

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.requests.append({"url": url, **kwargs})
        return FakeResponse()


@pytest.fixture()
def brevo_settings(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("EMAIL_PROVIDER", "brevo")
    monkeypatch.setenv("BREVO_API_KEY", "test-brevo-key")
    monkeypatch.setenv("EMAIL_FROM", "monitor@soberania.cloud")
    get_settings.cache_clear()
    FakeClient.requests = []
    yield
    get_settings.cache_clear()


def test_brevo_provider_returns_message_id(
    brevo_settings: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(httpx, "Client", FakeClient)

    message_id = email_verification.send_verification_email(
        email="resident@example.com",
        otp="123456",
    )

    assert message_id == "<brevo-message-id@example.com>"
    assert FakeClient.requests[0]["url"] == "https://api.brevo.com/v3/smtp/email"
    assert FakeClient.requests[0]["headers"]["api-key"] == "test-brevo-key"
    assert FakeClient.requests[0]["json"]["to"] == [{"email": "resident@example.com"}]
    assert FakeClient.requests[0]["json"]["subject"] == "Confirme seu cadastro no Monitor Comunitário"
    assert "123456" in FakeClient.requests[0]["json"]["textContent"]
    assert "48 horas" in FakeClient.requests[0]["json"]["textContent"]
    assert "Se você não iniciou este cadastro, ignore esta mensagem." in FakeClient.requests[0]["json"]["textContent"]
