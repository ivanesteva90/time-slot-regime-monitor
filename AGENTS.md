# AGENTS.md

## Project
Research and execution framework for SPX iron condor strategy analysis, with emphasis on capital preservation, adaptive sizing, and schedule/weekday regime detection. Source data lives in `data/` (dashboard) and may also arrive in `BTM/` subfolders per symbol (`rut/`, `spx/`, `xsp`). All analysis must ingest whatever CSVs the user uploads.

The main goal is **not** to maximize raw return. The main goal is to grow safely without blowing up the account.

## Core Strategy Context
- Strategy focus: “agresivo” SPX iron condor with time-based entry model.
- Reference entry time discussed: 11:15 (about 60 sessions).
- Reference results discussed (1 contract): total ≈ 3853; win rate ≈ 83.3%; avg win ≈ 141.22; avg loss ≈ -320.80; max DD ≈ 670.80.
- Reference results (2 contracts): total ≈ 7706; win rate ≈ 83.3%; avg win ≈ 282.44; avg loss ≈ -641.60; max DD ≈ 1341.60.

Interpretation: high win rate, losses larger than wins → sizing discipline is critical. Do **not** treat the system as invincible.

## Primary Objective
Preserve capital first. Scale only when equity and drawdown buffer justify it.

## Non-Negotiable Risk Philosophy
1. Survival > growth.
2. Avoid oversizing.
3. Assume live drawdown can exceed backtest drawdown.
4. Prefer robust rules over overfit optimization.
5. Do not chase the latest winning schedule without evidence.

## Current Position Sizing Rules
### Base ladder
- Stay at 1 contract until account equity reaches **4000**.
- At 4000, allow **2** contracts.
- If equity falls below **3300** after scaling, revert to **1** contract.

### Daily protection
- Max 1 trade per day.
- After 1 full loss, stop for the day.
- If red days cluster, cut risk and review behavior.

## Weekday Adaptive Sizing Rules (working model)
- Stronger: Monday, Thursday, Friday → 2 contracts (if equity allows).
- Weaker: Tuesday, Wednesday → 1 contract.
- This is a hypothesis; revalidate continuously. Do not hardcode as eternal truth.

## Schedule / Time Regime Philosophy
Entry-time edge moves over time; edge is **not** stationary. Maintain rolling windows:
- Short: recent 3–4 weeks
- Medium: 8–12 weeks
- Long/baseline: broader history
Rank schedules using multiple metrics, not just profit.

## Metrics to Use When Comparing Schedules
- total profit, trade count, win rate, avg win, avg loss, expectancy
- profit factor
- max drawdown; drawdown/profit ratio
- longest losing streak
- weekday stability
- monthly stability
- rolling degradation/improvement

Do **not** select a schedule only on total profit.

## Anti-Overfitting Rules
Penalize or reject schedules that:
- rely on tiny samples
- have unstable weekday behavior
- show high profit with ugly drawdown
- recently collapsed versus their baseline
- depend on one month or one cluster

## Desired Outputs From Codex
Build modules that:
1. **Data ingestion**: load CSVs from `data/` or user-provided folders, normalize date/time, derive weekday/month/regime windows.
2. **Metrics engine**: compute all key metrics; compare 1 vs 2 contracts; estimate survivability.
3. **Schedule ranking**: weighted rankings, labels follow/watch/replace; use rolling windows.
4. **Weekday adaptation**: test fixed 1, fixed 2, and mixed sizing (Mon/Thu/Fri = 2; Tue/Wed = 1); report profit, drawdown, risk-adjusted profile.
5. **Equity ladder**: simulate equity with 4000→2 contracts, 3300→back to 1; show equity curve and drawdown.
6. **Reporting**: concise tables + simple charts; monthly and weekday summaries; recommendation labels (GREEN / YELLOW / RED).

## Decision Labels
- GREEN = acceptable and robust
- YELLOW = promising but fragile / needs monitoring
- RED = too risky or unstable

## Coding Preferences
- Python + pandas; matplotlib for charts.
- Modular functions; clean naming; reproducible; only useful comments.
- Prefer robustness over fancy complexity; flag possible overfitting.

## Validation Requirements
Whenever logic changes:
- sanity check contract scaling math
- verify weekday labels
- verify rolling windows
- ensure no duplicated trades
- recheck drawdown logic

## Communication Style
- Be practical; numbers first; clear conclusions.
- Separate facts vs hypotheses; warn explicitly about overfitting.

## Important Strategic Conclusions (agreed)
- Start with 1 contract for defense.
- Scale to 2 contracts around 4000 equity; revert below 3300.
- Mixed weekday sizing likely better than 2 every day.
- Entry-time edge rotates; selection must stay adaptive.

## Extra: Operating Principle
“Do not chase the schedule that makes the most money; chase the schedule and sizing that keeps the account alive while it grows.”
