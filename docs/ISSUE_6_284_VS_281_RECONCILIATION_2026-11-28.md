# Issue #6 — 284-versus-281 equity-universe reconciliation

**Status: PARTIAL / LOW CONFIDENCE.** The 281-row candidate manifest is structurally reconciled; the 284-entry comparison is not reproducible at symbol level because the captured 284-row source export is not retained.

## Evidence

| Evidence | Result | Interpretation |
|---|---:|---|
| Dated candidate manifest, 2026-11-26 | 281 rows, 281 unique symbols and IDs | Secondary-provider equity candidate snapshot; not exchange certification |
| Declared source snapshot SHA-256 | 342d322bf438f27e9fe779fabac00ce0d40e24fd80f2c13dbb2cbcf3577ca7f8 | Shared source snapshot identity in manifest |
| NepseAlpha active-traded-stock page | 284 entries reported in prior source research | Count-only discrepancy; raw 284-row export and capture hash unavailable |
| Candidate additions | NESDO/8041, ULBSL/8063, YMHL/9342 | Dated secondary listing/classification evidence; included in 281 candidates |
| Historical identity register | 36 records | Includes predecessor/successor and non-equity lifecycle cases; many IDs/effective intervals unresolved |

## Current result

- Candidate manifest rows: **281**.
- Unique candidate symbols / IDs: **281 / 281**.
- Duplicate candidate symbols / IDs: **0 / 0**.
- Provider page count claim: **284**.
- Arithmetic difference: **3**, but no extra symbols can be named safely from a count alone.
- Symbol-level comparison with 284 page: **not computed**; raw provider export unavailable.
- Do not interpret the count gap as three extra or missing equities. The page may include other actively traded instrument classes; instrument type and status must be checked row by row.

## Implemented reconciliation utility

backend/reconcile_equity_universe.py compares two preserved CSV snapshots and reports candidate-only/provider-only symbols, duplicate rows, security-ID/type/status conflicts, source hashes, row counts and unique-symbol counts.

Run:

```bash
python backend/reconcile_equity_universe.py \
  --candidate data/reference/nepse_active_equity_manifest_2026-11-26.csv \
  --provider /path/to/preserved_284_entry_snapshot.csv \
  --candidate-date 2026-11-26 \
  --provider-date 2026-11-25 \
  --output reports/issue6_284_vs_281.json
```

The provider input must preserve raw symbol, security ID, instrument type and status. No target count is forced; duplicates and conflicts are retained.

## Required evidence to close

1. Preserve the exact 284-row export (original bytes, URL, capture timestamp, content type and SHA-256).
2. Reconcile all rows against the 281 manifest by symbol and security ID.
3. Classify the count difference by instrument type and status; do not assume the three records are equities.
4. Cross-check conflicts against dated NEPSE/SEBON or independent provider evidence.
5. Keep unresolved aliases, lifecycle intervals and identities unresolved.
6. Obtain independent review before any membership approval.

## Safety disposition

- Membership authoritatively verified: **false**.
- Canonical promotion: **not allowed**.
- Scanner admission from this comparison alone: **not allowed**.
- Confidence: **LOW** for the 284-versus-281 identity difference; **HIGH** for structural uniqueness of the 281-row candidate file.
