from dataclasses import replace

import pytest

from monitor_comunitario.notifications.telegram_admin_bot import (
    HermesEventSummary,
    PendingRegistration,
    RegistrationAdminBot,
    TelegramAdminUpdate,
)


class FakeApi:
    def __init__(self) -> None:
        self.pending = [
            PendingRegistration(
                email="person@example.com",
                phone="5548999912345",
                name="Pessoa Teste",
                email_verified=False,
                email_delivery_id="<delivery-id>",
                status="pending_email_verification",
            )
        ]
        self.events = [HermesEventSummary(1, "member_phone_confirmation_requested", "created", "")]
        self.resends: list[str] = []

    async def list_pending(self) -> list[PendingRegistration]:
        return self.pending

    async def list_hermes_events(self) -> list[HermesEventSummary]:
        return self.events

    async def resend_confirmation(self, email: str) -> PendingRegistration:
        self.resends.append(email)
        self.pending[0] = replace(
            self.pending[0],
            email_delivery_id="<new-delivery-id>",
        )
        return self.pending[0]


@pytest.mark.asyncio
async def test_unauthorized_telegram_user_cannot_read_registration_data() -> None:
    bot = RegistrationAdminBot(FakeApi(), {"7609256077"})

    response = await bot.handle(TelegramAdminUpdate("other", "chat", "/pending"))

    assert response.text == "Acesso nao autorizado."


@pytest.mark.asyncio
async def test_resend_requires_nonce_bound_to_user_and_chat() -> None:
    api = FakeApi()
    bot = RegistrationAdminBot(api, {"7609256077"})
    update = TelegramAdminUpdate("7609256077", "chat-1", "/resend-confirmation person@example.com")

    preview = await bot.handle(update)
    nonce = preview.text.split("/confirm ", 1)[1]

    wrong_chat = await bot.handle(
        TelegramAdminUpdate("7609256077", "chat-2", f"/confirm {nonce}")
    )
    assert wrong_chat.text == "Confirmacao invalida ou expirada."
    assert api.resends == []

    confirmed = await bot.handle(
        TelegramAdminUpdate("7609256077", "chat-1", f"/confirm {nonce}")
    )
    assert "E-mail reenviado" in confirmed.text
    assert api.resends == ["person@example.com"]


@pytest.mark.asyncio
async def test_bot_never_returns_otp_or_access_code() -> None:
    bot = RegistrationAdminBot(FakeApi(), {"7609256077"})

    response = await bot.handle(TelegramAdminUpdate("7609256077", "chat", "/pending"))

    assert "otp" not in response.text.lower()
    assert "codigo" not in response.text.lower()
