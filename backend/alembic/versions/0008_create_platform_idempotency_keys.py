"""create platform.idempotency_keys

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-27

TRADEOS_API_SPECIFICATION.md §3.6 specifies the *behavior* ("a request
with a previously-seen key returns the original response without
creating a duplicate resource") but no frozen document specifies the
storage mechanism — approved design (see CHANGELOG.md, Sprint 4.1):
a generic table in `platform` (not a `trading.trades` column), reusable
by any future `POST`-create endpoint, not just `POST /trades`.

Stores the *complete response* (`response_status` + `response_body`), not
just the created resource's ID — a repeat request never re-executes the
triggering Use Case, it just replays exactly what was returned the first
time.

`UNIQUE (user_id, idempotency_key)` is the concurrency-safety mechanism a
race between two identical concurrent requests must rely on (approved
requirement, explicitly not a "check then insert" pattern per the lesson
from `ADR_CONFIGURATION_PUBLISH_RACE_CONDITION.md`) — the *first* `INSERT`
to actually commit wins; a concurrent second `INSERT` attempt fails this
constraint immediately and the application layer (`app/platform/
idempotency.py`) interprets that failure as "someone else is already
handling this key," never as a hard error.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "idempotency_keys",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("identity.user_accounts.id"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("endpoint", sa.String(length=100), nullable=False),
        # Nullable: a row is inserted as a *claim* (both null) before the
        # wrapped Use Case runs, then updated with the real response once
        # it completes — see app/platform/idempotency.py. A row with
        # response_status IS NULL means "another request is still
        # processing this key right now."
        sa.Column("response_status", sa.Integer, nullable=True),
        sa.Column("response_body", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="platform",
    )
    op.create_index(
        "ix_idempotency_keys_user_key",
        "idempotency_keys",
        ["user_id", "idempotency_key"],
        unique=True,
        schema="platform",
    )


def downgrade() -> None:
    op.drop_index("ix_idempotency_keys_user_key", table_name="idempotency_keys", schema="platform")
    op.drop_table("idempotency_keys", schema="platform")
