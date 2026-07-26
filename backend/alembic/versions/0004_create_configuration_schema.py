"""create configuration schema, engine_types, scoring_profiles,
scoring_criteria, scoring_configuration_versions, scoring_weights

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-26

TRADEOS_DATABASE_DESIGN.md §6.3-6.7. Catalogs (§6.8) is Sprint 2.2, not
created here, even though it shares this same `configuration` schema
(TRADEOS_BACKEND_BLUEPRINT.md §3.6) — TRADEOS_IMPLEMENTATION_MASTER_PLAN.md
sprints it separately.

Seeds `engine_types` (5 rows) and `scoring_profiles` (3 rows) as reference
data in this same migration (TRADEOS_DATABASE_DESIGN.md §7.0: "adding a
profile/engine type is a data change, not a migration" — but the initial
rows still need to exist before any application code can reference them,
and neither table has a `created_by_user_id`, so no application user needs
to exist first, unlike `scoring_configuration_versions` — see
scripts/seed_configuration.py for that seed). `bias` is seeded as a
catalog row only; see CHANGELOG.md, Sprint 2.1, for why it deliberately
gets no ScoringCriterion/ScoringWeight rows this sprint.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ENGINE_TYPES_TABLE = sa.table(
    "engine_types",
    sa.column("code", sa.String),
    sa.column("display_name", sa.String),
    sa.column("is_signed", sa.Boolean),
    sa.column("is_active", sa.Boolean),
    schema="configuration",
)

SCORING_PROFILES_TABLE = sa.table(
    "scoring_profiles",
    sa.column("code", sa.String),
    sa.column("display_name", sa.String),
    sa.column("is_active", sa.Boolean),
    schema="configuration",
)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS configuration")

    op.create_table(
        "engine_types",
        sa.Column("code", sa.String(length=30), primary_key=True),
        sa.Column("display_name", sa.String(length=60), nullable=False),
        sa.Column("is_signed", sa.Boolean, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="configuration",
    )
    # TRADEOS_DATABASE_DESIGN.md §6.3.1: at most one active row may be
    # signed (Domain Invariant DI-05) — expressed as a partial unique
    # index since Postgres has no simple column CHECK for "at most one row
    # matching a condition."
    op.create_index(
        "ix_engine_types_unique_active_signed",
        "engine_types",
        ["is_signed"],
        unique=True,
        schema="configuration",
        postgresql_where=sa.text("is_signed = true AND is_active = true"),
    )

    op.create_table(
        "scoring_profiles",
        sa.Column("code", sa.String(length=30), primary_key=True),
        sa.Column("display_name", sa.String(length=60), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="configuration",
    )

    op.create_table(
        "scoring_criteria",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column(
            "engine_type_code",
            sa.String(length=30),
            sa.ForeignKey("configuration.engine_types.code"),
            nullable=False,
        ),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("source_field", sa.String(length=64), nullable=False),
        sa.Column("min_value", sa.Numeric, nullable=False),
        sa.Column("max_value", sa.Numeric, nullable=False),
        sa.Column("category_map", JSONB, nullable=True),
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
        sa.CheckConstraint("max_value >= min_value", name="ck_scoring_criteria_max_ge_min"),
        schema="configuration",
    )
    op.create_index(
        "ix_scoring_criteria_engine_type_code",
        "scoring_criteria",
        ["engine_type_code"],
        schema="configuration",
    )

    op.create_table(
        "scoring_configuration_versions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("version_label", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("identity.user_accounts.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('draft','published','superseded')",
            name="ck_scoring_configuration_versions_status",
        ),
        schema="configuration",
    )
    op.create_index(
        "ix_scoring_configuration_versions_version_label",
        "scoring_configuration_versions",
        ["version_label"],
        unique=True,
        schema="configuration",
    )

    op.create_table(
        "scoring_weights",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "configuration_version_id",
            UUID(as_uuid=True),
            sa.ForeignKey("configuration.scoring_configuration_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "criterion_id",
            sa.String(length=64),
            sa.ForeignKey("configuration.scoring_criteria.id"),
            nullable=False,
        ),
        sa.Column(
            "profile_code",
            sa.String(length=30),
            sa.ForeignKey("configuration.scoring_profiles.code"),
            nullable=False,
        ),
        sa.Column("weight", sa.Numeric, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("weight >= 0", name="ck_scoring_weights_weight_nonnegative"),
        schema="configuration",
    )
    op.create_index(
        "ix_scoring_weights_version_criterion_profile",
        "scoring_weights",
        ["configuration_version_id", "criterion_id", "profile_code"],
        unique=True,
        schema="configuration",
    )
    op.create_index(
        "ix_scoring_weights_version_profile",
        "scoring_weights",
        ["configuration_version_id", "profile_code"],
        schema="configuration",
    )

    op.bulk_insert(
        ENGINE_TYPES_TABLE,
        [
            {
                "code": "confidence",
                "display_name": "Trade Confidence",
                "is_signed": False,
                "is_active": True,
            },
            {
                "code": "quality",
                "display_name": "Trade Quality",
                "is_signed": False,
                "is_active": True,
            },
            {
                "code": "execution",
                "display_name": "Execution Score",
                "is_signed": False,
                "is_active": True,
            },
            {
                "code": "market_context",
                "display_name": "Market Context Score",
                "is_signed": False,
                "is_active": True,
            },
            # Registered as a complete catalog row (Domain Invariant DI-05:
            # exactly one signed engine) but deliberately has no
            # ScoringCriterion/ScoringWeight rows — see CHANGELOG.md,
            # Sprint 2.1.
            {"code": "bias", "display_name": "Bias Index", "is_signed": True, "is_active": True},
        ],
    )
    op.bulk_insert(
        SCORING_PROFILES_TABLE,
        [
            {"code": "day_trading", "display_name": "Day Trading", "is_active": True},
            {"code": "swing_trading", "display_name": "Swing Trading", "is_active": True},
            {"code": "scalping", "display_name": "Scalping", "is_active": True},
        ],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_scoring_weights_version_profile", table_name="scoring_weights", schema="configuration"
    )
    op.drop_index(
        "ix_scoring_weights_version_criterion_profile",
        table_name="scoring_weights",
        schema="configuration",
    )
    op.drop_table("scoring_weights", schema="configuration")
    op.drop_index(
        "ix_scoring_configuration_versions_version_label",
        table_name="scoring_configuration_versions",
        schema="configuration",
    )
    op.drop_table("scoring_configuration_versions", schema="configuration")
    op.drop_index(
        "ix_scoring_criteria_engine_type_code",
        table_name="scoring_criteria",
        schema="configuration",
    )
    op.drop_table("scoring_criteria", schema="configuration")
    op.drop_table("scoring_profiles", schema="configuration")
    op.drop_index(
        "ix_engine_types_unique_active_signed", table_name="engine_types", schema="configuration"
    )
    op.drop_table("engine_types", schema="configuration")
    op.execute("DROP SCHEMA IF EXISTS configuration")
