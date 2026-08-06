"""
Applies pending Alembic migrations — the only thing this script does.

Deliberately separate from `scripts/seed_configuration.py` (publishes the
first `ScoringConfigurationVersion`) and from `scripts/bootstrap.py` (a
local-development convenience wrapper that composes both in one command).
Migrations and Configuration-seeding have genuinely different lifecycles:
migrations apply once per schema version and are safe to re-run
(idempotent — Alembic itself tracks applied revisions, a no-op once
current); seeding requires a real, already-registered user
(`TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` Sprint 2.1: "Dependencies: Phase
1 (a `user_id` must exist to attribute the seed action)") and is a
one-time, per-environment operational step, not a deployment step.

This is the command a production deployment (Phase 9, Sprint 9.1's
containerized backend) runs — it has no dependency on any user existing
yet, unlike seeding, so it is safe to run unconditionally as part of
bringing a fresh environment's schema up to date, before the application
itself ever starts serving requests.

Usage:
    cd backend && PYTHONPATH=. poetry run python scripts/migrate.py
    # or, inside the container:
    docker run <image> python scripts/migrate.py
"""

from alembic import command
from alembic.config import Config


def run_migrations() -> None:
    alembic_config = Config("alembic.ini")
    command.upgrade(alembic_config, "head")


def main() -> None:
    print("Applying database migrations (alembic upgrade head)...")
    run_migrations()
    print("Migrations up to date.")


if __name__ == "__main__":
    main()
