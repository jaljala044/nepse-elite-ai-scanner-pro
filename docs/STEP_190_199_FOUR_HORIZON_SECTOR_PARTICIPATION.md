# Steps 190–199: four-horizon sector participation

## Implemented

1. Expanded market-health sector participation from 1M/3M to 1W/1M/3M/6M.
2. Aligned horizon weights to 20%/30%/30%/20%.
3. Preserved strict point-in-time source and payload-hash provenance requirements.
4. Enforced independent minimum sector coverage for each horizon.
5. Kept missing, stale or unverified horizon data fail-closed.
6. Added horizon-specific positive-sector counts and participation percentages.
7. Added a weighted participation result with explicit component weights.
8. Added early warning when 1W breadth deteriorates against a strong 6M baseline, and recovery warning for the inverse.
9. Expanded unit and market-health pipeline fixtures and regression tests.
10. Updated adapter documentation; production remains gated on real verified source evidence.

## Formula

For each horizon, participation is the percentage of observed sectors with
positive median constituent returns. Zero returns are not counted positive.

`score = 0.20 × 1W + 0.30 × 1M + 0.30 × 3M + 0.20 × 6M`

The component is descriptive market context, not a probability or trade signal.
Each horizon requires at least 80% of the expected sector universe to be
observed. No missing sector or return is imputed.

## Validation status

Synthetic regression tests are included. Exact-head CI is required before
this change can be considered validated. No live sector score is asserted,
and no production recommendations are enabled.
