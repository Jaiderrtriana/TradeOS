"""
Configuration infrastructure: SQLAlchemy models for the `configuration`
schema (TRADEOS_DATABASE_DESIGN.md §6.3-6.7).

Typed `Mapped`/`mapped_column` style (SQLAlchemy 2.0), matching every prior
module — required for mypy to type-check repository.py's round-trip into
domain dataclasses (see Identity infrastructure/models.py, Sprint 1.1).
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.base import Base


class EngineTypeModel(Base):
    __tablename__ = "engine_types"
    __table_args__ = {"schema": "configuration"}

    code: Mapped[str] = mapped_column(String(30), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(60), nullable=False)
    is_signed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class ScoringProfileModel(Base):
    __tablename__ = "scoring_profiles"
    __table_args__ = {"schema": "configuration"}

    code: Mapped[str] = mapped_column(String(30), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(60), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class ScoringCriterionModel(Base):
    __tablename__ = "scoring_criteria"
    __table_args__ = {"schema": "configuration"}

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    engine_type_code: Mapped[str] = mapped_column(
        String(30), ForeignKey("configuration.engine_types.code"), nullable=False
    )
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_field: Mapped[str] = mapped_column(String(64), nullable=False)
    min_value: Mapped[float] = mapped_column(Numeric, nullable=False)
    max_value: Mapped[float] = mapped_column(Numeric, nullable=False)
    category_map: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ScoringConfigurationVersionModel(Base):
    __tablename__ = "scoring_configuration_versions"
    __table_args__ = {"schema": "configuration"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_label: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity.user_accounts.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class ScoringWeightModel(Base):
    __tablename__ = "scoring_weights"
    __table_args__ = {"schema": "configuration"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    configuration_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("configuration.scoring_configuration_versions.id"),
        nullable=False,
    )
    criterion_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("configuration.scoring_criteria.id"), nullable=False
    )
    profile_code: Mapped[str] = mapped_column(
        String(30), ForeignKey("configuration.scoring_profiles.code"), nullable=False
    )
    weight: Mapped[float] = mapped_column(Numeric, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
