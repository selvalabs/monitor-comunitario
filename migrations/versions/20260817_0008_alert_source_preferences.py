"""add per-source alert preferences for residents

Revision ID: 20260817_0008
Revises: 20260816_0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260817_0008"
down_revision = "20260816_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_alert_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source_key", sa.String(length=80), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint(
            "user_id",
            "source_key",
            name="uq_user_alert_preference_user_source",
        ),
    )
    op.create_index(
        "ix_user_alert_preferences_user_id",
        "user_alert_preferences",
        ["user_id"],
    )
    op.create_index(
        "ix_user_alert_preferences_source_key",
        "user_alert_preferences",
        ["source_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_alert_preferences_source_key", table_name="user_alert_preferences")
    op.drop_index("ix_user_alert_preferences_user_id", table_name="user_alert_preferences")
    op.drop_table("user_alert_preferences")
