# Equity lifecycle provenance validator — 2026-11-26

## Purpose

The lifecycle coverage input has one row for each of the 281 active-equity candidates. This validator prevents unsupported first-trading dates from being promoted into coverage calculations and verifies each symbol/security-ID pair against the dated 2026-11-25 current-snapshot crosswalk.

## Implemented

Added `backend/validate_equity_lifecycle_input.py` and regression tests in `backend/tests/test_validate_equity_lifecycle_input.py`.

Checks include:
- Required lifecycle and provenance columns.
- Exactly 281 lifecycle rows and 281 eligible crosswalk symbols.
- Unique symbols and security IDs in the lifecycle input.
- Every row is an in-scope equity.
- Every symbol/security-ID pair matches the active current-snapshot crosswalk.
- Evidence status is one of `verified_primary_notice`, `verified_secondary_notice`, or `unverified`.
- Verified dates require a date, source URI and explanatory note.
- Unverified dates must remain blank, must not carry an evidence URI, and require an explanation.
- Date ordering is checked where dates are supplied.
- Input and crosswalk SHA-256 hashes are returned in the report.

## Current validation result

The checked-in input is structurally valid:
- 281 rows.
- 1 verified-secondary first-trading date: YMHL, 2026-06-22.
- 280 first-trading dates explicitly unverified.
- 0 validation errors.
- Promotion remains disabled.

This is not a claim that 280 securities have no listing history. It means the repository does not yet contain an accepted date plus provenance record for those rows.

## CI evidence

- Backend unit suite: [run 45834139262](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45834139262) — **741 tests passed**.
- Integrated evidence audit: [run 45834139271](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45834139271) — **success**.
- Historical data integrity: [run 45834139312](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45834139312) — **success**.

## Limits and next work

The validator confirms provenance shape and current-snapshot identity alignment. It does not independently fetch or authenticate each linked notice, establish complete lifecycle intervals, validate suspensions/delistings, establish official trading sessions, prove OHLCV row completeness, or approve canonical data promotion.

Next: acquire dated NEPSE/issuer notices or independently verifiable first-trade evidence for the remaining 280 symbols; record the evidence URL, retrieval timestamp, raw response/document hash and reviewer decision. Then rerun source-separated OHLCV coverage against verified open sessions.
