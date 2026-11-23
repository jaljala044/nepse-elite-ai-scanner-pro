# Analysis method (initial)

The initial scanner computes only transparent daily OHLCV descriptors:
- 20-session simple moving average
- 20-session price change
- Latest volume relative to its 20-session average

It does **not** claim to identify smart money, manipulation, accumulation/distribution, order blocks, fair-value gaps, or broker intent. Those require additional validated datasets and independently testable definitions.

## Planned research modules
1. Session calendar and corporate-action normalization
2. Trend structure and swing-point/BOS/CHOCH definitions
3. Wyckoff phase hypotheses with explicit invalidation conditions
4. VSA and relative-volume context
5. Liquidity zones and gap/imbalance candidates
6. Broker/floorsheet analysis only where source provenance and coverage are reliable
7. Confidence, data-quality and risk flags

Every future signal should include evidence, timestamp/session, source, invalidation, and limitations. Avoid deterministic language and never promise accuracy.
