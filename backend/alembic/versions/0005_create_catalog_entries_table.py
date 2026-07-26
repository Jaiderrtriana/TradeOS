"""create catalog_entries table and seed the five real catalog kinds

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-26

TRADEOS_DATABASE_DESIGN.md §6.8. Seeds all 37 real entries (8 Setups, 6
Sessions, 4 Strategies, 3 Entry Triggers, 16 Mistake Tags) directly in this
migration — unlike Sprint 2.1's `scoring_configuration_versions`,
`catalog_entries` carries no `created_by_user_id` column and the Master
Plan's Sprint 2.2 text names no Phase-1 user dependency, so no separate
script is needed (see CHANGELOG.md, Sprint 2.2).

Source: `legacy/Trading Journal v2.0 Stable.xlsx`, `⚙️ CONFIG` sheet's
SETUP_LIST/SESSION_LIST/STRATEGY_LIST/ENTRY_TRIGGER_LIST/MISTAKE_TAGS —
the same extraction already reviewed and approved during Sprint 2.1's
planning. Strategy names have the Excel's own visual numbering prefix
("1. Daily Open") stripped — approved as a data-cleanup decision, not part
of the business name.

Idempotent: the seed uses `INSERT ... ON CONFLICT (kind, name) DO NOTHING`
rather than a plain bulk insert, so re-running `upgrade()` against a
database that already has these rows changes nothing and raises no
integrity error.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, insert

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CATALOG_ENTRIES_TABLE = sa.table(
    "catalog_entries",
    sa.column("kind", sa.String),
    sa.column("name", sa.String),
    schema="configuration",
)

SETUPS = [
    "Pullback Continuation",
    "Range Reclaim",
    "Support/Resistance Flip",
    "Breakout Retest",
    "Failed Breakdown / Failed Breakout",
    "Sweep + Reclaim (Liquidity Sweep)",
    "Compression Breakout",
    "High Time Frame Reclaim",
]

SESSIONS = ["Weekend", "SYD", "TOK", "EU", "NY", "Overnight"]

# Excel's own visual numbering prefix ("1. Daily Open") stripped — not part
# of the business name (approved, Sprint 2.2).
STRATEGIES = ["Daily Open", "Nivel importante", "Trend Day / Expansion Day", "Rango"]

ENTRY_TRIGGERS = [
    "Price Action Triggers",
    "Market Structure Triggers",
    "Candle Close Confirmation Triggers",
]

MISTAKE_TAGS = [
    "FOMO",
    "Revenge Trade",
    "Overtrading",
    "Ignored HTF",
    "Ignored Bias",
    "Ignored Liquidity",
    "Ignored Volume",
    "Ignored Session",
    "Entered Too Early",
    "Entered Too Late",
    "Moved Stop Loss",
    "Closed Early",
    "News Trade",
    "Low Sleep",
    "Emotional Decision",
    "Other",
]


def upgrade() -> None:
    op.create_table(
        "catalog_entries",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
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
        sa.CheckConstraint(
            "kind IN ('setup','session','strategy','entry_trigger','mistake_tag')",
            name="ck_catalog_entries_kind",
        ),
        schema="configuration",
    )
    op.create_index(
        "ix_catalog_entries_kind_name",
        "catalog_entries",
        ["kind", "name"],
        unique=True,
        schema="configuration",
    )
    op.create_index(
        "ix_catalog_entries_kind",
        "catalog_entries",
        ["kind"],
        schema="configuration",
    )

    rows = (
        [{"kind": "setup", "name": name} for name in SETUPS]
        + [{"kind": "session", "name": name} for name in SESSIONS]
        + [{"kind": "strategy", "name": name} for name in STRATEGIES]
        + [{"kind": "entry_trigger", "name": name} for name in ENTRY_TRIGGERS]
        + [{"kind": "mistake_tag", "name": name} for name in MISTAKE_TAGS]
    )
    op.execute(
        insert(CATALOG_ENTRIES_TABLE)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["kind", "name"])
    )


def downgrade() -> None:
    op.drop_index("ix_catalog_entries_kind", table_name="catalog_entries", schema="configuration")
    op.drop_index(
        "ix_catalog_entries_kind_name", table_name="catalog_entries", schema="configuration"
    )
    op.drop_table("catalog_entries", schema="configuration")
