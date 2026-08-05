"""trade status/result split (v2.0 Trade Entry redesign)

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-30

TRADEOS_DOMAIN_MODEL.md v2.0 (KDD-07), TRADEOS_DATABASE_DESIGN.md v1.2
§6.9. Introduces `status` (planned|open|closed) as a concept independent
of `result` (tp|sl|be, NULL until closed -- `'open'` retired as a result
value). Adds `take_profit`/`margin_used`. Relaxes `entry_price`/
`stop_loss`/`entered_at` to nullable (absent while `status='planned'`).
Deliberately does NOT add `roi_percent`/`pnl_percent` columns -- both
remain computed-only (Domain Model DI-14).

Backfill: every existing row today is either `result='open'` (still
actively trading) or already closed (`tp`/`sl`/`be`) -- `status` is
derived directly from that, then the retired `'open'` result value is
cleared to NULL.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "trades",
        sa.Column("status", sa.String(length=10), nullable=False, server_default="open"),
        schema="trading",
    )
    op.add_column("trades", sa.Column("take_profit", sa.Numeric, nullable=True), schema="trading")
    op.add_column("trades", sa.Column("margin_used", sa.Numeric, nullable=True), schema="trading")

    # `result` must be relaxed to nullable *before* the backfill below can
    # set it to NULL for any row -- doing this after would violate the
    # still-active NOT NULL constraint for every currently-open trade.
    op.alter_column("trades", "entry_price", nullable=True, schema="trading")
    op.alter_column("trades", "stop_loss", nullable=True, schema="trading")
    op.alter_column("trades", "entered_at", nullable=True, schema="trading")
    op.alter_column("trades", "result", nullable=True, server_default=None, schema="trading")

    # Backfill: derive status from the (soon-to-be-retired) 'open' result
    # value, then clear it -- every row existing today is either still
    # open or already closed, never planned (the concept didn't exist).
    op.execute("UPDATE trading.trades SET status = 'closed' WHERE result != 'open'")
    op.execute("UPDATE trading.trades SET result = NULL WHERE result = 'open'")

    op.drop_constraint("ck_trades_result", "trades", schema="trading", type_="check")
    op.drop_constraint(
        "ck_trades_inv_trade_01_stop_placement", "trades", schema="trading", type_="check"
    )
    op.drop_constraint(
        "ck_trades_inv_trade_02_close_requires_result_and_exit_price",
        "trades",
        schema="trading",
        type_="check",
    )

    op.create_check_constraint(
        "ck_trades_status", "trades", "status IN ('planned','open','closed')", schema="trading"
    )
    op.create_check_constraint(
        "ck_trades_result",
        "trades",
        "result IS NULL OR result IN ('tp','sl','be')",
        schema="trading",
    )
    op.create_check_constraint(
        "ck_trades_inv_trade_01_stop_placement",
        "trades",
        "entry_price IS NULL OR stop_loss IS NULL OR "
        "(direction = 'long' AND stop_loss < entry_price) OR "
        "(direction = 'short' AND stop_loss > entry_price)",
        schema="trading",
    )
    op.create_check_constraint(
        "ck_trades_inv_trade_02_status_fields",
        "trades",
        "(status = 'planned' AND entry_price IS NULL AND entered_at IS NULL "
        "AND exit_price IS NULL AND closed_at IS NULL AND result IS NULL) OR "
        "(status = 'open' AND entry_price IS NOT NULL AND entered_at IS NOT NULL "
        "AND exit_price IS NULL AND closed_at IS NULL AND result IS NULL) OR "
        "(status = 'closed' AND entry_price IS NOT NULL AND entered_at IS NOT NULL "
        "AND exit_price IS NOT NULL AND closed_at IS NOT NULL AND result IS NOT NULL)",
        schema="trading",
    )

    # entered_at's index becomes partial -- v2.0 allows it to be absent
    # for `planned` rows, which Analytics never reads anyway (DI-13).
    op.drop_index("ix_trades_entered_at", table_name="trades", schema="trading")
    op.create_index(
        "ix_trades_entered_at",
        "trades",
        ["entered_at"],
        schema="trading",
        postgresql_where=sa.text("entered_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_trades_entered_at", table_name="trades", schema="trading")
    op.create_index("ix_trades_entered_at", "trades", ["entered_at"], schema="trading")

    op.drop_constraint(
        "ck_trades_inv_trade_02_status_fields", "trades", schema="trading", type_="check"
    )
    op.drop_constraint(
        "ck_trades_inv_trade_01_stop_placement", "trades", schema="trading", type_="check"
    )
    op.drop_constraint("ck_trades_result", "trades", schema="trading", type_="check")
    op.drop_constraint("ck_trades_status", "trades", schema="trading", type_="check")

    op.execute("UPDATE trading.trades SET result = 'open' WHERE status != 'closed'")
    op.execute(
        "UPDATE trading.trades SET entry_price = 0, stop_loss = 0, entered_at = now() "
        "WHERE status = 'planned'"
    )

    op.alter_column("trades", "result", nullable=False, server_default="open", schema="trading")
    op.alter_column("trades", "entered_at", nullable=False, schema="trading")
    op.alter_column("trades", "stop_loss", nullable=False, schema="trading")
    op.alter_column("trades", "entry_price", nullable=False, schema="trading")

    op.create_check_constraint(
        "ck_trades_inv_trade_02_close_requires_result_and_exit_price",
        "trades",
        "(result = 'open' AND exit_price IS NULL AND closed_at IS NULL) OR "
        "(result != 'open' AND exit_price IS NOT NULL AND closed_at IS NOT NULL)",
        schema="trading",
    )
    op.create_check_constraint(
        "ck_trades_inv_trade_01_stop_placement",
        "trades",
        "(direction = 'long' AND stop_loss < entry_price) OR "
        "(direction = 'short' AND stop_loss > entry_price)",
        schema="trading",
    )
    op.create_check_constraint(
        "ck_trades_result", "trades", "result IN ('open','tp','sl','be')", schema="trading"
    )

    op.drop_column("trades", "margin_used", schema="trading")
    op.drop_column("trades", "take_profit", schema="trading")
    op.drop_column("trades", "status", schema="trading")
