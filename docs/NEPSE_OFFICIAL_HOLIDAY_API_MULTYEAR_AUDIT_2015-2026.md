# NEPSE official holiday API multi-year capture audit — 2015–2026

Updated: 2026-11-25

## Result

A repeatable GitHub Actions capture was expanded to request the official NEPSE holiday API for every year from 2015 through 2025. The run succeeded and archived the raw response for all 11 years. The already captured 2026 response was retained separately.

- Workflow: `Capture primary reference evidence`
- Run: `45623107909` — completed successfully
- Artifact: `15027700386`
- Artifact SHA-256: `ce8959b0f185d92c936a0c5e137cb2645b33c5d6d23b1ff38c15e2e1d68b7eec`
- Capture commit: `39747bd2ade2bdb59ef7665f454bcbc04b3060df`
- Captured years: 12 (2015–2026)
- HTTP result: 200 for every year
- Total records: 499
- Unique dates within each year's response, summed: 498
- Duplicate date rows: 1 (2020-04-13)
- Failed years: 0

Raw bytes, parsed JSON, response headers, source URL, SHA256SUMS and capture reports are preserved under:

`data/evidence/raw/nepse/holiday-api-authenticated/{YYYY}-11-25/`

The year-level response hashes and row/date counts are recorded in
`data/evidence/acquired/nepse-holiday-api-multiyear-audit-2015-2026.json`.

## Findings requiring review

1. Every record across all 12 years has `instrumentTypeId=null` and
   `activeStatus=null`. The API is an official NEPSE holiday endpoint, but
   these null fields do not provide an explicit per-instrument scope or active
   flag. Do not silently invent either.
2. The 2020 response contains two records for 2020-04-13:
   - `As Per Order by SEBON Lockdown`
   - `New Year Holiday`

   Preserve both source records. Do not deduplicate them as if one were an
   accidental duplicate; determine whether they represent overlapping closure
   reasons.
3. The 2018 response's final date is 2018-11-09, and the 2019 response's final
   date is 2019-10-30. These truncated-looking ranges are warning signs; the
   API response alone does not prove each annual list is complete.
4. No date absent from an API response is inferred to be an open session.
5. The 2015–2025 payloads are archived as primary-source evidence but have not
   been promoted into the canonical calendar. The separately reviewed 2026
   capture remains 40 `verified_closed` dates plus one
   `verified_exceptional_closed` date (2026-09-21).

## Decision

This closes the *acquisition* task for historical NEPSE holiday API payloads
across 2015–2025. It does not close historical calendar acceptance: scope,
annual completeness, duplicate-reason review, verified open sessions and the
616-session source calendar remain unresolved. Canonical promotion is false
for the 2015–2025 captures; P1 remains active and P2 remains gated.

## Next evidence tasks

1. Compare each year's API holiday records with independent official NEPSE
   circulars and pinned source-date/floorsheet manifests; preserve every
   disagreement.
2. Resolve the 2020-04-13 dual-reason record and investigate the incomplete
   looking 2018/2019 response ranges.
3. Recover and reproduce the exact 616-session date list; use the holiday API
   only as closure evidence, never as a generator of open sessions.
4. Capture official dated NEPSE notices for the remaining historical years
   and document whether each notice applies to all securities or a narrower
   segment.
5. Rerun the calendar evidence validator and integrated P1 acceptance audit
   after independent review; do not infer open sessions from weekday regimes.


## Automated archive integrity verification

Added `backend/audit_nepse_holiday_api_archive.py` and four focused tests.
The auditor independently checks each archived year directory, HTTP status,
raw byte count, SHA-256, parsed/raw JSON equivalence, requested-year/date
consistency and duplicate dates. Duplicate holiday reasons are reported, not
silently removed. The auditor explicitly forbids canonical calendar promotion.

The integrated evidence workflow now runs this audit and uploads its report.
On commit `476a245e494fc43ecb84d27d80996041abe472ac`:

- Backend tests run `45624325569`: success.
- Integrated evidence audit run `45624325512`: success.
- Artifact ID `15027027115`; ZIP SHA-256
  `b65600839488e7a01ba81298effe25ca7f97897c713a147deef0b27a1a3a7b39`.
- The generated archive report confirms 12/12 valid year captures, 499 records,
  498 within-year unique dates, one duplicate-date row and zero integrity
  failures.

The same integrated artifact confirms the larger training-readiness gate is
still fail-closed: all 12 model-readiness blockers remain false. This is
expected; archived holiday records do not provide a verified open-session
calendar, universe snapshot, licensed OHLCV coverage, broker identity history,
corporate-action review or point-in-time holdout protocol.
