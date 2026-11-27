# Shared Trade Plan and Risk Engine — Steps 2 and 3

## Step 2: evidence-backed trade plan
`app.scanner_trade_plan.build_evidence_backed_trade_plan` accepts only source-supplied entry range, stop and target levels with independent source/evidence IDs, verified status and availability no later than the decision cutoff. It computes net T1/T2/T3 reward/risk conservatively using the upper entry price and explicit round-trip costs/slippage. A long plan requires stop < entry low <= entry high < T1 and net T1 R:R >= 2 by default. T2/T3 are optional but ordered when present.

Support, resistance and buy-/sell-side liquidity zones are shown only when each zone has verified provenance, a type, strength and lifecycle status (tested/untested/swept/invalidated/active). No levels are inferred by this module. Missing/invalid/future levels remain unavailable and block plan readiness. Order-book depth is not implied by chart-derived levels.

## Step 3: shared risk and execution
`app.scanner_risk_engine.calculate_risk_limited_position` sizes whole shares by the minimum of:
- risk budget (default 1%; hard cap 2%),
- available cash,
- maximum single-position allocation (default 20% of equity),
- average-daily-volume participation (default 5% of ADV).

Per-share risk includes explicit round-trip costs, slippage and a configurable adverse gap stress below the stop (default 5%). Stress is a scenario, not a forecast. Missing ADV or invalid inputs fail closed to zero shares.

`evaluate_execution_constraints` blocks stale/unavailable quotes, circuit/halt states, excessive or unavailable spread, insufficient bid depth and malformed broker sellable quantities. It requires point-in-time facts from a trusted upstream broker/market adapter. A passing snapshot is not a fill guarantee.

## Important boundaries
- Both modules are research/human-review support only; no order routing or production BUY.
- The current implementation is long-only.
- The caller must supply independently verified price levels and execution facts; these modules do not derive technical levels from OHLCV.
- Settlement sellability must use broker-confirmed quantity/date. No settlement calendar is hard-coded.
- Liquidity capacity uses ADV participation as a coarse cap; intraday depth, circuits, partial fills, impact and current market rules still require live validation.
