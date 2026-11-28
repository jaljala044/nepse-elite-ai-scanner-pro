# P4.11.4 — 2024 post-boundary lifecycle start cohort — 2026-11-28

## Scope and method

Priority-queue item 1 (P1 lifecycle) recovers first-trade dates for unverified rows in `data/reference/nepse_equity_lifecycle_coverage_input_2026-11-26.csv`.

The supplied cohort report identifies three unverified symbols whose archive first dates fall after the 2024-03-04/05 archive boundary. Two now have secondary contract-level corroboration; NLO remains unverified. The other 234 unverified symbols predate archive coverage and require external listing/first-trade evidence rather than archive-boundary inference.

| Symbol | Archive first date | Archive first volume | Disposition |
|---|---|---:|---|
| NLO | 2024-03-26 | 45 | Coverage artifact, not a debut — remains unverified |
| NMLBBL | 2024-05-19 | 864 | First executed trade corroborated by secondary contract-level evidence |
| SMPDA | 2024-08-18 | 5,314 | First executed trade corroborated by secondary contract-level evidence |

## NMLBBL — first executed trade 2024-05-19

Post-merger security (Nerude Laghubitta + Mirmire Laghubitta, 1:1).

- Official NEPSE listing/trading-release PDF dated 2024-05-17; it releases trading but does not itself certify the first executed contract. Captured PDF SHA-256: `366c28bcb864ea51d9ce4defff49ae0263fe03cff209e352c2a6a222b2e24053`.
- Merolagani report dated 2024-05-17 (`newsID=102161`) announces the listing, assigns NMLBBL ticker and opening price for the first transaction.
- Hash-verified third-party floorsheet archive (`urekmazino69/Nepse-floorsheet-and-indices`, git blob `dbd9ce881b109018d683cd6b6fe1e693a1505470`) reports 15 NMLBBL contract rows on 2024-05-19 (first rate 599.60) and zero NMLBBL rows on prior session 2024-05-16.
- Pinned OHLCV and ShareSansar-derived archive first positive-volume row is 2024-05-19.

Register status: `verified_secondary_notice`, `valid_from = 2024-05-19`. This is secondary corroboration, not NEPSE-primary first-trade certification.

## SMPDA — first executed trade 2024-08-18

Post-merger security (Sadhana Laghubitta + Sabko Laghubitta, 1:1 → Sampada Laghubitta).

- Official NEPSE listing PDF dated 2024-08-15; listing/opening-range evidence only. Captured PDF SHA-256: `f30ea664f83281449c916394631dbac2ad858b293edf4985627a554ca0e15438`.
- Lagani News report dated 2024-08-15 states secondary-market trading would commence on 2024-08-18 under SMPDA with NEPSE opening range Rs 1,057; KBL Securities notice of the same date corroborates.
- Hash-verified third-party floorsheet archive reports 192 SMPDA contract rows on 2024-08-18 (lowest rate 1057.40, within the opening range) and zero SMPDA rows on prior session 2024-08-14.
- Pinned OHLCV and ShareSansar-derived archive first positive-volume row is 2024-08-18.

Register status: `verified_secondary_notice`, `valid_from = 2024-08-18`. This is secondary corroboration, not NEPSE-primary first-trade certification.

## NLO — remains unverified

Nepal Lube Oil Limited listing date is reported as 1986-12-14 by ShareHub company metadata (`EVT-NLO-19861214`). Its 43-row OHLCV archive begins 2024-03-26 — a coverage artifact, not a debut. No contract-level or dated first-trade document is in the evidence register, so `valid_from` remains blank.

## Ledger and validation

- Event ledger extended from 6 to 8 typed events; NMLBBL and SMPDA first-executed-trade events use `secondary_nepse_listing_report` and `corroborated_not_exchange_primary`.
- Lifecycle coverage input updates only NMLBBL (security ID 396) and SMPDA (security ID 2896); no unrelated symbol dates are inferred.
- The validator contract continues to prohibit promotion. Listing and merger events remain distinct from first executed trades.
- The supplied local report states: 281 rows, 46 verified starts, 235 unverified; event ledger 8 events, 0 errors; 15 named lifecycle/identity tests passed locally. These are reported local results, not yet an exact-head CI attestation for this branch.

## Provenance caveat requiring resolution

The supplied report identifies crosswalk revision `e627168ffb4a9dfd1a56651030140d94baf75422`. That SHA could not be resolved as a commit in this repository during integration. The current `main` crosswalk file is available, but the cohort's stated 281/281 retrieval run has not yet been reproduced against that exact file revision here. Exact-head CI and a fresh inventory run are required before treating the local inventory counts as repository-verified.

## Limits and next work

- Both first-trade dates rely on secondary contract-level corroboration (third-party floorsheet archive + dated press/broker notices), not an exchange-primary first-trade attestation.
- The 235 remaining unverified symbols predate archive coverage; each needs its own dated listing/first-trade evidence. Bulk automated inference is prohibited.
- The official NEPSE EOD history API reportedly returned empty content for the 2024 candidate windows in the captured P4.36 investigation; deeper official history acquisition remains separate.
- Event URLs are references, not immutable source captures. Retrieval timestamps and raw payload hashes remain outstanding for the press/broker notices and floorsheet archive evidence.
- No canonical/training promotion, backtest admission, scanner eligibility expansion or BUY eligibility change is authorized by this cohort.

## Safety decision

NMLBBL and SMPDA are recorded as secondary-evidence lifecycle starts only. NLO and the other unverified symbols remain blank. No source OHLCV row, session calendar or canonical dataset is modified by this evidence classification.
