from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    outage_notice_id: int
    channel: str
    notification_kind: str
    status: str
    title: str
    message: str
    sent_at: datetime | None
    read_at: datetime | None
    error_message: str
    created_at: datetime
