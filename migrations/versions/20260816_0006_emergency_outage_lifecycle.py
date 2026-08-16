"""add emergency outage lifecycle fields

Revision ID: 20260816_0006
Revises: 20260807_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260816_0006"
down_revision = "20260807_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "outage_notices",
        sa.Column("notice_type", sa.String(length=40), nullable=False, server_default="scheduled"),
    )
    op.add_column("outage_notices", sa.Column("source_key", sa.String(length=200), nullable=True))
    op.add_column(
        "outage_notices",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "outage_notices",
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.add_column(
        "outage_notices",
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE outage_notices SET last_seen_at = created_at WHERE last_seen_at IS NULL"
    )
    op.alter_column("outage_notices", "last_seen_at", server_default=None)
    op.create_index("ix_outage_notices_notice_type", "outage_notices", ["notice_type"])
    op.create_index("ix_outage_notices_is_active", "outage_notices", ["is_active"])
    op.create_unique_constraint(
        "uq_outage_notices_source_key",
        "outage_notices",
        ["source_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_outage_notices_source_key", "outage_notices", type_="unique")
    op.drop_index("ix_outage_notices_is_active", table_name="outage_notices")
    op.drop_index("ix_outage_notices_notice_type", table_name="outage_notices")
    op.drop_column("outage_notices", "resolved_at")
    op.drop_column("outage_notices", "last_seen_at")
    op.drop_column("outage_notices", "is_active")
    op.drop_column("outage_notices", "source_key")
    op.drop_column("outage_notices", "notice_type")
