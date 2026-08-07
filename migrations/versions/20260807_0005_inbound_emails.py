"""add inbound email storage

Revision ID: 20260807_0005
Revises: 20260724_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260807_0005"
down_revision = "20260724_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.create_table(
        "inbound_emails",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("recipient", sa.String(320), nullable=False),
        sa.Column("sender", sa.String(320), nullable=False, server_default=""),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_mime", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_inbound_emails_idempotency_key", "inbound_emails", ["idempotency_key"], unique=True
    )
    op.create_index("ix_inbound_emails_recipient", "inbound_emails", ["recipient"])

def downgrade() -> None:
    op.drop_index("ix_inbound_emails_recipient", table_name="inbound_emails")
    op.drop_index("ix_inbound_emails_idempotency_key", table_name="inbound_emails")
    op.drop_table("inbound_emails")
