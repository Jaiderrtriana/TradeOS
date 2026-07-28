"""create trading schema: trades, checklist_snapshots, evaluation_snapshots,
evaluation_snapshot_breakdowns

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-27

TRADEOS_DATABASE_DESIGN.md §6.9-6.13. `trading.trade_mistakes` (§6.14) is
deliberately not created here — Sprint 4.1's own approved scope excludes
`TagMistake`, which owns that table (Sprint 4.3) — same precedent as
`catalog_entries` being its own migration (0005) separate from the rest
of `configuration` (0004), despite sharing a schema.

No `r_multiple`/`mfe_r`/`mae_r`/`captured_pct`/`potential_left_r` columns
— Database Design §6.9 is explicit these are computed at query/response
time, never stored (avoids the exact class of drift `PROJECT_AUDIT.md`
found repeatedly in the source Excel).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS trading")

    op.create_table(
        "trades",
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
            "strategy_id",
            UUID(as_uuid=True),
            sa.ForeignKey("configuration.catalog_entries.id"),
            nullable=True,
        ),
        sa.Column(
            "setup_id",
            UUID(as_uuid=True),
            sa.ForeignKey("configuration.catalog_entries.id"),
            nullable=True,
        ),
        sa.Column(
            "session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("configuration.catalog_entries.id"),
            nullable=True,
        ),
        sa.Column(
            "entry_trigger_id",
            UUID(as_uuid=True),
            sa.ForeignKey("configuration.catalog_entries.id"),
            nullable=True,
        ),
        sa.Column("market", sa.String(length=20), nullable=False),
        sa.Column("direction", sa.String(length=5), nullable=False),
        sa.Column("entry_price", sa.Numeric, nullable=False),
        sa.Column("stop_loss", sa.Numeric, nullable=False),
        sa.Column("exit_price", sa.Numeric, nullable=True),
        sa.Column("size", sa.Numeric, nullable=False, server_default=sa.text("0")),
        sa.Column("leverage", sa.String(length=10), nullable=False, server_default=""),
        sa.Column("result", sa.String(length=5), nullable=False, server_default="open"),
        sa.Column("realized_pnl", sa.Numeric, nullable=False, server_default=sa.text("0")),
        sa.Column("mfe_price", sa.Numeric, nullable=True),
        sa.Column("mae_price", sa.Numeric, nullable=True),
        sa.Column("notes", sa.Text, nullable=False, server_default=""),
        sa.Column("entered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column(
            "created_by_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("identity.user_accounts.id"),
            nullable=True,
        ),
        sa.CheckConstraint("direction IN ('long','short')", name="ck_trades_direction"),
        sa.CheckConstraint("result IN ('open','tp','sl','be')", name="ck_trades_result"),
        sa.CheckConstraint(
            "(direction = 'long' AND stop_loss < entry_price) OR "
            "(direction = 'short' AND stop_loss > entry_price)",
            name="ck_trades_inv_trade_01_stop_placement",
        ),
        sa.CheckConstraint(
            "(result = 'open' AND exit_price IS NULL AND closed_at IS NULL) OR "
            "(result != 'open' AND exit_price IS NOT NULL AND closed_at IS NOT NULL)",
            name="ck_trades_inv_trade_02_close_requires_result_and_exit_price",
        ),
        schema="trading",
    )
    op.create_index("ix_trades_user_id", "trades", ["user_id"], schema="trading")
    op.create_index("ix_trades_entered_at", "trades", ["entered_at"], schema="trading")
    op.create_index(
        "ix_trades_dimension",
        "trades",
        ["strategy_id", "setup_id", "session_id", "direction"],
        schema="trading",
    )
    op.create_index(
        "ix_trades_not_deleted",
        "trades",
        ["id"],
        schema="trading",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "checklist_snapshots",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "trade_id", UUID(as_uuid=True), sa.ForeignKey("trading.trades.id"), nullable=False
        ),
        sa.Column("answers", JSONB, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="trading",
    )
    op.create_index(
        "ix_checklist_snapshots_trade_id",
        "checklist_snapshots",
        ["trade_id"],
        unique=True,
        schema="trading",
    )

    op.create_table(
        "evaluation_snapshots",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "trade_id", UUID(as_uuid=True), sa.ForeignKey("trading.trades.id"), nullable=False
        ),
        sa.Column(
            "configuration_version_id",
            UUID(as_uuid=True),
            sa.ForeignKey("configuration.scoring_configuration_versions.id"),
            nullable=False,
        ),
        sa.Column("confidence_score", sa.Numeric, nullable=True),
        sa.Column("confidence_grade", sa.String(length=2), nullable=True),
        sa.Column("quality_score", sa.Numeric, nullable=True),
        sa.Column("quality_grade", sa.String(length=2), nullable=True),
        sa.Column("execution_score", sa.Numeric, nullable=True),
        sa.Column("execution_grade", sa.String(length=2), nullable=True),
        sa.Column("market_context_score", sa.Numeric, nullable=True),
        sa.Column("market_context_grade", sa.String(length=2), nullable=True),
        sa.Column("bias_score", sa.Numeric, nullable=True),
        sa.Column("is_current", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="trading",
    )
    # "Exactly one *current* snapshot per Trade" (Database Design §6.12) —
    # same partial-unique-index idiom as
    # ix_scoring_configuration_versions_one_published (migration 0006),
    # applied here from day one rather than retrofitted after a bug.
    op.create_index(
        "ix_evaluation_snapshots_one_current_per_trade",
        "evaluation_snapshots",
        ["trade_id"],
        unique=True,
        schema="trading",
        postgresql_where=sa.text("is_current = true"),
    )

    op.create_table(
        "evaluation_snapshot_breakdowns",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "evaluation_snapshot_id",
            UUID(as_uuid=True),
            sa.ForeignKey("trading.evaluation_snapshots.id"),
            nullable=False,
        ),
        sa.Column(
            "criterion_id",
            sa.String(length=64),
            sa.ForeignKey("configuration.scoring_criteria.id"),
            nullable=False,
        ),
        sa.Column(
            "engine_type_code",
            sa.String(length=30),
            sa.ForeignKey("configuration.engine_types.code"),
            nullable=False,
        ),
        sa.Column("criterion_name_at_time", sa.String(length=120), nullable=False),
        sa.Column("raw_value", sa.Text, nullable=False),
        sa.Column("normalized_value", sa.Numeric, nullable=False),
        sa.Column("weight", sa.Numeric, nullable=False),
        sa.Column("contribution", sa.Numeric, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="trading",
    )
    op.create_index(
        "ix_evaluation_snapshot_breakdowns_snapshot_id",
        "evaluation_snapshot_breakdowns",
        ["evaluation_snapshot_id"],
        schema="trading",
    )


def downgrade() -> None:
    op.drop_table("evaluation_snapshot_breakdowns", schema="trading")
    op.drop_index(
        "ix_evaluation_snapshots_one_current_per_trade",
        table_name="evaluation_snapshots",
        schema="trading",
    )
    op.drop_table("evaluation_snapshots", schema="trading")
    op.drop_index(
        "ix_checklist_snapshots_trade_id", table_name="checklist_snapshots", schema="trading"
    )
    op.drop_table("checklist_snapshots", schema="trading")
    op.drop_index("ix_trades_not_deleted", table_name="trades", schema="trading")
    op.drop_index("ix_trades_dimension", table_name="trades", schema="trading")
    op.drop_index("ix_trades_entered_at", table_name="trades", schema="trading")
    op.drop_index("ix_trades_user_id", table_name="trades", schema="trading")
    op.drop_table("trades", schema="trading")
