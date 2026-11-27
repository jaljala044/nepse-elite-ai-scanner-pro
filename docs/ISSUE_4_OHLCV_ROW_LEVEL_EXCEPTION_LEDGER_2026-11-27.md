# Issue #4 — OHLCV row-level exception ledger

## Reproducible baseline

The ledger generator consumes the immutable Actions artifact from workflow run `45397942163` (artifact `14921283424`, SHA-256 `e1e5e8ac84e1d2ad273b605725c69614693a831117f96a6b8d7f5af2b4c81cb8`). The source archives remain pinned to:

- `nepse-smc-data`: commit `937cfcf93d78dfcf28a9f09bb13291447988157b`
- `nepse-history-starter`: commit `b60728d39f34e0f9e428675d817fd52ed2784da6`

## Ledger population

The deterministic generator emits one record per exception:

| Type | Count |
|---|---:|
| Invalid OHLC rows | 1,331 |
| Cross-source OHLCV conflict keys | 8 |
| **Total unique exception records** | **1,339** |

Disposition is evidence-aware:

- **1,331 invalid OHLC rows:** `quarantined_unresolved`; source arithmetic failures cannot be resolved by choosing a mirror or third-party value.
- **3 remaining source conflicts:** `quarantined_unresolved`; both pinned source observations and file hashes are retained.
- **5 conflicts on 2025-07-28 (BGWT, MEHL, RAWA, RHGCL, ULHC):** `resolved_with_user_authoritative_evidence`. The user explicitly designated their supplied records as final and authoritative for these five symbols on this date. Preserve the user's supplied OHLC chart readings and floorsheet quantity/turnover; ignore conflicting Source A/B/C values and do not leave these five keys unresolved because of those conflicts. The original archive observations remain in the ledger for traceability.

This produces 1,334 unresolved and five user-authority-resolved records. The five user-authority dispositions are narrowly allow-listed by exact symbol/date; the validator rejects using this disposition for any other key or for invalid-OHLC records.

## Provenance and limitations

- Every invalid row includes pinned repository commit/tree, ticker path, source-file SHA-256, original CSV line, raw row and normalized OHLCV.
- Every source conflict includes both repositories' pinned commit/tree, path, file SHA-256 and original row values.
- Conflict CSV line numbers were not present in the immutable audit artifact; they remain null rather than being inferred.
- SocrateAI external observations and file hashes are retained as third-party corroboration only, never treated as exchange-origin truth or an automatic repair.
- All unresolved cases remain excluded from canonical ingestion and prediction training.
- No raw CSV was modified, repaired, merged, clamped, interpolated or promoted.

## Reproducibility

`scripts/build_ohlcv_exception_ledger.py` builds JSON and CSV from the pinned audit artifact inputs. `scripts/validate_ohlcv_exception_ledger.py` checks exact counts, unique IDs, allowed dispositions, required source evidence, SHA-256 shape, both sides of every conflict and JSON/CSV parity.

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
