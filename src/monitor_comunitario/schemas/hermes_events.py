from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
