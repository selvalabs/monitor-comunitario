from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for persisted records."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class NotificationStatus(StrEnum):
    CREATED = "created"
    READ = "read"
    DISMISSED = "dismissed"
    FAILED = "failed"


class MonitoringRunStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str] = mapped_column(String(40), index=True)
    municipality: Mapped[str] = mapped_column(String(120))
    neighborhood: Mapped[str] = mapped_column(String(160), default="")
    street: Mapped[str] = mapped_column(String(200), default="")
    number: Mapped[str] = mapped_column(String(40), default="")
    zipcode: Mapped[str] = mapped_column(String(20), default="")
    accept_municipality_wide_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    notifications_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    access_code_hash: Mapped[str] = mapped_column(String(128), default="")
    access_code_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class OutageNotice(Base):
    __tablename__ = "outage_notices"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(80), default="celesc")
    source_url: Mapped[str] = mapped_column(String(500))
    municipality: Mapped[str] = mapped_column(String(120), index=True)
    neighborhood: Mapped[str] = mapped_column(String(160), default="")
    street: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    raw_text: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class UserOutageMatch(Base):
    __tablename__ = "user_outage_matches"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "outage_notice_id",
            name="uq_user_outage_match_user_notice",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    outage_notice_id: Mapped[int] = mapped_column(ForeignKey("outage_notices.id"), index=True)
    match_level: Mapped[str] = mapped_column(String(40))
    match_score: Mapped[float] = mapped_column(Float, default=0.0)
    match_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "outage_notice_id",
            "channel",
            name="uq_notification_user_notice_channel",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    outage_notice_id: Mapped[int] = mapped_column(ForeignKey("outage_notices.id"), index=True)
    channel: Mapped[str] = mapped_column(String(40), default="app")
    status: Mapped[str] = mapped_column(String(40), default=NotificationStatus.CREATED.value)
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class MonitoringRun(Base):
    __tablename__ = "monitoring_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default=MonitoringRunStatus.RUNNING.value)
    municipalities_found: Mapped[int] = mapped_column(Integer, default=0)
    municipalities_captured: Mapped[int] = mapped_column(Integer, default=0)
    notices_found: Mapped[int] = mapped_column(Integer, default=0)
    notices_persisted: Mapped[int] = mapped_column(Integer, default=0)
    notices_created: Mapped[int] = mapped_column(Integer, default=0)
    users_checked: Mapped[int] = mapped_column(Integer, default=0)
    matches_created: Mapped[int] = mapped_column(Integer, default=0)
    notifications_created: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    raw_snapshot_path: Mapped[str] = mapped_column(String(500), default="")
