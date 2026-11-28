# P4.11.5 — official classification API lifecycle recovery — 2026-11-28

## Source acquisition

Discovered `GET /api/nots/security/classification` in the public NEPSE frontend
bundle (`main.6ca32ef2df433b06ed55.js`). The endpoint returns every security
record with official `listingDate` and `tradingStartDate` fields. A dedicated
capture script (`backend/capture_nepse_security_classification.py`) retrieved
all 15 pages on 2026-11-28:

- 281 rows, 281 unique symbols, 0 duplicate symbols, 0 request errors.
- Raw per-page response bytes, headers and SHA-256 preserved under
  `data/evidence/raw/nepse/security-classification/2026-11-28/`
  (`capture-report.json`, `SHA256SUMS`, `parsed-classification.json`).
- Every lifecycle symbol (281/281) is present; `id` matches the crosswalk
  security IDs.

## Field semantics validation

`tradingStartDate` is the exchange's record of when trading started for the
security. Before using it, semantics were validated against known ground truth:

| Check | Result |
|---|---|
| BHCL register 2025-08-20 | API tradingStartDate 2025-08-20 — match |
| YMHL register 2026-06-22 | API tradingStartDate 2026-06-22 — match |
| NESDO register 2022-03-28 | API tradingStartDate 2022-03-28 — match |
| ULBSL register 2022-05-27 | API tradingStartDate 2022-05-27 — match |
| BGWT OHLCV first row | API tradingStartDate 2023-10-12 — match |
| HRL OHLCV first row | API tradingStartDate 2024-01-08 — match |
| MEHL OHLCV first row | API tradingStartDate 2023-09-25 — match |

`listingDate` is the share-listing date (typically 1–3 sessions before
`tradingStartDate` for IPOs). For pre-2008 listings `tradingStartDate` clusters
around 2007-07-25/29 — a system-migration artifact, not a first-trade date;
those rows are not promoted.

## Promotion rule applied

An unverified row was promoted only when **all** of the following held:

1. `tradingStartDate` ≥ 2023-01-01 (recent enough that security-record reuse by
   an older predecessor is implausible without archive traces).
2. `listingDate` within 45 days before `tradingStartDate` (fresh-IPO pattern).
3. `tradingStartDate` ≥ 2008-01-01 (outside the migration-artifact window).

**44 symbols promoted** to `verified_primary_notice` with `valid_from` =
`tradingStartDate`. Each row's note records the API field values, security id,
evidence path and the semantic validation basis. Matching `first_executed_trade`
events (`primary_nepse_notice` / `primary_notice_verified`) were appended to the
lifecycle event ledger (52 events total).

Promoted cohort includes AHL, ANLB, BEDC, BGWT, BHPL, CITY, CKHL, CLI, DOLTI,
GCIL, HATHY, HRL, IHL, ILI, KBSH, KDL, MAKAR, MANDU, MCHL, MEHL, MEL, MHCL,
MKCL, MKHC, MKHL, MMKJL, MSHL, NRM, NWCL, RNLI, RAWA, SONA, SPL, SMH, SMHL,
SMJC, SNLI, TAMOR, TVCL, TSHL, ULHC, UNLB, USHL, VLUCL.

## Intentionally not promoted

- **47 artifact rows**: `tradingStartDate` in the 2007 migration window;
  `listingDate` remains the only official date and is not a first-trade proof.
- **144 older rows** (2008–2022 `tradingStartDate`): official dates exist but
  the register's symbol-level `valid_from` convention cannot distinguish an
  original listing from a successor reusing an older security record (the
  NMLBBL/SMPDA pattern, where the API reports predecessor dates). These stay
  `unverified` pending symbol-lineage adjudication; their official
  `listingDate`/`tradingStartDate` candidates are preserved in
  `parsed-classification.json` for the next review pass.
- Verified secondary rows (NMLBBL 2024-05-19, SMPDA 2024-08-18, MATRI etc.)
  intentionally keep symbol-debut dates; the API reports predecessor security
  dates for those records. No conflict was raised because the two semantics
  (security trading start vs current-symbol debut) are documented separately.

## Validation

- `validate_equity_lifecycle_input.py`: 281 rows, 0 errors — **90 verified**
  (44 primary + 46 secondary), **191 unverified**. Promotion still disabled.
- `validate_security_lifecycle_event_ledger.py`: 52 events, 0 errors.
- `audit_historical_identity_readiness.py` runs clean: 46
  `first_executed_trade` events, `primary_notice_count` 46.
- `tests.test_security_lifecycle_event_ledger` (count updated 8→52),
  `tests.test_validate_equity_lifecycle_input`,
  `tests.test_historical_identity_readiness`: 15 tests pass locally.

## Limits and next work

- `tradingStartDate` is an exchange reference field, not a contract-level
  first-trade document; it is primary-source but coarser than floorsheet proof.
- The 191 remaining unverified rows need either symbol-lineage adjudication
  (to safely use security-level `tradingStartDate`) or dated first-trade
  notices. The official `listingDate` for the 47 artifact rows is recorded but
  unused pending first-trade evidence.
- Semantic decision needed: whether `valid_from` means security trading start
  or current-symbol debut. The register currently follows symbol-debut
  convention for merger successors.
