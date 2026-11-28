# Steps 84–85 — Effective-dated identity and historical coverage pilot

## Step 84 — security identity and corporate-action evidence
- Validate symbol/security-ID/instrument-type intervals with explicit effective-from/to dates.
- Require timezone-aware availability/observation timestamps, publisher identity, authority class and raw evidence SHA-256.
- Detect overlapping symbol-to-ID, ID-to-symbol and instrument-class conflicts.
- Validate bonus, rights, split, reverse-split, dividend, merger, demerger, symbol-change and delisting events.
- Require at least two publishers including a primary exchange/depository source for each accepted action; conflicting effective dates/factors block the event.
- No first-trading date is inferred from first observed OHLCV. No historical identity is promoted from a current snapshot.

## Step 85 — bounded source-specific OHLCV coverage pilot
- Build the expected symbol/session grid only from supplied verified session calendar and effective-dated equity identities.
- Report per-provider coverage, missing symbol/session keys, duplicates, out-of-scope rows and close-price conflicts.
- Preserve provider-specific observations and raw hashes; never blend or select a winning source.
- Require corporate-action and calendar evidence before the coverage report can be review-ready.
- A review-ready report still cannot promote canonical data or authorize scanner replay.

## Current limitations
The implementation validates supplied evidence and data; it does not fetch NEPSE or third-party sources, authenticate publishers, grant redistribution rights, resolve missing official lifecycle records, or generate a full-market history. Unit tests use synthetic fixtures to verify rejection and acceptance paths. The existing three-date official NEPSE reconciliation remains review-only and does not become a broader historical validation by virtue of these tests.
