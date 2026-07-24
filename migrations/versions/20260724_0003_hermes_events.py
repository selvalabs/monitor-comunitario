"""add hermes events audit table

Revision ID: 20260724_0003
Revises: 20260618_0002
Create Date: 2026-07-24 12:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260724_0003"
down_revision: str | None = "20260618_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "hermes_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("channel", sa.String(length=40), nullable=False),
        sa.Column("recipient_phone", sa.String(length=40), nullable=False),
        sa.Column("intent", sa.String(length=80), nullable=False),
        sa.Column("template_key", sa.String(length=120), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("llm_allowed", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hermes_events_created_at", "hermes_events", ["created_at"])
    op.create_index("ix_hermes_events_event_type", "hermes_events", ["event_type"])
    op.create_index("ix_hermes_events_status", "hermes_events", ["status"])


def downgrade() -> None:
    op.drop_index("ix_hermes_events_status", table_name="hermes_events")
    op.drop_index("ix_hermes_events_event_type", table_name="hermes_events")
    op.drop_index("ix_hermes_events_created_at", table_name="hermes_events")
    op.drop_table("hermes_events")
