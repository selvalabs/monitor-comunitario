from datetime import datetime

from pydantic import BaseModel


class InboundEmailSummaryRead(BaseModel):
    """Safe mailbox metadata available to the restricted operator bot."""

    id: int
    sender: str
    recipient: str
    subject: str
    received_at: datetime


class InboundEmailPageRead(BaseModel):
    """One fixed-size mailbox page for the operator bot."""

    page: int
    page_size: int
    emails: list[InboundEmailSummaryRead]


class InboundEmailDetailRead(InboundEmailSummaryRead):
    """Sanitized text-only content of one inbound email."""

    body_text: str
    attachment_count: int
