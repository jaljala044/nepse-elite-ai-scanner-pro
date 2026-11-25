# NEPSE AI — five master priorities
Updated: 2026-11-25

These five priorities are the project execution order. Work should finish the
acceptance gates of one priority before promoting dependent outputs from the next.

## P1 — Historical data integrity (active)
- Build an evidence-backed, versioned NEPSE session calendar.
- Pin source revisions and preserve source-specific file manifests.
- Generate source-separated date coverage and conflict reports.
- Add symbol-level, row-level, corporate-action and cross-source reconciliation.
- Keep unknown, restricted and conflicting records out of canonical data.
- No missing-session claim from weekdays or a file-path date alone.

**Current increment:** a conservative file-level coverage matrix generator and
unit tests are committed. It intentionally does not infer missing sessions or
row completeness. The real calendar and source manifests still need to be
populated and independently verified.

## P1 progress update — 2026-11-25
- Added 198 dated market-summary records from the starter archive as calendar candidates, all explicitly `candidate_unverified`; none was promoted to a confirmed exchange session.
- Recorded the source file blob SHA and candidate-audit report.
- Updated the Hugging Face collector to resolve mutable refs such as `main` to immutable 40-character commit SHAs before inventory/download.
- Added separate listing and inventory completeness flags so a max-files cap cannot masquerade as a complete inventory.
- Updated the coverage matrix to preserve downloaded hashes, byte counts and per-file download statuses.
- Added unit tests for immutable revision resolution and retained the existing calendar/coverage tests.
- GitHub file contents have been re-fetched to verify commits. CI has not yet been observed for these latest commits.

**616-session calendar recovery investigation:** the starter backfill manifest reports
616 calendar-approved sessions, and its README says the original extraction used
a pinned session calendar. However, the manifest does not identify a calendar
path, blob SHA, exact date list, or generation command. The inspected import
utility does not enforce a session calendar. The count is therefore not yet
independently reproducible. See
`docs/616_SESSION_CALENDAR_RECOVERY_AUDIT_2026-11-25.md`. The 198 market-summary
dates remain candidates only; confirmed sessions added by this investigation: 0.

## P1 automation increment — 2026-11-25
- Added `backend/run_hf_inventory.py`, a read-only CLI that inventories the configured public Hugging Face datasets after resolving requested refs to immutable commit SHAs.
- Added `.github/workflows/nepse-data-integrity.yml` to run the focused collector and coverage-matrix unit-test suites, generate the inventory manifest, build a source-separated file/date coverage report against the candidate calendar, and upload both reports as an artifact.
- The report deliberately labels all 2026 candidate dates as unverified; it does not infer confirmed sessions or missing sessions.
- Workflow YAML, script, and paths were re-fetched from GitHub after commit. The GitHub status endpoint returned no status checks and the available workflow-run lookup returned no runs; execution and inventory output are therefore **not yet verified**. Do not claim the tests passed or that live dataset inventories have been generated until the Actions run and artifact are inspected.

## P1 row-level reconciliation increment — 2026-11-25
- Added `backend/app/ohlcv_reconciliation.py` and focused tests.
- The comparator matches CSVs by identical relative path, requires explicit ISO dates and recognized OHLCV columns, canonicalizes numeric formatting, and reports left-only/right-only dates, value mismatches, duplicate dates, invalid rows, file SHA-256 hashes and source revision labels.
- It does not infer sessions, adjust prices, merge sources, or select a winning value. Different relative paths are intentionally not guessed to be the same ticker.
- Added the focused test suite to the data-integrity workflow. Actual test execution and archive-to-archive reconciliation remain unverified; source archive roots/revisions must be supplied before a real comparison can be reported.

## P1 sample provenance and repeated-candle audit — 2026-11-25
- Inspected `03_stock_charts_ohlcv/NRN_OHLCV.csv` in both `nepse-smc-data` and `nepse-history-starter`.
- Both paths returned the same Git blob SHA `a644cc5eaa176ad5bc3f08caf4db262e903940c6`: the two copies are byte-identical, so they are not independent source corroboration for this symbol.
- The file has 936 rows, 936 unique dates, zero duplicate date keys, and 320 adjacent row pairs with identical OHLCV values. These are review flags only; no rows were deleted and no trading-session inference was made.
- Enhanced the reconciliation engine to flag adjacent identical candles and reject invalid OHLC bounds or negative/non-integral volume rows. Added focused tests.
- Sample findings are documented in `docs/NRN_SAMPLE_ROW_AUDIT_2026-11-25.md`. This does not establish the full 525-file overlap or resolve the 616-session calendar.

## P1 cross-repository OHLCV audit — 2026-11-25

- Enumerated both `03_stock_charts_ohlcv` directories through the GitHub
  Contents API: 525 files each, 525 exact filename matches, and no one-sided
  filenames.
- Compared Git blob SHAs for all 525 paths: 500 are byte-identical copies
  (95.24%); 25 differ. Identical copies are not independent corroboration.
- Fetched and structurally inventoried both versions of all 25 differing
  files: matching Date/OHLCV headers, row counts/date ranges recorded, and
  zero duplicate date keys observed in these 50 files.
- The SMC repository is longer for 24 of the 25 differing tickers; SOHL is
  the exception. Longer history is not automatically more accurate.
- See `docs/CROSS_REPOSITORY_OHLCV_AUDIT_2026-11-25.md` for the full table
  and limitations. Full row-by-row OHLCV reconciliation, pinned source
  revisions, upstream lineage verification, and session/corporate-action
  reconciliation remain pending. Canonical promotion remains blocked.

## P1 row-by-row cross-repository reconciliation — 2026-11-25

- Compared date keys and normalized OHLCV values for all 25 files whose Git
  blob SHAs differ. Found 8 same-date value conflicts across 7 symbols:
  API, BGWT, HRL, MEHL, RAWA, RHGCL (2 dates), and ULHC.
- Four symbols (BGWT, MEHL, RAWA, RHGCL) conflict on 2025-07-28; three
  symbols (API, HRL, RHGCL) conflict on 2026-11-19. These clusters warrant
  common-provenance/correction investigation, not an automatic winner choice.
- Date-key-only differences were counted separately from same-date value
  conflicts. They are not labelled missing trading sessions because the
  authoritative session calendar remains unresolved.
- Detailed per-symbol counts and exact conflicting OHLCV values are recorded
  in `docs/CROSS_REPOSITORY_OHLCV_AUDIT_2026-11-25.md`.
- The eight conflicting rows are quarantined from canonical promotion pending
  independent source evidence, revision pinning, corporate-action review and
  session-calendar reconciliation. No rows were merged or overwritten.

## P2 — Historical market intelligence
- Build separate market, sector, stock and broker execution-channel histories.
- Store timestamped episodes, recurring participation/accumulation/distribution
  observations, and source/evidence references.
- Compare current episodes with prior episodes using only information available
  at the historical decision time.
- Never equate broker codes with beneficial owners.
- Keep raw floorsheet transactions separate from broker/day aggregates.

## P3 — Dual scanner engine
- Preserve the Universal SMC/ICT + IDPAT engine as a distinct analytical engine.
- Preserve the NEPSE V3.0 engine with NEPSE-specific market rules and behavior.
- Share validated data contracts, not market assumptions or signal thresholds.
- Explain market structure, BOS/CHOCH, liquidity, FVG, order blocks, trend and
  volume observations with evidence, timestamps and invalidation conditions.
- Keep missing/stale data and low-confidence states explicit.

## P4 — Backtesting and prediction validation
- Enforce as-of replay and no-lookahead checks.
- Evaluate signals with walk-forward splits, realistic fees, taxes, slippage,
  liquidity and circuit/price-limit constraints.
- Measure false breakouts, calibration, drawdown and stability by regime.
- Compare against simple baselines; do not claim predictive accuracy without
  reproducible out-of-sample evidence.

## P5 — Product and production deployment
- Stabilize persistence, migrations, APIs and audit logs.
- Complete the 309-stock universe and evidence-driven frontend.
- Add authentication, secrets, backups, monitoring and operational controls.
- Connect only authorized, tested data providers with documented freshness,
  licensing, rate limits and failure behavior.
- Schedule scans only after source and deployment acceptance.

## Non-negotiable project rules
- No fabricated prices, dates, sessions, broker identities or signals.
- No look-ahead leakage in features, labels, training or backtests.
- No silent overwrite of source conflicts.
- No adjustment of historical prices without a documented corporate-action ledger.
- No automated order execution in this project scope.
- A successful unit test is not proof of complete historical data or production readiness.
