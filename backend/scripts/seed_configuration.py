"""
Seeds the first published ScoringConfigurationVersion — Sprint 2.1
(TRADEOS_IMPLEMENTATION_MASTER_PLAN.md: "seed the first published version
from the Excel-derived criteria/weights... Dependencies: Phase 1 (a
user_id must exist to attribute the seed action)").

Run manually, after at least one user has registered, from the `backend/`
directory (PYTHONPATH=. is required so `app.*` imports resolve, since this
script lives outside the `app` package):

    PYTHONPATH=. poetry run python scripts/seed_configuration.py --user-id <uuid> [--version-label v1.0]

Idempotent: re-running skips criteria that already exist and exits without
creating a second published version if one already exists. Uses the same
Application-layer Use Cases the HTTP API uses
(CreateScoringCriterionUseCase, CreateDraftConfigurationVersionUseCase,
UpdateDraftWeightsUseCase, PublishScoringConfigurationVersionUseCase) —
never raw SQL — so the seeded data can never bypass a domain invariant the
real API enforces.

--- Data provenance ---

Every criterion/weight below for Confidence, Quality, Execution, and
Market Context was extracted directly from
`legacy/Trading Journal v2.0 Stable.xlsx` (the `⚙️ CONFIG` sheet's weight
tables, category-lookup tables, and Market Context Tables 1-2; the exact
`IF(...)`/`VLOOKUP(...)` formulas in the `📒 Trades` sheet's TRADE
CONFIDENCE / TRADE QUALITY / EXECUTION SCORE columns; and that sheet's
data-validation dropdown lists) — approved by the user after reviewing
this extraction, not invented. Confidence/Quality/Execution weights are
profile-independent in the Excel (a single global weight per criterion);
since `configuration.scoring_weights.profile_code` is a required column in
the frozen schema, each of those weights is seeded identically across all
three profiles — a faithful, lossless translation (the real weight never
varies by profile), not new data. Market Context's weights are genuinely
per-profile in the Excel and are seeded as such, 1:1.

--- The Bias Engine is deliberately excluded ---

`bias` is registered as an `engine_type` (migration 0004) but gets ZERO
ScoringCriterion/ScoringWeight rows here — not an oversight. The Excel
proves Bias does not use this generic weighted-criteria model at all:

  1. Bias's per-criterion scores are signed integers whose mapping from a
     selected category to a point value DEPENDS ON THE TRADING PROFILE
     (Day Trade vs. Swing) — e.g. DXY "Strong Bullish" scores -3 for Day
     Trade but -4 for Swing. `scoring_criteria.category_map` is a single,
     profile-independent JSONB column; it cannot represent this.
  2. Bias's final index is `GROSS_SCORE / 38 * 100` (Day Trading/Scalping)
     or `GROSS_SCORE / 45 * 100` (Swing) — division by a FIXED CONSTANT,
     not by the sum of active weights (Domain Invariant INV-WEIGHT-01).
     `configuration.scoring_weights` has no column for a per-profile
     normalizing constant at all.
  3. This directly contradicts `PROJECT_AUDIT.md` §3.2's own claim that
     the Evaluation Engine is generic and "autonormalizado dividiendo por
     la suma de pesos activos, no una constante fija" — true for
     Confidence/Quality/Execution/Market Context, false for Bias.

Forcing Bias's real behavior into `scoring_criteria`/`scoring_weights`/
`category_map` as they exist today would either misrepresent the Excel's
actual behavior or require the model to already support per-profile
category maps and per-profile fixed normalizers, neither of which exists.
Any workaround here would produce a different score than the Excel and
would have to be redone once Sprint 3.2 (which owns "Bias's signed
normalization" per the Master Plan) makes that design decision. See
CHANGELOG.md, Sprint 2.1, for the full write-up and the registered
technical debt for Sprint 3.2.
"""

import argparse
import asyncio
import uuid
from typing import Any

from app.modules.configuration.application.create_draft_configuration_version import (
    CreateDraftConfigurationVersionUseCase,
)
from app.modules.configuration.application.create_scoring_criterion import (
    CreateScoringCriterionUseCase,
)
from app.modules.configuration.application.publish_scoring_configuration_version import (
    PublishScoringConfigurationVersionUseCase,
)
from app.modules.configuration.application.update_draft_weights import UpdateDraftWeightsUseCase
from app.modules.configuration.infrastructure.repository import (
    EngineTypeRepository,
    ScoringConfigurationVersionRepository,
    ScoringCriterionRepository,
    ScoringProfileRepository,
    ScoringWeightRepository,
)
from app.modules.identity.infrastructure.repository import UserAccountRepository
from app.platform.db.session import SessionLocal
from app.platform.errors import ConflictError
from app.platform.events.dispatcher import dispatcher

PROFILES = ["day_trading", "swing_trading", "scalping"]

# (id, name, source_field, min_value, max_value, category_map, weight)
# — weight is the single, profile-independent value from `⚙️ CONFIG`.
CONFIDENCE_CRITERIA: list[tuple[str, str, str, float, float, dict[str, Any] | None, float]] = [
    (
        "confidence.bias_index_at_entry",
        "Bias Index @ Entry",
        "bias_index_at_entry",
        0,
        100,
        None,
        0.5,
    ),
    (
        "confidence.htf_alignment",
        "HTF Alignment",
        "htf_alignment",
        0,
        100,
        {
            "Full Alignment": 100,
            "Moderate Alignment": 70,
            "Partial Conflict": 40,
            "Full Conflict": 0,
        },
        0.2,
    ),
    (
        "confidence.ltf_confirmation",
        "LTF Confirmation",
        "ltf_confirmation",
        0,
        100,
        {"Yes": 100, "Partial": 50, "No": 0},
        0.15,
    ),
    (
        "confidence.emotional_state",
        "Emotional State",
        "emotional_state",
        0,
        100,
        {"Calm": 100, "Slightly Emotional": 70, "Emotional": 30, "Revenge Trading": 0},
        0.15,
    ),
]

QUALITY_CRITERIA: list[tuple[str, str, str, float, float, dict[str, Any] | None, float]] = [
    ("quality.followed_plan", "Followed Plan", "followed_plan", 0, 100, {"Yes": 100, "No": 0}, 0.2),
    ("quality.valid_setup", "Valid Setup", "valid_setup", 0, 100, {"Yes": 100, "No": 0}, 0.15),
    (
        "quality.entered_at_planned_level",
        "Entered at Planned Level",
        "entered_at_planned_level",
        0,
        100,
        {"Yes": 100, "No": 0},
        0.15,
    ),
    (
        "quality.respected_stop",
        "Respected Stop",
        "respected_stop",
        0,
        100,
        {"Yes": 100, "No": 0},
        0.2,
    ),
    (
        "quality.respected_tp",
        "Respected TP",
        "respected_tp",
        0,
        100,
        {"Yes": 100, "N/A": 100, "Exited Early": 60, "Exited Late": 40, "No": 0},
        0.15,
    ),
    (
        "quality.respected_risk_mgmt",
        "Respected Risk Mgmt",
        "respected_risk_mgmt",
        0,
        100,
        {"Yes": 100, "No": 0},
        0.15,
    ),
]

EXECUTION_CRITERIA: list[tuple[str, str, str, float, float, dict[str, Any] | None, float]] = [
    (
        "execution.entry_timing",
        "Entry Timing",
        "entry_timing",
        0,
        100,
        {
            "Perfect": 100,
            "Slightly Early": 70,
            "Slightly Late": 70,
            "Too Early": 30,
            "Too Late": 30,
        },
        0.25,
    ),
    (
        "execution.stop_placement",
        "Stop Placement",
        "stop_placement",
        0,
        100,
        {"Perfect": 100, "Too Tight": 50, "Too Wide": 50},
        0.25,
    ),
    (
        "execution.tp_execution",
        "TP Execution",
        "tp_execution",
        0,
        100,
        {"Perfect": 100, "Exited Early": 60, "Exited Late": 60},
        0.25,
    ),
    (
        "execution.management",
        "Management",
        "management",
        0,
        100,
        {"Excellent": 100, "Good": 80, "Average": 50, "Poor": 20},
        0.25,
    ),
]

# (id, category, name, min_value, max_value)
# — from ⚙️ CONFIG's MARKET_CONTEXT_CRITERIA table (Table 1).
MARKET_CONTEXT_CRITERIA: list[tuple[str, str, str, float, float]] = [
    ("market_context.dxy", "Macro", "DXY — Dollar Index", -4, 4),
    ("market_context.spy", "Macro", "SPY / TradFi", -4, 3),
    ("market_context.etf_flow", "Macro", "ETF Flow (BTC Spot)", -3, 3),
    ("market_context.macro_events", "Macro", "Macro Events Today", -3, 0),
    ("market_context.btc_struct", "Trend", "BTC Market Structure", -4, 4),
    ("market_context.daily_trend", "Trend", "Daily Trend", -3, 3),
    ("market_context.weekly_trend", "Trend", "Weekly Trend", -3, 3),
    ("market_context.ema20", "Trend", "EMA 20", -1, 1),
    ("market_context.ema50", "Trend", "EMA 50", -2, 2),
    ("market_context.ema200", "Trend", "EMA 200", -3, 3),
    ("market_context.adx", "Trend", "ADX / Fuerza de Tendencia", -2, 2),
    ("market_context.htf_align", "Trend", "HTF Alignment", -3, 2),
    ("market_context.atr", "Volatility", "ATR / Volatilidad", -1, 2),
    ("market_context.volume", "Participation", "Volumen", -2, 2),
    ("market_context.open_interest", "Participation", "Open Interest", -2, 2),
    ("market_context.cvd_delta", "Participation", "CVD / Delta", -2, 2),
    ("market_context.fear_greed", "Sentiment", "Fear & Greed Index", -3, 3),
    ("market_context.funding", "Sentiment", "Funding Rate", -2, 2),
    ("market_context.ls_ratio", "Sentiment", "Long/Short Ratio", -1, 1),
    ("market_context.btc_dom", "Sentiment", "BTC Dominance", -1, 1),
    ("market_context.ssr", "Sentiment", "Stablecoin Supply Ratio", -1, 1),
    ("market_context.liq_heatmap", "Liquidity", "Liquidity Heatmap / Orderbook", -1, 1),
    ("market_context.liq_4h", "Liquidity", "Liquidaciones 4H", -1, 1),
    ("market_context.liq_24h", "Liquidity", "Liquidaciones 24H", -1, 1),
    ("market_context.struct_liq", "Liquidity", "Structural Liquidity", -1, 1),
    ("market_context.htf_zone", "Liquidity", "HTF Zone", -1, 1),
    ("market_context.session", "Execution Context", "Trading Session", -2, 2),
    ("market_context.vwap", "Execution Context", "VWAP", -2, 2),
    ("market_context.vpoc", "Execution Context", "VPOC", -1, 1),
    ("market_context.confluence", "Confluence", "Execution Confluence Score", -17, 7),
]

# {criterion_id: {profile_code: weight}} — from ⚙️ CONFIG's
# MARKET_CONTEXT_WEIGHTS table (Table 2); Score_Normalizado/Contribución
# columns discarded (worked-example output, not configuration).
MARKET_CONTEXT_WEIGHTS: dict[str, dict[str, float]] = {
    "market_context.dxy": {"day_trading": 0.02, "swing_trading": 0.0375, "scalping": 0.0075},
    "market_context.spy": {"day_trading": 0.02, "swing_trading": 0.0375, "scalping": 0.0075},
    "market_context.etf_flow": {"day_trading": 0.02, "swing_trading": 0.0375, "scalping": 0.0075},
    "market_context.macro_events": {
        "day_trading": 0.02,
        "swing_trading": 0.0375,
        "scalping": 0.0075,
    },
    "market_context.btc_struct": {
        "day_trading": 0.0275,
        "swing_trading": 0.0375,
        "scalping": 0.0125,
    },
    "market_context.daily_trend": {
        "day_trading": 0.0275,
        "swing_trading": 0.0375,
        "scalping": 0.0125,
    },
    "market_context.weekly_trend": {
        "day_trading": 0.0275,
        "swing_trading": 0.0375,
        "scalping": 0.0125,
    },
    "market_context.ema20": {"day_trading": 0.0275, "swing_trading": 0.0375, "scalping": 0.0125},
    "market_context.ema50": {"day_trading": 0.0275, "swing_trading": 0.0375, "scalping": 0.0125},
    "market_context.ema200": {"day_trading": 0.0275, "swing_trading": 0.0375, "scalping": 0.0125},
    "market_context.adx": {"day_trading": 0.0275, "swing_trading": 0.0375, "scalping": 0.0125},
    "market_context.htf_align": {
        "day_trading": 0.0275,
        "swing_trading": 0.0375,
        "scalping": 0.0125,
    },
    "market_context.atr": {"day_trading": 0.1, "swing_trading": 0.05, "scalping": 0.2},
    "market_context.volume": {"day_trading": 0.04, "swing_trading": 0.0267, "scalping": 0.05},
    "market_context.open_interest": {
        "day_trading": 0.04,
        "swing_trading": 0.0267,
        "scalping": 0.05,
    },
    "market_context.cvd_delta": {"day_trading": 0.04, "swing_trading": 0.0267, "scalping": 0.05},
    "market_context.fear_greed": {"day_trading": 0.02, "swing_trading": 0.024, "scalping": 0.01},
    "market_context.funding": {"day_trading": 0.02, "swing_trading": 0.024, "scalping": 0.01},
    "market_context.ls_ratio": {"day_trading": 0.02, "swing_trading": 0.024, "scalping": 0.01},
    "market_context.btc_dom": {"day_trading": 0.02, "swing_trading": 0.024, "scalping": 0.01},
    "market_context.ssr": {"day_trading": 0.02, "swing_trading": 0.024, "scalping": 0.01},
    "market_context.liq_heatmap": {"day_trading": 0.026, "swing_trading": 0.016, "scalping": 0.044},
    "market_context.liq_4h": {"day_trading": 0.026, "swing_trading": 0.016, "scalping": 0.044},
    "market_context.liq_24h": {"day_trading": 0.026, "swing_trading": 0.016, "scalping": 0.044},
    "market_context.struct_liq": {"day_trading": 0.026, "swing_trading": 0.016, "scalping": 0.044},
    "market_context.htf_zone": {"day_trading": 0.026, "swing_trading": 0.016, "scalping": 0.044},
    "market_context.session": {"day_trading": 0.0333, "swing_trading": 0.0067, "scalping": 0.05},
    "market_context.vwap": {"day_trading": 0.0333, "swing_trading": 0.0067, "scalping": 0.05},
    "market_context.vpoc": {"day_trading": 0.0333, "swing_trading": 0.0067, "scalping": 0.05},
    "market_context.confluence": {"day_trading": 0.15, "swing_trading": 0.2, "scalping": 0.1},
}


async def _seed_criteria_with_universal_weight(
    criterion_use_case: CreateScoringCriterionUseCase,
    engine_type_code: str,
    criteria: list[tuple[str, str, str, float, float, dict[str, Any] | None, float]],
) -> dict[str, float]:
    """Creates each criterion (skipping ones that already exist) and
    returns {criterion_id: weight} to be applied identically across all
    three profiles."""
    universal_weights: dict[str, float] = {}
    for criterion_id, name, source_field, min_value, max_value, category_map, weight in criteria:
        try:
            await criterion_use_case.execute(
                id=criterion_id,
                engine_type_code=engine_type_code,
                name=name,
                source_field=source_field,
                min_value=min_value,
                max_value=max_value,
                category_map=category_map,
            )
            print(f"  created criterion: {criterion_id}")
        except ConflictError:
            print(f"  already exists, skipping: {criterion_id}")
        universal_weights[criterion_id] = weight
    return universal_weights


async def seed(user_id: uuid.UUID, version_label: str) -> None:
    async with SessionLocal() as session:
        user_repository = UserAccountRepository(session)
        if await user_repository.get_by_id(user_id) is None:
            raise SystemExit(f"No user account found with id '{user_id}'. Aborting.")

        version_repository = ScoringConfigurationVersionRepository(session)
        weight_repository = ScoringWeightRepository(session)
        criterion_repository = ScoringCriterionRepository(session)
        profile_repository = ScoringProfileRepository(session)
        engine_type_repository = EngineTypeRepository(session)

        already_published = await version_repository.get_published()
        if already_published is not None:
            print(
                f"A published configuration version already exists "
                f"('{already_published.version_label}'). Nothing to do."
            )
            return

        criterion_use_case = CreateScoringCriterionUseCase(
            criterion_repository, engine_type_repository
        )

        print("Seeding Confidence criteria...")
        confidence_weights = await _seed_criteria_with_universal_weight(
            criterion_use_case, "confidence", CONFIDENCE_CRITERIA
        )
        print("Seeding Quality criteria...")
        quality_weights = await _seed_criteria_with_universal_weight(
            criterion_use_case, "quality", QUALITY_CRITERIA
        )
        print("Seeding Execution criteria...")
        execution_weights = await _seed_criteria_with_universal_weight(
            criterion_use_case, "execution", EXECUTION_CRITERIA
        )

        print("Seeding Market Context criteria...")
        for criterion_id, category, name, min_value, max_value in MARKET_CONTEXT_CRITERIA:
            try:
                await criterion_use_case.execute(
                    id=criterion_id,
                    engine_type_code="market_context",
                    name=name,
                    source_field=criterion_id.removeprefix("market_context."),
                    min_value=min_value,
                    max_value=max_value,
                    category=category,
                )
                print(f"  created criterion: {criterion_id}")
            except ConflictError:
                print(f"  already exists, skipping: {criterion_id}")
        await session.commit()

        print(f"Creating draft configuration version '{version_label}'...")
        create_draft_use_case = CreateDraftConfigurationVersionUseCase(
            version_repository, weight_repository
        )
        draft = await create_draft_use_case.execute(version_label, created_by_user_id=user_id)
        await session.commit()

        weight_use_case = UpdateDraftWeightsUseCase(
            version_repository, weight_repository, criterion_repository, profile_repository
        )

        print("Applying weights (Confidence/Quality/Execution: uniform across all profiles)...")
        for criterion_id, weight in {
            **confidence_weights,
            **quality_weights,
            **execution_weights,
        }.items():
            for profile_code in PROFILES:
                await weight_use_case.execute(draft.id, criterion_id, profile_code, weight)

        print("Applying Market Context weights (genuinely per-profile)...")
        for criterion_id, per_profile in MARKET_CONTEXT_WEIGHTS.items():
            for profile_code, weight in per_profile.items():
                await weight_use_case.execute(draft.id, criterion_id, profile_code, weight)
        await session.commit()

        print(f"Publishing '{version_label}'...")
        publish_use_case = PublishScoringConfigurationVersionUseCase(
            version_repository, weight_repository, criterion_repository, dispatcher, session
        )
        published = await publish_use_case.execute(draft.id)
        await session.commit()

        print(f"Done. '{published.version_label}' is now published ({published.id}).")
        print(
            "Bias was intentionally left unseeded — see this script's module "
            "docstring and CHANGELOG.md, Sprint 2.1."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--user-id", required=True, type=uuid.UUID, help="Attributed publisher's user_id."
    )
    parser.add_argument("--version-label", default="v1.0", help="Label for the published version.")
    args = parser.parse_args()
    asyncio.run(seed(args.user_id, args.version_label))


if __name__ == "__main__":
    main()
