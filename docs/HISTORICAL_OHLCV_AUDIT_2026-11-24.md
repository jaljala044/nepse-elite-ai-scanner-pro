# Jaljala OHLCV row audit — 2026-11-24

## Result

**Integrity gate: FAIL — do not promote either archive to canonical OHLCV.**

The read-only audit ran against the pinned default-branch commits below and fetched
all 525 ticker files from each repository. It parsed every row and compared overlapping
symbol/date observations. The OHLCV report and SocrateAI cross-check are retained as
GitHub Actions artifacts for workflow run
[45397942163](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45397942163).

| Measure | `nepse-smc-data` | `nepse-history-starter` |
|---|---:|---:|
| Pinned commit | `937cfcf93d78dfcf28a9f09bb13291447988157b` | `b60728d39f34e0f9e428675d817fd52ed2784da6` |
| Pinned tree | `5b4f7593523b92fe81b6cd3cb09584b256760314` | `a0cff911b0eb3610b935f6c93b63ddeb971ea283` |
| OHLCV files found / audited | 525 / 525 | 525 / 525 |
| Rows | 314,712 | 301,632 |
| Unique symbol/date keys | 313,381 | 301,632 |
| Invalid OHLC rows | 1,331 | 0 |
| Duplicate dates within ticker | 0 | 0 |
| Out-of-order transitions | 0 | 0 |
| Repeated adjacent calendar-row flags | 94,421 | 102,121 |
| Download errors | 0 | 0 |

Across the two sources, 293,863 symbol/date keys overlap. Eight overlapping keys
have differing OHLCV values:

| Symbol | Date |
|---|---|
| API | 2026-11-19 |
| BGWT | 2025-07-28 |
| HRL | 2026-11-19 |
| MEHL | 2025-07-28 |
| RAWA | 2025-07-28 |
| RHGCL | 2025-07-28 |
| RHGCL | 2026-11-19 |
| ULHC | 2025-07-28 |

The full source values for each conflict are retained in the JSON artifact. No
automatic winner is selected. A targeted SocrateAI unadjusted-EOD cross-check then
reviewed 1,339 candidates (the 1,331 invalid rows plus eight Jaljala source conflicts)
across 995 dates. It downloaded 994 daily files; one date was not published and
there were no download errors. Classifications were: 1,325 partial/conflicting,
five all-source matches, three one-source matches, two no-source matches, three
symbols absent from the external daily file, and one external daily file not published.
These are corroboration outcomes only: SocrateAI is a separate publisher, not an
exchange-origin truth source. The five matches do not repair invalid OHLC bounds.
The cross-check report retains source comparisons and external file hashes.

The 25 blob-level differences were rechecked from the exact pinned commits. All
525 relative ticker paths exist in both repositories; 500 file blobs are identical
and 25 have different blob SHAs. Those 25 files are:
`API, ULHC, RAWA, AHPC, KEF, MERO, SPDL, SMJC, HLI, CHL, HDHPC, HIDCL, UNHPL,
RADHI, UAIL, MEHL, HRL, BGWT, SOHL, KDBY, SKBBL, NRIC, NIFRA, RHGCL, MEL`.
Blob inequality is not automatically a row-level market-data conflict: this audit
finds eight overlapping symbol/date records with different normalized values.
Both kinds of discrepancy are retained for reconciliation.

## Invalid OHLC rows

All 1,331 invalid rows are in `nepse-smc-data`:
- 796 rows where high is below open, low or close.
- 535 rows where low is above open, high or close.

The source files remain untouched. These rows require source-owner review or an
independent source correction record; they must not be silently repaired.

## Repeated adjacent rows

The two archives contain 196,542 combined adjacent-calendar-date identical OHLCV
signatures. These are **review flags, not automatically invalid rows**. They may be
carry-forward/non-session rows, but an unchanged candle can also occur on a genuine
session. The session calendar must classify each date before the rows can be accepted
or quarantined. Never delete them merely because the values repeat.

## What this audit proves — and does not prove

- It proves all 1,050 discovered Jaljala ticker CSV files were downloaded and parsed
  from the pinned commits without download errors.
- It proves the row-level arithmetic/shape findings and eight overlapping source
  conflicts shown above.
- It does not prove that every NEPSE session or every expected ticker is present.
- It does not prove the actual exchange-open/closed status of any date.
- It does not reconcile floorsheets, broker summaries, indices, corporate actions,
  symbol lifecycle, adjusted/unadjusted series or point-in-time availability.
- It does not authorize any third-party data redistribution.

## Required remediation before canonical promotion

1. Resolve or formally quarantine all 1,331 invalid OHLC rows with immutable raw
   source evidence and row-level reason.
2. Investigate the eight source conflicts against an independently authorized
   exchange-origin or licensed source; retain both source versions.
3. Build and verify the date-level exchange calendar, including the 2022 and 2026
   weekly schedule changes, holidays, exceptional openings and closures.
4. Classify all repeated adjacent rows against that verified calendar; preserve
   raw rows and quarantine non-session carry-forward observations.
5. Reconcile the full symbol universe and file coverage, including the 25 blob-level
   file differences from the earlier inventory.
6. Run equivalent source-separated audits for floorsheets, indices, broker summaries
   and corporate actions; validate source rights and point-in-time availability.
7. Re-run the complete audit and require zero unexplained exceptions before
   canonical ingestion.

Predictive intelligence and scanner promotion remain blocked until these gates pass.


## Exception ledger generation — 2026-11-25

A machine-readable exception ledger was generated from the immutable Actions artifact for workflow run `45397942163` (artifact ID `14921283424`, SHA-256 `e1e5e8ac84e1d2ad273b605725c69614693a831117f96a6b8d7f5af2b4c81cb8`).

- 1,331 invalid OHLC rows and eight cross-source conflicts; 1,339 unique exception IDs.
- All 1,339 dispositions are `quarantined_unresolved`.
- JSON and CSV row counts and exception-ID sets match.
- Every invalid row retains its pinned source commit, ticker path, source-file SHA-256, CSV line and raw row.
- Each of the eight conflicts retains both source repositories' pinned commit, path, file SHA-256 and source row. Original source CSV line numbers are unavailable in the audit artifact and remain null; they are not inferred.
- Local validation passed against the generated JSON and CSV.

The validator is committed at `scripts/validate_ohlcv_exception_ledger.py`, with regression tests at `tests/test_ohlcv_exception_ledger.py`. The full ledger files were generated as local deliverables but have **not** yet been committed to this repository. No source OHLCV file was modified, repaired, merged or promoted.
