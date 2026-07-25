"""create platform schema and event_log table

Revision ID: 0001
Revises:
Create Date: 2026-07-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS platform")

    op.create_table(
        "event_log",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("aggregate_type", sa.String(length=60), nullable=False),
        sa.Column("aggregate_id", UUID(as_uuid=True), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="platform",
    )
    op.create_index(
        "ix_event_log_aggregate_type_aggregate_id",
        "event_log",
        ["aggregate_type", "aggregate_id"],
        schema="platform",
    )
    op.create_index("ix_event_log_event_type", "event_log", ["event_type"], schema="platform")
    op.create_index("ix_event_log_occurred_at", "event_log", ["occurred_at"], schema="platform")


def downgrade() -> None:
    op.drop_index("ix_event_log_occurred_at", table_name="event_log", schema="platform")
    op.drop_index("ix_event_log_event_type", table_name="event_log", schema="platform")
    op.drop_index(
        "ix_event_log_aggregate_type_aggregate_id", table_name="event_log", schema="platform"
    )
    op.drop_table("event_log", schema="platform")
    op.execute("DROP SCHEMA IF EXISTS platform")
