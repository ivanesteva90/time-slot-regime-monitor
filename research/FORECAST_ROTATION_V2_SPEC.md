# Forecast & Rotation V2 Spec

Status: proposed, not implemented yet  
Date: 2026-03-30

## 1. Objective

Redesign the current `forecast + KEEP/WATCH/ROTATE` stack so it behaves coherently under:

- a recent regime window centered on the last 3 months (`63` trading sessions),
- daily end-of-day updates from a future live backend,
- capital-preservation-first logic,
- strict no-leakage walk-forward validation.

The goal is not to predict exact P/L. The goal is to:

- estimate next-day and next-week edge more cleanly,
- reduce noisy rotations,
- make the system update reliably when a new confirmed daily close arrives,
- preserve interpretability.

## 2. Current V1 Weaknesses

The current V1 is useful, but it has structural issues that make it a weak long-term base for live updating.

### 2.1 Double counting inside the forecast pipeline

Today:

- `forecastScore` is built from long/medium/short windows.
- `KEEP/WATCH/ROTATE` depends on `forecastScore` plus `exhaustionScore`.
- `structureProbability()` uses `forecastScore`, `exhaustionScore`, `validation`, `ratio10to63`, `consistency`, and also a `labelBonus`.
- `decisionScore` then reuses `probability`, `confidence`, `forecastScore`, `exhaustionScore`, and `riskAdjustedEV`.

Effect:

- the same signal family affects ranking more than once,
- labels leak back into probability,
- rotations can become more reactive than they should be.

### 2.2 Rotation state is too relative

Current labels are mostly relative to the current dataset ranking percentile plus exhaustion. That is useful for UI, but weak for operational state changes.

What is missing:

- challenger pressure,
- hysteresis,
- confirmation across more than one close,
- explicit false-rotation control.

### 2.3 Live integration is not yet separated into confirmed vs provisional data

The future live flow needs a strict distinction between:

- confirmed end-of-day data, which can update history and validation,
- provisional intraday data, which can inform dashboards but must not contaminate backtests.

## 3. Operating Assumptions

### 3.1 Windows

Use trading sessions, not calendar months.

- Regime base: `63` sessions
- Momentum overlay: `21` and `10` sessions
- Calibration / stability layer: `126` and `252` sessions when available

Interpretation:

- `63` is the primary regime window
- `21` and `10` only accelerate or weaken the current regime
- `126/252` are not the main signal; they are calibration anchors and stability references

### 3.2 Data states

The model should treat data in two modes:

1. Confirmed close
- updates historical metrics
- updates walk-forward validation
- updates next-day and weekly forecast
- can trigger rotation state changes

2. Provisional intraday
- may update a preview layer
- must not change historical validation
- must not overwrite confirmed close history

### 3.3 Minimum history

For V2:

- forecast can still render with limited history if needed,
- but `next-day validation` should only be considered trustworthy after the minimum regime history is available.

Operational rule:

- below `63` confirmed dates: forecast is exploratory
- from `63+` confirmed dates: forecast is usable
- from `126+` confirmed dates: forecast is better calibrated

## 4. Model Layers

V2 should separate the stack into 4 explicit layers:

1. Regime score
2. Exhaustion pressure
3. Probability / EV forecast
4. Rotation pressure

These layers should be stored separately and displayed separately when useful.

## 5. Layer 1: Regime Score

Purpose:

- measure how healthy a slot is right now,
- using the recent regime first,
- without turning the result into a trade recommendation yet.

### 5.1 Inputs

Per slot, inside its dataset:

- `expectancy_63`
- `profit_factor_63`
- `win_rate_63`
- `drawdown_inverse_63`
- `consistency_63`
- `expectancy_21`
- `expectancy_10`
- `sample_strength_63`

Definitions:

- `drawdown_inverse_63`: a bounded inverse transform of drawdown burden
- `consistency_63`: percent of recent monthly / quarterly blocks with positive average
- `sample_strength_63`: capped sample adequacy factor

### 5.2 Normalization

Normalize each slot relative to the other slots in the same dataset using percentiles or bounded z-like transforms.

All components should end in `[0, 1]`.

### 5.3 Formula

```text
edge_63 =
  0.30 * pct(expectancy_63)
  + 0.20 * pct(profit_factor_63)
  + 0.15 * pct(win_rate_63)
  + 0.15 * pct(drawdown_inverse_63)
  + 0.10 * pct(consistency_63)
  + 0.10 * sample_strength_63
```

```text
momentum_21 =
  clamp01(0.5 + 0.5 * normalized_delta(expectancy_21 - expectancy_63))
```

```text
momentum_10 =
  clamp01(0.5 + 0.5 * normalized_delta(expectancy_10 - expectancy_21))
```

```text
regime_score =
  100 * clamp01(
    0.60 * edge_63
    + 0.25 * momentum_21
    + 0.15 * momentum_10
  )
```

Interpretation:

- `regime_score` is the main health score of the slot under the recent regime
- `21` and `10` can tilt the score, but they do not dominate it

## 6. Layer 2: Exhaustion Pressure

Purpose:

- detect deterioration pressure,
- separate “strong but tiring” from “structurally bad”.

### 6.1 Inputs

- `rank_drop_21_to_63`
- `ratio_drop_10_to_63`
- `block_fall_10`
- `validation_slip`
- `drawdown_acceleration`

Definitions:

- `rank_drop_21_to_63`: how much the slot loses rank in recent vs base window
- `ratio_drop_10_to_63`: weakness of short horizon versus base horizon
- `block_fall_10`: last 10 sessions versus previous 10 sessions
- `validation_slip`: deterioration in walk-forward health versus recent baseline
- `drawdown_acceleration`: recent drawdown burden versus base drawdown burden

### 6.2 Formula

```text
exhaustion_pressure =
  clamp01(
    0.30 * rank_drop_21_to_63
    + 0.25 * ratio_drop_10_to_63
    + 0.20 * block_fall_10
    + 0.15 * validation_slip
    + 0.10 * drawdown_acceleration
  )
```

```text
exhaustion_score = 100 * exhaustion_pressure
```

Interpretation:

- low exhaustion means current edge is still carrying
- high exhaustion means “do not trust the regime at face value”

## 7. Layer 3: Probability and EV Forecast

Purpose:

- estimate next-day positive probability and expected value,
- without feeding label decisions back into the forecast.

This is the main V2 change.

### 7.1 Core design rule

`KEEP/WATCH/ROTATE` must not enter the POP formula.

The probability model should depend on measurable features only.

### 7.2 Inputs

For a target day `t+1`:

- `p_slot_weekday_63`
- `p_slot_recent_21`
- `p_slot_all_63`
- `p_dataset_weekday_63`
- `validation_health`
- `regime_score`
- `exhaustion_pressure`
- `drawdown_pressure`
- `sample_penalty`

Definitions:

- `p_slot_weekday_63`: smoothed win probability of the slot on the same weekday, using recent confirmed history
- `p_slot_recent_21`: smoothed recent slot win probability
- `p_slot_all_63`: smoothed slot win probability regardless of weekday
- `p_dataset_weekday_63`: smoothed dataset-level weekday probability
- `validation_health`: walk-forward health in `[0, 1]`
- `drawdown_pressure`: bounded risk burden from recent drawdown profile
- `sample_penalty`: penalty when weekday / recent / slot samples are thin

### 7.3 Base probability blend

```text
p_base =
  0.40 * p_slot_weekday_63
  + 0.20 * p_slot_recent_21
  + 0.15 * p_slot_all_63
  + 0.15 * p_dataset_weekday_63
  + 0.10 * validation_health
```

### 7.4 Final POP formula

```text
POP_next =
  sigmoid(
    logit(clamp(p_base, 0.02, 0.98))
    + 0.35 * (regime_score / 100 - 0.5)
    - 0.55 * exhaustion_pressure
    - 0.40 * drawdown_pressure
    - 0.30 * sample_penalty
  )
```

Interpretation:

- `p_base` is the empirical probability spine
- `regime_score` nudges the forecast
- exhaustion, drawdown, and thin samples can pull the forecast down

This is cleaner than the current V1 because:

- no label bonus is injected into probability
- no direct double count of forecast + label + decision score

### 7.5 Avg win / avg loss hierarchy

Use hierarchical shrinkage instead of raw averages.

Priority chain for wins:

1. slot + same weekday
2. slot recent
3. dataset + same weekday
4. dataset all

Priority chain for losses:

1. slot + same weekday
2. slot recent
3. dataset + same weekday
4. dataset all

### 7.6 EV formula

```text
EV_next =
  POP_next * avg_win_shrunk
  - (1 - POP_next) * abs(avg_loss_shrunk)
```

### 7.7 Confidence

Confidence should be separate from probability.

```text
confidence =
  100 * clamp01(
    0.35 * sample_strength_weekday
    + 0.20 * sample_strength_recent
    + 0.20 * sample_strength_dataset_weekday
    + 0.15 * validation_health
    + 0.10 * stability_anchor
  )
```

Interpretation:

- high POP with low confidence is not the same as high POP with strong support

## 8. Layer 4: Rotation Pressure

Purpose:

- decide when a leader is still valid,
- when it should be watched,
- and when the model should actually rotate.

### 8.1 Core design rule

Rotation should be driven by challenger pressure plus leader deterioration, not by a single-day percentile ranking.

### 8.2 Leader / challenger objects

For each dataset and cutoff date:

- `leader`: current slot ranked first by forecast engine
- `challenger`: strongest alternative slot

### 8.3 Inputs

- `regime_advantage`
- `pop_advantage`
- `validation_advantage`
- `leader_exhaustion`
- `leader_validation_drop`

Definitions:

- `regime_advantage`: challenger regime score minus leader regime score
- `pop_advantage`: challenger POP minus leader POP
- `validation_advantage`: challenger validation health minus leader validation health
- `leader_exhaustion`: leader exhaustion pressure
- `leader_validation_drop`: leader recent walk-forward deterioration

### 8.4 Formula

```text
rotation_pressure =
  clamp01(
    0.35 * positive(regime_advantage)
    + 0.25 * positive(pop_advantage)
    + 0.20 * leader_exhaustion
    + 0.20 * leader_validation_drop
  )
```

### 8.5 State rules with hysteresis

```text
KEEP:
  rotation_pressure < 0.35
  and leader remains rank #1
```

```text
WATCH:
  0.35 <= rotation_pressure < 0.60
  or challenger beats leader on 1 confirmed close
  or leader regime_score drops >= 8 points vs recent baseline
```

```text
ROTATE:
  rotation_pressure >= 0.60 on 2 consecutive confirmed closes
  or challenger outranks leader on 3 of last 5 confirmed closes
     and challenger POP advantage >= 5 points
```

### 8.6 Promotion rule

Do not promote the challenger immediately on a single warning spike.

Promote challenger only when:

- `ROTATE` has been confirmed,
- challenger still leads on the latest confirmed close,
- challenger confidence is above the minimum operational floor.

### 8.7 De-escalation rule

To reduce flip-flop:

- `ROTATE -> WATCH` only after 2 confirmed closes below the rotate threshold
- `WATCH -> KEEP` only after 3 confirmed closes below the watch threshold while leader remains first

## 9. Weekly Horizon Logic

Once next-day forecasts are produced, the weekly horizon should aggregate them without changing the daily logic.

### 9.1 Daily candidate selection

For each target day:

- evaluate each dataset
- choose best slot within dataset
- compare winners across datasets
- keep top candidate and 2 alternatives

### 9.2 Weekly distribution

Use Monte Carlo or bootstrap over historical positive/negative pools, but only after daily POP and EV have been computed using the V2 model.

The weekly horizon should output:

- `P(week > 0)`
- `EV_week`
- scenario bands `10 / 50 / 90`
- candidate list by day

## 10. Live Data Integration

### 10.1 Recommended architecture

- `Python + FastAPI`
- daily worker / scheduler
- normalized persisted snapshots
- dashboard reads compact JSON or API payloads

### 10.2 Update cycle

At confirmed daily close:

1. fetch latest source data
2. normalize into project schema
3. append confirmed rows
4. rebuild:
   - datasets
   - ranking
   - walk-forward
   - regime / exhaustion
   - Weekly Outlook
   - Weekday Quality
   - mix suggested
5. write dashboard-ready output

### 10.3 Provisional intraday mode

Optional, later phase only.

Rules:

- intraday preview must be tagged `provisional`
- intraday preview must not alter historical validation
- intraday preview must not overwrite confirmed close results

## 11. Validation Protocol

Validation must remain walk-forward and strictly time-safe.

### 11.1 Core comparison

Compare:

- current V1
- proposed V2

using the same historical datasets.

### 11.2 Next-day metrics

- Brier score
- hit rate
- calibration gap
- avg expected vs avg realized
- decile calibration by POP bucket

### 11.3 Weekly metrics

- weekly Brier
- weekly hit rate
- interval coverage
- weekly EV MAE

### 11.4 Rotation metrics

These are essential and currently under-specified.

- rotation churn per 20 sessions
- false rotate rate
- missed rotate rate
- average leader tenure
- challenger promotion success rate over next 5 sessions

### 11.5 Success criteria

V2 should only replace V1 if it improves at least these:

- lower next-day Brier or materially better calibration
- lower rotation churn
- lower false-rotate rate
- no material deterioration in weekly MAE / coverage

## 12. Dashboard Implications

The UI should eventually expose these concepts separately:

- `Regime score`
- `Exhaustion`
- `POP`
- `EV`
- `Confidence`
- `Rotation pressure`

Do not present all of these as a single opaque number.

Recommended user-facing labels:

- `KEEP`: leader healthy and confirmed
- `WATCH`: tension building, not enough confirmation to rotate
- `ROTATE`: confirmed deterioration or confirmed challenger takeover

## 13. Implementation Phases

### Phase 1: Offline research build

- build V2 formulas in Python
- run strict walk-forward backtests on existing `DATA`
- compare V1 vs V2

### Phase 2: Dashboard integration

- port V2 outputs into dashboard
- keep V1 hidden behind a switch or a temporary comparison layer if needed

### Phase 3: Confirmed close live pipeline

- connect backend source
- rebuild all dashboard components after each confirmed close

### Phase 4: Optional provisional intraday

- show provisional preview only
- keep historical metrics untouched until confirmed close

## 14. Immediate Next Step

Before touching dashboard logic:

1. implement the V2 research engine in Python
2. run historical walk-forward tests on current `DATA`
3. produce a side-by-side report:
   - V1 vs V2 next-day
   - V1 vs V2 weekly
   - V1 vs V2 rotation behavior

Only after that should the dashboard forecast and rotation logic be replaced.
