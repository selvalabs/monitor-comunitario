import asyncio
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from monitor_comunitario.notifications.telegram_provider import TelegramMessage
from monitor_comunitario.notifications.telegram_security import telegram_request_error


@dataclass(frozen=True)
class TelegramAdminUpdate:
    """Minimal Telegram update data needed by the registration operator bot."""

    user_id: str
    chat_id: str
    text: str
    update_id: int = 0


@dataclass(frozen=True)
class PendingRegistration:
    email: str
    phone: str
    name: str
    email_verified: bool
    email_delivery_id: str
    status: str


@dataclass(frozen=True)
class HermesEventSummary:
    event_id: int
    event_type: str
    status: str
    recipient_phone: str


@dataclass(frozen=True)
class InboundEmailSummary:
    email_id: int
    sender: str
    recipient: str
    subject: str
    received_at: str


@dataclass(frozen=True)
class InboundEmailDetail(InboundEmailSummary):
    body_text: str
    attachment_count: int


class RegistrationAdminApi(Protocol):
    async def list_pending(self) -> list[PendingRegistration]:
        """Return redacted pending registration state."""

    async def list_hermes_events(self) -> list[HermesEventSummary]:
        """Return registration-related Hermes event state."""

    async def resend_confirmation(self, email: str) -> PendingRegistration:
        """Request one approved OTP resend."""

    async def list_mailbox(self, page: int) -> list[InboundEmailSummary]:
        """Return one safe page of inbound email metadata."""

    async def get_email(self, email_id: int) -> InboundEmailDetail | None:
        """Return one sanitized inbound email, if it exists."""


class TelegramTransport(Protocol):
    async def get_updates(self, offset: int | None = None) -> list[TelegramAdminUpdate]:
        """Poll Telegram for updates."""

    async def send_message(self, chat_id: str, message: TelegramMessage) -> None:
        """Send one operator response."""


class HttpRegistrationAdminApi:
    """Private HTTP client for the registration admin endpoints."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip()

    async def _request(self, method: str, path: str, **kwargs: Any) -> object:
        if not self.api_key:
            raise ValueError("Monitor bot API key is not configured.")
        headers = {"X-Monitor-Bot-Key": self.api_key}
        async with httpx.AsyncClient(base_url=self.base_url, timeout=15.0) as client:
            response = await client.request(method, path, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()

    async def list_pending(self) -> list[PendingRegistration]:
        payload = await self._request("GET", "/admin/registrations/pending")
        if not isinstance(payload, list):
            raise ValueError("Invalid pending registration response.")
        return [PendingRegistration(**item) for item in payload]

    async def list_hermes_events(self) -> list[HermesEventSummary]:
        payload = await self._request(
            "GET",
            "/internal/monitor-bot/registration-events",
            params={"limit": 50},
        )
        if not isinstance(payload, list):
            raise ValueError("Invalid Hermes event response.")
        return [
            HermesEventSummary(
                event_id=int(item["id"]),
                event_type=str(item["event_type"]),
                status=str(item["status"]),
                recipient_phone=str(item.get("recipient_phone", "")),
            )
            for item in payload
            if str(item.get("event_type", "")).startswith("member_phone_confirmation_")
        ]

    async def resend_confirmation(self, email: str) -> PendingRegistration:
        payload = await self._request(
            "POST",
            "/admin/registrations/pending/resend",
            json={"email": email},
        )
        if not isinstance(payload, dict):
            raise ValueError("Invalid resend response.")
        return PendingRegistration(**payload)

    async def list_mailbox(self, page: int) -> list[InboundEmailSummary]:
        payload = await self._request(
            "GET",
            "/internal/monitor-bot/mailbox",
            params={"page": page},
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("emails"), list):
            raise ValueError("Invalid mailbox response.")
        return [
            InboundEmailSummary(
                email_id=int(item["id"]),
                sender=str(item["sender"]),
                recipient=str(item["recipient"]),
                subject=str(item["subject"]),
                received_at=str(item["received_at"]),
            )
            for item in payload["emails"]
            if isinstance(item, dict)
        ]

    async def get_email(self, email_id: int) -> InboundEmailDetail | None:
        try:
            payload = await self._request("GET", f"/internal/monitor-bot/mailbox/{email_id}")
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                return None
            raise
        if not isinstance(payload, dict):
            raise ValueError("Invalid mailbox email response.")
        return InboundEmailDetail(
            email_id=int(payload["id"]),
            sender=str(payload["sender"]),
            recipient=str(payload["recipient"]),
            subject=str(payload["subject"]),
            received_at=str(payload["received_at"]),
            body_text=str(payload["body_text"]),
            attachment_count=int(payload["attachment_count"]),
        )


class HttpTelegramTransport:
    """Minimal long-polling transport for the Telegram Bot API."""

    def __init__(self, bot_token: str, api_base_url: str = "https://api.telegram.org") -> None:
        self.bot_token = bot_token.strip()
        self.api_base_url = api_base_url.rstrip("/")

    def _url(self, method: str) -> str:
        if not self.bot_token:
            raise ValueError("Telegram bot token is not configured.")
        return f"{self.api_base_url}/bot{self.bot_token}/{method}"

    async def get_updates(self, offset: int | None = None) -> list[TelegramAdminUpdate]:
        params: dict[str, int] = {"timeout": 25}
        if offset is not None:
            params["offset"] = offset
        async with httpx.AsyncClient(timeout=35.0) as client:
            try:
                response = await client.get(self._url("getUpdates"), params=params)
                response.raise_for_status()
            except httpx.HTTPError:
                raise telegram_request_error("getUpdates") from None
            payload = response.json()
        if not payload.get("ok") or not isinstance(payload.get("result"), list):
            raise ValueError("Invalid Telegram update response.")
        updates: list[TelegramAdminUpdate] = []
        for item in payload["result"]:
            message = item.get("message", {})
            sender = message.get("from", {})
            chat = message.get("chat", {})
            text = message.get("text")
            if text and "id" in item and "id" in sender and "id" in chat:
                updates.append(
                    TelegramAdminUpdate(
                        user_id=str(sender["id"]),
                        chat_id=str(chat["id"]),
                        text=str(text),
                        update_id=int(item["update_id"]),
                    )
                )
        return updates

    async def send_message(self, chat_id: str, message: TelegramMessage) -> None:
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.post(
                    self._url("sendMessage"),
                    json={
                        "chat_id": chat_id,
                        "text": message.text,
                        "disable_web_page_preview": message.disable_web_page_preview,
                    },
                )
                response.raise_for_status()
            except httpx.HTTPError:
                raise telegram_request_error("sendMessage") from None


class RegistrationAdminBotRunner:
    """Poll Telegram and dispatch only the registration-support command set."""

    def __init__(self, bot: "RegistrationAdminBot", transport: TelegramTransport) -> None:
        self.bot = bot
        self.transport = transport
        self.offset: int | None = None

    async def run_once(self) -> int:
        updates = await self.transport.get_updates(self.offset)
        for update in updates:
            response = await self.bot.handle(update)
            await self.transport.send_message(update.chat_id, response)
            self.offset = max(self.offset or 0, update.update_id + 1)
        return len(updates)

    async def run_forever(self, poll_interval_seconds: float = 1.0) -> None:
        """Keep polling until the process receives a cancellation."""
        while True:
            await self.run_once()
            await asyncio.sleep(poll_interval_seconds)


@dataclass(frozen=True)
class _ConfirmationNonce:
    value: str
    user_id: str
    chat_id: str
    email: str
    expires_at: float


class RegistrationAdminBot:
    """Authorize and route narrow Telegram commands for registration support."""

    def __init__(
        self,
        api: RegistrationAdminApi,
        allowed_user_ids: set[str],
        *,
        nonce_ttl_seconds: int = 120,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.api = api
        self.allowed_user_ids = {value.strip() for value in allowed_user_ids if value.strip()}
        self.nonce_ttl_seconds = nonce_ttl_seconds
        self.clock = clock
        self._nonces: dict[str, _ConfirmationNonce] = {}

    async def handle(self, update: TelegramAdminUpdate) -> TelegramMessage:
        """Handle one update and return a safe operator-facing response."""
        if update.user_id not in self.allowed_user_ids:
            return TelegramMessage(text="Acesso nao autorizado.")

        command, *arguments = update.text.strip().split(maxsplit=1)
        command = command.lower()
        argument = arguments[0].strip() if arguments else ""

        if command in {"/start", "/help"}:
            return TelegramMessage(text=self._help_text())
        if command == "/status":
            pending = await self.api.list_pending()
            events = await self.api.list_hermes_events()
            return TelegramMessage(
                text=(
                    "Monitor cadastro\n"
                    f"Pendencias: {len(pending)}\n"
                    f"Eventos Hermes: {len(events)}"
                )
            )
        if command == "/pending":
            return await self._pending_text()
        if command == "/email-status":
            return await self._email_status(argument)
        if command == "/mailbox":
            return await self._mailbox_text(argument)
        if command == "/email":
            return await self._mailbox_email_text(argument)
        if command == "/resend-confirmation":
            return self._request_resend(update, argument)
        if command == "/confirm":
            return await self._confirm(update, argument)
        if command == "/cancel":
            return self._cancel(update, argument)
        if command == "/events":
            return await self._events_text()
        return TelegramMessage(text="Comando invalido. Use /help.")

    def _help_text(self) -> str:
        return (
            "Comandos de cadastro:\n"
            "/status\n"
            "/pending\n"
            "/email-status EMAIL\n"
            "/mailbox [PAGINA] - lista 10 e-mails recebidos\n"
            "/email ID - le um e-mail listado\n"
            "/resend-confirmation EMAIL\n"
            "/confirm NONCE\n"
            "/cancel NONCE\n"
            "/events"
        )

    async def _pending_text(self) -> TelegramMessage:
        pending = await self.api.list_pending()
        if not pending:
            return TelegramMessage(text="Nenhum cadastro pendente.")
        lines = ["Cadastros pendentes:"]
        for item in pending[:20]:
            lines.append(f"- {item.name} | {item.email} | {item.status}")
        if len(pending) > 20:
            lines.append(f"... e mais {len(pending) - 20}.")
        return TelegramMessage(text="\n".join(lines))

    async def _email_status(self, email: str) -> TelegramMessage:
        if not email or "@" not in email:
            return TelegramMessage(text="Uso: /email-status EMAIL")
        matches = [item for item in await self.api.list_pending() if item.email == email.lower()]
        if not matches:
            return TelegramMessage(text="Cadastro pendente nao encontrado.")
        item = matches[0]
        delivery = item.email_delivery_id or "sem id"
        return TelegramMessage(
            text=(
                f"Cadastro: {item.email}\n"
                f"Status: {item.status}\n"
                f"Entrega: {delivery}"
            )
        )

    async def _mailbox_text(self, argument: str) -> TelegramMessage:
        page = 1
        if argument:
            if not argument.isdigit() or int(argument) < 1:
                return TelegramMessage(text="Uso: /mailbox [PAGINA]")
            page = int(argument)
        emails = await self.api.list_mailbox(page)
        if not emails:
            return TelegramMessage(text=f"Mailbox - pagina {page}\nNenhum e-mail recebido.")
        lines = [f"Mailbox - pagina {page}:"]
        for email in emails:
            lines.append(
                f"#{email.email_id} | {email.sender} | {email.subject} | {email.received_at}"
            )
        lines.append("Use /email ID para ler.")
        return TelegramMessage(text="\n".join(lines))

    async def _mailbox_email_text(self, argument: str) -> TelegramMessage:
        if not argument.isdigit() or int(argument) < 1:
            return TelegramMessage(text="Uso: /email ID")
        email = await self.api.get_email(int(argument))
        if email is None:
            return TelegramMessage(text="E-mail nao encontrado.")
        return TelegramMessage(
            text=(
                f"E-mail #{email.email_id}\n"
                f"De: {email.sender}\n"
                f"Para: {email.recipient}\n"
                f"Assunto: {email.subject}\n"
                f"Recebido: {email.received_at}\n"
                f"Anexos: {email.attachment_count}\n\n"
                f"Conteudo:\n{email.body_text or '(sem corpo textual)'}"
            )
        )

    def _request_resend(self, update: TelegramAdminUpdate, email: str) -> TelegramMessage:
        email = email.lower()
        if not email or "@" not in email:
            return TelegramMessage(text="Uso: /resend-confirmation EMAIL")
        nonce = secrets.token_urlsafe(12)
        self._nonces[nonce] = _ConfirmationNonce(
            value=nonce,
            user_id=update.user_id,
            chat_id=update.chat_id,
            email=email,
            expires_at=self.clock() + self.nonce_ttl_seconds,
        )
        return TelegramMessage(
            text=(
                f"Solicitar novo e-mail para {email}?\n"
                f"Confirme em {self.nonce_ttl_seconds}s com: /confirm {nonce}"
            )
        )

    async def _confirm(self, update: TelegramAdminUpdate, nonce: str) -> TelegramMessage:
        pending = self._pop_valid_nonce(update, nonce)
        if pending is None:
            return TelegramMessage(text="Confirmacao invalida ou expirada.")
        item = await self.api.resend_confirmation(pending.email)
        return TelegramMessage(
            text=(
                f"E-mail reenviado para {item.email}.\n"
                f"Status: {item.status}\n"
                f"Entrega: {item.email_delivery_id or 'sem id'}"
            )
        )

    def _cancel(self, update: TelegramAdminUpdate, nonce: str) -> TelegramMessage:
        pending = self._nonces.get(nonce)
        if (
            pending is not None
            and pending.user_id == update.user_id
            and pending.chat_id == update.chat_id
        ):
            self._nonces.pop(nonce, None)
        return TelegramMessage(text="Confirmacao cancelada.")

    def _pop_valid_nonce(
        self, update: TelegramAdminUpdate, nonce: str
    ) -> _ConfirmationNonce | None:
        pending = self._nonces.get(nonce)
        if pending is None:
            return None
        if pending.user_id != update.user_id or pending.chat_id != update.chat_id:
            return None
        if pending.expires_at <= self.clock():
            self._nonces.pop(nonce, None)
            return None
        self._nonces.pop(nonce, None)
        return pending

    async def _events_text(self) -> TelegramMessage:
        events = await self.api.list_hermes_events()
        if not events:
            return TelegramMessage(text="Nenhum evento Hermes de cadastro.")
        lines = ["Eventos Hermes de cadastro:"]
        for event in events[:20]:
            lines.append(f"- #{event.event_id} {event.event_type} | {event.status}")
        return TelegramMessage(text="\n".join(lines))
