"""create identity schema, user_accounts, and refresh_tokens tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-25

identity.refresh_tokens is a Sprint 1.1 addition beyond what
TRADEOS_DATABASE_DESIGN.md originally specified for the `identity` schema
(that document defines only user_accounts). TRADEOS_API_SPECIFICATION.md
§4.3 requires refresh tokens to be single-use (rotation) and server-side
revocable (to support POST /auth/logout) — properties that are impossible
to implement without persisting token state somewhere. This table is that
necessary, approved extension (see CHANGELOG.md, Sprint 1.1), not a new
business concept beyond what §4.3 already specifies.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS identity")

    op.create_table(
        "user_accounts",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
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
        schema="identity",
    )
    op.create_index(
        "ix_user_accounts_email",
        "user_accounts",
        ["email"],
        unique=True,
        schema="identity",
    )

    op.create_table(
        "refresh_tokens",
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
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        schema="identity",
    )
    op.create_index(
        "ix_refresh_tokens_user_id",
        "refresh_tokens",
        ["user_id"],
        schema="identity",
    )
    op.create_index(
        "ix_refresh_tokens_token_hash",
        "refresh_tokens",
        ["token_hash"],
        unique=True,
        schema="identity",
    )


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens", schema="identity")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens", schema="identity")
    op.drop_table("refresh_tokens", schema="identity")
    op.drop_index("ix_user_accounts_email", table_name="user_accounts", schema="identity")
    op.drop_table("user_accounts", schema="identity")
    op.execute("DROP SCHEMA IF EXISTS identity")
