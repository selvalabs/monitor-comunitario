#!/usr/bin/env python3
"""Deliver Monitor registration events through the dedicated Hermes instance."""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from contextlib import suppress
from pathlib import Path
from typing import Any

EVENT_TYPES = (
    "member_phone_confirmation_requested",
    "member_phone_confirmation_completed",
)
TEMPLATES = {"member_phone_confirmation_v1", "member_access_code_v1"}
HERMES_BIN = "/opt/hermes/bin/hermes"
ENV_PATH = Path("/opt/data/.env")


def load_env() -> dict[str, str]:
    """Load only the dispatcher configuration from its protected env file."""
    values: dict[str, str] = {}
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def api_request(
    base_url: str,
    secret: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"X-Hermes-Event-Secret": secret}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}", data=body, headers=headers, method=method
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def render_message(event: dict[str, Any], access_code: str | None = None) -> str:
    """Render approved deterministic content without logging personal data."""
    payload = event["payload"]
    name = str(payload.get("name") or "pessoa")
    if event["event_type"] == "member_phone_confirmation_requested":
        hours = int(payload.get("phone_confirmation_ttl_hours", 48))
        url = str(payload.get("url") or "")
        return (
            f"Oi, {name}! Esta e uma confirmacao do Monitor Comunitario. "
            "Ao responder OK, voce confirma que deseja receber notificacoes "
            "sobre possiveis desligamentos programados ou falta de energia "
            "no bairro/endereco cadastrado. "
            "As informacoes sao baseadas em avisos publicos e o Monitor "
            "Comunitario nao e um canal oficial da Celesc. "
            f"Saiba mais: {url} "
            "Responda OK para confirmar ou CANCELAR para nao ativar o cadastro. "
            f"Voce tem {hours} horas para responder. "
            "Sem resposta nesse prazo, a solicitacao expira automaticamente."
        )
    if not access_code:
        raise ValueError("Missing ephemeral access code")
    url = str(payload.get("url") or "")
    return (
        f"Cadastro confirmado, {name}! Seu codigo privado e {access_code}. "
        f"Acesse {url} para entrar na area do morador."
    )


def send_whatsapp(phone: str, message: str) -> None:
    result = subprocess.run(
        [HERMES_BIN, "send", "--to", f"whatsapp:{phone}", message, "--quiet"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("Hermes WhatsApp delivery failed")


def main() -> int:
    env = load_env()
    base_url = env.get("MONITOR_API_BASE_URL", "")
    secret = env.get("MONITOR_HERMES_EVENT_API_SECRET", "")
    if not base_url or not secret:
        raise RuntimeError("Monitor event API configuration is incomplete")
    query = urllib.parse.urlencode([("event_type", value) for value in EVENT_TYPES])
    events = api_request(base_url, secret, "GET", f"/internal/hermes/events?{query}")
    processed = 0
    failed = 0
    for event in events:
        if event.get("template_key") not in TEMPLATES:
            continue
        try:
            access_code = None
            if event["event_type"] == "member_phone_confirmation_completed":
                code_response = api_request(
                    base_url, secret, "GET", f"/internal/hermes/events/{event['id']}/access-code"
                )
                access_code = str(code_response["access_code"])
            send_whatsapp(str(event["recipient_phone"]), render_message(event, access_code))
            api_request(
                base_url,
                secret,
                "PATCH",
                f"/internal/hermes/events/{event['id']}",
                {"status": "processed", "error_message": ""},
            )
            processed += 1
        except (OSError, RuntimeError, KeyError, TypeError, ValueError, urllib.error.URLError):
            failed += 1
            with suppress(OSError, TypeError, ValueError, urllib.error.URLError):
                api_request(
                    base_url,
                    secret,
                    "PATCH",
                    f"/internal/hermes/events/{event['id']}",
                    {"status": "failed", "error_message": "Hermes delivery failed"},
                )
    print(f"monitor_registration processed={processed} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
