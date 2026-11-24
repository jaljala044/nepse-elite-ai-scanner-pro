# NEPSE Historical Data Window Policy

**Status:** Engineering policy; does not certify any source or archive as complete.

## Decision

Six to nine months is a useful *recent-regime* window, but it is not sufficient as the platform's only historical memory or as the sole basis for claiming that a stock, broker, or market pattern is recurring.

The platform must preserve and use a layered history. It must not discard older valid observations merely because the operational recent window is shorter.

## Required history layers

| Layer | Target window | Intended use | Guardrail |
|---|---:|---|---|
| Recent | Latest 6–9 months | Current regime, short-horizon behaviour, recent broker participation and scanner context | High recency weight; not enough alone to establish recurrence |
| Intermediate | At least 2–3 years where validated data exists | Repeated stock patterns, broker/stock relationships, multiple market conditions | Compare across regimes; do not assume all dates are sessions |
| Long-cycle | 5–10+ years where validated data exists | Long-cycle context, structural changes, rare events and regime comparison | Source quality and corporate-action history may limit usable features |
| Full archive | Every legally usable, provenance-preserved record | Research, future reprocessing and historical memory | Immutable raw layer; quarantine uncertain records rather than deleting them |

These are coverage targets, not permission to fill gaps with estimates. If a source only has 6–9 months, label its coverage honestly and use it only for analyses supported by that span.

## Different data types need different minimums

- **Daily OHLCV and indices:** retain the longest verified history available. Recent 6–9 months can support short-term context, but market-regime comparisons need multiple years and a verified session calendar.
- **Floorsheet and broker flow:** prioritize continuous, row-audited recent history first, then extend backward. A short but reconciled window is preferable to a longer archive with unknown missing sessions or duplicated contracts.
- **Corporate actions, symbol master and broker master:** preserve effective dates and historical versions. Current reference data must not be backfilled into past decisions as if it were known then.
- **Intraday data:** use only where timestamp semantics, timezone, ordering and source publication times are verified. Missing execution times remain missing.

## Recency without forgetting

The feature store and research layer should expose separate fields for:
1. recent-window statistics;
2. intermediate-window statistics;
3. long-history / regime statistics;
4. history coverage, missing-session count and data-quality status.

Models may weight recent observations more heavily, but must retain the window identity and show how much evidence supports each conclusion. Avoid a single blended score that hides a short sample or a source-quality problem.

## Evidence rules for pattern claims

- A pattern seen once is an observation, not a recurring pattern.
- A pattern seen only in the recent window must be labelled **recent / low-history evidence**.
- Recurrence claims require multiple independent occurrences, not many rows from one episode.
- Validate on chronological, out-of-sample periods. Never randomly mix future and past observations.
- Report sample count, distinct episodes, date span, market regime, data coverage and uncertainty.
- Calibrate confidence against historical outcomes; do not convert a heuristic score into a probability without calibration.
- No-lookahead applies to every feature, label, broker-flow aggregate and corporate-action adjustment. A record's event date is not necessarily its first public availability date.

## Project gate implications

A longer archive is not automatically better. The canonical dataset must pass:
- verified session-calendar reconciliation;
- immutable source snapshots and provenance;
- schema and key validation;
- duplicate and conflicting-contract quarantine;
- quantity × rate = amount checks with documented rounding tolerance;
- broker and symbol master effective-date checks;
- corporate-action-aware price handling;
- cross-source reconciliation and explicit unresolved-exception reporting.

Until the relevant gates pass, data remains research/quarantine material and must not silently enter the live scanner or a performance claim.

## Current project position (2026-11-24)

The project has multi-year OHLCV candidate archives and several floorsheet source candidates, but the prior audit found unresolved OHLCV exceptions and no fully reconciled, date-by-date official session calendar. Floorsheet candidate manifests have been inspected, but the large raw archives have not yet been fully acquired and row-audited. Therefore, neither the 6–9 month floor-sheet window nor the longer candidate archives are certified as canonical yet.

## Next implementation order

1. Establish a verified date-by-date NEPSE session calendar and a coverage matrix by source/data type.
2. Reconcile and quarantine known OHLCV invalid rows and cross-source conflicts without modifying raw snapshots.
3. Run public, unauthenticated Hugging Face manifest-only enumeration against the pinned dataset revision; verify the Hub metadata fields before any download.
4. Acquire only rights-cleared floorsheet files under explicit byte ceilings and verify each file against publisher-provided content hashes.
5. Validate daily floorsheet rows and control totals before canonical ingestion.
6. Build recent/intermediate/long-history feature views only from gate-passed records.
