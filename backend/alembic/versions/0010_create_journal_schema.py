"""create journal schema: journal_entries

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-29

TRADEOS_DATABASE_DESIGN.md §6.17. `trade_id` is nullable and references
`trading.trades` (Phase 4, already built); the exactly-one-reference
check constraint below is the direct schema realization of
TRADEOS_DOMAIN_MODEL.md §8.10's "either a Trade reference or a
date-range reference, never both." No column for a length limit on
`content`, a title, or tags -- none is named anywhere in the Domain
Model, this table's own spec, or the API Specification.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS journal")

    op.create_table(
        "journal_entries",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("identity.user_accounts.id"),
            nullable=False,
        ),
        sa.Column(
            "trade_id",
            UUID(as_uuid=True),
            sa.ForeignKey("trading.trades.id"),
            nullable=True,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("period_start", sa.Date, nullable=True),
        sa.Column("period_end", sa.Date, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(trade_id IS NOT NULL AND period_start IS NULL AND period_end IS NULL) OR "
            "(trade_id IS NULL AND period_start IS NOT NULL AND period_end IS NOT NULL)",
            name="ck_journal_entries_exactly_one_reference",
        ),
        schema="journal",
    )
    # Database Design §6.17's own "Indexes:" line names exactly these two
    # -- deliberately shorter than Trades' own richer index set (which
    # explicitly adds `user_id` and a `deleted_at IS NULL` partial index
    # for its analytics-heavy access patterns, §6.9's own "Indexes:"
    # line). Journal is a low-volume table with no equivalent access
    # pattern named anywhere, so no index beyond what's specified is
    # added here.
    op.create_index(
        "ix_journal_entries_trade_id", "journal_entries", ["trade_id"], schema="journal"
    )
    op.create_index(
        "ix_journal_entries_period",
        "journal_entries",
        ["period_start", "period_end"],
        schema="journal",
    )


def downgrade() -> None:
    op.drop_index("ix_journal_entries_period", table_name="journal_entries", schema="journal")
    op.drop_index("ix_journal_entries_trade_id", table_name="journal_entries", schema="journal")
    op.drop_table("journal_entries", schema="journal")
