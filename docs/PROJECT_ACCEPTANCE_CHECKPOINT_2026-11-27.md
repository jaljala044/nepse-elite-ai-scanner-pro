# Project acceptance checkpoint — 2026-11-27

Pinned reviewed main: 7fd6c902966d3e2af76e63f7872f5a46120e0249.

## Verified
- Backend run 46045641279: 1391 tests passed, including 10 dated-cost integration tests.
- Contract run 46045641341, integrity run 46045641184, integrated audit run 46045641199: success.
- SMC/ICT numerical fixtures, strategy research, scenario simulation, dated costs, portfolio valuation and risk-adjusted statistics implemented and regression tested. These are not independent market acceptance.

## Direct register inspection
- data/reference/nepse_active_equity_manifest_2026-11-26.csv (blob 56bdb41c7307870ad755ceb24fc32b5340fee137): 281 active equity rows, 281 unique symbols.
- data/reference/nepse_equity_lifecycle_coverage_input_2026-11-26.csv (blob be1567fadb69bdca11b0d7890da10ebc8df96d51): 281 rows; 237 unverified effective start dates, 30 secondary first-trade archive matches, 14 secondary notices. Secondary evidence is not canonical admission.
- data/reference/nepse_session_calendar.csv (blob 8d50de83ffebe7fba54d3f853087984161c5f8cb): 41 distinct dates, 40 verified_closed and 1 verified_exceptional_closed; zero open records in this file.
- data/reference/scanner_canonical_reviewed_rows.json: zero approved rows.
- Prior P1 checkpoint reports 146132 provider-supported equity-date bars, 132346 reconciled transaction totals, and 11628 bars without contract observations. These are previously reported counts, not a new archive audit.

## Priority queue (acceptance, not just implementation)
1. P1 lifecycle: recover 237 unverified start dates; review 44 secondary evidence records.
2. P1 calendar: certify open sessions, exceptional sessions and continuous civil-day decisions; distinguish evidence publication from retrospective retrieval.
3. P1 source provenance: match immutable source bytes, exact OHLCV and independently reviewed source rights.
4. P1 corporate actions: verify effective dates and raw/adjusted price basis; do not assume absence of actions.
5. P1 canonical admission: combine independently reviewed evidence and exact values, prevent duplicates and quarantine conflicts. No promotion without authority.
6. P4 floorsheet content and totals reconciliation: continue SMC issue #74/draft PR #80; P4.40 remains postponed.
7. P2 market and broker intelligence: validate actual breadth, sector and broker coverage before promotion.
8. Historical execution: certify fee/tax periods, settlement calendar and price limits; dated_reference is research only.
9. Historical strategy: run eligible point-in-time Swing/Positional/T+2 replay; benchmark and walk-forward validation; authentic IDPAT V3 remains blocked by original specification.
10. Product/security: reconcile frontend, Android, persistent database migrations, auth, private deployment, monitoring, backup and data licensing against actual acceptance tests; no production or AI recommendation approval.

No raw source changes or canonical promotions. This checkpoint supersedes outdated status counts in ROADMAP.md without declaring all roadmap tasks complete. A green workflow is not evidence that skipped real-source checks were executed. Scope is the inspected scanner main and prior linked evidence; other branches, full archives and deployment have not been independently re-audited in this checkpoint.
