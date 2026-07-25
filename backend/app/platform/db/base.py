"""
Platform: the single shared SQLAlchemy declarative base.

Every module's infrastructure-layer models (added from Phase 1 onward)
import this same Base, so Alembic's autogenerate sees one consistent
metadata across every Postgres schema (TRADEOS_DATABASE_DESIGN.md §2.2 —
one schema per Bounded Context, all migrated through one history).
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()
