import pytest

from monitor_comunitario.core.config import Settings, validate_runtime_settings
from monitor_comunitario.services.rate_limit import RateLimiter, RateLimitExceeded


class FakeStore:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    def increment(self, key: str, window_seconds: int) -> tuple[int, int]:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key], window_seconds


def test_rate_limiter_allows_requests_until_limit() -> None:
    limiter = RateLimiter(store=FakeStore())

    limiter.check("register:ip", limit=2, window_seconds=60)
    limiter.check("register:ip", limit=2, window_seconds=60)


def test_rate_limiter_rejects_requests_over_limit() -> None:
    limiter = RateLimiter(store=FakeStore())

    limiter.check("member:ip:phone", limit=1, window_seconds=300)

    with pytest.raises(RateLimitExceeded) as error:
        limiter.check("member:ip:phone", limit=1, window_seconds=300)

    assert error.value.retry_after == 300


def test_rate_limiter_keeps_keys_isolated() -> None:
    limiter = RateLimiter(store=FakeStore())

    limiter.check("member:ip-a:phone", limit=1, window_seconds=60)
    limiter.check("member:ip-b:phone", limit=1, window_seconds=60)

def test_production_requires_redis_url() -> None:
    settings = Settings(
        app_env="production",
        database_url="postgresql+psycopg://app:secret@db.example.com/app?sslmode=require",
        admin_api_key="a" * 32,
    )

    with pytest.raises(ValueError, match="Redis"):
        validate_runtime_settings(settings)
