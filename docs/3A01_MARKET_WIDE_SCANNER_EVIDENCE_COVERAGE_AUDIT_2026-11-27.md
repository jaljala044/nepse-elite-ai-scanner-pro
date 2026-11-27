# 3A.01 — Market-wide scanner evidence and coverage gate

**Audit date:** 2026-11-27  
**Scope:** acceptance evidence for 3A.01 All-market stock scanner  
**Disposition:** engineering implementation is testable; production/data acceptance remains blocked  
**Evidence baseline:** current `main` as inspected on 2026-11-27

## Executive decision

The repository now contains useful official-source evidence for a dated 281-equity candidate set and a 29-date per-security history sample. That evidence is not sufficient to certify the complete active NEPSE equity universe, all expected trading sessions, complete historical OHLCV coverage, or deployment-wide data readiness.

The 3A.01 scanner must therefore remain **research-only**. Candidate discovery may be displayed with explicit coverage and provenance warnings, but no ranking eligibility, BUY list, trade plan, or production promotion is authorized.

## Evidence inventory

| Evidence item | Observed result | What it establishes | What it does not establish |
|---|---:|---|---|
| Secondary-provider equity candidate manifest (2026-11-26) | 281 rows; 281 unique symbols; 281 unique security IDs | Structurally consistent, dated working candidate universe | NEPSE/SEBON-authoritative active membership or historical membership |
| Official current security-list comparison | 281 / 281 current IDs match the 2026-11-25 crosswalk | Current-snapshot ID consistency for these candidates | Effective-dated historical identity |
| Official per-security history sample (2026-10-05 to 2026-11-26) | 281 / 281 accepted responses; 8,142 returned rows out of 8,149 possible candidate/date cells | Captured per-security history response coverage for the requested window | Complete all-market OHLCV archive or verified exchange-session coverage |
| Per-security row classification | 8,079 positive-activity; 63 explicit zero-activity; 7 missing | Returned rows are separated into positive, explicit zero and missing | Missing = no trade; zero rows = complete session proof |
| Missing-row lifecycle context | All 7 missing cells are BENH before 2026-10-15 secondary first-trade evidence; 0 unexplained missing cells in this bounded audit | The seven gaps are contextually explained by secondary lifecycle evidence | Primary-source listing/effective date or historical stable-ID proof |
| Official bulk traded-symbol scope (19, 20, 24 Nov 2026) | 347, 352 and 350 symbols; 1,049 symbol-date rows classified | Date-specific aggregate controls and current-snapshot instrument scope | Full session completeness, historical identity, or a complete equity OHLCV archive |
| Canonical reviewed-row manifest on current main | 0 records | Runtime reviewed-row gate currently has no promoted evidence | Any OHLCV row is eligible for canonical scanner scoring |

## Important scope distinctions

1. **Candidate universe is not authoritative membership.** The 281-row manifest is explicitly a NepseAlpha secondary-provider snapshot observed on 2026-11-26. It is suitable as a working candidate list for development and comparison only.
2. **The 29-date per-security history is not a 29-session calendar.** The 29 dates come from positive-activity official market-summary-history rows. They do not independently prove that every other date was closed or that every candidate was expected to trade.
3. **The 8,142 rows are not certified OHLCV coverage.** The P4.23 report describes official per-security activity history responses and bounded aggregate checks. Do not relabel these counts as complete daily OHLCV candles without a separately validated field/schema and source reconciliation.
4. **The bulk endpoint is all-instrument scope.** Across the three captured dates, the 1,049 symbol-date rows include 838 ordinary-equity candidate rows, 132 mutual-fund rows, 65 debenture rows, 12 promoter-share rows and 2 bond rows. These are current-snapshot classifications, not historical lifecycle proof.
5. **Runtime promotion is a separate gate.** The current canonical reviewed-row manifest is empty. Runtime eligibility requires dated identity, lifecycle, verified open-session evidence, source hashes, price-basis review, corporate-action clearance, point-in-time availability and exact OHLCV value binding.

## Repository OHLCV archive inventory — 2026-11-27

A further read-only inventory was performed against the owner-controlled `jaljala044/nepse-smc-data` repository.

### Raw archive inventory

- Inspected repository tree commit: `56362fb4f65b91fdcca8f50b50e53ad80e703649` (tree SHA; recursive tree complete, not truncated).
- `03_stock_charts_ohlcv/`: 525 CSV files and 525 unique filename stems.
- Exact filename match against the 281-symbol candidate equity manifest: **281/281 files present**.
- The remaining 244 file stems are outside the current 281 candidate list. They are not automatically classified as equities; they may include other instrument classes or unresolved aliases.
- Only one of the 281 candidate files is under 1 KB: BENH (783 bytes). File size is an inventory clue, not a row-count or quality verdict.

This is stronger than a manifest-only file-presence assertion, but it still does not prove each file contains complete expected-session history.

### Derived official-EOD v2 archive

Pinned release branch: `derived/ohlcv-v2-official-eod`  
Pinned release commit: `4255cc293a347857ac77c04a947beb784203062f`

The derived v2 manifest was independently parsed from the pinned branch:
- 281 symbol entries and 246,238 total derived rows.
- Per-symbol row counts range from 17 to 3,780; median 936. Different history lengths are material and must not be represented as uniform coverage.
- All 281 raw source Git blob hashes are recorded and verified by the release integrity audit.
- 599 official NEPSE EOD rows were applied across 254 symbols and six business dates.
- Derived-v2 operations: 490 date shifts, 109 inserted rows and 112 field corrections (109 Open + 3 Close) = 711 v2 ledger rows. The complete 713-row correction ledger also retains 2 earlier RHGCL field corrections applied in v1 (1 Close + 1 Volume). The ledger status field confirms 711 `applied_in_derived_v2` rows and 2 `applied_in_derived_v1` rows; all 713 symbol/date/field keys are unique. This resolves the previously reported two-count discrepancy. Raw source files were not modified.
- This is a derived release, not a fully session-clean canonical dataset.

### Integrity and contamination evidence

The full v2 integrity audit reports:
- 1,329 unique invalid OHLCV symbol/date rows across 13 symbols, represented by 1,379 invariant flags (50 overlapping reasons); no automatic repair. Per-symbol values in the companion matrix are flag counts, not unique-row counts.
- 71,806 adjacent identical OHLCV rows across 256 symbols.
- 18,910 repeats are candidates on dates explicitly verified closed; 52,891 are outside the calendar evidence window and remain UNKNOWN; five open-session repeat pairs remain UNKNOWN pending symbol/date floorsheet checks.
- Corporate-action coverage remains partial: three recorded events, 278/281 symbols without an action record, and one NLIC split proposal with unverified effective date.

A separate official EOD parity sample across 24 active securities and 12 sectors (5,472 official rows) found:
- 1,455 canonical-only HLCV rows across 19 securities on 81 verified-closed dates, exactly matching another official EOD date's HLCV tuple.
- 36 official-only rows also match canonical tuples placed on verified-closed dates.
- Three exact-date HLCV mismatches remain unresolved (AHPC 2026-07-17, CFCL 2026-11-18, HDL 2026-07-17).
- No canonical source file was changed.

The 24-security parity sample and the 281-symbol integrity audit have different scopes; their repeat counts must not be added together. The observed contamination is sufficient to prohibit treating raw ShareSansar-derived calendar-date rows as clean trading-session bars without the derived quarantine logic and verified calendar.

### Scanner impact

The repository contains an extensive 281-symbol historical archive and a derived v2 candidate input. However, row presence and total row count are not scanner-ready coverage. Until the complete session calendar, per-symbol date mapping, OHLC invariant flags, repeated-candle dispositions, corporate actions, source rights and deployment import are resolved, v2 can only be evaluated as a research/quarantine dataset. The app's canonical reviewed-row manifest remains empty; no new rows are eligible for runtime scoring.

**Source reports:** `nepse-smc-data/reference/derived_ohlcv_v2_release_2026-11-26.md`, `derived_ohlcv_v2_integrity_audit_2026-11-26.md`, `reference/p437_cross_sector_date_contamination_audit_2026-11-26.md`, and `reference/equity_ohlcv_inventory_readiness_audit_2026-11-26.md`.

## 3A.01 acceptance matrix

| Acceptance gate | Status | Evidence / blocker |
|---|---|---|
| Deterministic market-wide orchestration and API | Implemented on PR #157 | Exact-head backend tests passed; PR remains draft and unmerged |
| Dedicated frontend entry point | Implemented on PR #157 | Dedicated UI module and build integration are included |
| Exact-head CI for PR #157 | Passed | Unit tests run 45926537471, backend-unit-tests run 45926537414, frontend build run 45926522336 all passed |
| Candidate universe has stable dated provenance | Partial | 281-row secondary snapshot is pinned; authoritative membership is not established |
| Current security ID crosswalk | Partial | 281/281 current-snapshot matches; historical effective-dated identity outstanding |
| Complete all-market instrument scope | Partial | Three official bulk dates reconcile; only those dates and current-snapshot instrument classifications are covered |
| Complete expected-session calendar | Blocked | Official open/closed calendar and full-session completeness remain unverified |
| Complete, validated daily OHLCV coverage by symbol/session | Blocked | The per-security activity-history sample is not a substitute for an independently reconciled OHLCV archive |
| Canonical reviewed-row eligibility | Blocked | Reviewed-row manifest contains zero records |
| Deployment-wide data coverage | Unknown | Deployment DuckDB and runtime dataset were not inspected in this audit |
| Source-use and redistribution rights | Unknown | Rights remain unverified |
| Production ranking / BUY authorization | Prohibited | Fail-closed policy remains in force |

## Required next evidence before 3A.01 acceptance

1. Obtain and pin primary dated evidence for active ordinary-equity membership and effective-dated symbol/security-ID lifecycle. Continue P4.25's registry work; do not treat the current 281 snapshot as authoritative.
2. Establish the verified NEPSE session calendar for the target period, including exceptional openings and closures.
3. Inventory the actual OHLCV sources and runtime store separately. Report per-source row counts, unique symbol/date keys, date ranges, duplicate/conflict counts, price basis, and per-symbol coverage. Do not infer expected sessions from weekdays or missing rows.
4. Reconcile daily OHLCV against date-matched official evidence and corporate-action records; preserve source conflicts and quarantine unresolved rows.
5. Review and promote canonical rows only after every required identity, lifecycle, session, source, price-basis, corporate-action and point-in-time field is supported. The canonical reviewed-row manifest must not be populated merely to make the scanner return results.
6. Verify deployment-wide coverage against the actual deployment database and report its retrieval timestamp and dataset fingerprint. Repository CI is not deployment evidence.
7. Confirm source-use rights before canonical promotion, training, backtests or redistribution.

## Engineering integration note

PR #157 (`reconcile/3a01-after-sebon-test-fix-2026-11-27`) is the current scanner integration candidate. Its exact-head unit tests (run `45926537471`), backend tests (`45926537414`) and frontend build (`45926522336`) all passed. The earlier `app.sebon_pdf_capture` import blocker was removed from main before this port. PR #157 remains draft and unmerged. PR #142, #153 and #155 remain open, superseded ports; no older port should replace the current integration. PR #158 carries the companion evidence audit and also remains draft and unmerged.

## Source reports

- [Equity-only universe gate — 2026-11-26](EQUITY_ONLY_UNIVERSE_GATE_2026-11-26.md)
- [P4.23 — 29-date official NEPSE per-security history window](P4.23_29_DATE_OFFICIAL_SECURITY_HISTORY_WINDOW_2026-11-26.md)
- [P4.24 — Official bulk traded-symbol scope reconciliation](P4.24_OFFICIAL_BULK_SYMBOL_SCOPE_RECONCILIATION_2026-11-26.md)
- [Stage 1 Runtime Evidence Gate](STAGE1_RUNTIME_EVIDENCE_GATE.md)
- [NEPSE historical session calendar and integrity gate](NEPSE_SESSION_CALENDAR_AND_INTEGRITY_GATE.md)

**Final disposition:** 3A.01 implementation work is substantially built, but task acceptance is not complete. Keep the scanner research-only and fail-closed. Do not advance to 3A.02 until the remaining data, integration and deployment gates pass.


## 281-symbol per-security OHLCV impact matrix — 2026-11-27

A companion CSV matrix is published at [3A01_281_SYMBOL_OHLCV_IMPACT_MATRIX_2026-11-27.csv](3A01_281_SYMBOL_OHLCV_IMPACT_MATRIX_2026-11-27.csv). It contains one row for each of the 281 symbols in the pinned v2 manifest and records:

- Derived row count and raw/derived Git blob hashes.
- Official EOD rows applied and the manifest's per-symbol `correction_count` metric (renamed `manifest_correction_count` in this matrix; aggregate 713).
- Per-symbol OHLCV invariant-flag counts (renamed `invalid_ohlcv_flags`); these are **flags, not unique invalid rows**. P4.30 reports 1,379 flags across 1,329 unique symbol/date rows. The per-symbol figures published in P4.30 sum to 1,379 flags; an exact per-symbol allocation of the 1,329 unique rows is not published, so the matrix does not claim one.
- Correction-ledger reconciliation: the 713-row ledger contains 711 v2 operations (490 Date + 109 Row insertions + 109 Open + 3 Close corrections) and 2 earlier v1 RHGCL corrections (1 Close + 1 Volume). The manifest's 713 `correction_count` includes both vintages; P4.30's 711 derived-v2 operation count excludes the two already-applied v1 rows. All 713 symbol/date/field keys are unique; the count difference is resolved.
- Known corporate-action records and the four-symbol exception review (LBBL, DORDI, BNHC and the unverified NLIC split proposal).
- The five open-session repeated-row pairs by symbol/date where explicitly reported.
- An explicit research-only, non-canonical eligibility disposition for every symbol.

**Important limits:** P4.30 publishes the 18,910 verified-closed repeat candidates and 52,891 outside-calendar UNKNOWN repeats as dataset-level totals, not a per-symbol allocation. The matrix therefore deliberately marks per-symbol closed-repeat and unresolved-repeat counts as NOT_PUBLISHED_PER_SYMBOL; it does not invent allocations. Similarly, absence from the partial corporate-action file is not proof that no action occurred. Per-symbol min/max dates and deployment-store coverage are not derived from the manifest and remain outside this matrix.

The matrix is an evidence index, not a reviewed-row manifest. It does not authorize technical-indicator eligibility, ranking, BUY-list inclusion, backtesting, or production promotion. The canonical reviewed-row manifest remains empty.


## Integration status refresh — 2026-11-27

The current scanner integration was re-applied onto the latest main snapshot after main removed the prematurely committed SEBON capture test:
- PR #157: [3A.01 scanner integration after SEBON CI repair](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/pull/157).
- Head: `a630ddf2660b8b304b2b524a5f5abbc11929c337`; base snapshot: `4b8d01be47b769f0ea03a1874c26da53f52ffa45`.
- The port includes deterministic market-wide orchestration, API and frontend scanner module, fail-closed reviewed-row gating, future-row exclusion and lowercase-symbol rejection.
- Branch comparison: 7 commits ahead, 0 behind at creation. GitHub initially reported mergeability as pending.
- The orphan SEBON test was removed from main by commit `3ba03e1e2c5702eba18334799d2f09c17b61d913`, so the previous unrelated import blocker should no longer apply. Exact-head CI for PR #157 is currently running; no passing result is claimed yet.
- Earlier scanner ports PR #142, #153 and #155 remain open but superseded. No merge or deployment is claimed.

The evidence artifacts have been re-based onto current main in companion PR #158: [3A.01 evidence audit refresh](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/pull/158). The evidence branch now includes the correction-ledger reconciliation: 713 total ledger rows = 711 derived-v2 operations + 2 earlier v1 RHGCL corrections. The 1,379 invariant flags remain distinct from 1,329 unique invalid symbol/date rows. Commit `653a9f49606e2942b668d39adcf8ae1df1f297cb` refreshed this audit; its exact-head backend workflow run `45928417697` completed successfully.

No pull request was merged. No deployment verification was performed.
