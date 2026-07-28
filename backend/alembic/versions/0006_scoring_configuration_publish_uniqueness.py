"""enforce at most one published scoring_configuration_version

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-27

Structural fix for the concurrent-publish race condition documented in
`ADR_CONFIGURATION_PUBLISH_RACE_CONDITION.md` (reviewed and approved
before this migration was written): two concurrent
`POST /configuration/versions/{id}/publish` calls could each read "no
row is currently published yet" (or the same, soon-to-be-superseded, row)
and both commit their own row as `status='published'` — Postgres's
row-level locking never serializes them, since they write to *different*
rows. `TRADEOS_DATABASE_DESIGN.md` §6.6 only lists `version_label` as a
Unique Constraint on this table; this migration adds the missing
invariant at the database level, the same partial-unique-index pattern
already specified for `evaluation_snapshots.trade_id WHERE
is_current = true` (§6.12).

Pre-migration data repair (idempotent, safe against an already-consistent
database): before creating the index, collapse any existing multiple
`published` rows down to the most-recently-`published_at` one, superseding
the rest. Without this, `upgrade()` would fail outright against a database
already corrupted by the race this migration closes (exactly the state
this project's own dev database was manually repaired out of, this
session).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCHEMA = "configuration"
_TABLE = "scoring_configuration_versions"
_INDEX_NAME = "ix_scoring_configuration_versions_one_published"


def upgrade() -> None:
    # Idempotent repair: if more than one row is currently `published`
    # (only possible today because of the race this migration closes),
    # keep the most-recently-published one and supersede the rest. A
    # no-op against an already-consistent database (at most one row
    # matches `status = 'published'` there already).
    op.execute(
        sa.text(
            f"""
            UPDATE {_SCHEMA}.{_TABLE}
            SET status = 'superseded'
            WHERE status = 'published'
              AND id NOT IN (
                  SELECT id FROM {_SCHEMA}.{_TABLE}
                  WHERE status = 'published'
                  ORDER BY published_at DESC NULLS LAST, created_at DESC
                  LIMIT 1
              )
            """
        )
    )

    # A unique index on a constant expression, filtered to published rows,
    # is the standard PostgreSQL idiom for "at most one row may satisfy
    # this condition" — there is no per-row value to be unique *of*, so
    # the index is built over the literal `true`.
    op.execute(
        sa.text(
            f"""
            CREATE UNIQUE INDEX {_INDEX_NAME}
            ON {_SCHEMA}.{_TABLE} ((true))
            WHERE status = 'published'
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text(f"DROP INDEX {_SCHEMA}.{_INDEX_NAME}"))
