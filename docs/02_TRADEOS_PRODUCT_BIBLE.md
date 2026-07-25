# TRADEOS_PRODUCT_BIBLE.md

**Document Status:** Canonical — supersedes `TradeOS_PRODUCT.docx`. Approved as the permanent foundation for all future technical documentation.
**Version:** 2.1
**Last Updated:** 2026-07-24
**Supersedes:** `TradeOS_PRODUCT.docx` (v1.0, 2026-07-04)
**Archives:** `EVALUATION_ENGINE_SPECIFICATION.docx` — the 5-dimension / 1–5 scale / penalty-first model it describes is **not** the TradeOS Evaluation Engine. It is retained only as historical record of a discarded design.
**Primary source of truth for all business logic:** `Trading_Journal_v2_0_Stable.xlsx`

This document is the highest-level product definition for TradeOS. Every future technical document (Domain Model, API specifications, database schemas, UI specifications) must be consistent with what is written here. Where a conflict arises between a future document and this one, this one wins unless it is explicitly revised.

---

## 0. What Changed From v1.0 of This Document

`TradeOS_PRODUCT.docx` was reviewed (`TradeOS_DESIGN_REVIEW.docx`) and found to have a critical, unresolved gap: its Score Engine section was vague, and a separate specification document (`EVALUATION_ENGINE_SPECIFICATION.docx`) was written later to fill that gap — but it invented a **different model** (five dimensions inside one composite score, 1–5 scale, penalty-first) than the one that was actually built and verified in the Excel workbook (five **independent** engines, 0–100 scale, additive weighted scoring).

A full audit (`PROJECT_AUDIT.md`) surfaced this contradiction. It has now been resolved by explicit decision:

> **The Excel Evaluation Engine is the official and definitive version of TradeOS. `EVALUATION_ENGINE_SPECIFICATION.docx` is obsolete and archived.**

Section 8 of this document is the authoritative replacement. Vision, mission, philosophy, personas, and principles carried over from v1.0 because they are independent of the scoring model — they did not need to change, only the scoring section did.

Version 2.1 (this revision) adds three sections v2.0 identified as gaps but did not yet fill — Product Principles, Non-Functional Requirements, and Future Vision — and splits the "Configuration" module into two distinct modules (business configuration vs. user preferences). See the Document Control table (Section 16) for the full change log.

---

## 1. Vision

### 1.1 What TradeOS Is

TradeOS is a complete operating system for discretionary traders — a unified, data-driven platform that helps traders improve through structured journaling, systematic analysis, and evidence-based decision-making.

Unlike a conventional trading journal that merely logs entries and exits, TradeOS treats trading as a professional discipline requiring the same rigor as any high-performance craft. It captures data, enforces process, measures execution quality independently of financial outcome, surfaces insight, and builds a personal knowledge base that compounds over time.

### 1.2 The Problem It Solves

Discretionary trading is one of the few professional activities where practitioners routinely operate without systematic feedback loops. Most traders:

- Lack structured data about their own behavior, decisions, and outcomes
- Cannot objectively measure their edge, consistency, or execution quality
- Repeat the same mistakes because there is no systematic mechanism for identifying patterns in failure
- Make emotional decisions because they lack a predefined process to fall back on
- Lose institutional knowledge over time because insight is scattered across notebooks, spreadsheets, and memory

TradeOS provides a single source of truth for every aspect of a trader's operational life — from pre-trade checklists to post-trade analytics — turning raw trading activity into actionable intelligence.

### 1.3 Why It Exists

The gap between "trading" and "trading well" is not primarily about strategy — it is about process, discipline, and self-awareness. TradeOS exists to be the infrastructure that makes systematic self-improvement possible, purpose-built for the discretionary trader's actual workflow, rather than a spreadsheet stretched past its limits or a generic journaling app with no trading semantics.

### 1.4 Who It Is For

- Day traders and swing traders across equities, futures, forex, and crypto
- Traders seeking to professionalize a discretionary practice
- Traders who have outgrown spreadsheets and need a system that scales without becoming fragile

TradeOS is **not** for passive buy-and-hold investors, fully systematic/algorithmic traders needing execution infrastructure, or casual speculation treated as entertainment.

---

## 2. Mission

**To transform discretionary trading from an art based on intuition into a discipline based on data, process, and continuous improvement.**

Mission pillars:

1. **Democratize Trading Intelligence** — make analytical capabilities that professional trading firms use accessible to individual traders.
2. **Institutionalize Personal Process** — give every trader the ability to build, enforce, and refine their own trading framework with professional rigor.
3. **Build Compounding Knowledge** — every trade, mistake, and insight contributes to a growing personal database that becomes more valuable over time.
4. **Close the Feedback Loop** — reduce the time between action, analysis, and adjustment from months to minutes.
5. **Elevate the Craft** — treat trading as a legitimate professional pursuit worthy of serious tooling.

---

## 3. Product Philosophy

### 3.1 Data Over Emotions
The product is a mirror that shows the truth, not a cheerleader that validates biases. Every claim about "what works" must be backed by data recoverable from the system.

### 3.2 Process Over Outcome
This is the philosophical root of the Evaluation Engine (Section 8): a trader can execute a flawless process and lose money, or violate every rule and get lucky. TradeOS is built to measure and reward the former, independent of the latter.

### 3.3 Continuous Improvement
The system exists to shorten the distance between a mistake happening and a trader recognizing the pattern behind it.

### 3.4 Simplicity Through Depth
Complexity is allowed in the engine; it must never leak into daily use. A trader should be able to log a trade in under a minute, while the same data feeds a system capable of much deeper analysis when the trader chooses to look.

### 3.5 Objectivity as a Feature
Wherever a number can replace a feeling, it should. This is the entire reason the Evaluation Engine exists.

### 3.6 Scalability of Self
The system that works for a trader's first 50 trades must still work, unmodified in its core logic, at 20,000+ trades. This principle directly motivated moving off spreadsheets.

### 3.7 Privacy and Ownership
The trader's data is the trader's asset. **How this principle is implemented technically (encryption, hosting, data portability, whether TradeOS is ever offered to other users) is not yet defined — see Section 15, Open Foundational Questions.**

---

## 4. Target Users

### 4.1 User Segmentation

- **The Beginner Trader** — needs structure and enforced discipline more than advanced analytics. Benefits most from the Checklist and Playbook modules.
- **The Intermediate Discretionary Trader** — has a process but lacks objective measurement of how well they follow it. Benefits most from the Evaluation Engine and Statistics.
- **The Advanced Trader** — already has data; needs it consolidated, queryable, and compounding rather than scattered. Benefits most from Rolling Statistics and cross-dimension analytics.

### 4.2 Primary User Today

As of this document, TradeOS has exactly one confirmed user: its own builder, using it for personal trading journaling. **Whether TradeOS will ever be offered to other traders (and under what model) is an open question — see Section 15.** Nothing in this document should assume multi-user, multi-tenant, or commercial use until that question is resolved.

---

## 5. Problems TradeOS Solves

1. **Spreadsheets are fragile and unscalable.** The Excel implementation itself is proof: over the course of its construction, dozens of real bugs were found that were invisible until specifically audited — formulas that silently stopped calculating past a certain row, category names that drifted out of sync with dropdown lists, a scoring function that returned a different rounding result depending on which spreadsheet engine evaluated it. None of these threw a visible error. All of them produced a plausible, wrong number.
2. **Generic journaling apps lack trading semantics.** They have no concept of R-multiple, MFE/MAE, setup attribution, or execution scoring independent of outcome.
3. **Broker platforms provide data but no analytical framework.** They show what happened, not why it happened or whether it was executed well.
4. **There is no objective measure of execution quality.** Most tools conflate "good trade" with "profitable trade." TradeOS's Evaluation Engine exists specifically to separate these two things.
5. **Institutional knowledge is lost over time.** Insights live in a trader's memory or scattered notes rather than a structured, queryable system.

---

## 6. Product Goals

### 6.1 Primary Goals
1. Improve trader consistency by making process adherence visible and measurable.
2. Centralize all trading data in one structured system.
3. Measure execution quality independent of financial outcome.
4. Reduce emotionally-driven trading by surfacing patterns the trader cannot see in the moment.
5. Build a compounding personal trading database.
6. Enable genuine data-driven strategy refinement (which setups, sessions, and conditions actually produce edge).

### 6.2 Secondary Goals
- Reduce the operational overhead of journaling to the point where skipping it feels like the wrong choice, not the easy one.
- Make historical performance data reusable across every new analytical question the trader thinks to ask, without rebuilding it.

---

## 7. Product Principles

These are not slogans. Every future feature, architectural decision, and design tradeoff must be checked against this list before it ships. If a proposed feature violates one of these without a documented, explicit exception, it should not be built as proposed.

1. **The Trader Owns Their Data.** Data portability and ownership are not a feature to build later — they are a constraint every data model must satisfy from the start, whatever the eventual answer to the business-model question (Section 15) turns out to be.
2. **Process Over Outcome Is Non-Negotiable.** No feature may collapse execution quality and financial outcome into a single number. This is why the Evaluation Engine has five independent engines rather than one composite score (Section 8).
3. **Every Feature Must Earn Its Place.** A feature is justified by the problem it solves (Section 5), not by its novelty or by what competitors have. This is what keeps v1.0 scope from expanding indefinitely.
4. **The System Must Compound.** Every trade logged, every mistake tagged, and every score recorded must remain queryable and useful indefinitely — nothing is captured only for immediate display and then discarded.
5. **Friction Is a Feature When It Protects Process.** Removing a step that enforces discipline (e.g., requiring a checklist before logging a trade) in the name of "speed" is a regression, not an improvement, unless the trader has explicitly configured it otherwise.
6. **Context Must Be Preserved.** A trade is never just a price and an outcome — the reasoning, the screenshots, the pre-trade state, and the post-trade review are part of the permanent record, not disposable notes.
7. **Analytics Must Be Actionable.** Every chart or statistic must answer a specific, real question a trader would ask. Decorative visualization that doesn't change a decision does not belong in the product.
8. **The Product Grows With the User.** The same system must serve a beginner who needs enforced structure and an advanced trader who needs raw analytical depth, without maintaining two separate products.
9. **Performance Under Pressure.** The system must never be slow or unresponsive at the moment a trader needs to log a decision or check a rule — this is precisely when friction causes the discipline to break down.
10. **Transparency Builds Trust.** Every score the Evaluation Engine produces must be explainable down to its individual criteria and weights on demand (see the Rule Explorer concept in `TRADEOS_MASTER_ROADMAP.md`). A score a trader cannot audit is a score they will not trust.
11. **Integration Over Replacement.** Where reasonable, TradeOS should complement a trader's existing tools (charting platforms, brokers) rather than assume it must replace everything.
12. **Long-Term Thinking Guides Short-Term Decisions.** Architecture decisions are made for where the product is going (Section 14), not for the shortest path to a demo.
13. **Modularity.** Every major module (Section 9) must be independently maintainable and must communicate with every other module only through well-defined contracts — never by reaching directly into another module's internal data or logic. A module should be replaceable or rebuildable without requiring changes to the modules around it, provided its contract is honored.

---

## 8. The Evaluation Engine — Canonical Definition

**This section is the single most important part of this document.** It is the resolution of the central contradiction found in `PROJECT_AUDIT.md`, and it is binding on every future technical document.

### 8.1 What the Evaluation Engine Is

The Evaluation Engine is **one generic, configuration-driven scoring engine**, instantiated five independent times. It is not five dimensions rolled into a single composite score — it is five separate engines, each producing its own independent score, because each answers a genuinely different question about a trade:

| Engine | Question It Answers | Independent Of |
|---|---|---|
| **Confidence** | How good did this setup look *before* entry? | The trade's actual outcome |
| **Quality** | Did this trade follow the trader's own plan and rules? | The trade's P&L |
| **Execution** | How well was the trade executed tactically (timing, stop placement, exit)? | Whether the trade won or lost |
| **Market Context** | How clear/strong were market conditions, regardless of direction? | The Bias Index's direction |
| **Bias** | Which direction does the evidence point — bullish or bearish? | The other four engines |

This separation is deliberate and load-bearing: a losing trade can score A+ on Quality (the process was perfect; the market simply didn't cooperate), and a winning trade can score F (the trader got lucky despite violating every rule). Collapsing these into one number would destroy the exact insight the product exists to provide (see Section 3.2 and Principle 2 in Section 7).

### 8.2 Architecture Principles (all confirmed against the Excel implementation)

1. **Config-driven criteria.** Every scoring criterion — its name, its category, the field it reads, its expected numeric range, and (where relevant) a lookup table mapping categorical answers to numeric sub-scores — lives in configuration, not in code or formulas written per-criterion. Adding a new criterion must never require touching the aggregation logic.
2. **Criteria are separated from weights.** A criterion's definition (what it measures) and its weight (how much it counts) are two different tables, joined by a stable ID — never by row position. This is what allows the same criterion catalog to support multiple scoring profiles simultaneously without duplication.
3. **0–100 scoring, with letter grades as a derived display layer.** A+ (≥95), A (≥90), B (≥80), C (≥70), D (<70). Grades are computed from the score; they are never stored as an independent input.
4. **Two independent normalization strategies, never mixed within one engine:**
   - **Unsigned (measures strength/clarity):** the score reflects how strong or clear a signal is, regardless of direction. Used by Confidence, Quality, Execution, and Market Context.
   - **Signed (measures direction):** the score preserves sign, because the entire purpose is to indicate which way the evidence points. Used exclusively by Bias.
5. **Self-normalizing aggregation.** A score is the weighted sum of its active criteria's normalized values, divided by the **sum of active weights** — not by a fixed constant. This means disabling a criterion never requires manually rebalancing every other weight to keep the total at 1.0.
6. **Versionable configuration.** Every weight, threshold, and criterion catalog must be capable of having its history tracked — "what weights were in effect when this trade was scored" must be an answerable question, not lost information.
7. **Scoring profiles.** Weights can vary by trading profile (Day Trading, Swing Trading, Scalping) without duplicating the criteria catalog — a criterion is defined once and weighted differently per profile.
8. **Historical scores are snapshots, not live recalculations.** The score a trade received at the time it was logged is a historical fact and is stored as such. It is never silently recalculated against a later configuration change — that would rewrite history. A configuration change affects future trades and any explicit "recalculate historical trades" action, never past evaluations implicitly.

### 8.3 What This Replaces

`EVALUATION_ENGINE_SPECIFICATION.docx` described a single-engine, 5-dimension (Plan Adherence, Risk Management, Entry Quality, Exit Quality, Emotional Control), 1–5 scale, penalty-first model with a formal state machine and rule-versioning language. **None of this reflects the actual product.** That document is archived as historical record only. Any future technical document that needs the formal detail of the Evaluation Engine (exact criteria catalogs, exact default weights, worked calculation examples) should be written fresh against Section 8.2 of this document and the Excel `⚙️ CONFIG` sheet — not adapted from the archived specification.

---

## 9. Modules

Modules are named and scoped to match what actually exists in the Excel (`Trading_Journal_v2_0_Stable.xlsx`), confirmed by direct inspection in `PROJECT_AUDIT.md`, with two exceptions explained below.

| Module | Purpose | Excel Equivalent |
|---|---|---|
| **Dashboard** | At-a-glance operational awareness | `DASHBOARD` |
| **Trades** | Core data capture and management | `📒 Trades` |
| **Checklist** | Pre-trade context capture; feeds the Evaluation Engine | `CHECKLIST` |
| **Playbook** | Setup documentation and live performance attribution | `📘 PLAYBOOK` |
| **Evaluation Engine** | The five independent scoring engines (Section 8) | `⚙️ CONFIG` (weights/criteria) + score columns in `📒 Trades` |
| **Statistics** | Performance analytics by dimension (strategy, setup, session, time, direction) | `📊 Estadísticas`, `Stats por Estrategia/Set Up/Entry Trigger`, `⏱️ Stats por Tiempo`, `📈 EXPECTANCY` |
| **Rolling Statistics** | Configurable moving-window performance vs. all-time comparison | `📈 Rolling Statistics` |
| **Mistakes** | Error taxonomy, frequency, cost, and prioritized correction ranking | `🚫 Errores` |
| **Journal / Review** | Qualitative notes, weekly review | `📝 Revisión de Trades`, `WEEKLY REVIEW` |
| **Configuration** | Business configuration: Evaluation Engine weights, criteria, scoring profiles, and catalogs (setups, sessions, strategies, entry triggers, mistake tags) | `⚙️ CONFIG` |
| **Settings** | User preferences: theme, language, notification preferences, user profile, account | *No Excel equivalent — see note below* |

### 9.1 Why Configuration and Settings Are Two Separate Modules

These were combined as one "Settings" module in `TradeOS_PRODUCT.docx` v1.0. They are split here because they are different concerns with different audiences, different volatility, and different modularity contracts (Principle 13, Section 7):

- **Configuration** changes *how the business logic behaves* — a change here can alter every future trade's score. It must be versionable, auditable, and treated with the same care as the Evaluation Engine itself, because it effectively *is* the Evaluation Engine's input surface.
- **Settings** changes *how the product feels to one user* — theme, language, notification preferences. Changing these has zero effect on scoring or historical data. It carries no versioning requirement and no business-logic risk.

Conflating them (as v1.0 did) was flagged in `TradeOS_DESIGN_REVIEW.docx` as a real design smell (H3: "'Settings' Is Actually Three Different Modules Masquerading as One") — this split directly resolves that finding.

### 9.2 Settings Has No Excel Equivalent — This Is Expected, Not a Gap

The Excel has no concept of theme, language, or notification preferences because it is a single file used by one person, opened in one spreadsheet application. Settings is a module the web application needs that the Excel simply never had a reason to have. This does not violate the principle that the Excel is the source of truth for business logic — Settings contains no business logic to source.

### 9.3 Design Principles (carried over from v1.0, still valid)

- Logging a standard trade should take well under a minute.
- Every statistic must answer a specific question — no decorative charts.
- The Checklist should feel like a safety harness, not a bureaucratic hurdle.
- A Playbook is a living document; performance data must be prominent enough to prevent a trader from clinging to a setup that no longer works.

---

## 10. Non-Functional Requirements

These describe qualities the system must have regardless of which feature is being built. Where a specific technical answer is still undecided, this section states the requirement at a principle level and points to the open question rather than inventing a specific number or standard.

### 10.1 Performance
The system must feel instantaneous for the operations a trader performs constantly — logging a trade, checking a checklist, viewing today's dashboard. This is a direct consequence of Principle 9 (Section 7). Analytical queries over the full trade history (Statistics, Rolling Statistics) may take longer than instant-feel operations, but must remain fast enough to be used in the moment, not treated as a "run overnight" report.

### 10.2 Scalability
The system must handle 20,000+ trades without degradation in the core logging and scoring path — this is the specific, named limitation that motivated moving off the Excel (Section 5.1) and is treated as a hard requirement, not an aspiration.

### 10.3 Security
Financial and behavioral trading data is sensitive. At minimum, data in transit must be encrypted, and access must be authenticated. **The full security posture (encryption at rest standard, key management, whether TradeOS staff can ever access user data, breach response process) is not yet defined — this is Open Question 3 in Section 15 and must be resolved before any multi-user or hosted-for-others deployment, not just before launch.**

### 10.4 Availability
For a single-user, personally-hosted or personally-used system, availability requirements are modest — the system should not lose data, but does not need enterprise-grade uptime guarantees. **This requirement changes materially if the business-model question (Open Question 2, Section 15) resolves toward offering TradeOS to other traders — that decision must trigger a revision of this section, not be absorbed silently.**

### 10.5 Accessibility
The web application should follow standard accessibility practice (keyboard navigability, sufficient color contrast, screen-reader-compatible markup) as a baseline, consistent with treating trading as a professional discipline worthy of professional tooling (Section 1.3). No specific compliance standard (e.g., WCAG level) has been chosen yet.

### 10.6 Observability
This is a direct, hard-won lesson from the Excel's construction (Section 5.1): **the system must never fail silently.** Every calculation that can fail must fail loudly (a visible error, a logged exception) rather than silently returning a plausible-looking wrong value — this was, repeatedly, the actual root cause of real bugs found during the Excel's development. Logging, error tracking, and automated tests over the Evaluation Engine specifically (Section 8) are non-negotiable, not nice-to-haves.

### 10.7 Maintainability
Directly enabled by Principle 13 (Modularity, Section 7): a well-defined contract between modules should mean a developer can understand and modify one module without reading or reasoning about the internals of the others. Configuration-driven design (Section 8.2) exists partly for this reason — extending the Evaluation Engine with a new criterion should be a configuration change, not a code change.

---

## 11. Out of Scope (Current Version)

Explicitly not part of the current product definition, reserved for a future version once the current foundation is stable and in daily real use:

- AI-powered coaching or natural-language insight generation
- Machine learning pattern discovery beyond simple two-variable cross-tabulation
- Automated broker/exchange integration
- Real-time market data
- Multi-account or multi-user / team features
- Mobile native applications
- Automated strategy backtesting

---

## 12. Future Vision

This section describes where TradeOS goes once the current foundation (Sections 8–11) is stable and in genuine daily use — not a commitment to build any of it now, and not a contradiction of Section 11's Out of Scope list, which it exists to elaborate on.

### 12.1 Near-Term: Consolidation
Before any new capability is added, the current foundation must be used in real daily trading long enough to accumulate a meaningful volume of real trade history. Every module described in Section 9 should be genuinely relied upon, not just built. This stage is a precondition for everything below — the historical lesson of this project (Section 5.1) is that building ahead of real usage is exactly how untested, unverified logic accumulates.

### 12.2 Intelligence Layer
Once real trade volume exists, the same Evaluation Engine architecture (Section 8) extends naturally into pattern discovery: automatically surfacing which combinations of setup, session, and market context conditions produce the strongest and weakest Expectancy — a bounded, two-variable version of this is explicitly in scope for early exploration; open-ended multivariate discovery is a later-stage capability.

### 12.3 AI Coaching Layer
A conversational layer that answers questions like "why did I lose on trade #45?" by querying the trader's own historical data — never by generating advice untethered from that trader's actual recorded evidence (this directly follows Principle 10, Transparency Builds Trust, in Section 7). This layer is explicitly downstream of the Intelligence Layer, not a replacement for it.

### 12.4 Ecosystem & Automation
Optional, later-stage integrations with brokers/exchanges for automated trade import, and richer reporting/export capabilities — approached under Principle 11 (Integration Over Replacement, Section 7): TradeOS augments a trader's existing broker relationship, it does not attempt to become one.

### 12.5 Long-Term Horizon
If — and only if — the business-model question (Section 15) resolves toward offering TradeOS to other traders, the long-term horizon includes multi-account support, team/manager dashboards, and the infrastructure (multi-tenancy, security posture per Section 10.3) that decision requires. This horizon is explicitly conditional, not assumed.

---

## 13. Success Criteria

**Carried over from v1.0, with an explicit caveat this document adds:** most of the following metrics are currently **unmeasurable** — the Excel contains only 2 real historical trades as of the last audit. These criteria describe what will be measured once real usage volume exists; they are not claims about current state.

- **User success:** measurable improvement in Confidence/Quality/Execution scores over time; measurable correlation between Evaluation Engine scores and profitability.
- **Product success:** the trader stops using the Excel for daily logging because the web application is strictly better for that purpose.
- **Technical success:** the system remains fast and correct at 20,000+ trades — the specific limitation the Excel cannot overcome.

---

## 14. Long-Term Roadmap Reference

Detailed version planning (v0.1 through v2.0+), milestones, and technology recommendations are maintained separately in `TRADEOS_MASTER_ROADMAP.md`, which was confirmed during audit to already be consistent with this document's model of the Evaluation Engine (Section 8). This Product Bible governs product intent; the Roadmap governs implementation sequencing. Where the two ever appear to disagree, this document wins, and the Roadmap should be revised to match.

---

## 15. Open Foundational Questions

These are carried forward unresolved from `PROJECT_AUDIT.md`, Section 7. This document does **not** answer them — they are listed here because a Product Bible is exactly the place future decisions on them should be recorded once made.

1. **Is TradeOS a time-boxed academic project or a long-term personal project with no fixed deadline?** This materially changes how ambitious any near-term scope should be.
2. **Is there a business model?** Free forever for personal use, or eventually offered to other traders under some pricing model? Unresolved, and it affects architecture decisions (multi-tenancy, data isolation) that should not be guessed at.
3. **What is the data privacy/security posture?** Encryption at rest, data portability guarantees, and whether anyone other than the trader will ever see this data are all undefined (see Section 10.3).
4. **Will "Pro" (full Excel-parity) trade entry or "Simple" entry be the default daily workflow?** Both exist as a concept; which one is primary is not yet decided.
5. **Does the Excel remain a permanent historical record, or does its data migrate fully into the application once built?**
6. **Does `Mistakes` remain free-text tags, or does it become a normalized, referentially-integrous catalog?**

---

## 16. Document Control

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-07-04 | Original `TradeOS_PRODUCT.docx` — Score Engine section vague, later found to conflict with a separately-written specification document. |
| 2.0 | 2026-07-24 | Renamed and restructured as `TRADEOS_PRODUCT_BIBLE.md`. Evaluation Engine section rewritten to match the Excel-confirmed canonical model. `EVALUATION_ENGINE_SPECIFICATION.docx` formally archived. Module names aligned to actual Excel sheets. Open questions from `PROJECT_AUDIT.md` carried forward explicitly rather than resolved by assumption. |
| 2.1 | 2026-07-24 | Approved as canonical. Added Product Principles (Section 7, including new Modularity principle), Non-Functional Requirements (Section 10), and Future Vision (Section 12). Split the combined "Configuration" module into two distinct modules — **Configuration** (business/scoring config) and **Settings** (user preferences) — per `TradeOS_DESIGN_REVIEW.docx` finding H3. |

**Status:** Frozen as the permanent foundation for all future technical documentation.
**Next document per the reconstruction plan in `PROJECT_AUDIT.md`:** `TRADEOS_DOMAIN_MODEL.md`.
