from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from monitor_comunitario.db.models import HermesEventStatus


class HermesEventStatusUpdate(BaseModel):
    status: HermesEventStatus


class HermesEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    status: str
    source: str
    channel: str
    recipient_phone: str
    intent: str
    template_key: str
    payload_json: str
    llm_allowed: bool
    error_message: str
    created_at: datetime
    processed_at: datetime | None


class HermesEventBotRead(BaseModel):
    """Redacted registration event envelope for the Telegram bot."""

    id: int
    event_type: str
    status: str
    channel: str
    created_at: datetime
    processed_at: datetime | None


class HermesEventDeliveryRead(BaseModel):
    """Minimal event envelope exposed to the Hermes delivery worker."""

    id: int
    status: str
    event_type: str
    channel: str
    recipient_phone: str
    intent: str
    template_key: str
    payload: dict[str, object]
    created_at: datetime


class HermesEventDeliveryUpdate(BaseModel):
    """Terminal delivery result reported by Hermes."""

    status: Literal["processed", "failed"]
    error_message: str = ""


class HermesDeliverySecretRead(BaseModel):
    """One-time secret fetched by Hermes for a completion event."""

    access_code: str
