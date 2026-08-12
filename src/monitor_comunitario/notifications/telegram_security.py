def telegram_request_error(method: str) -> RuntimeError:
    """Build a transport error without exposing the bot URL or response body."""
    return RuntimeError(f"Telegram API request failed for {method}.")
