from pydantic import BaseModel, Field

from monitor_comunitario.schemas.notifications import NotificationRead
from monitor_comunitario.schemas.users import UserRead


class MemberAccessRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=40)
    access_code: str = Field(min_length=4, max_length=40)


class MemberDeleteRequest(MemberAccessRequest):
    """Credentials required before permanently deleting member data."""

class MemberAccessRead(BaseModel):
    user: UserRead
    notifications: list[NotificationRead]
