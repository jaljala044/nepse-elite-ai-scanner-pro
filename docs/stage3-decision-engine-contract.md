# Stage 3 decision engine contract (alpha1)

## Purpose and boundary

`app.decision_engine` is a deterministic, research-only consumer of Stage 1 eligibility, Stage 2 component scores/structure, and pre-computed evidence-backed trade plans. It does not fetch market data, derive chart levels, infer broker intent, estimate probabilities, or submit orders.

The four horizons are evaluated independently:
- `T+2`: 3–5 trading days
- `SWING`: 1–4 weeks
- `POSITIONAL`: 1–6 months
- `INVESTMENT`: 6–24 months

## Required input contract

### Stage 1

The caller must provide explicit booleans for `eligible`, `identity_valid`, `session_valid`, `source_valid`, `corporate_actions_clear`, `point_in_time_valid`, `liquidity_pass`, and `market_tradeable`. Missing or non-boolean approvals fail closed. `data_quality` must be HIGH or MEDIUM; LOW or unknown blocks action.

### Stage 2

`components` may contain scores from 0 to 100 for Wyckoff, Minervini, relative strength, broker footprint, volume/VSA, liquidity, sector and SMC. Missing components remain missing. The weighted score is normalized over observed weights, and coverage is returned separately. Coverage below 75% is not decision-eligible. A rating is withheld below that coverage.

`structure.confirmed_by_horizon` must explicitly confirm the relevant horizon. `structure.entry_trigger` must explicitly be one of `at_entry`, `pullback`, `breakout_confirmed`, or `retest_confirmed`. No horizon inherits another horizon's confirmation.

### Trade plan

The plan must include positive `entry_low`, `entry_high`, `stop_loss`, and `targets.t1`, with:
- stop < entry low <= entry high < T1
- optional T2 strictly greater than T1
- optional T3 strictly greater than T2 (T3 requires T2)
- at least one non-empty plan evidence reference

Reward/risk uses the conservative upper entry:
`(T1 - entry_high) / (entry_high - stop_loss)`.
A value below 2.0 blocks BUY. This is a policy threshold, not a claim of proven strategy performance.

## Action precedence

1. Stage 1 approvals and general evidence references
2. Confirmed distribution, breakdown or invalidation
3. Evidence-backed entry/stop/T1 plan and level references
4. Stage 2 coverage and score threshold
5. Conservative T1 reward/risk
6. Horizon-specific structure confirmation
7. Horizon-specific entry trigger

Any missing required input returns NO_TRADE / INSUFFICIENT_DATA or WAIT. Existing holders may receive HOLD/HOLD_WAIT when confirmation is missing; confirmed distribution/breakdown/invalidation can return SELL_NOW only when the upstream gates pass.

## Output

Each horizon returns action/subtype, score and coverage, missing components, rating, data quality/confidence, entry zone, stop, T1–T3, risk percentage, reward/risk, invalidation, liquidity/support/resistance fields, evidence references, reasons and methodology version. Unavailable values remain null or empty; no synthetic price levels or probabilities are generated.

All results are marked `research_only_not_order_authorization`.

## Integration status

The engine and regression tests are on PR #24. The current `/v1/scan` route has not yet been wired to this contract. The existing scanner's eligibility assessment does not independently certify corporate-action clearance, execution liquidity, market-regime tradeability, all eight weighted Stage 2 scores, or evidence-backed horizon plans. Do not map missing inputs to positive approvals. API integration remains blocked until those upstream contracts exist and have tests.

## Validation

Regression tests cover:
- missing structure confirmation
- confirmed retest and conservative 2:1 geometry
- failed Stage 1 eligibility
- independent horizon confirmation
- distribution exit for a holder
- non-increasing target sequence
- malformed level evidence references
- low confidence for a no-trade outcome

CI is the authoritative test result for each commit. No performance/backtest claim is made by these unit tests.
