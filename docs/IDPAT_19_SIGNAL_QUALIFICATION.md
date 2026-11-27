# IDPAT-19 — Evidence-weighted scanner signal qualification

## Delivered
- Adds the project weighted component model: Wyckoff 25, Minervini 25, RS 15, broker 10, VSA 10, liquidity 5, sector 5, SMC 5.
- Scores are admitted only with verified status, source/evidence IDs and timezone-aware availability no later than decision cutoff.
- Missing or invalid component evidence reduces coverage; it is never scored as neutral.
- Requires seven independent verified gates: market, sector, broker, liquidity, execution, corporate actions and source quality.
- Requires explicit long entry, structural stop, T1, round-trip cost and slippage, with net T1 reward/risk >= 2.
- Returns BUY only as a human-review research qualification; otherwise NO_TRADE. No production recommendations, order routing or probabilities.

## Limitations
- Weights and score thresholds are inherited design assumptions, not calibrated.
- T+2/swing/positional/investment labels are accepted as independent configurations; no predictive horizon accuracy is claimed.
- No full production entry/exit generation, portfolio allocation, settlement state machine or live source connection is claimed.
- Tests use synthetic evidence only.
