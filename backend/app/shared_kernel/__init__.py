"""
Shared Kernel — TRADEOS_SYSTEM_ARCHITECTURE.md §3.2.

The one deliberate exception to "modules communicate only through
contracts": the handful of Value Objects and Enums used across module
boundaries by design (Money, RMultiple, Score, Grade, Direction,
TradeResult, EngineType — TRADEOS_DOMAIN_MODEL.md §9-10).

Deliberately empty as of Sprint 0.1 — populated only when a phase first
needs one of these shared types (Trading in Phase 4, Evaluation in Phase 3),
per TRADEOS_BACKEND_BLUEPRINT.md's own module-by-module sequencing. No
entity, aggregate, or domain service ever belongs here.
"""
