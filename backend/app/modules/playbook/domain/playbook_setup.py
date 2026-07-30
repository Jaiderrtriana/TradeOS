"""
Playbook domain: PlaybookSetup — Aggregate Root (`TRADEOS_DOMAIN_MODEL.md`
§8.8): "the living definition of one trading setup... a reference to its
corresponding Catalog entry so that Trading Context trades attributed to
this setup can be found."

No `name`/`description` field here despite Domain Model §8.8 naming them
as "Owned Information" -- `TRADEOS_DATABASE_DESIGN.md` §6.15's actual
column list has neither (a documentary contradiction, Sprint 7.1
pre-analysis; resolved by precedent: `name` is resolved transitively
from the linked `catalog_entries.name`, `GetPlaybookSetupUseCase`'s job,
same pattern `GetMistakeRankingUseCase` already established, Sprint 5.2).

No `__post_init__`/`validate_*`: no numbered Domain Invariant exists for
PlaybookSetup (confirmed absent, Domain Model §14-15), and its four text
fields (`entry_criteria`/`exit_criteria`/`ideal_conditions`/`risk_rules`)
are mutually independent -- no cross-field rule to enforce, unlike
`JournalEntry.validate_exactly_one_reference`.

`status` is never client-settable directly -- `CreatePlaybookSetupUseCase`
always constructs `ACTIVE`; only `DeprecatePlaybookSetupUseCase` changes
it (Domain Model §13.4's lifecycle: `Active -> Deprecated`, no reverse
transition, no third state).
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

ACTIVE = "active"
DEPRECATED = "deprecated"


@dataclass
class PlaybookSetup:
    catalog_entry_id: uuid.UUID
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    entry_criteria: str = ""
    exit_criteria: str = ""
    ideal_conditions: str = ""
    risk_rules: str = ""
    status: str = ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: datetime | None = None
