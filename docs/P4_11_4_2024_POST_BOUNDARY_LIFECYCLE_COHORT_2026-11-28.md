# P4.11.4 — 2024 post-boundary lifecycle start cohort — 2026-11-28

## Scope and method

Priority-queue item 1 (P1 lifecycle) requires recovering first-trade dates for the
unverified rows in `data/reference/nepse_equity_lifecycle_coverage_input_2026-11-26.csv`.
The pinned ShareSansar-derived per-equity history inventory was re-run against
crosswalk revision `e627168ffb4a9dfd1a56651030140d94baf75422` (281/281 symbols
retrieved and blob-verified) via `backend/audit_sharesansar_equity_history.py`;
the generated CSV/JSON land in git-ignored `data/reports/` and are reproducible
from the pinned revision.

Cross-referencing the lifecycle register against that inventory isolates the next
recoverable cohort: only **three** unverified symbols have an archive first date
after the archive boundary (2024-03-04/05). The other 234 unverified symbols were
already trading before archive coverage begins and require external listing-date
evidence rather than archive-boundary inference.

| Symbol | Archive first date | Archive first volume | Disposition |
|---|---|---:|---|
| NLO | 2024-03-26 | 45 | Coverage artifact, not a debut — remains unverified |
| NMLBBL | 2024-05-19 | 864 | First executed trade verified (secondary) |
| SMPDA | 2024-08-18 | 5,314 | First executed trade verified (secondary) |

## NMLBBL — first executed trade 2024-05-19

Post-merger security (Nerude Laghubitta + Mirmire Laghubitta, 1:1). Evidence chain:

- Official NEPSE listing/trading-release PDF dated 2024-05-17 (already captured in
  `p432_official_listing_documents`, sha256
  `366c28bcb864ea51d9ce4defff49ae0263fe03cff209e352c2a6a222b2e24053`); it releases
  trading but does not itself certify the first executed contract.
- Merolagani dated 2024-05-17 report (`newsID=102161`) announces the listing,
  assigns the NMLBBL ticker and opening price for the first transaction.
- Hash-verified third-party floorsheet archive
  (`urekmazino69/Nepse-floorsheet-and-indices`, git blob
  `dbd9ce881b109018d683cd6b6fe1e693a1505470`, captured under task P4.33) contains
  **15 NMLBBL contract rows on 2024-05-19** (first rate 599.60, matching the OHLCV
  open) and **zero NMLBBL rows on prior session 2024-05-16**.
- Pinned OHLCV (`nepse-smc-data/03_stock_charts_ohlcv/NMLBBL_OHLCV.csv`) and the
  ShareSansar-derived archive both begin 2024-05-19 with positive volume.

Register status: `verified_secondary_notice`, `valid_from = 2024-05-19`.
Ledger event: `EVT-NMLBBL-20240519` (`first_executed_trade`,
`corroborated_not_exchange_primary`).

## SMPDA — first executed trade 2024-08-18

Post-merger security (Sadhana Laghubitta + Sabko Laghubitta, 1:1 → Sampada
Laghubitta). Evidence chain:

- Official NEPSE listing PDF dated 2024-08-15 (sha256
  `f30ea664f83281449c916394631dbac2ad858b293edf4985627a554ca0e15438`); listing
  and opening-range release only.
- Lagani News dated 2024-08-15 states trading commences the coming Sunday
  (2024-08-18) under SMPDA with opening range Rs 1,057; KBL Securities same-date
  notice corroborates.
- Hash-verified floorsheet archive shows **192 SMPDA contract rows on 2024-08-18**
  (lowest rate 1057.40, inside the opening range) and **zero on prior session
  2024-08-14**.
- Pinned OHLCV and ShareSansar-derived archive first positive-volume row is
  2024-08-18.

Register status: `verified_secondary_notice`, `valid_from = 2024-08-18`.
Ledger event: `EVT-SMPDA-20240818` (`first_executed_trade`,
`corroborated_not_exchange_primary`).

## NLO — remains unverified

Nepal Lube Oil Limited listed 1986-12-14 (secondary company metadata; see
`EVT-NLO-19861214`). Its 43-row OHLCV archive begins 2024-03-26 — a coverage
artifact, not a debut. No contract-level or dated first-trade document exists in
the evidence register, so `valid_from` stays blank.

## Secondary-evidence URI re-check (44 verified rows, 40 unique URIs)

All 40 evidence URIs were re-requested on 2026-11-28:

- 38 returned HTTP 200.
- `english.insurancekhabar.com` (CREST) initially timed out; retry returned 200 —
  transient, not dead.
- `nepsealpha.com` (MATRI) returns HTTP 403 to automated requests — bot
  protection, not a dead link; content could not be re-verified by fetch.

## Validation

- `validate_equity_lifecycle_input.py`: 281 rows, 0 errors, 46 verified starts,
  235 unverified. Promotion remains disabled.
- `validate_security_lifecycle_event_ledger.py`: 8 events, 0 errors.
- `tests.test_security_lifecycle_event_ledger`,
  `tests.test_validate_equity_lifecycle_input`,
  `tests.test_historical_identity_readiness`: 15 tests pass locally.

## Limits and next work

- Both new dates rest on secondary contract-level corroboration (third-party
  floorsheet archive + dated press/broker notices), not an exchange-primary
  first-trade document. They remain `corroborated_not_exchange_primary`.
- The 235 remaining unverified symbols predate archive coverage; each needs its
  own dated listing/first-trade evidence. Bulk automated inference is prohibited
  by the contract.
- Official NEPSE EOD history API returns empty content for the 2024 candidate
  windows captured under P4.36; deeper official history acquisition remains a
  separate dependency.
