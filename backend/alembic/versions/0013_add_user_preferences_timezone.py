"""add user_preferences.timezone (Sprint 4, OQ-7)

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-10

Additive, nullable column — no backfill (Sprint 4 Fase 2, approved
contract). `NULL` means "not explicitly set"; the frontend resolves the
display/input timezone as: this field -> browser-detected timezone ->
UTC, so every existing row keeps its current (implicit browser-local)
behavior unchanged until a user explicitly sets a preference.

IANA identifier only (e.g. "America/Bogota"), validated at the API layer
(Pydantic), never a fixed offset — offsets don't represent DST correctly.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column("timezone", sa.String(length=50), nullable=True),
        schema="preferences",
    )


def downgrade() -> None:
    op.drop_column("user_preferences", "timezone", schema="preferences")
