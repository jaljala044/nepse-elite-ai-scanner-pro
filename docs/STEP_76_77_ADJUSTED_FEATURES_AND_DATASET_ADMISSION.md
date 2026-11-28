# Steps 76–77 — adjusted feature snapshots and six-scanner dataset admission

## Step 76 — point-in-time corporate-action adjustment integration
- Add a versioned feature-snapshot wrapper that consumes only Step-74 verified adjustment events.
- Require two distinct source IDs and publisher IDs, the approved theoretical ex-price convention, valid event hash/factor, timezone-aware availability and ex-date.
- Apply the factor only to bars strictly before ex-date and only when both ex-date and event availability are at/before the snapshot cutoff.
- Preserve raw OHLC fields; volume and turnover remain unchanged. Defer future/late events and reject malformed/duplicate events.
- Adjustment audit is embedded in the content-addressed snapshot. It does not prove source authenticity or action-universe completeness.

## Step 77 — six-strategy/four-horizon dataset admission
- Validate the shared dataset fingerprint, panel human-review qualification, corporate-action review and complete input lineage.
- Enforce timezone-aware point-in-time availability for each record and optional feature/label timestamps.
- Enforce chronological train < validation < untouched test windows; reject test windows at/before the decision cutoff.
- Emit all 24 strategy × horizon cells with a common admission result. One blocker blocks all cells.
- Admission is human-review preflight only; it does not run replay, calibrate probabilities, promote canonical data or enable production.

## Verification boundary
Synthetic tests only. No NEPSE/CDSC data acquired or strategy replay executed. Real data rights, source authenticity, complete sessions/corporate actions, exchange execution and independent review remain prerequisites.
