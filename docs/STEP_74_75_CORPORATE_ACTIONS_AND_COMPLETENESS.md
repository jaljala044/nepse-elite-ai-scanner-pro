# Steps 74–75 — corporate-action verification and historical completeness

## Step 74: independent corporate-action verification
- Requires matching event identity and terms from at least two distinct source IDs and publisher IDs.
- Calculates theoretical ex-price adjustment factors only for approved bonus/split, cash-dividend and rights-issue conventions with complete terms and prior close.
- Preserves raw prices and emits factors as separate research artifacts; no automatic adjustment or backtest admission.

## Step 75: historical symbol/session completeness audit
- Builds the eligible symbol × official-open-session matrix, respecting effective listing dates, supplied first-trade evidence and delisting dates.
- Reports per-symbol and aggregate coverage, missing expected bars, duplicate keys, out-of-scope rows, unknown calendar sessions and lifecycle conflicts.
- Closed days and pre/post-listing sessions are excluded; unknown dates are never silently treated as closed or open.

## Verification boundary
Synthetic tests only. No live NEPSE/CDSC data acquired. Source independence/authenticity still require human verification. Completeness is limited to the supplied cohort and session calendar; no exchange-wide completeness claim. Backtest admission, canonical promotion and production remain disabled.
