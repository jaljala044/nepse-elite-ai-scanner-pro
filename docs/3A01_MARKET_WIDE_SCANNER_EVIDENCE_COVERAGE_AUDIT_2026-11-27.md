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

## 3A.01 acceptance matrix

| Acceptance gate | Status | Evidence / blocker |
|---|---|---|
| Deterministic market-wide orchestration and API | Implemented on PR #131 | Backend implementation and regression tests are in the draft integration PR |
| Dedicated frontend entry point | Implemented on PR #131 | UI module and build integration are in the draft integration PR |
| Backend and contract CI for PR #131 implementation head | Passed | Runs 45895229307 and 45895305164 are successful on the recorded code/docs commit line; frontend smoke CI passed on the earlier code/UI head |
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

PR #131 (`reconcile/3a01-on-current-main`) is still open and draft. At the audit check it was 10 commits ahead and 6 behind `main`, with GitHub reporting it not mergeable. It must be reconciled against the latest main before integration. Do not merge the older PR #112 as a substitute; it risks replacing newer application features.

## Source reports

- [Equity-only universe gate — 2026-11-26](EQUITY_ONLY_UNIVERSE_GATE_2026-11-26.md)
- [P4.23 — 29-date official NEPSE per-security history window](P4.23_29_DATE_OFFICIAL_SECURITY_HISTORY_WINDOW_2026-11-26.md)
- [P4.24 — Official bulk traded-symbol scope reconciliation](P4.24_OFFICIAL_BULK_SYMBOL_SCOPE_RECONCILIATION_2026-11-26.md)
- [Stage 1 Runtime Evidence Gate](STAGE1_RUNTIME_EVIDENCE_GATE.md)
- [NEPSE historical session calendar and integrity gate](NEPSE_SESSION_CALENDAR_AND_INTEGRITY_GATE.md)

**Final disposition:** 3A.01 implementation work is substantially built, but task acceptance is not complete. Keep the scanner research-only and fail-closed. Do not advance to 3A.02 until the remaining data, integration and deployment gates pass.
