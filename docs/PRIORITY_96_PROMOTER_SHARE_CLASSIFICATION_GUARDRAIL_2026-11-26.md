# Priority 96 — explicit promoter-share classification guardrail (2026-11-26)

## Change

- Added `promoter_share` as a recognized non-target instrument class in both the dated instrument-manifest validator and the immutable universe-snapshot validator.
- Promoter-share rows can now be retained in lifecycle/audit records without being counted as ordinary equity or mutual-fund target instruments.
- The snapshot validator rejects any promoter-share row marked `target_in_scope: true`.
- Added regression tests proving an active promoter-share lifecycle row remains auditable, contributes zero active target rows, and cannot be promoted into the equity/mutual-fund target universe.

## Scope and safety

- This is a classification/validation change only. It does not add HIDCLP, NIMBPO, HEIP, NMLBBLP, or any other promoter-share symbol to the canonical universe.
- It does not alter OHLCV, floorsheet, or owner-finalized historical records.
- The four Priority 95 ID matches remain dated-snapshot mappings; effective-dated identity continuity is still open.
- No training-data promotion is authorized by this change.

## Validation

- Regression tests added to `backend/tests/test_instrument_manifest.py` and `backend/tests/test_universe_snapshot.py`.
- Repository CI has not yet been run for this commit; tests are committed but not represented as passing until CI confirms.
