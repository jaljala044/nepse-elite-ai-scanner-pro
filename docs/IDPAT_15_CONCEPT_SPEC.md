# IDPAT 15-concept integration specification (NEPSE)

## Source boundary

The supplied reference image is the source for the 15 concept names below. It does not define rules, parameters, examples, OPR/OPS expansions, proprietary candle names, weights, or entry/exit thresholds. This specification preserves the source wording and does not invent those details.

The image title is “Why IDPAT Method”. The exact acronym expansion is not established by the image.

## Concept register and implementation boundary

| # | Source wording | Scanner treatment | Evidence / dependency |
|---|---|---|---|
| 1 | Reading Price Correctly | OHLCV descriptors and price-structure context; descriptive only | Validated point-in-time OHLCV |
| 2 | Smart Money Hidden Levels | Candidate liquidity/zone observations only; never claim hidden orders or institutional intent | Causal swing/zone events; order-book evidence for displayed liquidity |
| 3 | Trading Using Correct Timeframe | Consume existing multi-timeframe evaluation; preserve horizon-specific output | Session-aligned daily/weekly/monthly data |
| 4 | OPR and Using Techniques | Disabled / UNKNOWN until OPR is defined | Original lesson or authoritative definition |
| 5 | OPS and Using Techniques | Disabled / UNKNOWN until OPS is defined | Original lesson or authoritative definition |
| 6 | Candle Stick Pattern That Nobody Uses | Registry slot only; no detection until exact names and rules are supplied | Original lesson, pattern geometry and validation set |
| 7 | Finding of Accumulation and Distribution | Hypotheses only; use existing Wyckoff evidence when available | Base/phase rules, effort-result, supply/demand and invalidation |
| 8 | Accumulation and Distribution With Volume | Volume context only; volume expansion is not automatically accumulation | Validated volume, turnover, trade frequency and VSA rules |
| 9 | Trading With Price Structure | Consume existing causal market-structure events | BOS/CHoCH/swing definitions and event timestamps |
| 10 | Trend Change in Market and Bending With The Trend | Combine existing trend and structure evidence | Index, sector, security trend and multi-timeframe context |
| 11 | How To Avoid Being In The Wrong Trend | Risk/contra-trend guard; require index/sector/security alignment | Market regime and multi-timeframe alignment |
| 12 | Special: How Not To Read Candle Sticks. | Anti-pattern/false-signal guard to be specified; no invented rule | Original lesson and labelled counterexamples |
| 13 | Shakeout And Climax Trading Technique | Candidate event only; require price rejection plus volume/turnover context | Session OHLCV, liquidity and causal follow-through |
| 14 | Binding Price and Timeframe | Price-zone/timeframe confluence, not a standalone signal | Zone lifecycle plus timeframe alignment |
| 15 | More Additions | Extensible registry slot; no behaviour until additions are supplied | Versioned source and reviewed specification |

## Integration with existing scanner

IDPAT is an additional evidence module, not a replacement scoring engine. It should consume or reference existing outputs where available:

- Wyckoff: accumulation/distribution phase hypotheses and invalidation.
- Minervini: trend-template context.
- SMC/ICT: causal BOS/CHoCH, sweeps, FVG and zone lifecycle.
- VSA: effort-versus-result and relative-volume context.
- Broker memory: daily/weekly/monthly/yearly verified broker observations.
- NEPSE market/sector regime: index and sub-index direction, breadth, turnover and rotation.

No existing component weights are changed. No IDPAT score is emitted until the complete method definition, weights, missing-data policy and independent validation are approved.

## NEPSE-specific safeguards

1. Use verified exchange sessions, not calendar-day assumptions.
2. Keep raw, adjusted and corporate-action-normalized prices separate.
3. Respect security-specific price bands/circuit limits and suspension/auction states when validating breakouts and executable stops.
4. Liquidity uses turnover, trade frequency, spread/depth where available, and realistic execution—not volume alone.
5. Broker participation is descriptive; broker codes do not establish beneficial ownership, intent, coordination or manipulation.
6. Missing data is UNKNOWN, never neutral or zero.
7. All features are point-in-time and causal.
8. Emit research observations, evidence references, limitations and invalidation. No automated orders.

## Acceptance gates

- All 15 source labels are represented without silently rewriting meaning.
- OPR, OPS, uncommon candle patterns, anti-pattern rules and “more additions” remain UNKNOWN until source definitions are supplied.
- IDPAT output is separate from the existing scanner score.
- Every mapped feature carries source/session/as-of metadata and data-quality status.
- Missing components reduce coverage; they are not assigned neutral points.
- Tests cover insufficient history, malformed OHLCV, unknown concepts, unavailable upstream components and no-lookahead behaviour.
- Walk-forward validation is required before any rating/action is enabled.

## Required research material

Obtain original IDPAT lessons/notes for concepts 4, 5, 6, 12, 13 and 15, plus concrete worked examples for all 15. The supplied image provides names, not operational definitions.
