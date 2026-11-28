# Steps 210–219: six-strategy, four-horizon sector context

1. Define the six scanner strategy identifiers: trend momentum, IDPAT smart money, broker footprint, SMC/ICT liquidity, hybrid consensus and fundamental investment.
2. Define T+2, swing, positional and investment horizons separately.
3. Select 1W for T+2; 1W/1M for swing; 1M/3M for positional.
4. Withhold 6–24 month investment context until verified 12M and 24M sector windows exist; 3M/6M are not a substitute.
5. Require observed same-session sector rotation and stock/benchmark source lineage.
6. Require effective-dated, hashed, verified symbol-to-sector membership.
7. Classify horizon context as supportive, headwind or mixed using median sector excess returns.
8. Keep broker footprint unavailable unless independently verified broker-flow evidence is supplied.
9. Keep all strategy actions unchanged and all score adjustments at zero; sector context is never a BUY override.
10. Add regression tests for all 24 combinations, stale evidence, membership, missing windows and broker-flow separation.

## Integration boundary

This module is a callable research annotation adapter for a future server-owned
scan integration. The current scan endpoint has no trusted runtime sector
membership/rotation store; client-supplied sector context is deliberately not
accepted. It does not change ranking eligibility, scanner scores or actions.

The investment horizon requires 12M and 24M verified evidence. The current
rotation engine supplies 1W/1M/3M/6M only, so investment sector context remains
insufficient evidence. Synthetic tests only; no live recommendations.
