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
- Through 2022-05-14: Sunday–Thursday regular-session candidates; Friday odd-lot excluded; Saturday closed.
- 2022-05-15 through 2022-06-14: temporary Monday–Friday candidates; Saturday/Sunday closed.
- 2022-06-15 through 2022-09-16: temporary Sunday–Friday candidates; Saturday closed.
- 2022-09-17 through 2026-04-05: Sunday–Thursday candidates; Friday/Saturday excluded.
- From 2026-04-06: Monday–Friday candidates; Saturday/Sunday excluded.

The 2022 transition from Sunday–Thursday to Monday–Friday was announced for the two-day weekend beginning 15 May; the next schedule change restored Sunday–Friday trading from 15 June. This makes 14 May the end of the first regime, not 5 May. Sources: [Nepal News, 29 April 2022](https://english.nepalnews.com/s/business/nepse-to-open-on-friday/), [Khabarhub, 13 June 2022](https://english.khabarhub.com/2022/13/257305/),
[The Himalayan Times, 13 June 2022](https://thehimalayantimes.com/business/nepse-to-operate-six-days-a-week-effective-june-15),
[ShareSansar, 16 June 2022](https://www.sharesansar.com/newsdetail/from-ashad-shares-will-be-traded-six-days-a-week-sunday-friday-2022-06-16),
and [ShareSansar, 4 September 2022](https://www.sharesansar.com/newsdetail/nepse-decides-to-close-trading-on-fridays-from-ashoj-2022-09-04).
The 2026 transition is reported by [The Himalayan Times, 8 April 2026](https://thehimalayantimes.com/business/nepse-shifts-to-mondayfriday-trading-week)
and [ShareSansar, 8 April 2026](https://www.sharesansar.com/newsdetail/nepal-stock-exchange-opens-monday-to-friday-under-new-government-timings-2026-04-08).
These sources establish schedule-regime changes, not the actual open/closed status
of every historical date. Daily closures and exceptional sessions still need dated
NEPSE evidence or independently verified exchange trading records.


## Source coverage matrix (inventory metadata only)

Build a date-by-date matrix from one or more JSONL manifests. Run from `backend/`:

```bash
python build_calendar_coverage_matrix.py \
  --manifest ../artifacts/source-manifests/urekmazino69_Nepse-floorsheet-and-indices_<revision>.jsonl \
  --calendar ../data/reference/nepse_session_calendar.csv \
  --start-date 2024-01-02 \
  --end-date 2026-08-26 \
  --output ../data/reports/nepse-calendar-coverage-matrix.json
```

Repeat `--manifest` for each independent source. The matrix records source file
counts and bytes by date, explicit calendar evidence, schedule-candidate notes,
and files found on dates explicitly marked closed. It rejects duplicate
source/path manifest entries and malformed dates. It does not treat file presence
as proof of a session, nor a weekday candidate without a file as proof of a missing
session. Review all closure conflicts and unverified candidate dates against dated
NEPSE notices or verified exchange records.

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

## 2026 calendar evidence review queue

A separate lead register now exists at
`data/reference/nepse_calendar_evidence_leads_2026.csv`. It records candidate
closure dates and source quality without promoting any row into the canonical
session calendar.

The first reviewed leads are:

- **21 Sep 2026:** ShareSansar reports NEPSE suspended trading after a Data Hub
  outage and resumed on 22 Sep. This is an exceptional exchange suspension, not
  a routine public holiday.
- **19–23 Oct 2026:** ShareSansar reports NEPSE closed Monday–Friday for Dashain.
- **9–12 Nov 2026:** ShareSansar reports NEPSE closed for Tihar, with trading
  resuming Friday 13 Nov.
- **16 Nov 2026:** ShareSansar's 13 Nov market report says the exchange would be
  closed Monday for Chhath and resume Tuesday 17 Nov.
- **28 Aug and 4 Sep 2026:** the Nepal Rastra Bank 2083 holiday list identifies
  government holidays, but this alone is not proof of a NEPSE closure.

These are secondary-source leads and/or government holiday candidates. The
canonical calendar remains empty until dated primary NEPSE notices or equivalent
exchange records are captured, preserved, hashed and reviewed. Do not mark any
candidate date verified solely from this lead file.
