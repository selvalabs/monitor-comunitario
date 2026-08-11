"""redact durable access codes from Hermes events

Revision ID: 20260811_0006
Revises: 20260807_0005
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260811_0006"
down_revision = "20260807_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove reusable resident codes from historical delivery payloads."""
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, payload_json FROM hermes_events "
            "WHERE event_type = 'member_phone_confirmation_completed'"
        )
    ).mappings()
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict) or "access_code" not in payload:
            continue
        payload.pop("access_code", None)
        connection.execute(
            sa.text("UPDATE hermes_events SET payload_json = :payload WHERE id = :id"),
            {
                "id": row["id"],
                "payload": json.dumps(payload, separators=(",", ":"), sort_keys=True),
            },
        )


def downgrade() -> None:
    """Irreversible: plaintext access codes must not be restored."""
