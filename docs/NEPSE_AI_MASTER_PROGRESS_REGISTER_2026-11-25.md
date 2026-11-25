# NEPSE AI — Master Progress, Evidence and Roadmap Register
**Report date:** 2026-11-25  
**Project:** NEPSE AI / broker-and-stock footprint intelligence  
**Maintained in:** `jaljala044/nepse-elite-ai-scanner-pro`  
**Status:** Active engineering and data-evidence preparation; canonical data promotion is blocked.

> This register is the durable project progress record. Update it after each substantive work session. A planned task is not complete until its evidence, artifact, tests and commit are recorded. Do not represent scheduled automation as continuous background execution.

## 1. Executive status

The project has progressed through foundational data-integrity audits, security improvements, repeat-row extraction, exception-ledger design and initial instrument-universe research. The latest full repeated-adjacent-OHLCV extraction succeeded on both pinned historical archives and its baseline-count discrepancy has been explained exactly.

**No historical OHLCV or floorsheet archive has been approved as canonical/training data.** Important blockers remain: primary-source exchange-session evidence, verified instrument membership, unresolved invalid OHLCV and cross-source conflicts, floorsheet source coverage/provenance, rights to use/redistribute source data, and point-in-time availability.

### Scope and priorities agreed with project owner

- Current project universe target: **281 equities + 47 mutual funds**.
- Exclude non-convertible debentures, suspended instruments and delisted instruments from the active universe output, while retaining historical lifecycle records for point-in-time research.
- Version 1 priority: **120 trading days**, with a one-year collection target where feasible.
- Later version: seek **2–3 years** of historical coverage.
- Required intelligence: market-wide and stock-level footprints, recurring participation/accumulation/distribution behaviour, broker activity, historical-episode matching, scenario estimates with evidence and calibrated confidence.
- Enforce strict point-in-time/no-lookahead rules, source provenance, timestamps, corporate-action awareness and explicit uncertainty.
- Never fabricate missing records, session dates, broker identity, instrument membership, or data rights.

## 2. Achievement register

### A. Session-weekday helper — completed, tested

Repository: `jaljala044/nepse-smc-data`

- Corrected historical weekday candidate regimes in `nepse_session_date.py`:
  - Through 2022-05-14: Sunday–Thursday candidates.
  - 2022-05-15 through 2022-06-14: Monday–Friday candidates.
  - 2022-06-15 through 2022-09-16: Sunday–Friday candidates.
  - 2022-09-17 through 2026-04-05: Sunday–Thursday candidates.
  - From 2026-04-06: Monday–Friday candidates.
- Helper documentation explicitly warns that weekday candidates do not prove a session occurred; exchange holidays, closures and exceptional sessions need separate evidence.
- Helper correction commit: [b73f8a5](https://github.com/jaljala044/nepse-smc-data/commit/b73f8a5e09821f4722dc83790e75dfc052f432eb).
- Added six unit tests and workflow. Corrected the boundary test after the first run exposed that 2022-09-16 was still a Friday candidate.
- Successful workflow: [run 45492038013](https://github.com/jaljala044/nepse-smc-data/actions/runs/45492038013).
- Work log: `NEPSE_SESSION_WEEKDAY_FIX_2026-11-25.md`, commit `a55a9097375782d0a982f1f94a881f0a4e036698`.

**Remaining:** build a date-level primary-evidence calendar; do not use this weekday helper as an authoritative calendar.

### B. Floorsheet fetcher transport security — code change complete; live production status unverified

Repository: `jaljala044/nepse-automation`

- Changed TLS verification from disabled to enabled in `fetch_floorsheet.py`. TLS failure should fail closed, not disable certificate checks.
- Changed date handling to Nepal local time (UTC+05:45) rather than the runner's local date.
- Security fix commit: [9dda76f](https://github.com/jaljala044/nepse-automation/commit/9dda76f46e9fd3dc199c7062af68a0029a23306a).
- Review record commit: `c42702731b460eb47746accee893648e7e4da761`.

**Not production-ready:** current script clears the existing worksheet before upload; no immutable raw API response/hash; actual exchange session date not verified from response metadata/primary source; no confirmed live NEPSE or Google Sheets execution; dependency pinning and full tests remain outstanding. Never claim a live successful fetch based on this code change.

### C. Floorsheet archive coverage and cross-source audit — analysis complete; canonical promotion blocked

Repository: `jaljala044/nepse-automation`

Reviewed:
- `data/reports/floorsheet-window-cross-source-comparison.json`
- `data/reports/socrateai-floorsheet-window-audit.json`
- `data/reports/urek-floorsheet-window-audit.json`
- `data/reports/socrateai-floorsheet-window.json`
- `data/reports/urek-floorsheet-window.json`
- `data/reference/nepse_observed_index_dates_2026-05-18_2026-11-24.csv`

Findings:
- SocrateAI: 120/120 observed-index candidate dates acquired; 373,773,838 bytes; zero download errors.
- Urek: 70/120 candidate dates acquired; 50 missing; 3,862,849 rows; quantity 755,991,047; amount NPR 315,580,133,330.96; no invalid-day or file errors.
- 70 shared dates; 3,862,849 shared contracts; zero shared-field mismatches; zero duplicate contracts in either source on shared dates; zero audit errors.
- Matching shared rows do not prove independent source lineage. Independent provenance is not established; no canonical promotion approved.
- SocrateAI audit companion file `data/reports/socrateai-floorsheet-window-audit.json` is zero bytes/empty despite another archive report marking acquisition complete.
- Both publishers declare MIT licenses, but upstream data lineage/rights are not independently verified.
- Urek missing dates are not proof of exchange holidays or closures.
- All 120 observed-index reference dates are marked `calendar_verified_status=not_verified_primary_exchange_evidence_missing`.
- Index anomalies quarantined for investigation: 2026-06-01 duplicate rows; 2026-07-03 high below OHLC; 2026-07-07 conflicting duplicate rows.

Issue: [nepse-automation #2](https://github.com/jaljala044/nepse-automation/issues/2) records the source coverage, missing dates, calendar and provenance acceptance gates.

### D. Historical OHLCV audit — completed; integrity gate FAIL

Repository: `jaljala044/nepse-elite-ai-scanner-pro`

Workflow evidence: [OHLCV audit run 45397942163](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45397942163).

Pinned source commits:
- `nepse-smc-data`: `937cfcf93d78dfcf28a9f09bb13291447988157b`; tree `5b4f7593523b92fe81b6cd3cb09584b256760314`.
- `nepse-history-starter`: `b60728d39f34e0f9e428675d817fd52ed2784da6`; tree `a0cff911b0eb3610b935f6c93b63ddeb971ea283`.

Each repository had 525 ticker OHLCV files audited (1,050 files total):
| Measure | SMC | History Starter |
|---|---:|---:|
| Rows | 314,712 | 301,632 |
| Unique symbol/date keys | 313,381 | 301,632 |
| Invalid OHLC rows | 1,331 | 0 |
| Duplicate dates within ticker | 0 | 0 |
| Out-of-order transitions | 0 | 0 |
| Baseline repeated adjacent calendar-row flags | 94,421 | 102,121 |
| Download errors | 0 | 0 |

Across sources:
- 293,863 overlapping symbol/date keys.
- Eight differing overlapping records: API 2026-11-19; BGWT 2025-07-28; HRL 2026-11-19; MEHL 2025-07-28; RAWA 2025-07-28; RHGCL 2025-07-28 and 2026-11-19; ULHC 2025-07-28.
- 1,331 invalid OHLC rows in SMC: 796 high-bound violations and 535 low-bound violations.
- 25 ticker file blobs differ between repositories; blob inequality is not automatically a row-level conflict.
- SocrateAI unadjusted EOD cross-check reviewed 1,339 candidates across 995 dates; one external date was not published. It is secondary corroboration, not exchange-origin truth.

The audit proves the downloaded pinned files were parsed and these row-level findings were found. It does not prove all NEPSE sessions/instruments are represented, nor resolve corporate actions, source lineage, licensing, point-in-time availability or broker/floorsheet relationships.

### E. OHLCV exception ledger — generated and validated locally; not yet committed as ledger data

- Downloaded actual audit artifact ID `14921283424`, workflow run `45397942163`.
- Artifact SHA-256: `e1e5e8ac84e1d2ad273b605725c69614693a831117f96a6b8d7f5af2b4c81cb8`.
- Generated local files:
  - `/mnt/data/ohlcv_exception_ledger_2026-11-25.json` (~1.98 MB)
  - `/mnt/data/ohlcv_exception_ledger_2026-11-25.csv` (~1.09 MB)
- 1,339 unique exceptions: 1,331 invalid OHLC rows + 8 cross-source conflicts.
- All 1,339 dispositions `quarantined_unresolved`.
- JSON/CSV IDs and counts agree. Invalid rows retain source commit, path, file hash, CSV line and raw row. Conflicts retain both source versions; unknown source CSV line numbers are left null rather than guessed.
- Added `scripts/validate_ohlcv_exception_ledger.py`, regression tests and audit documentation in GitHub. Validator checks counts, IDs, unresolved dispositions and evidence fields.
- **Important:** actual 1.98 MB JSON and 1.09 MB CSV remain local files; they have not been committed to GitHub as ledger data. Do not say otherwise.

### F. Repeated adjacent OHLCV extraction — full archive success; counts reconciled

Repository: `jaljala044/nepse-elite-ai-scanner-pro`

- Added read-only extractor `scripts/extract_repeated_adjacent_ohlcv.py`, pinned-source workflow `.github/workflows/repeated-adjacent-ohlcv-audit.yml`, and unit tests.
- Fixed workflow YAML/test step and hardened handling of incomplete rows.
- Extractor now emits calendar-day gap, OHLC bounds validity, baseline eligibility and reason; incomplete rows break adjacency.
- Full pinned-source run [45532881509](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45532881509) succeeded.
- Enriched full pinned-source run [45533449785](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45533449785) succeeded; both source checkouts, tests, extraction and artifact upload passed.
- Enriched artifact ID `14985599288`; ZIP SHA-256 `4b8b7c27c642fee768eb3b031928e785a5ef296dc346b4d5c3b8212ba09def67`.
- Broad extraction: 196,784 review candidates (SMC 94,543; History Starter 102,241).
- Exact reconciliation:
  - Baseline-comparable: 196,542 (94,421 + 102,121).
  - Date-gap candidates: 240 (120 per source).
  - Additional repeated signature with invalid OHLC bounds: 2 (SMC only).
  - Thus 196,784 = 196,542 + 240 + 2.
- Every candidate remains `calendar_status_unverified_review_flag`; baseline-comparable means consecutive calendar dates and valid OHLC bounds, not verified exchange sessions.
- New extractor commit: [72eed3d](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/72eed3d0306ff8cf711d7416b06373721cc30cb4).
- Regression test commit: [136d376](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/136d376cafed8ca36a1fbf061befe2383a775f0b).
- Reconciliation report commit: [bf88999](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/bf88999690932de3ded86850acec0c0f6b8e3138).
- Enriched rerun report commit: [e9d512a](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/e9d512a2c4808ce5537811bf3db1f3120998e0cd).
- Issue [#5](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/issues/5) updated with run, artifact, reconciliation and remaining gates.

### G. Active universe research — evidence gathered; manifest not verified

Issue [#6](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/issues/6); report `docs/ACTIVE_UNIVERSE_SOURCE_RESEARCH_2026-11-25.md`.

- Official NEPSE stock list search snapshot: 2026-10-15; official catalogue snapshot: 2026-09-24. Both are primary exchange pages, but accessible snapshots do not provide a complete, dated 2026-11-25 instrument-type/lifecycle registry.
- Secondary directories disagree: some show 47 mutual-fund schemes; Punji search snapshot shows 11 funds and 2 delisted/suspended. NEPSE Alpha has shown 284 actively traded stock entries.
- These counts may have different definitions; no forced reconciliation or invented symbol list.
- Need official NEPSE/SEBON registry export or reproducible official endpoint response with instrument IDs, symbols, names, instrument type, listing/trading status and effective dates; retain raw response/hash.

### H. Project tracking and automation

- Three earlier scheduled audits existed: footprint audit, build audit and historical data monitoring.
- A daily continuation task was created: “Continue NEPSE AI project work”, daily 9:00 AM Asia/Dubai starting 2026-11-26, with a prompt to inspect state, continue scoped work, preserve evidence, and report. One manual run was invoked. A later lookup returned 404, so current task state has not been re-verified; do not claim it is definitely active now.
- Scheduled execution is not continuous background work. This assistant does not run indefinitely between user turns.

## 3. Current hard blockers

1. No primary-source, date-by-date NEPSE session calendar with preserved raw evidence, hash, publication/effective date and exceptional-session handling.
2. No official dated instrument membership/lifecycle registry proving the exact 281 equities + 47 mutual funds.
3. 1,331 invalid OHLC rows and eight source conflicts remain unresolved/quarantined.
4. Repeated-row candidates not classified against verified sessions.
5. Floorsheet archive has 50 Urek candidate dates missing; independent provenance not established; empty companion audit file requires correction.
6. No final evidence of third-party source data licensing/redistribution permission.
7. Floorsheet fetcher not yet safe for unattended production because worksheet clearing is destructive and immutable raw capture/idempotency/tests are incomplete.
8. No complete end-to-end evidence yet for broker summary, corporate action, index, adjusted/unadjusted OHLCV, point-in-time availability or cross-domain reconciliation.
9. The actual exception ledger files remain local, not committed.
10. The 120-day / one-year target coverage by verified current universe is not yet demonstrated.

## 4. Current next five priorities (execution order)

### Priority 1 — Establish an authoritative NEPSE session calendar
- Find official NEPSE notices, exchange circulars, trading schedule changes, holiday/closure announcements and any official date/session endpoint.
- Treat government/NRB holiday lists as corroboration only; bank holidays do not prove NEPSE closure.
- Build a source register with exact URL, published date, effective interval, retrieved timestamp, raw body/file, SHA-256, authority level and affected dates.
- Preserve known weekday regime changes as candidate rules, not proof.
- Output: versioned date-level calendar with statuses `confirmed_open`, `confirmed_closed`, `exceptional_session`, `unverified`; no silent inference.
- Gate: every status backed by evidence; unresolved dates remain unverified.

### Priority 2 — Reconcile all 196,784 repeated-row candidates
- Download enriched artifact ID `14985599288`; independently validate JSON/CSV totals and hashes.
- Join previous/current dates to the verified session calendar.
- Separate consecutive exchange sessions, date gaps containing confirmed closed days, confirmed non-session observations, and unresolved cases.
- Never infer a missing session from a gap alone; inspect raw source and independent evidence.
- Output: row-level disposition and calendar evidence pointer. Do not mutate raw source.

### Priority 3 — Resolve the 1,339 OHLCV exception ledger and source conflicts
- Commit immutable JSON/CSV ledger files (or a compact reproducible artifact pipeline if repository size policy requires) with hashes and validator run.
- Investigate the 1,331 invalid rows and eight source conflicts against independently authorized primary/licensed evidence.
- Preserve original values and source versions; only record correction overlays with evidence and reviewer rationale.
- Keep unresolved rows excluded from canonical/training data.

### Priority 4 — Build the official 281-equity + 47-mutual-fund universe manifest
- Identify official NEPSE/SEBON registry or documented official API response.
- Preserve unmodified payload, hash, retrieval time and effective date.
- Normalize instrument ID, symbol, name, type, listing status, trading status, suspension/resumption/delisting dates.
- Reconcile exactly 281 + 47 against the project owner's defined scope; explain every inclusion/exclusion and keep historical lifecycle entities.
- Do not infer missing entries from secondary directories.

### Priority 5 — Re-run coverage and quality audits against the verified universe
- Re-run 120-day, one-year and available 2–3-year OHLCV coverage per active equity/fund.
- Re-run floorsheet contract/stock/date coverage; reconcile 50 missing Urek candidate dates.
- Add corporate actions, indices, broker summaries, point-in-time timestamps, source lineage and data-rights status.
- Produce per-symbol/per-date coverage matrix, gaps, duplicates, stale rows, adjusted/unadjusted lineage and source confidence.
- Keep canonical promotion blocked until all required gates pass.

## 5. Following five priorities (next wave after the above)

6. **Make floorsheet ingestion production-safe:** immutable raw response capture, SHA-256, request/response metadata, idempotent append/upsert, no destructive sheet clear, retry/backoff, TLS enforcement, session-date verification, schema checks and test fixtures.
7. **Reconcile broker identity and footprint data:** stable broker IDs, name changes, buy/sell sides, contract IDs, duplicate handling, missing broker observations, broker-to-stock/date aggregation, and source provenance.
8. **Build point-in-time feature store:** as-of timestamps, publication/availability timestamps, corporate-action-aware prices, symbol lifecycle joins, no future leakage, immutable raw-to-normalized lineage.
9. **Build explainable footprint features and historical episode retrieval:** market breadth, turnover, concentration, broker accumulation/distribution, participation shifts, volume/price structure, regime context, per-stock and market-wide patterns.
10. **Backtest and validate scenario engine:** walk-forward splits, leakage tests, baseline comparisons, calibration, uncertainty intervals, costs/slippage, robustness across regimes and instruments; no trading claims until out-of-sample evidence supports them.

## 6. Data governance and acceptance policy

- Raw source archives are immutable; never edit upstream CSVs in place.
- Every derived record must retain source repository, commit/version, path, file hash, original row/line, extraction time and transformation version.
- Distinguish source observation date, exchange trade date, publication timestamp, retrieval timestamp and model decision timestamp.
- Never use future information in a historical decision replay.
- Calendar and instrument status must be point-in-time effective, not overwritten by today's status.
- Independent sources must have independently established lineage; matching values alone do not establish independence.
- Licenses declared by a downstream publisher do not automatically establish upstream rights.
- No automatic repair, forward-fill, deletion or source winner selection.
- Keep unresolved exceptions outside canonical datasets and training labels.
- Every report should state counts, scope, pinned versions, known gaps, confidence and next acceptance tests.

## 7. Report maintenance protocol

For each future work session, append a dated entry containing:
1. Objective and priority.
2. Repositories/files/URLs/artifacts examined.
3. Exact commands/workflows or tests and result.
4. New findings with row counts and hashes.
5. Commits/issues/artifacts created or updated.
6. What is complete versus partial/unverified.
7. Remaining blockers and next action.

When asked for “all progress”, retrieve this register plus latest GitHub commits, issues, workflows and artifacts; report any differences between this document and live repository state. Never imply work continued between turns unless an automation run actually executed.


## 8. Work-session update — 2026-11-25 (after master register creation)

### Permanent reporting record created
- Master register: [NEPSE_AI_MASTER_PROGRESS_REGISTER_2026-11-25.md](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/blob/main/docs/NEPSE_AI_MASTER_PROGRESS_REGISTER_2026-11-25.md)
- Commit: `bca84ab9b2feb52319fbb931ceff32d9537f515a`.
- It consolidates prior project scope, achievements, exact audit counts, pinned source commits, artifacts, hashes, issues, limitations, hard blockers, current five priorities and following five priorities.
- Future sessions must append evidence-based dated entries and reconcile the report against live repository state when asked.

### Priority 1 research advanced — primary calendar still not acquired
- Created [NEPSE_SESSION_CALENDAR_SOURCE_RESEARCH_2026-11-25.md](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/blob/main/docs/NEPSE_SESSION_CALENDAR_SOURCE_RESEARCH_2026-11-25.md), commit `0a22328e340d6ed7b763bf4e56cea9fcfec7a816`.
- Located official NEPSE catalogue and stock-list pages, but accessible snapshots are not a dated date-level session calendar.
- Located a 2026-04-08 ShareSansar report that attributes Monday-Friday trading (including Friday) to a NEPSE Board meeting on 22 Chaitra 2082. This is secondary reporting of the exchange decision, not the original NEPSE circular.
- Located official NRB 2083 holiday list effective 2026-04-14 through 2027-04-13. It explicitly describes NRB office hours as Sunday-Thursday and Friday half-day. This demonstrates why bank/NRB holidays cannot be substituted for NEPSE exchange sessions; the reported NEPSE weekday schedule differs.
- Conclusion: historical weekday regimes remain candidate rules only. No complete primary-source NEPSE session calendar was obtained. Do not classify any repeated-row candidate as a non-session solely from these sources.

### Current priorities — status refresh
1. **Calendar evidence acquisition:** research/documentation advanced; original NEPSE circular and complete official session dates still missing.
2. **196,784 candidate reconciliation:** extractor and enriched artifact complete; calendar join/classification blocked by Priority 1.
3. **1,339 OHLCV exception ledger:** validator and local ledger exist; actual JSON/CSV still not committed; source adjudication unresolved.
4. **281 + 47 instrument manifest:** source research documented; official dated registry still missing.
5. **Coverage reruns:** blocked pending verified manifest and calendar; do not run final canonical coverage conclusions on guessed membership.

### Following five priorities
6. Production-safe floorsheet ingestion and immutable raw capture.
7. Broker identity/footprint reconciliation and aggregation.
8. Point-in-time feature store with strict as-of lineage.
9. Explainable market-wide and stock-level footprint features and historical episode retrieval.
10. Walk-forward/backtest/calibration/leakage and robustness validation.

### Reporting rule
When the project owner asks for all progress, retrieve this register and current GitHub evidence. The report is a record of verified work, not a claim that work ran continuously between messages.


## 9. Work-session update — additional source and artifact verification (2026-11-25)

### Calendar schedule-transition evidence strengthened (still secondary)
- Located [Ratopati, 2026-04-06](https://english.ratopati.com/story/57517/stock-trading-closed-on-saturday-and-sunday-open-on-friday) and [The Himalayan Times, 2026-04-08](https://thehimalayantimes.com/business/nepse-shifts-to-mondayfriday-trading-week). Both report a NEPSE Board decision to move to Monday-Friday effective 2026-04-06, with Friday replacing Sunday.
- This corroborates the ShareSansar report from 2026-04-08. The original NEPSE signed notice/circular still has not been retrieved; the weekly regime is strongly secondarily corroborated, not primary-document verified.
- Expanded calendar source record: [NEPSE_SESSION_CALENDAR_SOURCE_RESEARCH_2026-11-25.md](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/blob/main/docs/NEPSE_SESSION_CALENDAR_SOURCE_RESEARCH_2026-11-25.md), latest commit `3f01d932d392bfc9021930c44a48078e8e477d07`.

### Enriched repeated-row artifact downloaded and independently revalidated
- Artifact ID `14985599288`; downloaded ZIP SHA-256 `4b8b7c27c642fee768eb3b031928e785a5ef296dc346b4d5c3b8212ba09def67`, matching the GitHub artifact digest.
- CSV row count: 196,784; unique (repository, path, current CSV line) identities: 196,784; required evidence fields present for all records.
- Exact split: 196,542 baseline-metric eligible (calendar-day adjacency + valid OHLC bounds); 240 date-gap/unparseable; two repeated signatures with invalid OHLC bounds.
- All 196,784 remain review-only; no session classifications were assigned.
- This completes artifact integrity verification for Priority 2 input. The exchange-calendar join itself remains blocked by the missing primary date-level calendar.

### Priority state
1. Calendar: weekly schedule transition supported by three secondary reports; primary NEPSE circular and date-level holiday/open/closure archive still outstanding.
2. Repeated rows: full enriched artifact independently verified; calendar classification remains pending.
3. Exception ledger: still need to commit local 1,339-row JSON/CSV ledger or a reproducible artifact pipeline and resolve cases against authorized sources.
4. Active universe: still need dated primary registry and exact 281 + 47 symbol/ID reconciliation.
5. Coverage: still waiting for verified calendar and manifest before final coverage conclusions.

### Following five priorities unchanged
6. Production-safe immutable floorsheet ingestion.
7. Broker identity/footprint reconciliation.
8. Point-in-time feature store.
9. Explainable footprint features and historical episode retrieval.
10. Walk-forward scenario validation, leakage tests and calibration.


## 10. Work-session update — active-universe and exception-evidence acquisition (2026-11-25)

### Active-universe search extended
- Additional search did not locate a reproducible official NEPSE/SEBON endpoint response or downloadable registry containing stable security IDs, symbol, instrument type and lifecycle effective dates together.
- A broad third-party symbol page mixes equities, funds and debt-like symbols; symbol-only scraping is not safe for membership classification.
- Research update: [ACTIVE_UNIVERSE_SOURCE_RESEARCH_2026-11-25.md](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/blob/main/docs/ACTIVE_UNIVERSE_SOURCE_RESEARCH_2026-11-25.md), commit `51f67e5a74449c55f0e7180796061fa904440e3a`.
- Outcome: no manifest created; exact 281 + 47 remains a project scope target pending authoritative instrument registry evidence.

### Exception artifact re-acquired
- Re-downloaded OHLCV audit artifact ID `14921283424` to continue ledger work. Its ZIP contains the aggregate audit JSON and SocrateAI cross-check JSON. The artifacts expose all 1,331 invalid-row candidate values and eight cross-source conflicts, but do not themselves expose every original CSV line number in a directly reusable field.
- Do not invent missing row numbers. Ledger recreation must either retrieve original pinned ticker CSVs to recover exact source lines or preserve the line number as explicitly unavailable.
- Existing committed validator remains a useful gate, but ledger data files still need a controlled commit or reproducible immutable artifact workflow.

### Priority execution update
- Priority 1: calendar research documented; primary official circular and full date-level calendar still missing.
- Priority 2: enriched 196,784-row artifact downloaded, hash verified and all CSV rows independently counted; calendar join blocked.
- Priority 3: source audit artifact re-acquired; ledger recreation/commit and adjudication still open.
- Priority 4: additional official registry search completed without finding sufficient source; no manifest.
- Priority 5: remains blocked until verified date calendar and universe manifest exist.
