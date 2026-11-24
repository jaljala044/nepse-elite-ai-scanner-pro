# Jaljala OHLCV row audit — 2026-11-24

## Result

**Integrity gate: FAIL — do not promote either archive to canonical OHLCV.**

The read-only audit ran against the pinned default-branch commits below and fetched
all 525 ticker files from each repository. It parsed every row and compared overlapping
symbol/date observations. The JSON report is retained as GitHub Actions artifact
`nepse-historical-ohlcv-audit` for workflow run
[45397680346](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45397680346).

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
automatic winner is selected. The earlier inventory's 25 differing file blobs are
not the same metric as row-level conflicting keys: this run identifies eight
overlapping symbol/date records with different normalized values.

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
