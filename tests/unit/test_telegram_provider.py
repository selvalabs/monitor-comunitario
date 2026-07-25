import pytest

from monitor_comunitario.notifications.telegram_provider import (
    TelegramMessage,
    TelegramNotificationProvider,
)


class FakeResponse:
    def raise_for_status(self) -> None:
        return None


class FakeAsyncClient:
    def __init__(self, timeout: int) -> None:
        self.timeout = timeout
        self.posts: list[tuple[str, dict[str, object]]] = []

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def post(self, url: str, json: dict[str, object]) -> FakeResponse:
        self.posts.append((url, json))
        return FakeResponse()


@pytest.mark.asyncio
async def test_telegram_provider_sends_message_payload() -> None:
    fake_client = FakeAsyncClient
    provider = TelegramNotificationProvider(
        bot_token="test-token",
        chat_id="123456",
        client_factory=fake_client,
    )

    await provider.send_message(TelegramMessage(text="worker failed"))

    client = provider.last_client
    assert client is not None
    assert client.posts == [
        (
            "https://api.telegram.org/bottest-token/sendMessage",
            {
                "chat_id": "123456",
                "text": "worker failed",
                "disable_web_page_preview": True,
            },
        )
    ]


@pytest.mark.asyncio
async def test_telegram_provider_requires_configuration() -> None:
    provider = TelegramNotificationProvider(bot_token="", chat_id="")

    with pytest.raises(ValueError, match="Telegram provider is not configured"):
        await provider.send_message(TelegramMessage(text="hello"))
