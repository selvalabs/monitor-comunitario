"""add notification kinds for alert resolution messages

Revision ID: 20260816_0007
Revises: 20260816_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260816_0007"
down_revision = "20260816_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column(
            "notification_kind",
            sa.String(length=40),
            nullable=False,
            server_default="alert",
        ),
    )
    op.alter_column("notifications", "notification_kind", server_default=None)
    op.drop_constraint(
        "uq_notification_user_notice_channel",
        "notifications",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_notification_user_notice_channel_kind",
        "notifications",
        ["user_id", "outage_notice_id", "channel", "notification_kind"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_notification_user_notice_channel_kind",
        "notifications",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_notification_user_notice_channel",
        "notifications",
        ["user_id", "outage_notice_id", "channel"],
    )
    op.drop_column("notifications", "notification_kind")
