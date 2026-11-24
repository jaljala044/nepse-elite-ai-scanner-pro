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


## Follow-up triage — 2026-11-24

The retained workflow artifact `nepse-ohlcv-row-audit` (run 45397942163; SHA-256 ZIP digest recorded by GitHub as `e1e5e8ac84e1d2ad273b605725c69614693a831117f96a6b8d7f5af2b4c81cb8`) was downloaded and the 1,331 invalid Jaljala rows were joined to the SocrateAI cross-check by exact symbol/date.

| Cross-check result for the 1,331 invalid rows | Count | Disposition |
|---|---:|---|
| Partial/conflicting values | 1,320 | Quarantine; no automatic field substitution |
| Exact match to SocrateAI despite invalid OHLC | 5 | Quarantine; independent agreement does not make invalid OHLC arithmetically valid |
| No source matches external | 2 | Quarantine; source adjudication required |
| External daily file not published | 1 | Quarantine; evidence unavailable |
| Symbol absent from external daily file | 3 | Quarantine; evidence unavailable |
| **Total** | **1,331** | **Zero rows approved for automatic repair** |

The five exact matches are especially important: SocrateAI reproduces the same invalid values, so it is corroboration of the recorded values, not evidence that the OHLC candle is valid. For the 1,320 partial/conflicting rows, a field-level match is not sufficient authority to replace the entire source row. The two no-match rows and four rows without an independently usable external symbol/date observation cannot be resolved from this cross-check.

### Quarantine policy

- Keep the original Jaljala CSV bytes unchanged.
- Exclude all 1,331 rows from canonical OHLCV, feature generation, memory construction, backtests and signals until adjudicated.
- Preserve the original row, repository path, line number, source commit, source file hash, exact validation reason, external comparison status and external file hash.
- A correction requires an independently authorized source record for the same symbol/date and an append-only correction record linking old and replacement values. Never edit the raw source in place.
- The 196,542 repeated adjacent-calendar-row flags remain a separate calendar-classification queue; they are not included in the 1,331 invalid-row quarantine.

### Data rights and limits

The SocrateAI archive is declared MIT-licensed by its publisher, but it is not exchange-origin truth. The cross-check is limited to the 994 downloaded daily files; one requested date was not published. This triage does not establish completeness of the market archive, the session calendar, corporate-action adjustments or historical point-in-time availability.

**Decision: integrity gate remains FAIL.** No invalid row was silently repaired or promoted.
