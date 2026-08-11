from dataclasses import replace

import pytest

from monitor_comunitario.notifications.telegram_admin_bot import (
    HermesEventSummary,
    InboundEmailDetail,
    InboundEmailSummary,
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
        self.mailbox = [
            InboundEmailSummary(
                email_id=42,
                sender="morador@example.com",
                recipient="monitor@monitor-mail.soberania.cloud",
                subject="Duvida sobre o aviso",
                received_at="2026-08-11T15:00:00+00:00",
            )
        ]
        self.email = InboundEmailDetail(
            email_id=42,
            sender="morador@example.com",
            recipient="monitor@monitor-mail.soberania.cloud",
            subject="Duvida sobre o aviso",
            received_at="2026-08-11T15:00:00+00:00",
            body_text="Ola, gostaria de confirmar o horario do aviso.",
            attachment_count=0,
        )
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

    async def list_mailbox(self, page: int) -> list[InboundEmailSummary]:
        assert page == 2
        return self.mailbox

    async def get_email(self, email_id: int) -> InboundEmailDetail | None:
        return self.email if email_id == 42 else None


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


@pytest.mark.asyncio
async def test_mailbox_lists_a_requested_page_with_safe_metadata() -> None:
    bot = RegistrationAdminBot(FakeApi(), {"7609256077"})

    response = await bot.handle(TelegramAdminUpdate("7609256077", "chat", "/mailbox 2"))

    assert "Mailbox - pagina 2" in response.text
    assert "#42" in response.text
    assert "morador@example.com" in response.text
    assert "Duvida sobre o aviso" in response.text
    assert "raw_mime" not in response.text


@pytest.mark.asyncio
async def test_email_reads_a_selected_sanitized_message() -> None:
    bot = RegistrationAdminBot(FakeApi(), {"7609256077"})

    response = await bot.handle(TelegramAdminUpdate("7609256077", "chat", "/email 42"))

    assert "E-mail #42" in response.text
    assert "Ola, gostaria de confirmar o horario" in response.text
    assert "Anexos: 0" in response.text


@pytest.mark.asyncio
async def test_email_rejects_an_invalid_or_unknown_identifier() -> None:
    bot = RegistrationAdminBot(FakeApi(), {"7609256077"})

    invalid = await bot.handle(TelegramAdminUpdate("7609256077", "chat", "/email no"))
    unknown = await bot.handle(TelegramAdminUpdate("7609256077", "chat", "/email 99"))

    assert invalid.text == "Uso: /email ID"
    assert unknown.text == "E-mail nao encontrado."
