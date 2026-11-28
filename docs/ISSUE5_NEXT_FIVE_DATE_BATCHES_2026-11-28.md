# Issue #5 — next five unlisted-date batches (review only)

Prepared 2026-11-28 as a continuation of the highest-incidence workload after the five batches recorded in `ISSUE5_TOP_FIVE_WEEKLY_CLOSURE_BATCHES_2026-11-28.md`.

| Current date | Candidate pairs | Symbols | Weekday | Disposition |
|---|---:|---:|---|---|
| 2026-06-21 | 677 | 351 | Sunday | UNKNOWN_EXCHANGE_SESSION |
| 2026-06-06 | 665 | 345 | Saturday | UNKNOWN_EXCHANGE_SESSION |
| 2026-06-07 | 665 | 345 | Sunday | UNKNOWN_EXCHANGE_SESSION |
| 2026-03-20 | 657 | 341 | Friday | UNKNOWN_EXCHANGE_SESSION |
| 2026-03-21 | 657 | 341 | Saturday | UNKNOWN_EXCHANGE_SESSION |

## Evidence boundary

The existing review notes identify the April 2026 weekly schedule transition and the NRB holiday calendars as T2/T3 context. They do not include a date-matched NEPSE-hosted session record or preserved exchange notice bytes for these five dates. A weekday or public-holiday calendar is not sufficient to certify a NEPSE trading session.

Therefore all five dates remain `UNKNOWN_EXCHANGE_SESSION`; no `verified_open_tier1` or `verified_closed_tier1` status is assigned. The CSV explicitly disallows canonical promotion.

## Data safety

- Candidate-pair counts are workload-priority metadata, not row dispositions.
- Identical adjacent OHLCV is not proof of carry-forward or fabrication.
- No raw OHLCV, calendar, canonical dataset, or training dataset is modified.
- Next required evidence: date-matched NEPSE-origin session/tape artifact with retrieval timestamp, raw bytes, and SHA-256.
