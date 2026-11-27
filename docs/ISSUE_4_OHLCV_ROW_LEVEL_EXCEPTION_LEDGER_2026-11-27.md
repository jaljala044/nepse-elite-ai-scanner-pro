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
- Every cross-source conflict retains both original source CSV line numbers inside each repository's `source_evidence` record; all 16 source-line references were verified against the exact pinned files.
- SocrateAI external observations and file hashes are retained as third-party corroboration only, never treated as exchange-origin truth or an automatic repair.
- All unresolved cases remain excluded from canonical ingestion and prediction training.
- No raw CSV was modified, repaired, merged, clamped, interpolated or promoted.

## Reproducibility

`backend/build_ohlcv_exception_ledger.py` builds JSON and CSV from the pinned audit artifact inputs. `scripts/validate_ohlcv_exception_ledger.py` checks exact counts, unique IDs, allowed dispositions, required source evidence, SHA-256 shape, both sides of every conflict and JSON/CSV parity.

The new `OHLCV exception ledger` workflow downloads the original immutable artifact by run ID, generates the ledger, validates it and publishes JSON/CSV as a workflow artifact. A passing CI run is required before the generated artifact is considered validated.

## Current disposition

Implementation and exact-head CI validation are complete in draft PR #179. This report does not authorize canonical OHLCV promotion, price repair, training, or predictive-signal promotion.

## CI result — latest exact PR head `58f0ed0828ca393fff839fd1a4ac17abbc0a114d`

All three exact-head workflows passed:

- OHLCV exception ledger run [45933953438](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45933953438): **passed**. It reran the pinned source archive audit, cross-checked SocrateAI unadjusted EOD, generated the canonical ledger, validated JSON/CSV, passed ledger regression tests and uploaded the artifact.
- Backend unit tests run [45933953436](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45933953436): **passed**.
- Backend contract tests run [45933953451](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45933953451): **passed**.

The pinned audit rerun scanned all 525 files in each source repository (314,712 SMC rows and 301,632 History Starter rows), and retained 1,331 invalid OHLC rows and eight cross-source conflict keys. The audit report now records original CSV line numbers for both sides of all eight conflicts (16 source-line references); they are no longer null or inferred. SocrateAI cross-check downloaded 994 daily files; one was not published. The audit integrity gate remains **not clean by design** while exceptions exist; the ledger workflow passes because it preserves and classifies exceptions rather than suppressing them.

- Generated artifact: [15169872483](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45933953438/artifacts/15169872483), retained through 2027-02-25.
- Artifact ZIP SHA-256: `7b0327ab21da3ef175f878be349146920cde7e94b3f9e612900f71c03c8a044a`
- Ledger JSON SHA-256: `d8ef3f15ab38def0a8f2e71212fcb6b8eaf1636d07de118f4b860398f5ed21be`
- Ledger CSV SHA-256: `43b19ba98703b32274064eedf55daf675d9c5cd31039315f97bb45aa0aff5afe`
- Counts: 1,339 unique exceptions; 1,331 invalid OHLC; eight conflicts; 1,332 unresolved; seven user-authoritatively resolved.
- Independent downloaded-artifact inspection confirmed 1,339 JSON/CSV rows, identical unique ID sets, zero per-field JSON/CSV mismatches, all 1,331 invalid rows carrying their violated rule, 16 valid conflict source-line references, and seven resolution payloads with canonical promotion disabled.

PR #179 remains draft/open/unmerged pending independent review. No raw source edits or canonical OHLCV promotion are authorized.

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


## Final pinned rerun with conflict line-number provenance — 2026-11-27

The exact pinned-commit rerun and canonical ledger pipeline passed on PR head `58f0ed0828ca393fff839fd1a4ac17abbc0a114d`:

- Workflow: [OHLCV exception ledger run 45933953438](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45933953438)
- Backend unit tests: [45933953436](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45933953436)
- Backend contract tests: [45933953451](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45933953451)
- Output artifact: [15169872483](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45933953438/artifacts/15169872483)
- Artifact ZIP SHA-256: `7b0327ab21da3ef175f878be349146920cde7e94b3f9e612900f71c03c8a044a`
- Audit JSON SHA-256: `e91b19819c3e6a802dbfc5fc2b44e591f8de064bb873a810b14f22cb2a578ebb`
- SocrateAI cross-check JSON SHA-256: `d7b1201098c1a0c73efc53c3274e102f0c058686b07d9226659f63114c99f60e`
- Ledger JSON SHA-256: `d8ef3f15ab38def0a8f2e71212fcb6b8eaf1636d07de118f4b860398f5ed21be`
- Ledger CSV SHA-256: `43b19ba98703b32274064eedf55daf675d9c5cd31039315f97bb45aa0aff5afe`

The audit re-fetched all 525 OHLCV files from each exact pinned commit (1,050/1,050 files; zero download errors), totaling 314,712 rows from `nepse-smc-data` and 301,632 from `nepse-history-starter`. Counts remained unchanged: 1,331 invalid OHLC rows, eight cross-source conflict keys, zero duplicate dates, zero out-of-order transitions, 196,542 repeated-adjacent-calendar flags, 25 blob-level differences, and eight row-level conflicts. The audit gate correctly remains FAIL; repeated rows are review flags and are not automatically deleted.

The SocrateAI cross-check used commit `70324524df83eaa7c2964441ad4026d6ab00cc7e`, covering all 1,339 exception candidates across 995 dates: 994 daily files downloaded, one not published, zero download errors. Classifications: 1,325 partial/conflicting, five all-source matches, three one-source matches, two no-source matches, three symbols absent, and one daily file not published. This is third-party corroboration, not exchange-origin truth.

The audit now retains original CSV line numbers on every normalized valid observation. Each of the eight conflict records contains the source file SHA-256 and the exact original CSV line for both source repositories; the strict validator rejects a missing/invalid conflict line. The final JSON and CSV each contain 1,339 unique records with identical ID sets. All 1,339 records retain external corroboration metadata. Seven user-authoritative conflicts are separately documented (five 2025-07-28 records plus API and HRL on 2026-11-19); 1,332 records remain quarantined unresolved.

The read-only builder test also asserts that the source audit JSON bytes remain unchanged and that the output stores their SHA-256. No raw OHLCV rows were modified, repaired, merged or promoted.


## Invalid-row evidence triage — 2026-11-27

A read-only analysis of the latest downloaded ledger classified all 1,331 quarantined invalid rows by their raw OHLC relationships. This is a structural triage, not a repair or source-of-truth decision.

| Mutually exclusive raw-value pattern | Rows |
|---|---:|
| High is below open or close, while high is not below low | 774 |
| Low is above open or close, while low is not above high | 535 |
| High is below low | 22 |
| **Total** | **1,331** |

Both sides of the original validation rule remain preserved verbatim in `validation_rule_violated`; the categories above are derived only for review. All 1,331 invalid rows originate from the pinned `nepse-smc-data` snapshot.

Concentration by symbol:

| Symbol | Invalid rows |
|---|---:|
| AHPC | 588 |
| SKBBL | 379 |
| API | 122 |
| MERO | 102 |
| SPDL | 53 |
| CHL | 45 |
| HIDCL | 30 |
| Other eight symbols combined | 12 |

The SocrateAI corroboration metadata for these 1,331 records classifies 1,320 as partial/conflicting, five as all-source matches, two as no-source matches, three as symbol not present in the external daily file, and one as external daily file not published. It is third-party EOD corroboration only; even an external match does not authorize overwriting an invalid source row.

No pattern is treated as a proven transposition, column shift, or vendor error. Every row remains quarantined until exchange-origin evidence or a documented, independently reviewed correction establishes the actual values. No historical prices, model features, or signals are promoted from this triage.

## Closure status

The ledger implementation, source-lineage, exact pinned rerun, corroboration attachment, deterministic JSON/CSV validation and regression tests are complete. The source-quality gate itself remains FAIL because 1,331 invalid rows and one non-user-authoritative conflict (RHGCL 2026-11-19) remain quarantined; this does not authorize canonical OHLCV promotion. PR #179 is stacked on PR #177 (Issue #20 evaluator), remains draft, and still requires independent review and integration of its base dependency. Do not close Issue #4 or merge this stacked PR until the PR base is integrated and the final review is complete.

## Latest exact-head validation — 2026-11-27

Current PR head: `ae4b9b28378fabadb00a72f9eb61b18235c1efa9`. All three workflows completed successfully on this exact head:

- [OHLCV exception ledger — run 45934659355](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45934659355)
- [Backend contract tests — run 45934659385](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45934659385)
- [Backend unit tests — run 45934659415](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45934659415)

The exact-head ledger run fetched and audited all 525 files from each pinned source repository (1,050/1,050; zero download errors), covering 314,712 SMC rows and 301,632 History Starter rows. It identified 25 differing blobs among 525 common paths in the complete pinned-tree comparison, 1,331 invalid OHLC rows, eight cross-source conflict keys, zero duplicate dates, zero out-of-order transitions, and 196,542 repeated-adjacent-calendar flags. The latter remain review flags, not automatic deletions. SocrateAI cross-check downloaded 994 daily files, with one date not published and zero download errors.

- Artifact [15170257741](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45934659355/artifacts/15170257741)
- Artifact ZIP SHA-256: `a427eba723b7acc1e76aa34ac30da125d656726050ee3416f2b64bf642cde2a9`
- Audit JSON SHA-256: `99c50ddd994b6d5642b965952f707f71149a05f44051c1b73af3c9fd65aa3997`
- SocrateAI cross-check JSON SHA-256: `c5f041321d07ff59316ebd7e9d19d69eaae8be83fe85239591cc72ce299450fc`
- Ledger JSON SHA-256: `4c216f3f1e83e61c2047d2dd1cae10ba5ebf2e21f9faffcab0a9d51ad3534665`
- Ledger CSV SHA-256: `43b19ba98703b32274064eedf55daf675d9c5cd31039315f97bb45aa0aff5afe`

Downloaded-artifact inspection independently confirmed 1,339 JSON rows and 1,339 CSV rows, identical unique exception IDs, zero field or nested-evidence mismatches, 1,331 invalid rows each carrying a specific violated rule, all 16 conflict source-line references present, and seven resolution payloads with canonical promotion disabled. Dispositions: 1,332 unresolved; seven user-authoritatively resolved. The archive audit's integrity gate remains FAIL while unresolved source-quality exceptions exist; the ledger workflow succeeds because it preserves and validates those exceptions.



## Disposition correction — 2026-11-28

The earlier seven-record description above is superseded by the field-scoped correction in the current PR branch:

| Disposition | Records | Keys |
|---|---:|---|
| User-authoritative project values | 5 | BGWT, MEHL, RAWA, RHGCL, ULHC — 2025-07-28 only |
| Captured NEPSE field-scoped evidence | 2 | API and RHGCL — 2026-11-19 |
| Source conflict retained | 1 | HRL — 2026-11-19 |
| Invalid OHLC rows quarantined | 1,331 | All original invalid rows |
| **Total** | **1,339** | |

API and RHGCL 2026-11-19 are no longer classified as user-authoritative. Their resolution evidence is separately typed as `resolved_with_nepse_field_evidence` and lists only the fields supported by the captured NEPSE security-history responses. The response omits `open`; the ledger explicitly records that omission and does not infer an opening price. RHGCL's supported fields include high, low, close, volume (9,054) and trades (47).

HRL 2026-11-19 remains `quarantined_unresolved` as a source conflict. Preserve the user-finalized project low NPR 483.90 and the NEPSE/ShareHub observed low NPR 480.00 side by side. The project value is not silently replaced, but it is not re-labelled as exchange-verified. The OHLC geometry discrepancy (open NPR 483.00 versus project low NPR 483.90) remains visible.

The corrected disposition totals are 1,332 unresolved (1,331 invalid rows plus HRL), five user-authoritative resolutions and two field-scoped NEPSE resolutions. Neither resolution class permits canonical promotion or source-row mutation. Regression tests and the strict validator now enforce the exact keys and supported field sets.
