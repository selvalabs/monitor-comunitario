from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable

import httpx
from sqlalchemy import func, select

from monitor_comunitario.core.config import Settings
from monitor_comunitario.db.models import HermesEvent, HermesEventStatus, InboundEmail, User
from monitor_comunitario.db.session import SessionLocal

logger = logging.getLogger(__name__)
MAX_MESSAGE_LENGTH = 4_000


def parse_allowed_user_ids(value: str) -> frozenset[int]:
    return frozenset(int(item.strip()) for item in value.split(",") if item.strip().isdigit())


def _chunks(lines: Iterable[str]) -> list[str]:
    chunks: list[str] = []
    current = ""
    for line in lines:
        candidate = f"{current}\n{line}".strip()
        if len(candidate) > MAX_MESSAGE_LENGTH and current:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks or ["Sem dados."]


def _help_text() -> str:
    return (
        "Monitor ComunitÃ¡rio - administraÃ§Ã£o\n\n"
        "/status - resumo operacional\n"
        "/events - eventos Hermes recentes\n"
        "/mailbox - e-mails recebidos recentemente\n"
        "/user <id> - consultar cadastro\n"
        "/approve <id> CONFIRM - aprovar notificaÃ§Ãµes\n"
        "/disable <id> CONFIRM - desativar cadastro\n"
    )


class MonitorTelegramBot:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.bot_token = settings.monitor_telegram_bot_token.strip()
        self.allowed_user_ids = parse_allowed_user_ids(settings.monitor_telegram_allowed_user_ids)
        self.api_base_url = settings.monitor_telegram_api_base_url.rstrip("/")
        self.poll_timeout = settings.monitor_telegram_poll_timeout_seconds
        self.client = client

    def is_authorized(self, user_id: int | None) -> bool:
        return user_id is not None and user_id in self.allowed_user_ids

    async def _api(self, method: str, payload: dict[str, object]) -> dict[str, object]:
        if not self.bot_token:
            raise RuntimeError("Monitor Telegram bot token is not configured.")
        response = await self.client.post(
            f"{self.api_base_url}/bot{self.bot_token}/{method}", json=payload
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or data.get("ok") is not True:
            raise RuntimeError(f"Telegram API rejected {method}.")
        return data

    async def send_message(self, chat_id: int, text: str) -> None:
        for chunk in _chunks(text.splitlines()):
            await self._api(
                "sendMessage", {"chat_id": chat_id, "text": chunk, "disable_web_page_preview": True}
            )

    def _status_text(self) -> str:
        with SessionLocal() as session:
            active = (
                session.scalar(
                    select(func.count()).select_from(User).where(User.is_active.is_(True))
                )
                or 0
            )
            pending = (
                session.scalar(
                    select(func.count())
                    .select_from(HermesEvent)
                    .where(
                        HermesEvent.status.in_(
                            {HermesEventStatus.CREATED.value, HermesEventStatus.FAILED.value}
                        )
                    )
                )
                or 0
            )
            emails = session.scalar(select(func.count()).select_from(InboundEmail)) or 0
        return f"Status do Monitor\nCadastros ativos: {active}\nEventos pendentes/falhos: {pending}\nE-mails recebidos: {emails}"  # noqa: E501

    def _events_text(self) -> str:
        with SessionLocal() as session:
            events = list(
                session.scalars(
                    select(HermesEvent)
                    .order_by(HermesEvent.created_at.desc(), HermesEvent.id.desc())
                    .limit(10)
                ).all()
            )
        return (
            "Eventos Hermes recentes\n"
            + "\n".join(f"#{event.id} {event.event_type} [{event.status}]" for event in events)
            if events
            else "Nenhum evento Hermes registrado."
        )

    def _mailbox_text(self) -> str:
        with SessionLocal() as session:
            emails = list(
                session.scalars(
                    select(InboundEmail)
                    .order_by(InboundEmail.received_at.desc(), InboundEmail.id.desc())
                    .limit(10)
                ).all()
            )
        return (
            "Mailbox recente\n"
            + "\n".join(
                f"#{email.id} {email.sender or '-'} -> {email.recipient} ({email.received_at.isoformat()})"  # noqa: E501
                for email in emails
            )
            if emails
            else "Nenhum e-mail recebido."
        )

    def _user_text(self, user_id: int) -> str:
        with SessionLocal() as session:
            user = session.get(User, user_id)
            if user is None:
                return "Cadastro nÃ£o encontrado."
            return f"Cadastro #{user.id}\nNome: {user.name}\nTelefone: {user.phone}\nLocalidade: {user.municipality} / {user.neighborhood}\nAtivo: {'sim' if user.is_active else 'nÃ£o'}\nNotificaÃ§Ãµes aprovadas: {'sim' if user.notifications_approved else 'nÃ£o'}"  # noqa: E501

    def _mutate_user(self, command: str, args: list[str]) -> str:
        if len(args) != 2 or args[1].upper() != "CONFIRM" or not args[0].isdigit():
            return f"Uso: /{command} <id> CONFIRM"
        user_id = int(args[0])
        with SessionLocal() as session:
            user = session.get(User, user_id)
            if user is None:
                return "Cadastro nÃ£o encontrado."
            if command == "approve":
                user.notifications_approved = True
                result = "aprovado"
            else:
                user.is_active = False
                result = "desativado"
            session.add(user)
            session.commit()
        return f"Cadastro #{user_id} {result}."

    async def handle_update(self, update: dict[str, object]) -> None:
        message = update.get("message")
        if not isinstance(message, dict):
            return
        sender, chat, text = message.get("from"), message.get("chat"), message.get("text")
        if not isinstance(sender, dict) or not isinstance(chat, dict) or not isinstance(text, str):
            return
        user_id, chat_id = sender.get("id"), chat.get("id")
        if (
            not isinstance(user_id, int)
            or not isinstance(chat_id, int)
            or not self.is_authorized(user_id)
        ):
            return
        parts = text.strip().split()
        if not parts:
            return
        command = parts[0].split("@", 1)[0].lower()
        if command in {"/start", "/help"}:
            reply = _help_text()
        elif command == "/status":
            reply = self._status_text()
        elif command == "/events":
            reply = self._events_text()
        elif command == "/mailbox":
            reply = self._mailbox_text()
        elif command == "/user" and len(parts) == 2 and parts[1].isdigit():
            reply = self._user_text(int(parts[1]))
        elif command in {"/approve", "/disable"}:
            reply = self._mutate_user(command[1:], parts[1:])
        else:
            reply = "Comando desconhecido. Use /help."
        await self.send_message(chat_id, reply)

    async def run(self) -> None:
        if not self.bot_token or not self.allowed_user_ids:
            raise RuntimeError("Monitor Telegram requires a bot token and an allowed user ID.")
        offset = 0
        await self._api("deleteWebhook", {"drop_pending_updates": False})
        while True:
            data = await self._api(
                "getUpdates",
                {"offset": offset, "timeout": self.poll_timeout, "allowed_updates": ["message"]},
            )
            updates = data.get("result", [])
            if not isinstance(updates, list):
                continue
            for update in updates:
                if not isinstance(update, dict):
                    continue
                update_id = update.get("update_id")
                if isinstance(update_id, int):
                    offset = max(offset, update_id + 1)
                await self.handle_update(update)


async def run_telegram_bot(settings: Settings) -> None:
    while True:
        try:
            timeout = settings.monitor_telegram_poll_timeout_seconds + 10
            async with httpx.AsyncClient(timeout=timeout) as client:
                await MonitorTelegramBot(settings, client).run()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Monitor Telegram bot loop failed; retrying.")
            await asyncio.sleep(5)