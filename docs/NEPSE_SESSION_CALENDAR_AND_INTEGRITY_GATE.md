# NEPSE historical session calendar and integrity gate

Status: implementation baseline; the full historical calendar is **not yet verified**.
This module intentionally refuses to infer a verified session from a weekday or an
OHLCV row. It provides the evidence-backed mechanism and a fail-closed row audit.

## Calendar contract

CSV columns: `date,status,source_id,evidence_uri,verified_at_utc,notes`.
Only `verified_open` and `verified_closed` are accepted. Every explicit row must
carry a source identifier, evidence URI and verification timestamp. Conflicting or
duplicate date rows fail calendar loading. Keep the source notice/document and its
hash in the evidence archive; do not cite a general public-holiday list as proof that
NEPSE actually closed.

The schedule regimes are candidate hints only:
- Through 2026-04-05: Sunday–Thursday candidate weekdays (Friday/Saturday excluded).
- From 2026-04-06: Monday–Friday candidate weekdays (Saturday/Sunday excluded).

The 2026 transition is supported by contemporary reporting of NEPSE's board decision
and notice; see [The Himalayan Times, 8 April 2026](https://thehimalayantimes.com/business/nepse-shifts-to-mondayfriday-trading-week)
and [ShareSansar, 8 April 2026](https://www.sharesansar.com/newsdetail/nepal-stock-exchange-opens-monday-to-friday-under-new-government-timings-2026-04-08).
These sources establish a schedule-regime change, not the actual open/closed status
of every historical date. Daily closures and exceptional sessions still need dated
NEPSE evidence or independently verified exchange trading records.

## OHLCV gate

Run from `backend/`:
```bash
python -m app.session_calendar --calendar ../data/reference/nepse_session_calendar.csv \
  --input ../data/raw/ohlcv --output ../data/reports/ohlcv-session-integrity.json
```
Every row must parse, have valid OHLC bounds and non-negative volume, and map to an
explicit `verified_open` calendar date. Duplicate symbol/date keys are quarantined,
including exact duplicates; conflicting values are never resolved by overwrite.
Original files remain untouched. Each file and calendar is SHA-256 fingerprinted.
A report pass is limited to the supplied files and explicit evidence; it does not
prove all expected archive files were supplied.

## Important limits / remaining evidence work

- Do not use Nepal Rastra Bank's bank-holiday calendar as a substitute for NEPSE's
  own notices. Government holidays may be modified by the exchange.
- Do not promote weekday candidates, repeated candles, filenames, or inferred dates.
- This gate does not yet perform cross-source reconciliation of the 25 differing
  Jaljala OHLCV files, corporate-action reconciliation, or source-completeness proof.
- Full calendar completion requires acquisition and review of dated NEPSE notices /
  exchange trading evidence for the entire target period, including exceptional
  openings, closures, schedule changes and historical gaps.
- Full data-integrity completion additionally requires the raw archives to be staged
  and all rows to be audited. Until those are done, canonical import and predictive
  intelligence remain blocked.
