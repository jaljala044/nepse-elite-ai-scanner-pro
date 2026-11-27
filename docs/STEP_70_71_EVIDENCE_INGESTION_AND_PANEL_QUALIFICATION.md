# Steps 70–71 — evidence ingestion and historical panel qualification

## Step 70: explicit-schema evidence ingestion

Adds a reusable CSV ingestion boundary for official calendar, security master, corporate actions, floorsheet, CDSC first-trade evidence, sector indices and broker trade summaries. Each parser requires an explicit semantic-to-source column map, an accepted capture package, matching capture identity, raw page hashes, timezone-aware availability, dataset-specific required fields, duplicate business-key checks and typed date/number/boolean validation. No provider schema is guessed.

## Step 71: bounded panel qualification

Compares a supplied cohort against OHLCV symbol/session coverage, official open-session evidence, permanent security identities and lifecycle intervals, corporate-action records plus a human-reviewed coverage attestation, and CDSC first-trade dates. It reports missing/contradictory evidence and supplemental floorsheet/sector/broker coverage. A passing result is eligible only for human review and explicit research replay admission.

## Boundary

All tests use synthetic fixtures. No NEPSE/CDSC endpoint was guessed or queried and no real historical records were captured. Human attestations, source authority, licensing, secure transport and exchange-wide completeness require independent verification. Backtest admission, canonical promotion and production remain disabled.
