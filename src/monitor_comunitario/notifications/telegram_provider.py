from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, cast

import httpx


@dataclass(frozen=True)
class TelegramMessage:
    """Message payload expected by the Telegram notification provider."""

    text: str
    disable_web_page_preview: bool = True


class TelegramResponse(Protocol):
    def raise_for_status(self) -> None:
        """Raise if Telegram returned a non-success status."""


class TelegramClient(Protocol):
    async def __aenter__(self) -> "TelegramClient":
        """Enter async context."""

    async def __aexit__(self, *_args: object) -> None:
        """Exit async context."""

    async def post(self, url: str, **kwargs: Any) -> TelegramResponse:
        """Post JSON to Telegram."""


class TelegramNotificationProvider:
    """Thin Telegram Bot API adapter for internal operator escalation."""

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        client_factory: Callable[[int], TelegramClient] | None = None,
        api_base_url: str = "https://api.telegram.org",
    ) -> None:
        self.bot_token = bot_token.strip()
        self.chat_id = chat_id.strip()
        self.api_base_url = api_base_url.rstrip("/")
        self.client_factory = client_factory or self._default_client_factory
        self.last_client: TelegramClient | None = None

    @staticmethod
    def _default_client_factory(timeout: int) -> TelegramClient:
        return cast(TelegramClient, httpx.AsyncClient(timeout=timeout))

    async def send_message(self, message: TelegramMessage) -> None:
        """Send a text message through Telegram Bot API."""
        if not self.bot_token or not self.chat_id:
            raise ValueError("Telegram provider is not configured.")

        url = f"{self.api_base_url}/bot{self.bot_token}/sendMessage"
        payload: dict[str, object] = {
            "chat_id": self.chat_id,
            "text": message.text,
            "disable_web_page_preview": message.disable_web_page_preview,
        }

        async with self.client_factory(30) as client:
            self.last_client = client
            response = await client.post(url, json=payload)
            response.raise_for_status()
