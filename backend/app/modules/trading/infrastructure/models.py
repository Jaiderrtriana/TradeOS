"""
Trading infrastructure: SQLAlchemy models for the `trading` schema
(TRADEOS_DATABASE_DESIGN.md §6.9-6.13, migration 0007).

Typed `Mapped`/`mapped_column` style (SQLAlchemy 2.0), matching every
prior module.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.base import Base


class TradeModel(Base):
    __tablename__ = "trades"
    __table_args__ = {"schema": "trading"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity.user_accounts.id"), nullable=False
    )
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("configuration.catalog_entries.id"), nullable=True
    )
    setup_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("configuration.catalog_entries.id"), nullable=True
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("configuration.catalog_entries.id"), nullable=True
    )
    entry_trigger_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("configuration.catalog_entries.id"), nullable=True
    )
    market: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(String(5), nullable=False)
    entry_price: Mapped[float] = mapped_column(Numeric, nullable=False)
    stop_loss: Mapped[float] = mapped_column(Numeric, nullable=False)
    exit_price: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    size: Mapped[float] = mapped_column(Numeric, nullable=False, default=0)
    leverage: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    result: Mapped[str] = mapped_column(String(5), nullable=False, default="open")
    realized_pnl: Mapped[float] = mapped_column(Numeric, nullable=False, default=0)
    mfe_price: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    mae_price: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity.user_accounts.id"), nullable=True
    )


class ChecklistSnapshotModel(Base):
    __tablename__ = "checklist_snapshots"
    __table_args__ = {"schema": "trading"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trade_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trading.trades.id"), nullable=False
    )
    answers: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class EvaluationSnapshotModel(Base):
    __tablename__ = "evaluation_snapshots"
    __table_args__ = {"schema": "trading"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trade_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trading.trades.id"), nullable=False
    )
    configuration_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("configuration.scoring_configuration_versions.id"),
        nullable=False,
    )
    confidence_score: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    confidence_grade: Mapped[str | None] = mapped_column(String(2), nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    quality_grade: Mapped[str | None] = mapped_column(String(2), nullable=True)
    execution_score: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    execution_grade: Mapped[str | None] = mapped_column(String(2), nullable=True)
    market_context_score: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    market_context_grade: Mapped[str | None] = mapped_column(String(2), nullable=True)
    bias_score: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class EvaluationSnapshotBreakdownModel(Base):
    __tablename__ = "evaluation_snapshot_breakdowns"
    __table_args__ = {"schema": "trading"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trading.evaluation_snapshots.id"), nullable=False
    )
    criterion_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("configuration.scoring_criteria.id"), nullable=False
    )
    engine_type_code: Mapped[str] = mapped_column(
        String(30), ForeignKey("configuration.engine_types.code"), nullable=False
    )
    criterion_name_at_time: Mapped[str] = mapped_column(String(120), nullable=False)
    raw_value: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_value: Mapped[float] = mapped_column(Numeric, nullable=False)
    weight: Mapped[float] = mapped_column(Numeric, nullable=False)
    contribution: Mapped[float] = mapped_column(Numeric, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class TradeMistakeModel(Base):
    __tablename__ = "trade_mistakes"
    __table_args__ = {"schema": "trading"}

    trade_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trading.trades.id"), primary_key=True
    )
    catalog_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("configuration.catalog_entries.id"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
