"""create preferences schema and user_preferences table

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-26

TRADEOS_DATABASE_DESIGN.md §6.2 already fully specifies this table
(columns, defaults, FK, unique constraint) — no extension beyond the
frozen schema, unlike Sprint 1.1's refresh_tokens addition.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS preferences")

    op.create_table(
        "user_preferences",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("identity.user_accounts.id"),
            nullable=False,
        ),
        sa.Column("theme", sa.String(length=20), nullable=False, server_default="dark"),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="es"),
        sa.Column(
            "notification_settings",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
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
        schema="preferences",
    )
    op.create_index(
        "ix_user_preferences_user_id",
        "user_preferences",
        ["user_id"],
        unique=True,
        schema="preferences",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_preferences_user_id", table_name="user_preferences", schema="preferences"
    )
    op.drop_table("user_preferences", schema="preferences")
    op.execute("DROP SCHEMA IF EXISTS preferences")
