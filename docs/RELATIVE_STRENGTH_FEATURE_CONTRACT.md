# Relative-strength feature contract (P4.8)

## Purpose
The 15% relative-strength component measures a stock's excess return versus the
NEPSE benchmark and ranks eligible equities cross-sectionally. It is a
descriptive 0–100 percentile, not a probability or standalone trading signal.

## Benchmark admission
Only point-in-time rows with all of the following are admitted:
- `record_type=index_ohlcv` and `index_code=NEPSE`
- `source_validation_status=verified` and `finality_status=final`
- Valid ISO session date and finite positive final close
- Nonblank immutable `source_id` and 64-character SHA-256 payload digest
- `available_at` no later than the feature decision time

The pipeline does not fetch or verify benchmark data. Verification is an
upstream responsibility. Third-party mirrors and quarantined archives must not
be promoted merely because they pass the adapter's synthetic tests.

## Equity price admission
Every stock close used in the 1W/1M/3M/6M windows must carry:
- `source_validation_status=verified`
- `price_basis_status` equal to `verified_unadjusted_no_actions` or
  `verified_adjusted`
- `corporate_action_status` equal to `clear` or `adjusted_verified`
- Nonblank `source_id` and a valid 64-character SHA-256 payload digest

These statuses must be assigned only after point-in-time source validation,
corporate-action review and price-basis reconciliation. Missing or unverified
metadata excludes the symbol; it is never assumed clear.

## Return and ranking method
- Horizons are 5, 21, 63 and 126 prior exchange-session intervals plus the
  current benchmark session.
- Stock and benchmark prices must exist on every exact benchmark session in
  each horizon. No forward-fill, interpolation, stale endpoint, calendar
  substitution or shortened window is permitted.
- RS for each horizon is stock return minus NEPSE return, in percentage points.
- Weighted excess return = 20% 1W + 30% 1M + 30% 3M + 20% 6M.
- The component score is the average-tie percentile rank across the supplied
  expected equity universe. At least two symbols and 80% universe coverage are
  required before any score is emitted.

## Current limitation
The adapter and tests validate calculation behavior only. They do not certify
that a live NEPSE benchmark archive or every stock's point-in-time adjusted
price history has passed the project's source, session, identity and corporate
action gates. Until those inputs are supplied, the RS component remains null
and the aggregate Stage 2 score reports the missing 15% weight.
