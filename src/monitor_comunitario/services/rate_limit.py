import hashlib
from functools import lru_cache
from typing import Protocol

import redis

from monitor_comunitario.core.config import get_settings


class RateLimitStore(Protocol):
    def increment(self, key: str, window_seconds: int) -> tuple[int, int]:
        """Atomically increment a key and return its count and remaining TTL."""


class RateLimitUnavailable(Exception):
    """Raised when the backing store cannot enforce a limit."""


def rate_limit_key(scope: str, *identifiers: str) -> str:
    """Build an opaque Redis key without storing phone numbers or IPs."""
    value = "|".join((scope, *identifiers))
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"monitor:rate:{scope}:{digest}"

class RateLimitExceeded(Exception):
    """Raised when a caller exceeds a configured request window."""

    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__("rate limit exceeded")


class RedisRateLimitStore:
    """Redis-backed counter store using one atomic Lua operation per request."""

    _INCREMENT_SCRIPT = """
    local count = redis.call('INCR', KEYS[1])
    if count == 1 then
      redis.call('EXPIRE', KEYS[1], ARGV[1])
    end
    return {count, redis.call('TTL', KEYS[1])}
    """

    def __init__(self, url: str) -> None:
        self._client = redis.Redis.from_url(url, decode_responses=True)

    def ping(self) -> None:
        self._client.ping()

    def increment(self, key: str, window_seconds: int) -> tuple[int, int]:
        result = self._client.eval(self._INCREMENT_SCRIPT, 1, key, window_seconds)
        count, ttl = result
        return int(count), int(ttl)


class RateLimiter:
    def __init__(self, store: RateLimitStore) -> None:
        self._store = store

    def check(self, key: str, *, limit: int, window_seconds: int) -> None:
        count, ttl = self._store.increment(key, window_seconds)
        if count > limit:
            raise RateLimitExceeded(retry_after=max(ttl, 1))


@lru_cache
def get_rate_limit_store() -> RedisRateLimitStore | None:
    """Return the shared Redis store, or no limiter for local development."""
    settings = get_settings()
    if not settings.redis_url:
        return None
    return RedisRateLimitStore(settings.redis_url)


def enforce_rate_limit(key: str, *, limit: int, window_seconds: int) -> None:
    """Enforce a configured limit, failing closed when Redis is unavailable."""
    store = get_rate_limit_store()
    if store is None:
        return

    try:
        RateLimiter(store).check(key, limit=limit, window_seconds=window_seconds)
    except redis.RedisError as error:
        raise RateLimitUnavailable from error


