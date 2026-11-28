# Steps 88–89 — identity resolution and corporate-action reconciliation

## Step 88: point-in-time effective identity resolution
- Resolve symbol/security-ID/instrument-class intervals only when a primary NEPSE/CDSC archive entry exists and the supplied evidence hash and publisher exactly match that archived document.
- Enforce timezone-aware availability timestamps at or before the decision cutoff, document-availability ordering, independent reviewer, valid interval ordering, duplicate rejection and overlap detection by symbol/class and stable security ID.
- Missing target symbols remain explicitly unresolved. This report does not authorize historical-universe joins; a separate reviewed admission remains required.

## Step 89: independent corporate-action assertion reconciliation
- Validate action identity, type, announcement/availability timestamps, ex-date, source tier, publisher/source ID, raw evidence hash, status, factor/methodology where applicable and independent review.
- Require at least two distinct publishers including NEPSE/CDSC primary evidence. Duplicate publisher/source assertions, future evidence, invalid dates, non-independent reviewers and disagreement on symbol/security ID/type/announcement date/ex-date/status/factor/methodology block.
- Cash/non-price actions cannot carry a price-adjustment factor. The validator never computes factors, adjusts OHLCV or admits adjusted prices.
- Reconciled assertions are evidence readiness only. Corporate-action completeness, effective-dated identity, factor methodology approval and a separate adjustment-admission gate remain mandatory.

## Data and production boundary
This PR adds validators and synthetic unit tests only. It does not acquire NEPSE, CDSC, ShareSansar, Chukul, ShareHub Nepal, Punji, Merolagani, NepseAlpha, ChartNepali or Bullhouse data. It does not resolve any real predecessor ID or admit any real corporate action. Raw source files and hashes must be supplied and reviewed before these gates can produce real evidence outcomes.
