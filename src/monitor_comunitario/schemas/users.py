from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    email: str = Field(default="", max_length=320)
    name: str = Field(min_length=2, max_length=160)
    phone: str = Field(min_length=8, max_length=40)
    municipality: str = Field(min_length=2, max_length=120)
    neighborhood: str = Field(default="", max_length=160)
    street: str = Field(default="", max_length=200)
    number: str = Field(default="", max_length=40)
    zipcode: str = Field(default="", max_length=20)
    accept_municipality_wide_alerts: bool = True


class UserCreate(UserBase):
    pass


class RegistrationPendingRead(BaseModel):
    status: str = "pending_email_verification"
    message: str


class EmailVerificationRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    otp: str = Field(min_length=6, max_length=6)

class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    phone: str | None = Field(default=None, min_length=8, max_length=40)
    municipality: str | None = Field(default=None, min_length=2, max_length=120)
    neighborhood: str | None = Field(default=None, max_length=160)
    street: str | None = Field(default=None, max_length=200)
    number: str | None = Field(default=None, max_length=40)
    zipcode: str | None = Field(default=None, max_length=20)
    accept_municipality_wide_alerts: bool | None = None
    notifications_approved: bool | None = None
    is_active: bool | None = None


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    notifications_approved: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserCreatedRead(UserRead):
    access_code: str
