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

## P1 immutable-source rerun — 2026-11-25

- Repeated both 525-file directory inventories and all 50 CSV fetches for the
  25 differing ticker pairs using explicit immutable refs:
  - `nepse-smc-data`: `a55a9097375782d0a982f1f94a881f0a4e036698`
  - `nepse-history-starter`: `2bd6976cbbb0d40cf60f77c0f712e0b708dc4dbe`
- The pinned directory comparison again yielded 525 matching paths, 500
  identical blob SHAs and 25 differing blobs. All 50 fetched file blob SHAs
  matched the previously recorded values; row counts, date-key differences
  and eight OHLCV conflicts were reproduced.
- The prior revision-pinning caveat is closed for this audit snapshot. This
  establishes reproducibility of the content, not correctness or independent
  provenance. The eight conflicts remain quarantined; calendar,
  corporate-action and upstream-lineage checks remain open.
- Full details: `docs/CROSS_REPOSITORY_OHLCV_AUDIT_2026-11-25.md`.

## P1 source-lineage and corporate-action review — 2026-11-25

- Reviewed the starter's pinned ShareSansar import record: it identifies the
  ShareSansarScraper source commit, source XLSX SHA-256, published OHLC/volume
  price basis, and per-symbol output SHA-256 inventory. It reports 303,438
  source rows, 301,632 imported rows and 1,806 flagged rows across 525
  symbols.
- This supports treating the 500 byte-identical files as shared ShareSansar
  content lineage, not independent corroboration. The source lineage and
  price basis of the longer legacy portions of the 25 differing SMC files
  remain unresolved.
- The current corporate-action ledger documents only LBBL, DORDI and BNHC;
  none is among the seven symbols with same-date OHLCV conflicts. This is
  insufficient to rule out other actions or explain the conflicts.
- See the provenance section of
  `docs/CROSS_REPOSITORY_OHLCV_AUDIT_2026-11-25.md`. Canonical promotion
  remains blocked pending legacy source tracing, issuer/exchange action
  checks, and independent raw-price/tape evidence.

## P1 external EOD corroboration — 2026-11-25

- Cross-checked all eight same-date conflicts against pinned Srijan EOD and
  SocrateAI unadjusted EOD files. The 2025-07-28 five-symbol cluster splits:
  SMC agrees with Srijan, while starter OHLC agrees with SocrateAI. Some
  volume counts differ between the EOD sources.
- For API, HRL and RHGCL on 2026-11-19, starter Close agrees with both pinned
  EOD datasets; SMC Close and volume differ materially. This is strong
  corroboration, not primary exchange proof.
- Detailed blob SHAs, source values and limitations are in
  `docs/CROSS_REPOSITORY_OHLCV_AUDIT_2026-11-25.md`. Preserve all source
  observations; do not automatically overwrite or promote disputed rows.
  Primary exchange verification and upstream-feed independence remain open.

## P1 2026 calendar evidence triage — 2026-11-25

- Reviewed the 2083 Nepal Rastra Bank holiday PDF for government/banking
  holiday context and compared it with NEPSE-specific secondary closure
  reports for May 28–29, Sep 8, Sep 25, Oct 19–23, Nov 9–12 and Nov 16.
- Kept the Sep 21 Data Hub outage as an exceptional operational-suspension
  lead, not a routine holiday.
- Rechecked the weekday regime boundary: Monday–Friday candidates from
  2026-04-06; schedule candidates still do not establish actual trading.
- Rechecked the calendar loader's fail-closed contract: only evidence-backed
  verified statuses with raw SHA-256, source URI/ID, UTC retrieval and
  verification timestamps and scope are accepted. OHLCV rows on unverified
  dates remain quarantined.
- No new calendar dates were promoted. Primary NEPSE notice bytes have not
  yet been archived and hashed. Full review:
  `docs/NEPSE_SESSION_CALENDAR_AND_INTEGRITY_GATE.md`.



## P1 CI repair and real-data acceptance status — 2026-11-25

- Diagnosed the prior `backend-tests` failure: two OHLCV reconciliation test
  fixtures encoded literal backslash-n text, producing malformed CSV headers.
  Corrected the fixtures; production parser behavior was unchanged.
- At commit `5c6269d90b2f94c0dc4bcb34b35a3556d460f077`, GitHub Actions
  completed successfully: backend tests (532), backend contract tests (532),
  and integrated evidence audit (532). The historical data-integrity workflow
  also passed its focused collector, coverage-matrix and OHLCV reconciliation
  tests and uploaded the pinned inventory/coverage artifact.
- Inspected the inventory artifact: the pinned Urekmazino repository lists
  7,032 files (603 floorsheets and 6,429 index files); the AnkitSanjyal
  repository lists 312 configured records. These are complete repository
  listings, not downloaded or validated raw data.
- The 198 dates in the coverage report remain `candidate_unverified`; confirmed
  sessions remain 0. The canonical `data/reference/nepse_session_calendar.csv`
  contains only its header.
- Inspected the integrated audit artifact. It completed but skipped source
  inventory, calendar reconciliation, OHLCV, universe, security coverage and
  floorsheet checks because required source manifests/raw files/normalized
  inputs are absent. Training readiness is false; canonical promotion is false.
- Located the official NEPSE Holiday Listing page, but the page returned no
  readable date records in this review. No primary notice bytes were captured
  or hashed, so no calendar rows were promoted.
- P1 remains **active and blocked on real-source evidence**. Detailed status,
  artifact digests and the next five P1 tasks are in
  `docs/P1_ACCEPTANCE_STATUS_AND_NEXT_5_2026-11-25.md`.

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


## P1 evidence acquisition contracts — 2026-11-25

- Added empty templates for immutable source objects, source-file dates,
  calendar evidence captures/claims, corporate-action review, OHLCV conflicts,
  and normalized broker party observations.
- Added `docs/P1_EVIDENCE_MANIFEST_CONTRACTS_2026-11-25.md` with required
  schemas, raw-byte SHA-256 and immutable revision rules, primary calendar
  evidence requirements, scope-conflict handling, OHLCV quarantine and broker
  execution-channel identity policy.
- These are acquisition contracts only. No real data was fabricated or
  promoted; the canonical calendar still has zero verified rows and the exact
  616-session calendar is still unrecovered. P1 remains blocked.
- Detailed next five actions are in
  `docs/P1_ACCEPTANCE_STATUS_AND_NEXT_5_2026-11-25.md`.



## P1 first pinned raw floorsheet acquisition — 2026-11-25

- Preserved the full 2026-11-19 floorsheet file from
  `rajeevpaudel/nepse-history` at immutable revision
  `927a15986012b31dba6c29c2266fb17f966a087b`.
- Verified source and copied file Git blob OID match; 2,300,941 bytes,
  40,818 contracts, 8 expected columns, all rows date-keyed to 2026-11-19,
  zero structurally malformed rows; raw SHA-256
  `771d856187844f5608cb31225c03d065a4ce13fe655601d465c4e167a7b62e15`.
- Added source-object and source-file-date manifests under
  `data/evidence/acquired/`.
- Upstream is community-maintained and uses Merolagani historical collection;
  its README discloses per-day row shortfalls, historical fetch failures and
  no intraday timestamps. This is not primary exchange evidence. Redistribution
  and commercial terms still require independent verification.
- One date does not establish completeness, broker identity or calendar
  validity. P1 remains blocked; details and the next five acquisition tasks
  are in `docs/P1_ACCEPTANCE_STATUS_AND_NEXT_5_2026-11-25.md`.



## P1 execution increment — 2026-11-25 (broker and external EOD)

- Added pinned-source broker party derivation script, tests and CI artifact
  generation. Every contract becomes one buy and one sell execution-channel
  observation; source codes remain strings; identities remain unmapped.
- Independently calculated one-date control: 40,818 contracts, 81,636 party
  observations, 91 codes, 346 securities, 15,466 broker/security/side groups,
  9,435,392 quantity, NPR 3,877,623,296.62 gross amount, zero duplicate
  contract IDs and zero quantity-rate-amount exceptions. The source itself
  reports 19 missing contracts against 40,837 expected; totals are internal,
  not independent exchange controls.
- Added separate-repository EOD cross-check: 346 common symbols, one extra
  symbol, 77 symbols with OHLCV differences (Open 4, High 7, Low 72, Close 1,
  Volume 0). Its data license excludes the dataset; raw copy was removed and
  only pointer/hash/metrics retained. Not primary exchange evidence.
- Reviewed 2015-01-04 and 2026-11-18 pinned floorsheet samples by hash and
  structure without staging extra raw copies pending rights review. The latter
  has a publisher-reported 33-row shortfall; 2015 sample has one amount
  arithmetic exception.
- Repeated 616-calendar recovery search against the exact backfill base tree
  and later pinned tree; no calendar file or generator found. Exact date set
  remains unavailable.
- P1 remains blocked. Current increment and next five actions are documented
  in `docs/P1_ACCEPTANCE_STATUS_AND_NEXT_5_2026-11-25.md`.


### CI and generated broker evidence — verified

- Latest backend suite: run `45617995122`, success, 535 tests, head
  `16bffbfd4faa5a1093d72499ac76791ba1068dbb`.
- Historical data-integrity workflow: run `45617821684`, success; broker
  derivation executed against the pinned raw sample and produced 81,636 party
  observations and 15,466 aggregate rows.
- Artifact ZIP SHA-256:
  `074a627f3d7ee403e8bffcfba31a4a9cdbcd45822a9076189c5ce0b53a5bdcc6`;
  party CSV SHA-256:
  `050139c4f6c4ecc65a49c762f2e7cce0b7d7ad2d75c193349a7d1b0e7fefe9d0`;
  aggregate JSON SHA-256:
  `9c4cec23837cba310a6202080f8e7ec6ac36d0397913cdee88073d80037725e0`.
- No buyer/seller party row is mapped to a canonical broker entity. P1 remains
  blocked by calendar recovery, source rights/completeness, independent
  exchange controls, corporate actions and primary OHLCV conflict resolution.

