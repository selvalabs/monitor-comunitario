import pytest

from monitor_comunitario.scraper import celesc_page


class FakePage:
    def __init__(self) -> None:
        self.goto_calls: list[dict[str, object]] = []
        self.load_state_calls: list[dict[str, object]] = []

    async def goto(self, url: str, **kwargs: object) -> None:
        self.goto_calls.append({"url": url, **kwargs})

    async def wait_for_load_state(self, state: str, **kwargs: object) -> None:
        self.load_state_calls.append({"state": state, **kwargs})


@pytest.mark.asyncio
async def test_wait_for_celesc_page_uses_domcontentloaded_then_short_idle_wait() -> None:
    page = FakePage()

    await celesc_page.wait_for_celesc_page(  # type: ignore[attr-defined]
        page, "https://example.test/celesc", timeout_ms=30_000
    )

    assert page.goto_calls == [
        {
            "url": "https://example.test/celesc",
            "wait_until": "domcontentloaded",
            "timeout": 30_000,
        }
    ]
    assert page.load_state_calls == [
        {"state": "networkidle", "timeout": 5_000}
    ]
