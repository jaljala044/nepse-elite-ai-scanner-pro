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
