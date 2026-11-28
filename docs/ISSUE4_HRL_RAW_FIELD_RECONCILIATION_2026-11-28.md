# Issue #4 follow-up — HRL 2026-11-19 raw-field reconciliation

Generated 2026-11-28 by inspecting the merged row-level ledger artifact from PR #355 (workflow artifact `15274540199`).

## Finding: project-designated low is not the raw source low

The current ledger correctly keeps the HRL conflict unresolved, but its project-owner context labels NPR 483.90 as a project-designated **low**. The pinned raw source rows in the same ledger show:

| Source | Pinned commit | CSV line | Open | High | Low | Close | Volume |
|---|---|---:|---:|---:|---:|---:|---:|
| History Starter | `b60728d39f34e0f9e428675d817fd52ed2784da6` | 935 | 483.00 | 488.00 | **480.00** | **483.90** | 49,184 |
| SMC Data | `937cfcf93d78dfcf28a9f09bb13291447988157b` | 654 | 483.00 | 488.00 | **480.00** | 486.00 | 18,817 |

The external SocrateAI cross-check in the same artifact reports open 483.00, high 488.00, low 480.00, close 483.90, volume 49,148. It is corroborative only, not exchange-origin truth.

Thus NPR 483.90 is the History Starter close in the pinned raw row and is also the external cross-check close; it is not the low field in either pinned raw archive row. The user-designated project context (`open=483.00, low=483.90`) must remain preserved as a separate project-owner assertion, but it must not be described as a raw-source field or used to overwrite the raw row.

## Correct unresolved conflict framing

- Raw low agrees across both pinned archives and the external cross-check at NPR 480.00.
- History Starter close is NPR 483.90; SMC Data close is NPR 486.00; external cross-check close is NPR 483.90.
- Raw volumes differ: 49,184 / 18,817 / 49,148.
- The user-designated project context labels 483.90 as low, which conflicts with the raw-field mapping and requires owner clarification.
- Do not infer which close or volume is the official exchange value from this cross-check.
- Keep the HRL conflict quarantined and unresolved until the project-owner field designation and authoritative exchange evidence are reconciled.

## Artifact integrity check

Downloaded PR #355 workflow artifact `15274540199`:
- ZIP SHA-256: `7b4fbaf618bf4801ad1e61e10e745c55013a371067e052ad7a60f42f82aee3f3`
- JSON ledger: 1,339 records, 1,339 unique exception IDs.
- CSV ledger: 1,339 records, 1,339 unique exception IDs.
- JSON/CSV exception-ID sets match.
- Counts: 1,331 invalid OHLC rows; 8 cross-source conflict keys; 1,332 quarantined unresolved; 5 user-authoritative dispositions; 2 field-scoped NEPSE dispositions.
- No raw data or canonical data was changed.

## Acceptance boundary

This is a field-mapping audit note, not a correction or adjudication. Keep HRL unresolved. No canonical, training, backtest, scanner or AI recommendation promotion is authorized by this note.
