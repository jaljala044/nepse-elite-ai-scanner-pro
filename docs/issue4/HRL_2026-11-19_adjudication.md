# HRL 2026-11-19 — OHLCV Source Conflict Adjudication

## Status

**QUARANTINED / UNRESOLVED — pending project-owner decision**

Default disposition: **Option C — Keep quarantined**. No decision has been made or inferred on behalf of the project owner.

- Canonical promotion: **NOT ALLOWED**
- Training/backtest/scanner eligibility: **NOT ALLOWED**
- Raw source modification, deletion, merge or forward-fill: **NOT ALLOWED**

## Scope and identity

- Symbol: `HRL`
- Trade date: `2026-11-19`
- Exception ID: `cross_source_ohlcv_conflict:HRL:2026-11-19`
- Pinned artifact: Issue #4 OHLCV exception ledger, workflow artifact [15274540199](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/460?).
- Artifact ZIP SHA-256: `7b4fbaf618bf4801ad1e61e10e745c55013a371067e052ad7a60f42f82aee3f3`
- Ledger JSON SHA-256: `1b8e8a0967cdb2c0d4293a786c0f3ad687994e4075e50544836aabb174486106`
- Ledger CSV SHA-256: `74d2f2af6f3687fb82f28c9a29865babd4130ed512d5815a0534fe5ee6624616`

## Observed values

The two pinned project archive rows agree on open, high and low, but disagree on close and volume. NPR 483.90 is the History Starter **close**, not its low.

| Field | History Starter (NPR / shares) | SMC Data (NPR / shares) | Source provenance |
|---|---:|---:|---|
| Open | 483.00 | 483.00 | Pinned raw archive row |
| High | 488.00 | 488.00 | Pinned raw archive row |
| Low | **480.00** | **480.00** | Pinned raw archive row |
| Close | 483.90 | 486.00 | Pinned raw archive row |
| Volume | 49,184 | 18,817 | Pinned raw archive row |

### Pinned source provenance

| Repository | Commit | Source path | CSV line | Source-file SHA-256 |
|---|---|---|---:|---|
| [nepse-history-starter](https://github.com/jaljala044/nepse-history-starter/blob/b60728d39f34e0f9e428675d817fd52ed2784da6/03_stock_charts_ohlcv/HRL_OHLCV.csv#L935) | `b60728d39f34e0f9e428675d817fd52ed2784da6` | `03_stock_charts_ohlcv/HRL_OHLCV.csv` | 935 | `2aaac3df4b8bf236d1d1864fc5af96e6548eac95dc20c23f97cec82d0c972db3` |
| [nepse-smc-data](https://github.com/jaljala044/nepse-smc-data/blob/937cfcf93d78dfcf28a9f09bb13291447988157b/03_stock_charts_ohlcv/HRL_OHLCV.csv#L654) | `937cfcf93d78dfcf28a9f09bb13291447988157b` | `03_stock_charts_ohlcv/HRL_OHLCV.csv` | 654 | `2d4c103cc07d54bd8b197784763c9a5f8c4a6fe014452ae0c91f28d03ccbc83b` |

### Separate project-owner assertion

| Field | Value | Classification |
|---|---:|---|
| Project-designated open | 483.00 | Project-owner context; not a separate raw source row |
| Project-designated low | 483.90 | Project-owner context; conflicts with raw field mapping |

The project designation `low=483.90` is retained as a separate assertion. It is not relabelled as a raw-source low. In the History Starter row, 483.90 is the close.

### Third-party corroboration (not exchange-origin truth)

The pinned external SocrateAI daily observation reports open 483.00, high 488.00, low 480.00, close 483.90 and volume 49,148. Its daily-file SHA-256 is `3aa11c4a60b7407599890d065b5c32caa383d654dfdeac9ae9dd577dc6a7cb3c`. This is third-party corroboration only and does not establish an official NEPSE value.

## Geometry check

OHLC geometry requires:

- `high >= max(open, close, low)`
- `low <= min(open, close, high)`
- `low <= high`
- all prices > 0

**Raw archive rows:** Both pinned rows have open 483.00, high 488.00 and low 480.00; the geometry is valid for both recorded closes (483.90 and 486.00).

**Project-designated values:** open 483.00 versus designated low 483.90 violates the low-bound condition (`low <= open`). The project designation is therefore geometrically invalid if interpreted as the OHLC low.

The raw low agreement does not resolve the separate close and volume disagreement between the two pinned archives.

## Evidence findings

1. Both pinned project archive rows record low = NPR 480.00.
2. The project-designated NPR 483.90 is not the low field in either pinned archive row; it is the History Starter close and matches the third-party close.
3. The pinned archives disagree on close (483.90 versus 486.00) and volume (49,184 versus 18,817).
4. The external daily observation is corroborative only; it is not first-party NEPSE evidence.
5. No source values have been modified, deleted, merged, clamped or forward-filled.
6. The current ledger disposition remains `quarantined_unresolved`.

## Options — project owner must choose one

- [ ] **Option A — Confirm raw low NPR 480.00**
  - Retain project-designated 483.90 in provenance as `project_designated_low` (non-canonical).
  - The raw low geometry is valid.
  - This decision resolves only the low-field designation. It does **not** resolve the close or volume conflict.
  - Requires explicit project-owner sign-off and authoritative evidence for any additional field resolution.

- [ ] **Option B — Retain project-designated low NPR 483.90**
  - Preserve 480.00 as `raw_low` in provenance.
  - Record an explicit geometry exception: low 483.90 exceeds open 483.00.
  - This option remains OHLC-invalid and cannot be admitted to canonical OHLCV or model training without a separately justified, approved exception policy.
  - Requires project-owner sign-off and written justification.

- [x] **Option C — Keep quarantined (default; no owner decision recorded)**
  - No canonical promotion.
  - Status remains `QUARANTINED / UNRESOLVED`.
  - Preserve both pinned rows and the project assertion unchanged.
  - Continue to exclude this conflict from canonical ingestion and training.

## Decision

- Chosen option: **C (default only; pending project-owner decision)**
- Decided by: **Not yet recorded**
- Date: **Not yet recorded**
- Justification: No explicit project-owner adjudication is attached to this record. The safe default is to preserve all evidence and keep the conflict quarantined. No owner decision is inferred from prior context.

## Sign-off

- [ ] Project owner approval
- [ ] Independent reviewer confirmation
- [x] Both pinned source rows and the project-designated value preserved in provenance
- [x] No silent replacement of either value
- [x] Canonical promotion remains disabled

## Review metadata

- Prepared: 2026-11-28
- Preparer: automated repository documentation update; human reviewer not yet assigned
- Independent review status: **PENDING**
- Next action: project owner to select A, B or C and record identity, date and evidence; independent reviewer to verify the ledger and sign-off before any PR is merged.
