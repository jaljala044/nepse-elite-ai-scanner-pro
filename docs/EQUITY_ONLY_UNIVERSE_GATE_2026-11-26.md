# Equity-only universe gate — 2026-11-26

## Result

The versioned file `data/reference/nepse_active_equity_manifest_2026-11-26.csv` contains 281 records and was parsed from the repository snapshot during this work session.

Structural checks:
- 281 rows; 281 unique symbols; 281 unique security IDs.
- Every row is explicitly typed `Equity` and `Active`.
- Every row has the same observation date: 2026-11-26.
- Every row names NepseAlpha and the same source URL.
- Every row carries the same 64-character source snapshot SHA-256: `342d322bf438f27e9fe779fabac00ce0d40e24fd80f2c13dbb2cbcf3577ca7f8`.
- The three previously missing equity candidates are present: NESDO (8041), ULBSL (8063), YMHL (9342).
- NICEF is not in the equity manifest; it remains a mutual fund and is excluded from this scanner universe.
- No duplicate symbol or security ID was found.

## Code and tests

Added:
- `backend/app/equity_universe_manifest.py`: equity-only manifest validator. It checks declared type/status, date, source consistency, source hash, uniqueness and expected count. It does not infer type from ticker text.
- `backend/tests/test_equity_universe_manifest.py`: tests the actual checked-in 281-row CSV and negative cases for duplicate IDs/symbols, mutual funds/promoter/debenture records, inactive records, mixed source hashes, malformed symbols and count mismatch.

The validator deliberately returns:
- `manifest_structurally_validated=true`
- `membership_authoritatively_verified=false`
- `promotion_allowed=false`
- evidence tier `secondary_provider_snapshot`

## Evidence limitation and operational decision

This manifest is a dated **secondary-provider snapshot (NepseAlpha)**, not a raw NEPSE/SEBON primary registry response. Structural consistency and matching symbol/ID counts do not independently establish official exchange membership or effective-dated lifecycle. Therefore:

1. Use this file as the current 281-equity **candidate/working universe** for equity-only scanner development and coverage reconciliation.
2. Keep mutual funds, promoter shares, debentures, suspended and delisted records outside the current scanner universe.
3. Do not label this manifest exchange-authoritative, and do not promote it as canonical/training data.
4. Preserve the 2026-11-25 successor security-ID snapshot policy. Do not recover predecessor IDs or splice historical prices.
5. Continue primary-source membership/lifecycle validation and downstream per-equity coverage checks as separate gates.

## CI status

The new tests are part of the existing `backend-tests` workflow, which runs full unittest discovery on pushes to main. CI confirmation must be recorded from the resulting workflow run before marking the code gate complete.
