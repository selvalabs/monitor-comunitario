import hashlib
import json
import secrets
import smtplib
from email.message import EmailMessage
from functools import lru_cache
from typing import Any

import redis

from monitor_comunitario.core.config import get_settings

OTP_LENGTH = 6


def normalize_email(value: str) -> str:
    return value.strip().lower()


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):0{OTP_LENGTH}d}"


def hash_otp(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def format_expiration(seconds: int) -> str:
    """Format a verification TTL for the resident-facing email."""
    hours, remainder = divmod(seconds, 3600)
    if hours and remainder == 0:
        return f"{hours} horas"
    return f"{max(seconds // 60, 1)} minutos"


class EmailVerificationUnavailable(Exception):
    """Raised when pending registration storage or delivery is unavailable."""


class PendingRegistrationStore:
    def __init__(self, url: str) -> None:
        self._client = redis.Redis.from_url(url, decode_responses=True)

    def _key(self, value: str) -> str:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return f"monitor:registration:{digest}"

    def save(self, email: str, phone: str, payload: dict[str, Any], ttl_seconds: int) -> None:
        try:
            serialized = json.dumps(payload)
            self._client.setex(self._key(email), ttl_seconds, serialized)
            self._client.setex(self._key(phone), ttl_seconds, serialized)
        except redis.RedisError as error:
            raise EmailVerificationUnavailable from error

    def load(self, email: str) -> dict[str, Any] | None:
        try:
            value = self._client.get(self._key(email))
        except redis.RedisError as error:
            raise EmailVerificationUnavailable from error
        return json.loads(value) if value else None

    def load_by_phone(self, phone: str) -> dict[str, Any] | None:
        try:
            value = self._client.get(self._key(phone))
        except redis.RedisError as error:
            raise EmailVerificationUnavailable from error
        return json.loads(value) if value else None

    def delete(self, email: str, phone: str) -> None:
        try:
            self._client.delete(self._key(email), self._key(phone))
        except redis.RedisError as error:
            raise EmailVerificationUnavailable from error

    def list_pending(self) -> list[dict[str, Any]]:
        """List pending registrations without exposing Redis key material."""
        try:
            values: dict[str, dict[str, Any]] = {}
            for key in self._client.scan_iter(match="monitor:registration:*"):
                raw_value = self._client.get(key)
                if not raw_value:
                    continue
                payload = json.loads(raw_value)
                email = normalize_email(str(payload.get("email", "")))
                if email:
                    values[email] = payload
        except (redis.RedisError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise EmailVerificationUnavailable from error
        return list(values.values())


@lru_cache
def get_pending_registration_store() -> PendingRegistrationStore | None:
    settings = get_settings()
    return PendingRegistrationStore(settings.redis_url) if settings.redis_url else None


def send_verification_email(*, email: str, otp: str) -> str | None:
    settings = get_settings()
    message = EmailMessage()
    message["Subject"] = "Confirme seu cadastro no Monitor Comunitario"
    message["From"] = settings.email_from
    message["To"] = email
    message.set_content(
        "Seu codigo de confirmacao do Monitor Comunitario e: "
        + otp
        + "\n\nEle expira em "
        + format_expiration(settings.email_verification_ttl_seconds)
        + "."
    )

    if settings.email_provider.lower() == "brevo":
        import httpx

        payload = {
            "sender": {"email": settings.email_from},
            "to": [{"email": email}],
            "subject": message["Subject"],
            "textContent": message.get_content(),
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(
                    settings.brevo_api_url,
                    headers={
                        "accept": "application/json",
                        "api-key": settings.brevo_api_key,
                        "content-type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                response_payload = response.json()
        except (OSError, httpx.HTTPError, ValueError) as error:
            raise EmailVerificationUnavailable from error
        message_id = response_payload.get("messageId")
        return str(message_id) if message_id else None

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_tls:
                server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        raise EmailVerificationUnavailable from error
    return None
