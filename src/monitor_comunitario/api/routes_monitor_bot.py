import re
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from monitor_comunitario.api.security import require_monitor_bot_api_key
from monitor_comunitario.db.models import HermesEvent, InboundEmail
from monitor_comunitario.db.session import get_session
from monitor_comunitario.schemas.hermes_events import HermesEventBotRead
from monitor_comunitario.schemas.monitor_bot import (
    InboundEmailDetailRead,
    InboundEmailPageRead,
    InboundEmailSummaryRead,
)

router = APIRouter(
    prefix="/internal/monitor-bot",
    tags=["internal", "monitor-bot"],
    dependencies=[Depends(require_monitor_bot_api_key)],
)
SessionDep = Annotated[Session, Depends(get_session)]
REGISTRATION_EVENT_TYPES = frozenset(
    {"member_phone_confirmation_requested", "member_phone_confirmation_completed"}
)
MAILBOX_PAGE_SIZE = 10
MAX_EMAIL_BODY_LENGTH = 3_000


class _HtmlTextExtractor(HTMLParser):
    """Convert an HTML fallback email part into plain display text."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._ignored_depth += 1
        elif tag in {"br", "div", "p", "li", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._ignored_depth:
            self._ignored_depth -= 1
        elif tag in {"div", "p", "li", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)

    def text(self) -> str:
        return " ".join("".join(self.parts).split())


def _normalize_text(value: str) -> str:
    """Make untrusted e-mail content safe for a plain-text Telegram message."""
    value = " ".join(value.split())
    value = re.sub(
        r"(?i)https?://",
        lambda match: "hxxps://" if match.group().lower().startswith("https") else "hxxp://",
        value,
    )
    return value[:MAX_EMAIL_BODY_LENGTH]


def _email_text_part(email: InboundEmail) -> tuple[str, int]:
    """Return a text-only email body and attachment count without exposing MIME."""
    message = BytesParser(policy=policy.default).parsebytes(email.raw_mime)
    plain_parts: list[str] = []
    html_parts: list[str] = []
    attachments = 0

    for part in message.walk():
        if part.is_multipart():
            continue
        if part.get_content_disposition() == "attachment" or part.get_filename():
            attachments += 1
            continue
        try:
            content = part.get_content()
        except (LookupError, UnicodeError):
            continue
        if not isinstance(content, str):
            continue
        if part.get_content_type() == "text/plain":
            plain_parts.append(content)
        elif part.get_content_type() == "text/html":
            parser = _HtmlTextExtractor()
            parser.feed(content)
            html_parts.append(parser.text())

    body = "\n".join(plain_parts) or "\n".join(html_parts)
    return _normalize_text(body), attachments


def _email_summary(email: InboundEmail) -> InboundEmailSummaryRead:
    message = BytesParser(policy=policy.default).parsebytes(email.raw_mime)
    sender = _normalize_text(str(message.get("From", ""))) or _normalize_text(email.sender)
    return InboundEmailSummaryRead(
        id=email.id,
        sender=sender,
        recipient=_normalize_text(email.recipient),
        subject=_normalize_text(str(message.get("subject", ""))),
        received_at=email.received_at,
    )


@router.get("/registration-events", response_model=list[HermesEventBotRead])
def list_registration_events(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[HermesEvent]:
    """Return registration event metadata without resident payloads."""
    query = (
        select(HermesEvent)
        .where(HermesEvent.event_type.in_(REGISTRATION_EVENT_TYPES))
        .order_by(HermesEvent.created_at.desc(), HermesEvent.id.desc())
        .limit(limit)
    )
    return list(session.scalars(query).all())


@router.get("/mailbox", response_model=InboundEmailPageRead)
def list_mailbox(
    session: SessionDep,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
) -> InboundEmailPageRead:
    """List a fixed page of mailbox metadata without raw email content."""
    query = (
        select(InboundEmail)
        .order_by(InboundEmail.received_at.desc(), InboundEmail.id.desc())
        .offset((page - 1) * MAILBOX_PAGE_SIZE)
        .limit(MAILBOX_PAGE_SIZE)
    )
    return InboundEmailPageRead(
        page=page,
        page_size=MAILBOX_PAGE_SIZE,
        emails=[_email_summary(email) for email in session.scalars(query).all()],
    )


@router.get("/mailbox/{email_id}", response_model=InboundEmailDetailRead)
def get_mailbox_email(email_id: int, session: SessionDep) -> InboundEmailDetailRead:
    """Read one sanitized inbound email for the restricted operator bot."""
    email = session.get(InboundEmail, email_id)
    if email is None:
        raise HTTPException(status_code=404, detail="Inbound email not found.")
    summary = _email_summary(email)
    body_text, attachment_count = _email_text_part(email)
    return InboundEmailDetailRead(
        **summary.model_dump(),
        body_text=body_text,
        attachment_count=attachment_count,
    )
