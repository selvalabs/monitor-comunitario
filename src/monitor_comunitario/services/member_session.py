import hashlib
import json
import secrets
from functools import lru_cache
from typing import Protocol

import redis

from monitor_comunitario.core.config import get_settings

MEMBER_SESSION_COOKIE_NAME = "monitor_member_session"
MEMBER_CSRF_COOKIE_NAME = "monitor_member_csrf"
MEMBER_SESSION_TTL_SECONDS = 3600
MEMBER_CSRF_TOKEN_BYTES = 32


class MemberSessionUnavailable(Exception):
    """Raised when the member session store cannot be reached."""


class MemberSessionStoreProtocol(Protocol):
    def create(self, user_id: int, ttl_seconds: int = MEMBER_SESSION_TTL_SECONDS) -> str: ...

    def get_user_id(self, token: str) -> int | None: ...

    def delete(self, token: str) -> None: ...


class MemberSessionStore:
    def __init__(self, url: str) -> None:
        self._client = redis.Redis.from_url(url, decode_responses=True)

    def _key(self, token: str) -> str:
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return f"monitor:member-session:{digest}"

    def create(self, user_id: int, ttl_seconds: int = MEMBER_SESSION_TTL_SECONDS) -> str:
        token = secrets.token_urlsafe(32)
        try:
            self._client.setex(self._key(token), ttl_seconds, json.dumps({"user_id": user_id}))
        except redis.RedisError as error:
            raise MemberSessionUnavailable from error
        return token

    def get_user_id(self, token: str) -> int | None:
        try:
            value = self._client.get(self._key(token))
        except redis.RedisError as error:
            raise MemberSessionUnavailable from error
        if not value:
            return None
        try:
            user_id = json.loads(value).get("user_id")
            return int(user_id) if user_id is not None else None
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise MemberSessionUnavailable from error

    def delete(self, token: str) -> None:
        try:
            self._client.delete(self._key(token))
        except redis.RedisError as error:
            raise MemberSessionUnavailable from error


@lru_cache
def get_member_session_store() -> MemberSessionStore | None:
    settings = get_settings()
    return MemberSessionStore(settings.redis_url) if settings.redis_url else None


def generate_member_csrf_token() -> str:
    return secrets.token_urlsafe(MEMBER_CSRF_TOKEN_BYTES)
