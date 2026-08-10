from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable

import httpx

from monitor_comunitario.core.config import Settings
from monitor_comunitario.notifications.telegram_admin_bot import (
    RegistrationAdminBot,
    TelegramAdminUpdate,
)
from monitor_comunitario.notifications.telegram_provider import TelegramMessage

logger = logging.getLogger(__name__)
MAX_MESSAGE_LENGTH = 4_000


def parse_allowed_user_ids(value: str) -> frozenset[int]:
    return frozenset(int(item.strip()) for item in value.split(",") if item.strip().isdigit())


def _chunks(text: str | Iterable[str]) -> list[str]:
    chunks: list[str] = []
    current = ""
    lines = text.splitlines() if isinstance(text, str) else text
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


class MonitorTelegramBot:
    """Telegram transport for the restricted registration admin controller."""

    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.bot_token = settings.monitor_telegram_bot_token.strip()
        self.allowed_user_ids = parse_allowed_user_ids(settings.monitor_telegram_allowed_user_ids)
        self.api_base_url = settings.monitor_telegram_api_base_url.rstrip("/")
        self.poll_timeout = settings.monitor_telegram_poll_timeout_seconds
        self.client = client
        from monitor_comunitario.notifications.telegram_admin_bot import HttpRegistrationAdminApi

        self.controller = RegistrationAdminBot(
            HttpRegistrationAdminApi(settings.monitor_bot_api_url, settings.monitor_bot_api_key),
            {str(user_id) for user_id in self.allowed_user_ids},
        )

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

    async def send_message(self, chat_id: int, message: TelegramMessage) -> None:
        for chunk in _chunks(message.text):
            await self._api(
                "sendMessage",
                {"chat_id": chat_id, "text": chunk, "disable_web_page_preview": True},
            )

    async def handle_update(self, update: dict[str, object]) -> None:
        message = update.get("message")
        if not isinstance(message, dict):
            return
        sender, chat, text = message.get("from"), message.get("chat"), message.get("text")
        if not isinstance(sender, dict) or not isinstance(chat, dict) or not isinstance(text, str):
            return
        user_id, chat_id, update_id = sender.get("id"), chat.get("id"), update.get("update_id", 0)
        if (
            not isinstance(user_id, int)
            or not isinstance(chat_id, int)
            or not self.is_authorized(user_id)
        ):
            return
        response = await self.controller.handle(
            TelegramAdminUpdate(
                user_id=str(user_id),
                chat_id=str(chat_id),
                text=text,
                update_id=int(update_id) if isinstance(update_id, int) else 0,
            )
        )
        await self.send_message(chat_id, response)

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
