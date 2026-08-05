import hashlib
import hmac
import time
from secrets import token_urlsafe

SESSION_COOKIE_NAME = "monitor_admin_session"
CSRF_COOKIE_NAME = "monitor_admin_csrf"
SESSION_TTL_SECONDS = 3600
CSRF_TOKEN_LENGTH = 32


def create_session_token(api_key: str, now: int | None = None) -> str:
    """Create a short-lived, signed bearer token without storing the API key."""
    issued_at = int(time.time() if now is None else now)
    payload = f"{issued_at}.{token_urlsafe(24)}"
    signature = hmac.new(api_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def verify_session_token(api_key: str, token: str, now: int | None = None) -> bool:
    """Verify token integrity and enforce its one-hour lifetime."""
    try:
        issued_at_text, nonce, signature = token.split(".", 2)
        issued_at = int(issued_at_text)
    except (ValueError, TypeError):
        return False

    current_time = int(time.time() if now is None else now)
    if issued_at > current_time or current_time - issued_at > SESSION_TTL_SECONDS:
        return False

    payload = f"{issued_at}.{nonce}"
    expected = hmac.new(api_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)
