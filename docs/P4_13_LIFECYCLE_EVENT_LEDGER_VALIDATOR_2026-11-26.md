# P4.13 — lifecycle event ledger validator — 2026-11-26

## Implementation

Added `backend/validate_security_lifecycle_event_ledger.py` and six regression tests in `backend/tests/test_security_lifecycle_event_ledger.py`.

The validator checks:
- required typed-event fields;
- unique event IDs;
- security ID and symbol alignment against the dated active-equity crosswalk;
- ISO event dates;
- approved event types, evidence tiers and review statuses;
- HTTP(S) source URL shape;
- required source labels and explanatory notes;
- no secondary source can be labeled as a primary NEPSE notice.

It reports event-type and evidence-tier coverage plus SHA-256 hashes of the local ledger and crosswalk files.

## Fail-closed limits

- The validator does not fetch or authenticate source URLs.
- It does not treat a merger effective date, listing date or trading-release date as first execution.
- It does not prove floorsheet completeness or official session coverage.
- Source payload retrieval timestamps and immutable raw response hashes are still missing from the eight current event rows.
- Promotion is always false.

## Current ledger

The current eight-row event ledger is expected to validate with status `valid_event_ledger_with_uncaptured_raw_sources`. This status means structural and crosswalk validation only; it is not a verified first-trade or production-data status.

Run from the repository root:

```bash
python backend/validate_security_lifecycle_event_ledger.py \
  --ledger data/reference/nepse_security_lifecycle_events_2026-11-26.csv \
  --crosswalk data/reference/nepse_equity_security_id_crosswalk_2026-11-26.csv \
  --expected-count 8
```


## P4.11.4 follow-up — 2026-11-28

The event ledger now contains eight rows, including secondary contract-level first-execution corroboration for NMLBBL (2024-05-19) and SMPDA (2024-08-18). These are explicitly `corroborated_not_exchange_primary`; the official NEPSE listing PDFs remain listing/release evidence only. The lifecycle input records the two dates with `verified_secondary_notice`, not primary verification. Promotion remains disabled.
