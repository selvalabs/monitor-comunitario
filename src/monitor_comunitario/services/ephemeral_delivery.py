import hashlib
import json
import secrets
from functools import lru_cache
from typing import Any

import redis

from monitor_comunitario.core.config import get_settings

DELIVERY_REF_BYTES = 24
DELIVERY_TTL_SECONDS = 900


class EphemeralDeliveryUnavailable(Exception):
    """Raised when a one-time delivery secret cannot be stored or consumed."""


class EphemeralDeliveryStore:
    def __init__(self, url: str) -> None:
        self._client = redis.Redis.from_url(url, decode_responses=True)

    def _key(self, reference: str) -> str:
        digest = hashlib.sha256(reference.encode("utf-8")).hexdigest()
        return f"monitor:delivery-secret:{digest}"

    def save(self, reference: str, payload: dict[str, Any], ttl_seconds: int) -> None:
        try:
            self._client.setex(self._key(reference), ttl_seconds, json.dumps(payload))
        except redis.RedisError as error:
            raise EphemeralDeliveryUnavailable from error

    def consume(self, reference: str) -> dict[str, Any] | None:
        try:
            with self._client.pipeline() as pipeline:
                pipeline.get(self._key(reference))
                pipeline.delete(self._key(reference))
                value, _ = pipeline.execute()
        except redis.RedisError as error:
            raise EphemeralDeliveryUnavailable from error
        return json.loads(value) if value else None


@lru_cache
def get_ephemeral_delivery_store() -> EphemeralDeliveryStore | None:
    settings = get_settings()
    return EphemeralDeliveryStore(settings.redis_url) if settings.redis_url else None


def generate_delivery_reference() -> str:
    return secrets.token_urlsafe(DELIVERY_REF_BYTES)
