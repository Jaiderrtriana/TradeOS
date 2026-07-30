"""create playbook schema: playbook_setups, playbook_setup_attachments

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-30

TRADEOS_DATABASE_DESIGN.md §6.15-6.16. `catalog_entry_id` is UNIQUE (the
1:1 linkage to a `kind=setup` Catalog entry, §5.1's own "One-to-One"
list). No performance metric column anywhere here -- always a live
Statistics read (Domain Model §8.8). No `Indexes:` line exists in either
§6.15 or §6.16 (unlike `journal_entries`, which has one) -- no index
beyond what PK/UNIQUE/FK already provide is added here.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS playbook")

    op.create_table(
        "playbook_setups",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "catalog_entry_id",
            UUID(as_uuid=True),
            sa.ForeignKey("configuration.catalog_entries.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("entry_criteria", sa.Text, nullable=False, server_default=""),
        sa.Column("exit_criteria", sa.Text, nullable=False, server_default=""),
        sa.Column("ideal_conditions", sa.Text, nullable=False, server_default=""),
        sa.Column("risk_rules", sa.Text, nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
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
        sa.CheckConstraint("status IN ('active','deprecated')", name="ck_playbook_setups_status"),
        schema="playbook",
    )

    op.create_table(
        "playbook_setup_attachments",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "playbook_setup_id",
            UUID(as_uuid=True),
            sa.ForeignKey("playbook.playbook_setups.id"),
            nullable=False,
        ),
        sa.Column("file_reference", sa.String(500), nullable=False),
        sa.Column("caption", sa.String(255), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="playbook",
    )


def downgrade() -> None:
    op.drop_table("playbook_setup_attachments", schema="playbook")
    op.drop_table("playbook_setups", schema="playbook")
    op.execute("DROP SCHEMA IF EXISTS playbook")
