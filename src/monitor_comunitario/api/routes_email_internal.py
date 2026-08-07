import base64

# ruff: noqa: E501
import binascii
import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from monitor_comunitario.core.config import get_settings
from monitor_comunitario.db.models import InboundEmail
from monitor_comunitario.db.session import get_session

router = APIRouter(prefix="/internal/email", tags=["internal", "email"])
SessionDep = Annotated[Session, Depends(get_session)]
MAX_ENVELOPE_BYTES = 15 * 1024 * 1024
MAX_TIMESTAMP_SKEW_SECONDS = 300

def _reject() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email ingress request.")

def _allowed_recipient(value: str) -> bool:
    allowed = {item.strip().lower() for item in get_settings().email_ingress_allowed_recipients.split(",") if item.strip()}
    return value.strip().lower() in allowed

@router.post("/inbound", status_code=status.HTTP_202_ACCEPTED)
async def receive_email(
    request: Request,
    session: SessionDep,
    timestamp: Annotated[str | None, Header(alias="X-Email-Ingress-Timestamp")] = None,
    signature: Annotated[str | None, Header(alias="X-Email-Ingress-Signature")] = None,
) -> dict[str, str]:
    settings = get_settings()
    if not settings.email_ingress_secret or not timestamp or not signature or not signature.startswith("sha256="):
        raise _reject()
    body = await request.body()
    if len(body) > MAX_ENVELOPE_BYTES:
        raise HTTPException(status_code=413, detail="Email ingress payload is too large.")
    try:
        received_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if received_at.tzinfo is None or abs((datetime.now(UTC) - received_at).total_seconds()) > MAX_TIMESTAMP_SKEW_SECONDS:
            raise ValueError
    except ValueError as error:
        raise _reject() from error
    expected = hmac.new(settings.email_ingress_secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature[7:], expected):
        raise _reject()
    try:
        payload = json.loads(body)
        raw = base64.b64decode(payload["rawMimeBase64"], validate=True)
        key = payload["idempotencyKey"]
        recipient = payload["recipient"].strip().lower()
        sender = payload.get("sender", "").strip().lower()
    except (KeyError, TypeError, ValueError, binascii.Error, json.JSONDecodeError) as error:
        raise HTTPException(status_code=400, detail="Invalid email ingress envelope.") from error
    if payload.get("version") != 1 or not isinstance(key, str) or len(key) != 64 or not all(c in "0123456789abcdef" for c in key) or not _allowed_recipient(recipient) or len(raw) > get_settings().email_ingress_max_raw_bytes:
        raise HTTPException(status_code=400, detail="Invalid email ingress envelope.")
    if session.scalar(select(InboundEmail).where(InboundEmail.idempotency_key == key)) is not None:
        return {"status": "duplicate"}
    session.add(InboundEmail(idempotency_key=key, recipient=recipient, sender=sender, received_at=received_at, raw_mime=raw))
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return {"status": "duplicate"}
    return {"status": "accepted"}
