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
