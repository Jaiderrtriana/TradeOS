"""
Platform: Idempotency-Key support (`TRADEOS_API_SPECIFICATION.md` §3.6) —
a cross-cutting concern, not owned by Trading specifically, even though
`POST /trades` is its first (and, this sprint, only) caller: any future
POST-create endpoint can reuse `claim_idempotency_key`.

Concurrency-safe by construction (approved design, Sprint 4.1 — see
CHANGELOG.md): the *first* INSERT to actually commit into
`platform.idempotency_keys` wins a given `(user_id, idempotency_key)`
pair, enforced by `ix_idempotency_keys_user_key`'s UNIQUE constraint
(migration 0008) — never a "SELECT to check, then INSERT" sequence,
which is exactly the race `ADR_CONFIGURATION_PUBLISH_RACE_CONDITION.md`
diagnosed and fixed for Configuration's publish flow.

The claim INSERT, the wrapped Use Case's own writes, and the later
`store_idempotent_response` UPDATE all happen inside the *same* request
transaction, committed together by the router exactly once (same
convention every other endpoint already follows). This is what makes an
explicit "release on failure" step unnecessary: if the wrapped Use Case
raises, the router never reaches `session.commit()`, and the whole
transaction — claim row included — is discarded when the request's
session closes, exactly as if the claim had never been attempted. A
retry with the same key then simply claims fresh.

`claim_idempotency_key` performs the INSERT inside a SAVEPOINT
(`session.begin_nested()`) specifically so a *losing* race — the UNIQUE
constraint rejecting our INSERT because a concurrent request already
holds this exact key — only unwinds that one statement, not any work the
caller's own transaction has already staged. Postgres itself provides
the actual serialization: a second concurrent INSERT for the same key
blocks on the first (uncommitted) row until that transaction resolves,
then either fails the UNIQUE check (first committed — read its stored
response) or succeeds outright (first rolled back — nothing to conflict
with).
"""

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.db.models import IdempotencyKeyModel
from app.platform.errors import ConflictError


@dataclass(frozen=True)
class StoredResponse:
    """A previously-completed request's exact response — the caller must
    return this directly, verbatim, never re-run its Use Case."""

    status: int
    body: dict[str, Any]


@dataclass(frozen=True)
class Claim:
    """A newly-acquired claim on this `(user_id, idempotency_key)` pair —
    the caller must run its Use Case and then call
    `store_idempotent_response` exactly once before the request commits."""

    id: uuid.UUID


async def claim_idempotency_key(
    session: AsyncSession, *, user_id: uuid.UUID, idempotency_key: str, endpoint: str
) -> Claim | StoredResponse:
    try:
        async with session.begin_nested():
            claim_id = uuid.uuid4()
            session.add(
                IdempotencyKeyModel(
                    id=claim_id,
                    user_id=user_id,
                    idempotency_key=idempotency_key,
                    endpoint=endpoint,
                    response_status=None,
                    response_body=None,
                )
            )
            await session.flush()
        return Claim(id=claim_id)
    except IntegrityError:
        result = await session.execute(
            select(IdempotencyKeyModel).where(
                IdempotencyKeyModel.user_id == user_id,
                IdempotencyKeyModel.idempotency_key == idempotency_key,
            )
        )
        row = result.scalar_one()
        if row.response_status is None or row.response_body is None:
            # Still in flight (a genuinely concurrent duplicate, not yet
            # committed) — there is no response to replay yet.
            raise ConflictError(
                "A request with this Idempotency-Key is already being processed."
            ) from None
        return StoredResponse(status=row.response_status, body=row.response_body)


async def store_idempotent_response(
    session: AsyncSession, claim: Claim, *, status: int, body: dict[str, Any]
) -> None:
    result = await session.execute(
        select(IdempotencyKeyModel).where(IdempotencyKeyModel.id == claim.id)
    )
    row = result.scalar_one()
    row.response_status = status
    row.response_body = body
