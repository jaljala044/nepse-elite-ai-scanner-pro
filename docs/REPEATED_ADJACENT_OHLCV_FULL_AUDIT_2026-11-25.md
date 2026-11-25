# Repeated adjacent OHLCV audit — full archive result (2026-11-25)

## Execution

- Workflow: [Repeated adjacent OHLCV candidate audit](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45532881509)
- Run ID: 45532881509; run number 6; event: push
- Result: **success**. All seven substantive job steps completed, including checkout of both pinned archives, unit tests, full extraction, and artifact upload.
- Audit code commit: `f51deac3e2978c9fbf4bca6ebfce841d877c667a`
- Pinned `nepse-smc-data`: `937cfcf93d78dfcf28a9f09bb13291447988157b`
- Pinned `nepse-history-starter`: `b60728d39f34e0f9e428675d817fd52ed2784da6`
- Artifact: `repeated-adjacent-ohlcv-candidates` (artifact ID `14984793779`, 4,053,855 bytes, expires 2027-02-23)
- Artifact ZIP SHA-256: `f50c8f035cae8eece6b5066a4e4b85d19707e5a3a3097416dab42da02337ae2f`

## Extracted counts

| Source | Previous audit baseline | New extraction | Difference |
|---|---:|---:|---:|
| `nepse-smc-data` | 94,421 | 94,543 | +122 |
| `nepse-history-starter` | 102,121 | 102,241 | +120 |
| **Combined** | **196,542** | **196,784** | **+242** |

The extractor found 196,784 candidates across 483 symbols: 462 in `nepse-smc-data` and 483 in `nepse-history-starter`. Candidate current dates range from 2011-06-20 through 2026-11-20 in the SMC archive and 2024-03-06 through 2026-11-20 in History Starter.

## Artifact integrity checks

Independent local inspection of the downloaded artifact found:
- 196,784 CSV records, matching the JSON summary.
- 196,784 unique (repository, path, current CSV line) candidate identities.
- No missing date, line-number, file-hash or OHLCV evidence fields in candidate rows.
- All candidate CSV line numbers are consecutive (current line = previous line + 1).
- No invalid ISO date strings in the two candidate date fields.
- Every row is labelled `calendar_status_unverified_review_flag`.

## Interpretation and blockers

These are **review candidates, not invalid OHLCV records**. Identical adjacent values do not prove a market closure, missing session, stale data, or forward-fill. A valid trading session can produce unchanged OHLCV.

The +122 / +120 count differences against the previous baseline are not yet explained. Do not suppress or force these differences. Reproduce the prior count-generation method and compare at file/symbol/row level before accepting either count as reconciled.

The observed-date reference calendar remains unverified against primary NEPSE evidence. Therefore this report does not classify any candidate as a holiday, closure, missing session, or carry-forward. No source rows were modified, deleted, repaired, or forward-filled. Keep all candidates out of canonical rejection/repair logic until session evidence and row-level reconciliation are complete.

## Next acceptance work

1. Reproduce the baseline counting algorithm and isolate the +122 / +120 deltas by ticker and row.
2. Review duplicate dates, invalid OHLC, out-of-order rows and missing rows independently.
3. Obtain a primary-source NEPSE session calendar with source URL, retrieval time, raw response and SHA-256.
4. Join candidate pairs to verified session dates; distinguish true sessions, closures, holidays and unresolved dates.
5. Preserve unresolved cases as review-only; do not auto-repair or use them as training labels.


## Baseline reconciliation — 2026-11-25

The apparent +122 / +120 discrepancy is explained by scope differences between the broad row-adjacency extractor and the previous baseline metric:

- Exactly 120 candidates in each archive have adjacent CSV rows whose dates are more than one calendar day apart. The prior metric counted only identical signatures on consecutive calendar dates.
- Two additional `nepse-smc-data` candidates have a one-day date gap but violate OHLC bounds (AHPC, 2011-06-19 → 2011-06-20; API, 2016-09-03 → 2016-09-04). The previous baseline excluded these invalid OHLC rows.
- Therefore baseline-comparable counts are exactly 94,421 for `nepse-smc-data` and 102,121 for `nepse-history-starter`, matching the original audit.

The broader extractor is intentionally retained because date-gap repeats and repeated signatures on invalid OHLC rows remain useful review evidence. The updated extractor now emits `calendar_day_gap`, `ohlc_bounds_valid`, `baseline_metric_eligible` and `review_reason`, so these populations are separated rather than silently discarded.

This reconciliation does **not** verify NEPSE session dates. Consecutive calendar dates are not necessarily consecutive exchange sessions, especially across weekends, holidays and historical trading-week changes.


## Enriched rerun — successful

After adding explicit date-gap and OHLC-bound classifications, the full pinned-archive workflow ran again successfully:
- [Run #8](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45533449785), head commit `136d376cafed8ca36a1fbf061befe2383a775f0b`.
- Unit tests, both source checkouts, full extraction and artifact upload all succeeded.
- Artifact ID `14985599288`; ZIP SHA-256 `4b8b7c27c642fee768eb3b031928e785a5ef296dc346b4d5c3b8212ba09def67`.

The enriched artifact independently confirms:
- SMC: 94,543 total = 94,421 baseline-comparable + 120 date-gap candidates + 2 repeated signatures with invalid OHLC bounds.
- History Starter: 102,241 total = 102,121 baseline-comparable + 120 date-gap candidates + 0 invalid-bound candidates.
- Combined: 196,784 total = 196,542 baseline-comparable + 240 date-gap candidates + 2 invalid-bound candidates.

The JSON summary and CSV records agree. All 196,784 remain review-only; baseline eligibility means only consecutive calendar dates with OHLC bounds passing, **not** verified exchange sessions.


## Cross-archive candidate concordance check — 2026-11-25

The enriched workflow artifact was downloaded from GitHub Actions and independently inspected locally. The downloaded ZIP SHA-256 is `4b8b7c27c642fee768eb3b031928e785a5ef296dc346b4d5c3b8212ba09def67`, matching the workflow artifact digest. The CSV contains 196,784 rows and 15 columns.

A second-level comparison normalized the OHLCV JSON field (sorted keys, compact JSON) and grouped on `(symbol, previous_date, current_date, normalized_ohlcv)`:
- 102,246 distinct signature/date tuples across both archives.
- 94,538 tuples appear in both archives.
- 7,708 tuples appear in only one archive.

This is a reproducible archive-concordance statistic, not independent publisher confirmation: the two GitHub repositories may share upstream data or copied files. Do not count a match across mirrors as independent provenance. The 7,708 single-archive tuples are not automatically errors; they may reflect different date coverage, ticker coverage or archive histories.

Per-source archive scope in this artifact:
- `nepse-smc-data`: 462 symbol files; candidate current dates 2011-06-20 through 2026-11-20.
- `nepse-history-starter`: 483 symbol files; candidate current dates 2024-03-06 through 2026-11-20.

Year distribution of the 196,784 candidates:
- 2011: 1 invalid-OHLC-bound repeated signature.
- 2016: 3 consecutive-date valid-bound candidates and 1 invalid-OHLC-bound repeated signature.
- 2024: 69,036 consecutive-date valid-bound + 78 date-gap candidates.
- 2025: 84,732 consecutive-date valid-bound + 70 date-gap candidates.
- 2026: 42,771 consecutive-date valid-bound + 92 date-gap candidates.

The 196,542 consecutive-calendar-date candidates remain review-only, not exchange-session-confirmed. No source rows were modified. This analysis does not resolve the calendar blocker or authorize OHLCV repair/training.
