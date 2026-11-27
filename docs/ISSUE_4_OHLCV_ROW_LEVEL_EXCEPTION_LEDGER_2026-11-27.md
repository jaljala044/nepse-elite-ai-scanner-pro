# Issue #4 — OHLCV row-level exception ledger

## Reproducible baseline

The ledger generator consumes the immutable Actions artifact from workflow run `45397942163` (artifact `14921283424`, SHA-256 `e1e5e8ac84e1d2ad273b605725c69614693a831117f96a6b8d7f5af2b4c81cb8`). The source archives remain pinned to:

- `nepse-smc-data`: commit `937cfcf93d78dfcf28a9f09bb13291447988157b`
- `nepse-history-starter`: commit `b60728d39f34e0f9e428675d817fd52ed2784da6`

## Ledger population

The canonical backend generator emits one record per exception:

| Type | Count |
|---|---:|
| Invalid OHLC rows | 1,331 |
| Cross-source OHLCV conflict keys | 8 |
| **Total unique exception records** | **1,339** |

Disposition is evidence-aware:

- **1,331 invalid OHLC rows:** `quarantined_unresolved`; source arithmetic failures cannot be resolved by choosing a mirror or third-party value.
- **1 remaining source conflict (RHGCL, 2026-11-19):** `quarantined_unresolved`; both pinned source observations and file hashes are retained.
- **7 user-finalized conflicts:** the five 2025-07-28 records (BGWT, MEHL, RAWA, RHGCL, ULHC) plus API and HRL on 2026-11-19 use `resolved_with_user_authoritative_evidence`. The supplied values are embedded separately in `resolution_evidence.authoritative_values`; both original pinned-source observations remain preserved.

This produces 1,332 unresolved and seven user-authority-resolved records. The seven user-authority dispositions are narrowly allow-listed by exact symbol/date; the validator rejects using this disposition for any other key or for invalid-OHLC records.

## Provenance and limitations

- Every invalid row includes pinned repository commit/tree, ticker path, source-file SHA-256, original CSV line, raw row and normalized OHLCV.
- Every source conflict includes both repositories' pinned commit/tree, path, file SHA-256 and original row values.
- Conflict CSV line numbers were not present in the immutable audit artifact; they remain null rather than being inferred.
- SocrateAI external observations and file hashes are retained as third-party corroboration only, never treated as exchange-origin truth or an automatic repair.
- All unresolved cases remain excluded from canonical ingestion and prediction training.
- No raw CSV was modified, repaired, merged, clamped, interpolated or promoted.

## Reproducibility

`backend/build_ohlcv_exception_ledger.py` builds JSON and CSV from the pinned audit artifact inputs. `scripts/validate_ohlcv_exception_ledger.py` checks exact counts, unique IDs, allowed dispositions, required source evidence, SHA-256 shape, both sides of every conflict and JSON/CSV parity.

The new `OHLCV exception ledger` workflow downloads the original immutable artifact by run ID, generates the ledger, validates it and publishes JSON/CSV as a workflow artifact. A passing CI run is required before the generated artifact is considered validated.

## Current disposition

Implementation and CI validation are pending in draft PR. This report does not authorize canonical OHLCV promotion, price repair, training, or predictive-signal promotion.

## CI result — 2026-11-27

The ledger workflow passed on PR #179 head `979f37c10bbe00e9a0da6a661b3fb34271bf42b8` (run `45932511623`). It downloaded the original audit artifact and matched its SHA-256, generated the JSON/CSV outputs, passed the strict validator and passed all three ledger regression tests.

- Output artifact: `ohlcv-row-level-exception-ledger` (artifact ID `15169085846`)
- ZIP SHA-256: `0db218d52d2777df0fb6f2f1dbe4eea7b7f1c9d65a7ef52913aba6faed221fc7`
- JSON: 1,339 records; SHA-256 `1d7277067a6c839eb897b9d2d79fd3171840b8983d063c2fe34808c60b87ea46`
- CSV: 1,339 records; SHA-256 `05e8b607d5501f7abbb070fa07bd0d23c2f5b141ed1617ff01fa7762c738c859`
- Dispositions: 1,334 unresolved, five user-authority-resolved.

The separate repository-wide backend test workflow failed because the Issue #20 implementation module `app.historical_segment_eligibility` exists only on PR #177 and has not been merged to `main`. This is a cross-PR dependency, not a ledger-validator failure. PR #179 remains draft and Issue #4 remains open until this dependency is resolved and the pinned full audit is rerun/reconciled.

## Canonical pipeline integration

The first draft introduced a second, parallel builder. This was removed after review. PR #179 now extends the repository's existing `backend/build_ohlcv_exception_ledger.py` and its backend unit tests, so the normal `ohlcv-archive-row-audit` workflow produces the same canonical ledger. The builder accepts the SocrateAI cross-check JSON and attaches per-record corroboration status, external row, source comparisons and daily-file SHA-256 without selecting an external value.

The canonical audit workflow now runs the external cross-check before building the ledger. The dedicated PR workflow downloads the pinned original audit artifact and runs this same backend builder plus the strict JSON/CSV validator. The seven user-authoritative source-conflict keys are dispositioned separately; all invalid OHLC rows and RHGCL 2026-11-19 remain unresolved.

## User-authoritative resolution values

The five 2025-07-28 values are transcribed from the user-provided `NEPSE_Chart_Evidence.pdf`, page 1 (ShareHub daily OHLC and reconciled floorsheet totals). The API/HRL 2026-11-19 values are recorded in the user-finalized reconciliation at `nepse-smc-data` commit `e4d069c6ed292c127e7805b19f98e2837e999073`. The latter are accepted as user-final project values, not independently verified NEPSE records.

| Symbol/date | Open | High | Low | Close | Shares | Turnover (NPR) | Trades | VWAP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BGWT 2025-07-28 | 940.00 | 992.00 | 933.40 | 957.17 | 14,028 | 13,256,345.00 | 194 | — |
| MEHL 2025-07-28 | 471.10 | 480.50 | 460.00 | 475.63 | 29,753 | 14,008,898.10 | 333 | — |
| RAWA 2025-07-28 | 796.00 | 811.00 | 780.30 | 796.90 | 3,165 | 2,515,662.50 | 74 | — |
| RHGCL 2025-07-28 | 346.70 | 362.00 | 341.40 | 357.05 | 296,715 | 103,872,614.40 | 1,030 | — |
| ULHC 2025-07-28 | 509.00 | 515.00 | 495.00 | 510.75 | 32,288 | 16,273,342.10 | 300 | — |
| API 2026-11-19 | 331.00 | 334.20 | 330.00 | 331.80 | 105,340 | 34,929,701 | null | 331.59 |
| HRL 2026-11-19 | 483.00 | 488.00 | 483.90 | 483.90 | 49,184 | 23,836,472 | null | 484.64 |

Trade counts for API and HRL were not present in the reconciliation record and remain null. The PDF binary SHA-256 was not captured; no checksum is claimed. These dispositions do not authorize canonical promotion or raw source edits.

