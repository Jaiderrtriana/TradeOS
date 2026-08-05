"""
Single, official entrypoint to leave a fresh TradeOS backend environment
operational — applies pending Alembic migrations and, once a user exists,
publishes the first `ScoringConfigurationVersion` by delegating to
`scripts/seed_configuration.py`.

--- Why this exists ---

`RegisterTradeUseCase`/`OpenTradeUseCase`/`PreviewEvaluationUseCase` all
require a published `ScoringConfigurationVersion` to evaluate against
(`TRADEOS_SYSTEM_ARCHITECTURE.md` ADR-03) — without one, `POST /trades`
correctly rejects with a 422. On a freshly cloned/migrated environment,
nothing produced that published version automatically, and running
`seed_configuration.py` by hand was a step easy to forget. This script
does not change that business rule (Trade creation is still, correctly,
impossible without a published Configuration) — it removes the operational
gap of nobody having satisfied its precondition.

--- Why this is two stages, not one ---

`TRADEOS_IMPLEMENTATION_MASTER_PLAN.md`'s own Sprint 2.1 entry states the
seed's "Dependencies: Phase 1 (a `user_id` must exist to attribute the
seed action)" — `scoring_configuration_versions.created_by_user_id` is a
required attribution to a real, already-registered user, not an
invented system account. A single command cannot both apply migrations
(which must succeed against a schema with zero users) and publish a
Configuration (which needs one to exist) without either inventing a
user out of nothing or accepting a chicken-and-egg ordering. This script
therefore supports being run twice:

    # Stage 1 -- right after cloning, before any user exists:
    cd backend && PYTHONPATH=. poetry run python scripts/bootstrap.py

    # Stage 2 -- after registering at least one user (via the frontend's
    # /register page, or POST /api/v1/auth/register):
    cd backend && PYTHONPATH=. poetry run python scripts/bootstrap.py --user-id <uuid>

Idempotent in both stages: Alembic itself tracks applied revisions
(re-running `upgrade head` is a no-op once current), and
`seed_configuration.seed()` already skips seeding once a published
version exists.
"""

import argparse
import asyncio
import uuid

from alembic import command
from alembic.config import Config

from scripts.seed_configuration import seed


def run_migrations() -> None:
    alembic_config = Config("alembic.ini")
    command.upgrade(alembic_config, "head")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--user-id",
        type=uuid.UUID,
        default=None,
        help="Attributed publisher's user_id. Omit to only run migrations "
        "(Stage 1, before any user is registered).",
    )
    parser.add_argument("--version-label", default="v1.0", help="Label for the published version.")
    args = parser.parse_args()

    print("Applying database migrations (alembic upgrade head)...")
    run_migrations()
    print("Migrations up to date.")

    if args.user_id is None:
        print(
            "\nNo --user-id given: skipping the Configuration seed.\n"
            "Register at least one user (frontend /register, or "
            "POST /api/v1/auth/register), then re-run:\n"
            "  PYTHONPATH=. poetry run python scripts/bootstrap.py --user-id <uuid>"
        )
        return

    asyncio.run(seed(args.user_id, args.version_label))


if __name__ == "__main__":
    main()
