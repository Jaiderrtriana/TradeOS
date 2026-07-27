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

--- The Bias Engine: seeded here too, following Sprint 3.2's approved data proposal ---

Sprint 2.1 left Bias unseeded (see CHANGELOG.md, Sprint 2.1) because its
real Excel mechanism doesn't fit `scoring_criteria`/`scoring_weights` as
they existed then: category-to-point mappings that vary by an axis
(`Operation Type`: Day Trade / Swing / Breakout × Long / Short) the schema
has no column for, and a fixed per-profile divisor (38 or 45) instead of
`INV-WEIGHT-01`'s sum-of-active-weights. Sprint 3.2 (Camino A, already
implemented in `app/modules/evaluation/domain/bias_engine.py`) settled the
*aggregation mechanism*: Bias reuses the exact same generic weighted-core
every other engine uses, with signed category-map values — a deliberate,
approved, documented divergence from the raw Excel, not a bug. This seed
supplies the *data* for that decision, approved after a full written
proposal review (`PROPUESTA_DATOS_BIAS_ENGINE.md`, session-scoped, not
committed — see CHANGELOG.md, Sprint 3.2, for the complete decision log).

Six real simplifications were required to translate the Excel's 35
`GROSS_SCORE` inputs onto TradeOS's `profile_code` model (none invent a
category-to-point value not present in the Excel; all are documented in
CHANGELOG.md and summarized here):

  1. **Axis collapse.** The Excel's real branching axis is `C5`
     ("Operation Type": Day Trade Long/Short, Swing Long/Short, Breakout
     Long/Short) — never `profile_code`. Approved mapping: "No-Swing"
     Excel branch (Day Trade + Breakout, either direction) -> BOTH
     `day_trading` and `scalping`; "Swing" branch -> `swing_trading`.
  2. **Scalping has no real data.** The Excel never had an
     `Operation Type = Scalping`; it inherits Day Trading's real numbers
     verbatim (decision #1 above).
  3. **3 direction-dependent criteria** (`btc_dom`, `liq_4h`, `liq_24h`)
     use the real "trade is Long" branch as their single, profile-uniform
     category_map — `category_map` has no direction axis. Registered as
     technical debt for Phase 4 (Trading), when `Trade.direction` exists
     and this can be revisited.
  4. **`atr`** branches on `Breakout Long/Short` in the real Excel, an
     axis with no `scoring_profile` equivalent at all; the real
     "No-Breakout" branch is used uniformly across all 3 profiles.
  5. **Equal weights.** No real per-criterion weight table exists for
     Bias (unlike Market Context) — the real formula sums all 35 values
     unweighted. `BIAS_WEIGHT = 1/35` for every criterion, every profile:
     the only reading that adds zero invented weighting.
  6. **11 of the 35 real fields have a category_map that genuinely
     differs between the "No-Swing" and "Swing" branches**
     (`scoring_criteria.category_map` cannot vary by profile — Section
     6.1 of the proposal). Seeded as **two criterion rows** per such
     field (e.g. `bias.dxy` active for day_trading/scalping,
     `bias.dxy_swing` active only for swing_trading), both sharing the
     same real `source_field` (`dxy`) — the exact mechanism the Sprint
     3.2 fan-out fix (`PreviewEvaluationUseCase`) exists to support. Net
     effect: 35 real fields become 46 `scoring_criteria` rows.

28 of the 35 real fields reuse the exact `source_field` already seeded
for Market Context above (`dxy`, `spy`, `btc_struct`, ... — this is what
motivated the fan-out fix); 7 are exclusive to Bias
(`setup_type`, `ltf_confirmation`, `correlation`, `invalidation`,
`risk_reward`, `entry_zone`, `emotional_state`), new `source_field`s with
no prior overlap.

**Also not reproduced here** (both already accepted as technical debt
before this seed, unrelated to the six simplifications above): the fixed
38/45 divisor (Bias divides by the sum of active weights instead, per
`INV-WEIGHT-01`), and the resulting score's *scale* — `bias_engine.py`
applies an explicit, isolated `BIAS_SCALE_FACTOR` there (never here, never
in `scoring_core.py`) to bring the naturally small weighted-average range
back toward the Excel's -100..100 feel.
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

# (id, category, name, min_value, max_value, category_map)
# — from ⚙️ CONFIG's MARKET_CONTEXT_CRITERIA table (Table 1).
#
# `category_map` (Sprint 3.2 correction, not part of the original Sprint
# 2.1 seed): 28 of these 30 criteria are the exact real Excel cells Bias
# also reads (`bias_engine.py`'s docstring, `PROPUESTA_DATOS_BIAS_ENGINE.md`)
# — Sprint 2.1 originally modeled them as pure numeric ranges, implicitly
# expecting `checklist_answers` to already carry the Excel's post-category
# -conversion number. That's inconsistent with every other criterion in
# this system (Confidence/Quality/Execution/Bias all expect the user's
# real category label) and, once Bias's fan-out reuses the same
# `source_field`, unworkable: two criteria can't require two different
# representations of the same one real answer. Corrected here: each
# category_map value is the exact number the OLD min/max rescale would
# have produced for that category's real point (`(raw_point - min) /
# (max - min) * 100`, using this table's own already-seeded min/max) —
# `checklist_answers` now carries the label for these 28 too, and
# Market Context's own `category_map` does the (identical, regression-
# tested) translation, never `scoring_core.py`. `macro_events` and
# `confluence` (the 2 Market Context criteria Bias's GROSS_SCORE doesn't
# read) are deliberately left as-is — untouched, out of this correction's
# scope. See CHANGELOG.md, Sprint 3.2, for the full write-up.
MARKET_CONTEXT_CRITERIA: list[tuple[str, str, str, float, float, dict[str, float] | None]] = [
    (
        "market_context.dxy",
        "Macro",
        "DXY — Dollar Index",
        -4,
        4,
        {
            "Strong Bullish": 12.5,
            "Bullish": 37.5,
            "Neutral": 50.0,
            "Bearish": 62.5,
            "Strong Bearish": 75.0,
        },
    ),
    (
        "market_context.dxy_swing",
        "Macro",
        "DXY — Dollar Index (Swing)",
        -4,
        4,
        {
            "Strong Bullish": 0.0,
            "Bullish": 25.0,
            "Neutral": 50.0,
            "Bearish": 75.0,
            "Strong Bearish": 100.0,
        },
    ),
    (
        "market_context.spy",
        "Macro",
        "SPY / TradFi",
        -4,
        3,
        {
            "Strong Uptrend": 85.714286,
            "Uptrend": 71.428571,
            "Range": 57.142857,
            "Downtrend": 42.857143,
            "Panic Selloff": 14.285714,
        },
    ),
    (
        "market_context.spy_swing",
        "Macro",
        "SPY / TradFi (Swing)",
        -4,
        3,
        {
            "Strong Uptrend": 100.0,
            "Uptrend": 85.714286,
            "Range": 57.142857,
            "Downtrend": 28.571429,
            "Panic Selloff": 0.0,
        },
    ),
    (
        "market_context.etf_flow",
        "Macro",
        "ETF Flow (BTC Spot)",
        -3,
        3,
        {
            "Strong Inflows": 83.333333,
            "Mild Inflows": 66.666667,
            "Neutral": 50.0,
            "Mild Outflows": 33.333333,
            "Strong Outflows": 16.666667,
        },
    ),
    (
        "market_context.etf_flow_swing",
        "Macro",
        "ETF Flow (BTC Spot) (Swing)",
        -3,
        3,
        {
            "Strong Inflows": 100.0,
            "Mild Inflows": 66.666667,
            "Neutral": 50.0,
            "Mild Outflows": 33.333333,
            "Strong Outflows": 0.0,
        },
    ),
    ("market_context.macro_events", "Macro", "Macro Events Today", -3, 0, None),
    (
        "market_context.btc_struct",
        "Trend",
        "BTC Market Structure",
        -4,
        4,
        {
            "Bullish Trend": 87.5,
            "Bearish Trend": 12.5,
            "Range": 50.0,
            "Accumulation": 62.5,
            "Distribution": 37.5,
        },
    ),
    (
        "market_context.btc_struct_swing",
        "Trend",
        "BTC Market Structure (Swing)",
        -4,
        4,
        {
            "Bullish Trend": 100.0,
            "Bearish Trend": 0.0,
            "Range": 37.5,
            "Accumulation": 75.0,
            "Distribution": 25.0,
        },
    ),
    (
        "market_context.daily_trend",
        "Trend",
        "Daily Trend",
        -3,
        3,
        {"Bullish": 83.333333, "Bearish": 16.666667, "Neutral/Range": 50.0},
    ),
    (
        "market_context.daily_trend_swing",
        "Trend",
        "Daily Trend (Swing)",
        -3,
        3,
        {"Bullish": 100.0, "Bearish": 0.0, "Neutral/Range": 50.0},
    ),
    (
        "market_context.weekly_trend",
        "Trend",
        "Weekly Trend",
        -3,
        3,
        {"Bullish": 66.666667, "Bearish": 33.333333, "Neutral/Range": 50.0},
    ),
    (
        "market_context.weekly_trend_swing",
        "Trend",
        "Weekly Trend (Swing)",
        -3,
        3,
        {"Bullish": 100.0, "Bearish": 0.0, "Neutral/Range": 50.0},
    ),
    (
        "market_context.ema20",
        "Trend",
        "EMA 20",
        -1,
        1,
        {
            "Price Above": 100.0,
            "Price Below": 0.0,
            "Testing from Above": 50.0,
            "Testing from Below": 50.0,
        },
    ),
    (
        "market_context.ema50",
        "Trend",
        "EMA 50",
        -2,
        2,
        {"Above": 100.0, "Below": 0.0, "Testing from Above": 75.0, "Testing from Below": 25.0},
    ),
    (
        "market_context.ema200",
        "Trend",
        "EMA 200",
        -3,
        3,
        {
            "Above": 83.333333,
            "Below": 16.666667,
            "Testing from Above": 66.666667,
            "Testing from Below": 33.333333,
        },
    ),
    (
        "market_context.ema200_swing",
        "Trend",
        "EMA 200 (Swing)",
        -3,
        3,
        {
            "Above": 100.0,
            "Below": 0.0,
            "Testing from Above": 83.333333,
            "Testing from Below": 16.666667,
        },
    ),
    (
        "market_context.adx",
        "Trend",
        "ADX / Fuerza de Tendencia",
        -2,
        2,
        {
            "Range (<20)": 0.0,
            "Emerging Trend (20-25)": 50.0,
            "Healthy Trend (25-40)": 100.0,
            "Mature Trend (40-55)": 75.0,
            "Exhausted Trend (>55)": 25.0,
        },
    ),
    (
        "market_context.htf_align",
        "Trend",
        "HTF Alignment",
        -3,
        2,
        {
            "Full Alignment": 100.0,
            "Moderate Alignment": 80.0,
            "Partial Conflict": 40.0,
            "Full Conflict": 0.0,
        },
    ),
    (
        "market_context.atr",
        "Volatility",
        "ATR / Volatilidad",
        -1,
        2,
        {
            "Compression / Squeeze": 66.666667,
            "Normal": 33.333333,
            "Expansion": 33.333333,
            "Extreme / High": 0.0,
        },
    ),
    (
        "market_context.volume",
        "Participation",
        "Volumen",
        -2,
        2,
        {"Very High": 100.0, "High": 75.0, "Average": 50.0, "Low": 25.0, "Very Low": 0.0},
    ),
    (
        "market_context.open_interest",
        "Participation",
        "Open Interest",
        -2,
        2,
        {
            "Rising + Price Up (Trend)": 100.0,
            "Rising + Price Down (Short Squeeze Risk)": 0.0,
            "Falling + Price Up (Short Squeeze)": 75.0,
            "Falling + Price Down (Long Liquidation)": 0.0,
            "Stable/Neutral": 50.0,
        },
    ),
    (
        "market_context.cvd_delta",
        "Participation",
        "CVD / Delta",
        -2,
        2,
        {
            "Bullish Confirmation": 75.0,
            "Bearish Confirmation": 25.0,
            "Bullish Divergence": 100.0,
            "Bearish Divergence": 0.0,
            "Neutral/No Signal": 50.0,
        },
    ),
    (
        "market_context.fear_greed",
        "Sentiment",
        "Fear & Greed Index",
        -3,
        3,
        {
            "Extreme Fear (0-25)": 66.666667,
            "Fear (26-45)": 66.666667,
            "Neutral (46-55)": 50.0,
            "Greed (56-75)": 33.333333,
            "Extreme Greed (76-100)": 16.666667,
        },
    ),
    (
        "market_context.fear_greed_swing",
        "Sentiment",
        "Fear & Greed Index (Swing)",
        -3,
        3,
        {
            "Extreme Fear (0-25)": 100.0,
            "Fear (26-45)": 83.333333,
            "Neutral (46-55)": 50.0,
            "Greed (56-75)": 33.333333,
            "Extreme Greed (76-100)": 0.0,
        },
    ),
    (
        "market_context.funding",
        "Sentiment",
        "Funding Rate",
        -2,
        2,
        {
            "Overheated Longs (>+0.05%)": 0.0,
            "Slightly Bullish (+0.01% to +0.05%)": 75.0,
            "Neutral (-0.01% to +0.01%)": 50.0,
            "Slightly Bearish (-0.05% to -0.01%)": 50.0,
            "Overheated Shorts (<-0.05%)": 100.0,
        },
    ),
    (
        "market_context.ls_ratio",
        "Sentiment",
        "Long/Short Ratio",
        -1,
        1,
        {
            "Crowded Longs (>65%)": 0.0,
            "Mild Long Bias (55-65%)": 50.0,
            "Balanced (45-55%)": 50.0,
            "Mild Short Bias (35-45%)": 50.0,
            "Crowded Shorts (<35%)": 100.0,
        },
    ),
    (
        "market_context.btc_dom",
        "Sentiment",
        "BTC Dominance",
        -1,
        1,
        {"Rising": 100.0, "Falling": 50.0, "Neutral": 50.0},
    ),
    (
        "market_context.ssr",
        "Sentiment",
        "Stablecoin Supply Ratio",
        -1,
        1,
        {"SSR Low (High Buy Power)": 100.0, "SSR Neutral": 50.0, "SSR High (Low Buy Power)": 0.0},
    ),
    (
        "market_context.liq_heatmap",
        "Liquidity",
        "Liquidity Heatmap / Orderbook",
        -1,
        1,
        {
            "Liquidity Above": 100.0,
            "Liquidity Below": 0.0,
            "Balanced": 50.0,
            "Stacked Above (Thick)": 0.0,
            "Stacked Below (Thick)": 100.0,
        },
    ),
    (
        "market_context.liq_4h",
        "Liquidity",
        "Liquidaciones 4H",
        -1,
        1,
        {"Longs Dominated": 100.0, "Shorts Dominated": 0.0, "Balanced": 50.0},
    ),
    (
        "market_context.liq_24h",
        "Liquidity",
        "Liquidaciones 24H",
        -1,
        1,
        {"Longs Dominated": 100.0, "Shorts Dominated": 0.0, "Balanced": 50.0},
    ),
    (
        "market_context.struct_liq",
        "Liquidity",
        "Structural Liquidity",
        -1,
        1,
        {
            "Above DO (Clear)": 100.0,
            "Below DO (Clear)": 0.0,
            "Near PDH from Below": 0.0,
            "Near PDL from Above": 100.0,
            "Swept PDH": 100.0,
            "Swept PDL": 0.0,
        },
    ),
    (
        "market_context.htf_zone",
        "Liquidity",
        "HTF Zone",
        -1,
        1,
        {
            "At HTF Support": 100.0,
            "At HTF Resistance": 0.0,
            "Clear Space (No Level Nearby)": 50.0,
            "Inside Value Area": 50.0,
        },
    ),
    (
        "market_context.session",
        "Execution Context",
        "Trading Session",
        -2,
        2,
        {
            "London-NY Overlap": 100.0,
            "New York": 75.0,
            "London": 75.0,
            "Asia": 25.0,
            "Off-Hours": 0.0,
        },
    ),
    (
        "market_context.session_swing",
        "Execution Context",
        "Trading Session (Swing)",
        -2,
        2,
        {
            "London-NY Overlap": 50.0,
            "New York": 50.0,
            "London": 50.0,
            "Asia": 50.0,
            "Off-Hours": 50.0,
        },
    ),
    (
        "market_context.vwap",
        "Execution Context",
        "VWAP",
        -2,
        2,
        {"Above VWAP": 100.0, "Below VWAP": 0.0, "At VWAP": 50.0},
    ),
    (
        "market_context.vwap_swing",
        "Execution Context",
        "VWAP (Swing)",
        -2,
        2,
        {"Above VWAP": 50.0, "Below VWAP": 50.0, "At VWAP": 50.0},
    ),
    (
        "market_context.vpoc",
        "Execution Context",
        "VPOC",
        -1,
        1,
        {"Above VPOC": 100.0, "Below VPOC": 0.0, "At VPOC": 50.0},
    ),
    (
        "market_context.vpoc_swing",
        "Execution Context",
        "VPOC (Swing)",
        -1,
        1,
        {"Above VPOC": 50.0, "Below VPOC": 50.0, "At VPOC": 50.0},
    ),
    ("market_context.confluence", "Confluence", "Execution Confluence Score", -17, 7, None),
]

# The 11 real fields whose category_map genuinely differs between the
# Excel's "No-Swing" (Day Trade + Breakout) and "Swing" branches -- same
# real fields as BIAS_CRITERIA's profile-varying set (Section 4.1 of
# PROPUESTA_DATOS_BIAS_ENGINE.md), seeded above as two criterion rows
# each (`market_context.<field>` / `market_context.<field>_swing`).
# `_split_profile_varying_weights` below derives each row's weight from
# the SAME already-verified per-profile value in MARKET_CONTEXT_WEIGHTS
# -- no new weight data, only which row each existing weight attaches to.
MARKET_CONTEXT_PROFILE_VARYING_FIELDS = {
    "dxy",
    "spy",
    "etf_flow",
    "btc_struct",
    "daily_trend",
    "weekly_trend",
    "ema200",
    "fear_greed",
    "session",
    "vwap",
    "vpoc",
}

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


def _split_profile_varying_weights(
    weights: dict[str, dict[str, float]],
    varying_fields: set[str],
) -> dict[str, dict[str, float]]:
    """For each of `MARKET_CONTEXT_PROFILE_VARYING_FIELDS`, moves the
    `swing_trading` entry from `market_context.<field>`'s weight dict into
    a new `market_context.<field>_swing` entry — deriving both criterion
    rows' weights from the one already-verified per-profile value already
    in `MARKET_CONTEXT_WEIGHTS`, rather than duplicating weight data by
    hand (Sprint 3.2 correction; see `MARKET_CONTEXT_CRITERIA`'s
    docstring comment)."""
    split: dict[str, dict[str, float]] = {}
    for criterion_id, per_profile in weights.items():
        field = criterion_id.removeprefix("market_context.")
        if field not in varying_fields:
            split[criterion_id] = dict(per_profile)
            continue
        remaining = dict(per_profile)
        swing_weight = remaining.pop("swing_trading")
        split[criterion_id] = remaining
        split[f"{criterion_id}_swing"] = {"swing_trading": swing_weight}
    return split


# --- Bias Engine data (Sprint 3.2) --------------------------------------
#
# Extracted from `legacy/Trading Journal v2.0 Stable.xlsx`, CHECKLIST
# sheet, "04 · BIAS ENGINE" section (the 35 real GROSS_SCORE inputs,
# rows E10-E46 and E76-E83) — see this module's docstring for the six
# approved simplifications and `PROPUESTA_DATOS_BIAS_ENGINE.md` for the
# full derivation. `category` mirrors the Excel's own four section names
# (Primary/Secondary/Confirmation/Execution), not an invented taxonomy.
#
# No real per-criterion weight table exists for Bias — every criterion
# gets the same weight in every profile it applies to.
BIAS_WEIGHT = 1 / 35

DAY_AND_SCALPING = ("day_trading", "scalping")
SWING_ONLY = ("swing_trading",)
ALL_PROFILES = ("day_trading", "swing_trading", "scalping")

# (id, name, source_field, category, category_map, applicable_profiles)
BIAS_CRITERIA: list[tuple[str, str, str, str, dict[str, float], tuple[str, ...]]] = [
    # --- Primary (7 real fields; DXY/SPY/BTC Structure/Daily/Weekly
    # Trend/EMA200 vary Day-or-Breakout vs Swing; HTF Alignment doesn't) ---
    (
        "bias.dxy",
        "DXY — Dollar Index",
        "dxy",
        "Primary",
        {"Strong Bullish": -3, "Bullish": -1, "Neutral": 0, "Bearish": 1, "Strong Bearish": 2},
        DAY_AND_SCALPING,
    ),
    (
        "bias.dxy_swing",
        "DXY — Dollar Index (Swing)",
        "dxy",
        "Primary",
        {"Strong Bullish": -4, "Bullish": -2, "Neutral": 0, "Bearish": 2, "Strong Bearish": 4},
        SWING_ONLY,
    ),
    (
        "bias.spy",
        "SPY / TradFi",
        "spy",
        "Primary",
        {"Strong Uptrend": 2, "Uptrend": 1, "Range": 0, "Downtrend": -1, "Panic Selloff": -3},
        DAY_AND_SCALPING,
    ),
    (
        "bias.spy_swing",
        "SPY / TradFi (Swing)",
        "spy",
        "Primary",
        {"Strong Uptrend": 3, "Uptrend": 2, "Range": 0, "Downtrend": -2, "Panic Selloff": -4},
        SWING_ONLY,
    ),
    (
        "bias.btc_struct",
        "BTC Market Structure",
        "btc_struct",
        "Primary",
        {
            "Bullish Trend": 3,
            "Bearish Trend": -3,
            "Range": 0,
            "Accumulation": 1,
            "Distribution": -1,
        },
        DAY_AND_SCALPING,
    ),
    (
        "bias.btc_struct_swing",
        "BTC Market Structure (Swing)",
        "btc_struct",
        "Primary",
        {
            "Bullish Trend": 4,
            "Bearish Trend": -4,
            "Range": -1,
            "Accumulation": 2,
            "Distribution": -2,
        },
        SWING_ONLY,
    ),
    (
        "bias.daily_trend",
        "Daily Trend",
        "daily_trend",
        "Primary",
        {"Bullish": 2, "Bearish": -2, "Neutral/Range": 0},
        DAY_AND_SCALPING,
    ),
    (
        "bias.daily_trend_swing",
        "Daily Trend (Swing)",
        "daily_trend",
        "Primary",
        {"Bullish": 3, "Bearish": -3, "Neutral/Range": 0},
        SWING_ONLY,
    ),
    (
        "bias.weekly_trend",
        "Weekly Trend",
        "weekly_trend",
        "Primary",
        {"Bullish": 1, "Bearish": -1, "Neutral/Range": 0},
        DAY_AND_SCALPING,
    ),
    (
        "bias.weekly_trend_swing",
        "Weekly Trend (Swing)",
        "weekly_trend",
        "Primary",
        {"Bullish": 3, "Bearish": -3, "Neutral/Range": 0},
        SWING_ONLY,
    ),
    (
        "bias.ema200",
        "EMA 200",
        "ema200",
        "Primary",
        {"Above": 2, "Below": -2, "Testing from Above": 1, "Testing from Below": -1},
        DAY_AND_SCALPING,
    ),
    (
        "bias.ema200_swing",
        "EMA 200 (Swing)",
        "ema200",
        "Primary",
        {"Above": 3, "Below": -3, "Testing from Above": 2, "Testing from Below": -2},
        SWING_ONLY,
    ),
    (
        "bias.htf_align",
        "HTF Alignment",
        "htf_align",
        "Primary",
        {"Full Alignment": 2, "Moderate Alignment": 1, "Partial Conflict": -1, "Full Conflict": -3},
        ALL_PROFILES,
    ),
    # --- Secondary (7 real fields; ETF Flow/Fear & Greed vary; the rest
    # don't. BTC Dominance is direction-dependent in the Excel -- the
    # "trade is Long" branch is used uniformly, per your approved
    # decision #2.) ---
    (
        "bias.ema20",
        "EMA 20",
        "ema20",
        "Secondary",
        {"Price Above": 1, "Price Below": -1, "Testing from Above": 0, "Testing from Below": 0},
        ALL_PROFILES,
    ),
    (
        "bias.ema50",
        "EMA 50",
        "ema50",
        "Secondary",
        {"Above": 2, "Below": -2, "Testing from Above": 1, "Testing from Below": -1},
        ALL_PROFILES,
    ),
    (
        "bias.adx",
        "ADX / Fuerza de Tendencia",
        "adx",
        "Secondary",
        {
            "Range (<20)": -2,
            "Emerging Trend (20-25)": 0,
            "Healthy Trend (25-40)": 2,
            "Mature Trend (40-55)": 1,
            "Exhausted Trend (>55)": -1,
        },
        ALL_PROFILES,
    ),
    (
        "bias.btc_dom",
        "BTC Dominance",
        "btc_dom",
        "Secondary",
        {"Rising": 1, "Falling": 0, "Neutral": 0},
        ALL_PROFILES,
    ),
    (
        "bias.volume",
        "Volumen",
        "volume",
        "Secondary",
        {"Very High": 2, "High": 1, "Average": 0, "Low": -1, "Very Low": -2},
        ALL_PROFILES,
    ),
    (
        "bias.etf_flow",
        "ETF Flow (BTC Spot)",
        "etf_flow",
        "Secondary",
        {
            "Strong Inflows": 2,
            "Mild Inflows": 1,
            "Neutral": 0,
            "Mild Outflows": -1,
            "Strong Outflows": -2,
        },
        DAY_AND_SCALPING,
    ),
    (
        "bias.etf_flow_swing",
        "ETF Flow (BTC Spot) (Swing)",
        "etf_flow",
        "Secondary",
        {
            "Strong Inflows": 3,
            "Mild Inflows": 1,
            "Neutral": 0,
            "Mild Outflows": -1,
            "Strong Outflows": -3,
        },
        SWING_ONLY,
    ),
    (
        "bias.fear_greed",
        "Fear & Greed Index",
        "fear_greed",
        "Secondary",
        {
            "Extreme Fear (0-25)": 1,
            "Fear (26-45)": 1,
            "Neutral (46-55)": 0,
            "Greed (56-75)": -1,
            "Extreme Greed (76-100)": -2,
        },
        DAY_AND_SCALPING,
    ),
    (
        "bias.fear_greed_swing",
        "Fear & Greed Index (Swing)",
        "fear_greed",
        "Secondary",
        {
            "Extreme Fear (0-25)": 3,
            "Fear (26-45)": 2,
            "Neutral (46-55)": 0,
            "Greed (56-75)": -1,
            "Extreme Greed (76-100)": -3,
        },
        SWING_ONLY,
    ),
    # --- Confirmation (14 real fields; VWAP/VPOC/Session vary -- and are
    # explicitly 0 in the Swing branch, "not relevant for Swing Trading"
    # in the real Excel; Liq4H/Liq24H are direction-dependent, "trade is
    # Long" branch used uniformly per decision #2; ATR branches on
    # Breakout in the real Excel, an axis with no scoring_profile
    # equivalent -- the "No-Breakout" branch is used uniformly per
    # decision #3.) ---
    (
        "bias.htf_zone",
        "HTF Zone",
        "htf_zone",
        "Confirmation",
        {
            "At HTF Support": 1,
            "At HTF Resistance": -1,
            "Clear Space (No Level Nearby)": 0,
            "Inside Value Area": 0,
        },
        ALL_PROFILES,
    ),
    (
        "bias.vwap",
        "VWAP",
        "vwap",
        "Confirmation",
        {"Above VWAP": 2, "Below VWAP": -2, "At VWAP": 0},
        DAY_AND_SCALPING,
    ),
    (
        "bias.vwap_swing",
        "VWAP (Swing)",
        "vwap",
        "Confirmation",
        {"Above VWAP": 0, "Below VWAP": 0, "At VWAP": 0},
        SWING_ONLY,
    ),
    (
        "bias.vpoc",
        "VPOC",
        "vpoc",
        "Confirmation",
        {"Above VPOC": 1, "Below VPOC": -1, "At VPOC": 0},
        DAY_AND_SCALPING,
    ),
    (
        "bias.vpoc_swing",
        "VPOC (Swing)",
        "vpoc",
        "Confirmation",
        {"Above VPOC": 0, "Below VPOC": 0, "At VPOC": 0},
        SWING_ONLY,
    ),
    (
        "bias.cvd_delta",
        "CVD / Delta",
        "cvd_delta",
        "Confirmation",
        {
            "Bullish Confirmation": 1,
            "Bearish Confirmation": -1,
            "Bullish Divergence": 2,
            "Bearish Divergence": -2,
            "Neutral/No Signal": 0,
        },
        ALL_PROFILES,
    ),
    (
        "bias.open_interest",
        "Open Interest",
        "open_interest",
        "Confirmation",
        {
            "Rising + Price Up (Trend)": 2,
            "Rising + Price Down (Short Squeeze Risk)": -2,
            "Falling + Price Up (Short Squeeze)": 1,
            "Falling + Price Down (Long Liquidation)": -2,
            "Stable/Neutral": 0,
        },
        ALL_PROFILES,
    ),
    (
        "bias.funding",
        "Funding Rate",
        "funding",
        "Confirmation",
        {
            "Overheated Longs (>+0.05%)": -2,
            "Slightly Bullish (+0.01% to +0.05%)": 1,
            "Neutral (-0.01% to +0.01%)": 0,
            "Slightly Bearish (-0.05% to -0.01%)": 0,
            "Overheated Shorts (<-0.05%)": 2,
        },
        ALL_PROFILES,
    ),
    (
        "bias.ls_ratio",
        "Long/Short Ratio",
        "ls_ratio",
        "Confirmation",
        {
            "Crowded Longs (>65%)": -1,
            "Mild Long Bias (55-65%)": 0,
            "Balanced (45-55%)": 0,
            "Mild Short Bias (35-45%)": 0,
            "Crowded Shorts (<35%)": 1,
        },
        ALL_PROFILES,
    ),
    (
        "bias.liq_heatmap",
        "Liquidity Heatmap / Orderbook",
        "liq_heatmap",
        "Confirmation",
        {
            "Liquidity Above": 1,
            "Liquidity Below": -1,
            "Balanced": 0,
            "Stacked Above (Thick)": -1,
            "Stacked Below (Thick)": 1,
        },
        ALL_PROFILES,
    ),
    (
        "bias.liq_4h",
        "Liquidations 4H",
        "liq_4h",
        "Confirmation",
        {"Longs Dominated": 1, "Shorts Dominated": -1, "Balanced": 0},
        ALL_PROFILES,
    ),
    (
        "bias.liq_24h",
        "Liquidations 24H",
        "liq_24h",
        "Confirmation",
        {"Longs Dominated": 1, "Shorts Dominated": -1, "Balanced": 0},
        ALL_PROFILES,
    ),
    (
        "bias.session",
        "Trading Session",
        "session",
        "Confirmation",
        {"London-NY Overlap": 2, "New York": 1, "London": 1, "Asia": -1, "Off-Hours": -2},
        DAY_AND_SCALPING,
    ),
    (
        "bias.session_swing",
        "Trading Session (Swing)",
        "session",
        "Confirmation",
        {"London-NY Overlap": 0, "New York": 0, "London": 0, "Asia": 0, "Off-Hours": 0},
        SWING_ONLY,
    ),
    (
        "bias.atr",
        "ATR / Volatilidad",
        "atr",
        "Confirmation",
        {"Compression / Squeeze": 1, "Normal": 0, "Expansion": 0, "Extreme / High": -1},
        ALL_PROFILES,
    ),
    (
        "bias.ssr",
        "Stablecoin Supply Ratio",
        "ssr",
        "Confirmation",
        {"SSR Low (High Buy Power)": 1, "SSR Neutral": 0, "SSR High (Low Buy Power)": -1},
        ALL_PROFILES,
    ),
    (
        "bias.struct_liq",
        "Structural Liquidity",
        "struct_liq",
        "Confirmation",
        {
            "Above DO (Clear)": 1,
            "Below DO (Clear)": -1,
            "Near PDH from Below": -1,
            "Near PDL from Above": 1,
            "Swept PDH": 1,
            "Swept PDL": -1,
        },
        ALL_PROFILES,
    ),
    # --- Execution (7 real fields, exclusive to Bias -- new source_fields,
    # no overlap with any previously-seeded criterion. None vary by
    # profile in the real Excel.) ---
    (
        "bias.setup_type",
        "Setup Type",
        "setup_type",
        "Execution",
        {"Trend Continuation": 1, "Reversal": -1, "Range Trade": 0, "Breakout": 1, "Retest": 1},
        ALL_PROFILES,
    ),
    (
        "bias.ltf_confirmation",
        "LTF Confirmation",
        "ltf_confirmation",
        "Execution",
        {"Yes": 1, "Partial": 0, "No": -2},
        ALL_PROFILES,
    ),
    (
        "bias.correlation",
        "BTC / Asset Correlation",
        "correlation",
        "Execution",
        {
            "Aligned with Market": 1,
            "Diverging (Stronger)": 2,
            "Diverging (Weaker)": -1,
            "Inversely Correlated": -2,
        },
        ALL_PROFILES,
    ),
    (
        "bias.invalidation",
        "Clear Invalidation Defined",
        "invalidation",
        "Execution",
        {"Yes": 1, "No": -2},
        ALL_PROFILES,
    ),
    (
        "bias.risk_reward",
        "R:R Minimum 1:2",
        "risk_reward",
        "Execution",
        {"Yes": 1, "No": -3},
        ALL_PROFILES,
    ),
    (
        "bias.entry_zone",
        "Entry in Pre-Marked Zone",
        "entry_zone",
        "Execution",
        {"Yes": 1, "No": -2},
        ALL_PROFILES,
    ),
    (
        "bias.emotional_state",
        "Emotional / Mental State",
        "emotional_state",
        "Execution",
        {"Calm": 0, "Slightly Emotional": -1, "Emotional": -3, "Revenge Trading": -5},
        ALL_PROFILES,
    ),
]


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


async def _seed_bias_criteria(
    criterion_use_case: CreateScoringCriterionUseCase,
) -> dict[str, tuple[str, ...]]:
    """Creates each of the 46 Bias criterion rows (skipping ones that
    already exist) and returns {criterion_id: applicable_profiles} — every
    row gets the same `BIAS_WEIGHT`, but only in the profiles it applies
    to (see BIAS_CRITERIA's `DAY_AND_SCALPING` / `SWING_ONLY` /
    `ALL_PROFILES` tags). `min_value`/`max_value` are derived from the
    real category_map's own values rather than hardcoded, since Bias's
    signed range differs criterion by criterion."""
    applicable_profiles: dict[str, tuple[str, ...]] = {}
    for criterion_id, name, source_field, category, category_map, profiles in BIAS_CRITERIA:
        try:
            await criterion_use_case.execute(
                id=criterion_id,
                engine_type_code="bias",
                name=name,
                source_field=source_field,
                min_value=min(category_map.values()),
                max_value=max(category_map.values()),
                category=category,
                category_map=category_map,
            )
            print(f"  created criterion: {criterion_id}")
        except ConflictError:
            print(f"  already exists, skipping: {criterion_id}")
        applicable_profiles[criterion_id] = profiles
    return applicable_profiles


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
        for (
            criterion_id,
            category,
            name,
            min_value,
            max_value,
            category_map,
        ) in MARKET_CONTEXT_CRITERIA:
            try:
                await criterion_use_case.execute(
                    id=criterion_id,
                    engine_type_code="market_context",
                    name=name,
                    # "_swing" rows share the same real source_field as
                    # their non-swing counterpart (Sprint 3.2 fan-out) --
                    # strip that suffix from the id, never from the field.
                    source_field=criterion_id.removeprefix("market_context.").removesuffix(
                        "_swing"
                    ),
                    min_value=min_value,
                    max_value=max_value,
                    category=category,
                    category_map=category_map,
                )
                print(f"  created criterion: {criterion_id}")
            except ConflictError:
                print(f"  already exists, skipping: {criterion_id}")

        print("Seeding Bias criteria...")
        bias_applicable_profiles = await _seed_bias_criteria(criterion_use_case)
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
        market_context_weights = _split_profile_varying_weights(
            MARKET_CONTEXT_WEIGHTS, MARKET_CONTEXT_PROFILE_VARYING_FIELDS
        )
        for criterion_id, per_profile in market_context_weights.items():
            for profile_code, weight in per_profile.items():
                await weight_use_case.execute(draft.id, criterion_id, profile_code, weight)

        print(
            "Applying Bias weights (equal weight, BIAS_WEIGHT=1/35, only in each "
            "criterion's applicable profiles)..."
        )
        for criterion_id, profiles in bias_applicable_profiles.items():
            for profile_code in profiles:
                await weight_use_case.execute(draft.id, criterion_id, profile_code, BIAS_WEIGHT)
        await session.commit()

        print(f"Publishing '{version_label}'...")
        publish_use_case = PublishScoringConfigurationVersionUseCase(
            version_repository, weight_repository, criterion_repository, dispatcher, session
        )
        published = await publish_use_case.execute(draft.id)
        await session.commit()

        print(f"Done. '{published.version_label}' is now published ({published.id}).")


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
