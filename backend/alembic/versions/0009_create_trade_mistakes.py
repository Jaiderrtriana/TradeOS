"""create trading.trade_mistakes

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-28

TRADEOS_DATABASE_DESIGN.md §6.14 — many-to-many junction between
`trading.trades` and `configuration.catalog_entries` (kind=mistake_tag).
Deferred from migration 0007 (Sprint 4.1) to this migration, matching
that migration's own precedent set by `catalog_entries` (0005) being its
own migration separate from the rest of `configuration` (0004): each
migration ships exactly what its own sprint's approved scope needs.

Primary key is the composite `(trade_id, catalog_entry_id)` itself — no
surrogate `id` column, per §6.14's own "Primary Key: composite
(trade_id, catalog_entry_id)." The composite PK is also the concurrency
-safety mechanism `TagMistakeUseCase` relies on (a duplicate INSERT is
rejected by this constraint, never a "SELECT then INSERT" check, same
discipline as `ADR_CONFIGURATION_PUBLISH_RACE_CONDITION.md`).

`kind = 'mistake_tag'` is deliberately not a database-level check
constraint — §6.14 is explicit this requires a cross-table lookup
("application-level ... rule"), enforced in `TagMistakeUseCase` instead.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trade_mistakes",
        sa.Column(
            "trade_id", UUID(as_uuid=True), sa.ForeignKey("trading.trades.id"), nullable=False
        ),
        sa.Column(
            "catalog_entry_id",
            UUID(as_uuid=True),
            sa.ForeignKey("configuration.catalog_entries.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("trade_id", "catalog_entry_id"),
        schema="trading",
    )


def downgrade() -> None:
    op.drop_table("trade_mistakes", schema="trading")
