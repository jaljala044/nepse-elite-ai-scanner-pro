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


## 11. Work-session update — priorities 6–10 engineering contracts (2026-11-25)

- Retrieved the live master register (blob SHA `a8dafdcae6897b9f147420f25eeb9a64c6717199`) and latest repository commit history before editing.
- Added [NEPSE_AI_ENGINEERING_CONTRACTS_PRIORITIES_6_TO_10.md](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/blob/main/docs/NEPSE_AI_ENGINEERING_CONTRACTS_PRIORITIES_6_TO_10.md). It defines immutable floorsheet capture and safe ingestion invariants; broker identity and aggregation models; point-in-time temporal fields and leakage barriers; explainable market/security footprint features and episode retrieval; and walk-forward scenario validation, baselines, calibration, costs and negative tests.
- The new document explicitly distinguishes engineering contracts from implemented/live capabilities. It does not claim production ingestion, broker mapping, feature store, predictive performance or deployment.
- Implementation sequencing is dependency-aware: Priority 6 capture/idempotency primitives first; Priority 7 broker registry and reconciliation; Priority 8 as-of store; Priority 9 explainable feature/episode layer; Priority 10 validation engine. Parallel synthetic fixtures are allowed, but real-data model activation remains blocked by unresolved session calendar, universe, provenance, rights and coverage.
- Next coding slice: implement and test Priority 6 immutable raw-envelope, hash, append-only persistence and idempotency against synthetic fixtures. Then implement broker identity tables and reconciliation fixtures. No live exchange endpoint has been activated.


## 12. Work-session update — Priority 6 implementation slice (2026-11-25)

### Implemented in repository
- Added `backend/app/raw_capture.py` (commit `090d65cbf8e8ed8412d8fcd2231f28cb40ecf14b`): standard-library raw-response envelope builder, timezone-aware UTC normalization, exact-byte SHA-256 and byte count, explicit session-evidence status validation, and immutable content-addressed persistence using atomic no-clobber file creation. It refuses payload/hash mismatch, path traversal components, and conflicting metadata for the same content hash; identical payload+manifest repeats are idempotent.
- Added `backend/tests/test_raw_capture.py` (commit `37d0544a3c785003a2cc9d5419afb6d750203580`): seven test cases cover exact bytes/hash, UTC conversion, naive timestamp rejection, evidence requirements for confirmed session statuses, idempotent persistence, hash mismatch and conflict non-overwrite.
- The code does not perform network requests and cannot disable/enable TLS. Its contract explicitly requires callers to supply redacted metadata and use a TLS-verifying HTTP client. It does not infer session dates or promote source data.

### Verification status and limits
- The existing `.github/workflows/backend-tests.yml` is configured to run unittest discovery on pushes to `main`, pull requests and manual dispatch. The connector's commit-associated workflow lookup returned no run for the test commit; therefore the seven tests are **authored but not yet confirmed executed**. Do not call this a passing CI result.
- No live NEPSE endpoint was called, no Google Sheet was modified, and no live ingestion was activated.
- Priorities 7–10 remain engineering contracts, not implemented features. Broker mapping, point-in-time feature generation, footprint signals and predictive validation are not yet live.

### Next implementation actions
1. Obtain an actual successful backend-tests workflow result; fix any failures before proceeding.
2. Add source/session/fetch metadata validation and captured-fixture integration tests around raw capture.
3. Implement broker source-ID/name history and explicit ambiguous/unmapped identity states.
4. Continue only with synthetic fixtures until primary session calendar, instrument registry, source lineage and rights gates are met.


## 13. Work-session update — five implementation slices across priorities 6–10 (2026-11-25)

### Implemented and committed
1. **Priority 6 — raw capture foundation:** `backend/app/raw_capture.py` and seven tests. Exact bytes, SHA-256, timezone-aware UTC timestamps, evidence-gated session status, immutable content-addressed persistence and idempotency. Backend workflow run [45534399726](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45534399726) completed **success** on commit `c62c6dd880d9617634e8e48437625557d691b4ef`.
2. **Priority 7 — broker identity primitives:** `backend/app/broker_identity.py` and seven tests. Source-specific code mapping, verified/ambiguous/unmapped/rejected states, evidence requirement for verified links, and side-specific aggregation that keeps unknown identities separate. Workflow runs [45534500188](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45534500188) and [45534504253](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45534504253) completed **success**.
3. **Priority 8 — point-in-time primitives:** `backend/app/point_in_time.py` and four tests. UTC-aware `available_at` cutoffs; missing availability timestamps excluded; future/late records excluded from historical snapshots. Workflow runs [45534531947](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45534531947) and [45534537413](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45534537413) completed **success**.
4. **Priority 9 — explainable feature primitives:** `backend/app/footprint_features.py` and four tests. Market breadth with explicit denominator/coverage, prior-only volume baseline, and broker participation that uses only verified broker mappings while exposing unknown share. Workflow runs [45534568441](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45534568441) and [45534571534](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45534571534) completed **success**.
5. **Priority 10 — scenario validation primitives:** `backend/app/scenario_validation.py` and five tests. Brier score, log loss, constant-prevalence baseline and expanding chronological walk-forward folds. Workflow runs [45534593982](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45534593982) and [45534599502](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45534599502) were still **in progress** at the time of this update; do not report them as passed until completed.

### Scope and interpretation limits
- These are dependency-free research primitives, not a production data pipeline or a trained prediction system.
- No live exchange API or Google Sheets were accessed. No production ingestion or trade execution was activated.
- Broker IDs are not authoritatively mapped; only caller-supplied links marked verified with evidence are accepted by the helper. Effective-dated broker registry persistence and exchange broker master source still need implementation.
- Point-in-time helper enforces availability cutoffs but does not yet provide a persistent versioned feature store, corporate-action engine, or as-of security master.
- Footprint features are descriptive; they do not infer accumulation/distribution intent or produce trading recommendations. Their inputs must be verified and point-in-time filtered upstream.
- Validation metrics are helper functions; no real forecast dataset, trained model, calibrated confidence, fees/slippage backtest or final holdout has been run.
- Primary NEPSE session calendar, dated official 281-equity + 47-mutual-fund manifest, source lineage/rights and historical coverage gates remain unresolved. No feature or model output is approved for canonical training or live decisions.

### Next implementation slice
- Check completion of the two scenario-validation workflow runs.
- Add integration-level tests linking raw capture to broker ingestion, point-in-time snapshots and feature generation using synthetic fixtures.
- Add effective-date-aware broker identity mapping and corporate-action/security-master as-of joins.
- Build a reproducible dataset/label contract and fold-level evaluation report before any model training.


## 14. Work-session update — next five engineering priorities / integration layer (2026-11-25)

### Implemented in GitHub
1. **Broker identity effective dating:** extended `BrokerIdentityLink` with inclusive `valid_from` / `valid_to`; historical resolution now accepts an explicit `as_of` date, excludes dated mappings when no as-of date is supplied, rejects reversed date ranges and returns ambiguous when multiple effective mappings overlap. Regression tests cover historical mapping changes, missing as-of, overlap and invalid ranges. Commits: [7930b01](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/7930b018fc7c56f6c8036f566f7b703f6d869d51), [f3105c3](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/f3105c396fd4f2606d58c68f532513db255a5510).
2. **Temporal security master and corporate actions:** added `backend/app/temporal_registry.py` with effective-dated security lifecycle resolution, conflicting-overlap ambiguity, evidence IDs, and corporate-action as-of filtering by `available_at` (not merely ex-date). Five tests cover lifecycle changes, ambiguity, invalid ranges, late announcements and timezone enforcement. Commits: [59e9782](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/59e9782baa096fe4f9c9de675c285f82fb384121), [40e2725](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/40e2725b6b35acdfdaa7ed640609854be5f1b550).
3. **Point-in-time feature integration:** added `backend/app/feature_pipeline.py` to apply availability-time filtering before market breadth, per-security descriptive features and broker participation are computed. Synthetic test proves a future OHLCV row is excluded before feature calculation. Commits: [ec1844b](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/ec1844b0b9349342c6f9f7c74bec1aec235e5f28), [1f06c96](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/1f06c96a0145756f8ee15f5a6ab46725b84e7c97).
4. **Walk-forward evaluation report:** added `backend/app/walk_forward_report.py`; expanding chronological folds now compute a prevalence benchmark from training outcomes only, rather than using test-fold prevalence. Tests cover fold chronology, insufficient history and invalid probabilities. Commits: [6fa7a3d](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/6fa7a3db4b398f43171bca27399791adf4f694c2), [b7b1e05](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/b7b1e0557c7ae52f0e3558b9108f1ce92367e1e9).
5. **Raw-capture path hardening:** corrected capture-key validation to reject Windows backslash path separators as well as slash traversal. Commit: [372b1f2](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/372b1f22ac3e3dd295fc6431e1b26bed26af8387).

### Verification and limitations
- Backend test workflows for all five implementation slices completed **success**: [broker effective-date resolver run 45534892339](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45534892339), [broker regression tests run 45534909202](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45534909202), [temporal registry run 45534860415](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45534860415), [temporal registry tests run 45534876865](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45534876865), [feature pipeline run 45534924428](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45534924428), [feature pipeline tests run 45534936077](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45534936077), [walk-forward report run 45534955301](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45534955301), [walk-forward report tests run 45534968600](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45534968600), and [raw-capture hardening run 45534978362](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45534978362).
- The changes are tested through committed synthetic unit tests, but no local execution or real NEPSE source ingestion is claimed here.
- Security-master and corporate-action records are data structures/lookups only; no authoritative NEPSE/SEBON/CDSC corporate-action feed or verified registry has been loaded.
- Feature outputs remain descriptive and depend on correctly sourced, point-in-time input rows. No accumulation/distribution intent classifier, trained model, calibration, trading signal or live decision engine is claimed.
- Walk-forward report is an evaluation scaffold; no verified real dataset or forecast series has been evaluated, and no predictive edge is established.
- Raw capture still does not fetch the network, manage TLS, verify actual exchange session dates, or prove data rights. Caller must use TLS verification and provide redacted metadata.

### Next acceptance gates
- Confirm backend CI completion and fix failures before declaring these slices green.
- Add full synthetic end-to-end capture → normalization → as-of registry → feature → fold evaluation test.
- Add source lineage, raw fixture hashes, and documented field contracts for floorsheet and OHLCV.
- Keep real-data activation blocked until primary session evidence, official dated 281-equity + 47-mutual-fund manifest, broker source identity, source rights and coverage are verified.


## 15. Work-session update — next five priorities, step-by-step implementation (2026-11-25)

### Step 1 — synthetic end-to-end capture → normalization → features
- Added `backend/app/capture_pipeline.py`: persists exact response bytes and manifest before parsing; validates a deliberately narrow JSON-array fixture schema; overwrites any untrusted row-level `available_at` with the capture receipt timestamp; then applies the point-in-time feature pipeline.
- Added `backend/tests/test_capture_pipeline.py`: verifies raw-byte preservation, normalized record counts, market breadth, unknown broker retention, post-decision receipt exclusion, untrusted availability override and unsupported record rejection.
- Both implementation and test workflows passed: [45535181860](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45535181860), [45535210716](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45535210716).

### Step 2 — floorsheet contract records and duplicate reconciliation
- Added `backend/app/floorsheet_contract.py`: typed contract schema, Decimal monetary/quantity values, payload hash and source-row lineage, positive-value checks, gross amount reconciliation, and conservative classification of unique / exact duplicate / conflicting duplicate rows.
- All duplicate rows are retained; no silent de-duplication occurs. Amount exceptions are separately flagged.
- Both implementation and test workflows passed: [45535249235](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45535249235), [45535268903](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45535268903).

### Step 3 — broker-name history and source-code reconciliation
- Extended `backend/app/broker_identity.py` with dated source-name observations and effective-dated canonical broker-name records.
- Exact normalized name matches return `candidate_requires_evidence`, never an automatically verified broker link. Multi-entity matches remain ambiguous; source name history is preserved chronologically.
- Both implementation and test workflows passed: [45535313914](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45535313914), [45535329707](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45535329707).

### Step 4 — versioned point-in-time feature snapshot with corporate-action joins
- Added `backend/app/versioned_feature_store.py`: versioned content-addressed snapshot hash, effective-dated security-master join, corporate-action availability-time join, and immutable/idempotent snapshot persistence.
- Corporate actions are attached as evidence context only; historical OHLCV is not adjusted. Ambiguous security identities block the join.
- Both implementation and test workflows passed: [45535357162](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45535357162), [45535376771](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45535376771).

### Step 5 — evaluation coverage, missingness and leakage diagnostics
- Added `backend/app/evaluation_diagnostics.py`: expected-date coverage, missing decision dates, duplicate-date exclusion, missing-label reporting, future-input and premature-label leakage flags, and chronological fold metrics.
- Training labels are included only when their `label_available_at` is earlier than the first test decision time. Duplicate forecast dates are not arbitrarily selected or averaged.
- Commits: implementation [d84709c](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/d84709c9669b5f82b53dc69abcd0801101724170), tests [df5b55e](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/df5b55e62824de2088799b4b6ba3d10ee6b7c00a).
- Both implementation and test workflows subsequently completed **success**: [45535424520](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45535424520), [45535439412](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45535439412).

### Overall boundaries
- All new integration fixtures are synthetic. No live NEPSE fetch, Google Sheets write, or historical ZIP ingestion occurred.
- The JSON capture parser is a narrow fixture contract, not yet a parser for actual NEPSE floorsheet CSV/XLS exports.
- Floorsheet amount = quantity × rate is treated as a configurable-tolerance consistency check, not as a guarantee that every source's amount convention is identical.
- Broker-name matching remains review-only; no official broker master has been reconciled.
- Versioned feature snapshots do not yet prove the completeness or authority of security/corporate-action inputs.
- No forecast model, predictive edge, or live signal has been validated on verified historical data.

### Next acceptance gates
1. Confirm Step 5 CI and address any failures.
2. Add parser adapters only after a real source sample and field-level provenance are available.
3. Connect canonical floorsheet contract records to effective-dated broker identity resolution without dropping unknown parties.
4. Add primary-source security master, exchange calendar, corporate-action and data-rights evidence before historical training.


## 16. Work-session update — next ten priorities (2026-11-25)

### Priority 1 — connect normalized contracts to effective-dated broker identity
- Added `backend/app/floorsheet_broker_join.py` and `backend/tests/test_floorsheet_broker_join.py`.
- Each normalized contract emits separate buyer/buy and seller/sell party observations. Broker resolution is evaluated on the contract trade date using the existing effective-dated identity links.
- Source broker code, source payload SHA-256, source row number, contract ID, side and identity evidence IDs are retained. Unmapped and ambiguous parties remain explicit; no contract rows are dropped.
- Commits: implementation [7ca572a](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/7ca572a97426aa3ba4c4960eceef13aaa2669b38), tests [b3a9cee](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/b3a9ceeeadac5b3784ac01c58426f28a6facd56c).

### Priority 2 — add a real-source adapter boundary without guessing source columns
- Added `backend/app/floorsheet_csv_adapter.py` and `backend/tests/test_floorsheet_csv_adapter.py`.
- Adapter requires an explicit reviewed mapping from normalized fields to exact CSV headers; no column-name inference is performed. It preserves exact payload SHA-256 and physical source row numbers, reports malformed rows, and fails closed for missing/duplicate headers.
- The mapping is deliberately marked `source_specific_mapping_verified=false`. No real NEPSE/Mero Lagani/SocrateAI/other publisher field mapping is claimed because a representative source export has not yet been supplied or verified.
- Commits: implementation [9158124](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/9158124b25af03fd666b164a68c1bd95a00dec96), tests [8a97f10](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/8a97f102f4bcdad4bd7031d27d9e525cad664cbc).

### Backend test execution gate
- Added `.github/workflows/backend-contract-tests.yml`, running Python 3.12 `unittest` discovery over the complete `backend/tests` suite on backend changes: [23808b0](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/23808b0f2b9f1a79173580d9b6fae82d7188ccd8).
- At register-update time, the GitHub combined-status endpoint returned no status entries for the new commits. Therefore these two slices are **committed, but CI execution is not yet independently confirmed**. Do not report them as passing until an Actions run is visible and successful.
- Tests are synthetic fixtures. The CSV adapter is not a verified real-source parser, and no historical floorsheet archive was parsed by it in this session.

### Remaining priorities in this ten-step sequence
3. Add explicit broker aggregation from joined contract-party rows, with exact Decimal totals and coverage denominators.
4. Define source provenance and rights metadata for every capture and normalized batch.
5. Add a source-to-canonical OHLCV row adapter with explicit mappings and exception retention.
6. Build a dated instrument-manifest import/validation gate for the required 281 equities and 47 mutual funds; do not manufacture membership.
7. Add exchange-session evidence ingestion and a verified/unknown session-state gate.
8. Add corporate-action source ingestion and evidence-backed adjustment policy, keeping raw prices immutable.
9. Add cross-source coverage and reconciliation reports for the 120-day / one-year priority window.
10. Add a real-data readiness gate that blocks model training until lineage, calendar, universe, broker identity, rights and quality thresholds are satisfied.


## 17. Remaining eight priorities — implementation record (2026-11-25)

### Priority 3 — exact broker aggregation and coverage
- Added `backend/app/broker_aggregation.py` and tests.
- Uses `Decimal` totals at trade-date/security/broker/side/identity-status grain. Unknown and ambiguous identity rows remain separate buckets.
- Reports party-observation, gross-amount and quantity denominators and verified/unresolved coverage. Duplicate source-payload/row/side lineage is rejected.
- Commits: [1a7e5f7](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/1a7e5f7ddc140af270debe09ed107076de0c6e47), [65cf790](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/65cf79097cfd8ff1f6a6199ebec123f59c78517e).

### Priority 4 — source provenance and rights metadata
- Added `backend/app/source_provenance.py` and tests.
- Records publisher/source identity, provenance class, capture method/time, actor, exact payload hash/bytes, rights state, attribution/redistribution declarations and evidence references.
- Unknown/review-required rights block rights clearance. Redistribution requires an explicit permission state and evidence ID. These declarations are not legal advice or an independent legal opinion.
- Commits: [4ac39d9](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/4ac39d9d68e725bb5ad191a2b68980e97df008e3), [3936bea](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/3936beac96f140a5f5b6d2f4a36c6e55ae6e3a89).

### Priority 5 — explicit-mapping OHLCV source adapter
- Added `backend/app/ohlcv_csv_adapter.py` and tests.
- Requires explicit source-header mapping; records source payload SHA-256, physical CSV line, raw mapped values and numeric values. Invalid OHLC bounds are retained as quarantined exceptions; malformed rows are retained in a rejection ledger.
- Source-specific mapping remains unverified, and no source archive was parsed in this step. The adapter does not promote data.
- Commits: [9b90d62](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/9b90d62a401eb2746e82b412b4cfde5ada7c841c), [3f759db](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/3f759db130f253b8519c3f60cac20479618c711c), input-row count correction [8e51cdf](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/8e51cdf09cf2efb252bac9b1518cad791a1ea187).

### Priority 6 — dated active-universe manifest gate
- Added `backend/app/instrument_manifest.py` and tests.
- Validates effective dates, stable IDs, unique active symbols/IDs, target counts (281 equities and 47 mutual funds), primary-source tier and source-record evidence. Suspended/delisted instruments are not counted as active; lifecycle rows are retained.
- An empty or incomplete manifest fails closed. This is a validator, not an official 328-instrument manifest; exact official membership is still unverified.
- Commits: [81f6de4](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/81f6de4c30bf8cb19fade3ac1a20f27aa4a90ac0), [8d9001f](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/8d9001fe0be13fd440c36ef6aaaa9d858bdea8fb).

### Priority 7 — point-in-time exchange-session evidence
- Added `backend/app/session_evidence.py` and tests.
- Resolves confirmed trading sessions, confirmed exchange closures and exceptional sessions only from evidence visible at the decision time and, by default, exchange/regulator primary tiers. Conflicts remain unknown.
- Missing evidence never means closed. Weekday regimes and banking holidays are not silently converted into confirmed NEPSE sessions.
- Commits: [549ab07](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/549ab0715c6240c4abe30f0a775e052f617978e4), [c095f8b](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/c095f8ba54821cfdd273525a552434f491357cb0).

### Priority 8 — corporate-action evidence and adjustment policy
- Added `backend/app/corporate_action_policy.py` and tests.
- Validates event identity, type, announcement/availability timestamps, status and positive Decimal factors. As-known selection excludes events not yet available at decision time.
- Adjustment eligibility is only a separate review decision; no raw price series is modified and no adjusted series is emitted.
- Commits: [eb2f880](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/eb2f880aab411100b584afab3d17b58dd2d6c32e), [37b7241](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/37b724175aa3e5996ab980c6d08a8161c8fc2187).

### Priority 9 — expected-session coverage and cross-source reconciliation
- Added `backend/app/historical_coverage.py` and tests.
- Computes source-by-source coverage against caller-supplied verified session dates and symbols, flags duplicate keys and differing overlapping close values, and reports union gaps.
- It does not infer exchange sessions from weekdays or select a canonical source. No 120-day/one-year real archive run is claimed.
- Commits: [6545c4c](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/6545c4c84b028a79c32939f93ea4292f433a70ff), [df7d54d](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/df7d54d9d7b7c9f5349a9b53680d74119279d82c).

### Priority 10 — fail-closed training readiness gate
- Added `backend/app/training_readiness.py` and tests.
- Requires explicit boolean evidence for universe, calendar, rights, lineage, OHLCV integrity, broker identity, point-in-time leakage, corporate-action review, historical coverage and holdout protocol. Configurable OHLCV and broker-identity coverage thresholds are enforced.
- Missing/false evidence blocks model training. The gate reports no model performance and does not claim the current project is training-ready.
- Commits: [44871a8](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/44871a8fbe249fff60a4ff77f480ce48b8f58519), [2b93b5c](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/2b93b5c29e4f6d90dc53d9c1abf12583af3be4dd).

### Verification status and blockers
- Backend CI workflow `.github/workflows/backend-contract-tests.yml` is configured to run the complete `backend/tests` unittest suite for backend changes.
- The GitHub status endpoint did not expose check/status entries for the commits at this update. Therefore the eight priorities above are **committed implementations with synthetic tests authored, but test execution is not yet independently verified**. Do not mark them CI-passing until an actual successful Actions run is confirmed.
- No real floorsheet or OHLCV publisher export was parsed. No official 281+47 instrument manifest or complete primary NEPSE session calendar has been ingested. Rights clearance and corporate-action completeness remain unverified. Historical archive coverage has not been re-run using verified session dates.
- Training readiness remains blocked; the gate is implemented but not passed with real evidence.


### Follow-up correctness refinements after Priority 10
- OHLCV adapter now permits zero traded volume while requiring positive OHLC prices; a zero-volume row may occur on a valid session and must not be rejected solely for that reason. Commits: [45da0e0](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/45da0e0b9859d2204c2cdb831e0d4c7defe69d3b), regression test [c4f2aef](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/c4f2aef3f0f0d5d991efdb27af9ec5401c49ca01).
- Historical reconciliation now labels a close-price difference as a cross-source conflict only when multiple distinct sources disagree; same-source duplicate rows remain in the duplicate review ledger. Commits: [727beca](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/727beca084f1b7711b245e6ba0200e8ef9c3f947), regression test [58f9424](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/58f94245225e06640171be38a699c4277553e16c).
- GitHub combined-status queries returned empty status lists for the latest test commits. CI is still **unconfirmed**, not passed. No local test execution is represented as having occurred.


## 18. Next five integration priorities — implementation record (2026-11-25)

### Priority 1 — end-to-end floorsheet CSV to broker footprint aggregation
- Added `backend/app/floorsheet_pipeline.py` and `backend/tests/test_floorsheet_pipeline.py`.
- Integrates explicit CSV header mapping, typed floorsheet contracts, duplicate/amount reconciliation, effective-dated broker resolution and exact Decimal broker aggregation.
- Only unique contracts without amount-reconciliation exceptions enter aggregates. All duplicates, conflicts and parser rejections remain in the audit output; unresolved broker parties remain in coverage denominators.
- Commits: [6433da1](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/6433da116527510ce88bac0ce9cf88db6cc3a2e3), [1e6376a](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/1e6376aa2235bda028d90b57b803abde94a9c7f7).

### Priority 2 — OHLCV ingestion joined to dated universe, exchange-session and point-in-time evidence
- Added `backend/app/ohlcv_evidence_pipeline.py` and `backend/tests/test_ohlcv_evidence_pipeline.py`.
- Each parsed row is joined to an effective-dated security identity, primary-source session evidence and explicit source-availability timestamp. Missing, ambiguous, future or unverified evidence quarantines the row.
- The output remains review-only and cannot be promoted to canonical data. A CSV file's current capture time is not treated as proof of historical availability.
- Commits: [53622e8](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/53622e8482a2b556f4b2be9647e476ccc6126c7d), [58a7886](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/58a788673858d053f813d290ceb373ba19d2b74c).

### Priority 3 — deterministic content-addressed audit bundle
- Added `backend/app/audit_bundle.py` and `backend/tests/test_audit_bundle.py`.
- Canonical JSON serialization supports Decimal/date/dataclass structures, hashes every named artifact and a manifest, and rejects non-finite/unsupported values.
- This creates reproducible audit evidence but is not itself a data-quality approval or file-persistence operation.
- Commits: [c0626e0](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/c0626e061647a435a70c6652d1be520763d3f821), [dc68932](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/dc6893289c814b0320856e37cf517f87b26b37e9).

### Priority 4 — project-level evidence assembly for the training gate
- Added `backend/app/data_readiness_evidence.py` and `backend/tests/test_data_readiness_evidence.py`.
- Derives training-gate booleans only from explicit upstream reports: dated universe, session evidence, rights/provenance, OHLCV integrity, broker identity policy, point-in-time leakage, corporate-action review, coverage and holdout protocol.
- Missing inputs fail closed. Synthetic complete-evidence tests demonstrate the gate contract only; they are not evidence that this project is currently ready.
- Commits: [ab2a1c2](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/ab2a1c2c74ed759daa2a50b34d8716c506749cbf), [2b5753c](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/2b5753c7d70c0e9b1568877d0130a6f1dfd66a02).

### Priority 5 — evidence-backed source adapter profiles
- Added `backend/app/source_adapter_profile.py` and `backend/tests/test_source_adapter_profile.py`.
- A profile binds a named source, schema version and explicit column mapping to an exact sample payload hash, header fingerprint, reviewer, review timestamp and evidence ID. Verification fails when the sample or header differs.
- No NEPSE, Mero Lagani or archive profile has been approved: no representative publisher export was available in this session.
- Commits: [d37ee81](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/d37ee816e18c8c3e1cf5b42e4b00f6ac6a9c539d), [859cc20](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/859cc20823e18e755463af95c118e777d0db6358).

### Verification and real-data status
- Backend test workflow is configured for pushes affecting `backend/**`. Combined commit-status queries for the five latest test commits returned empty status arrays; no successful Actions run or local test execution is claimed.
- All five additions currently have authored synthetic regression tests, but CI execution remains unverified.
- No real floorsheet/market-data file was available to validate a publisher mapping or run these pipelines against the historical archive.
- Canonical promotion and model training remain blocked pending real-source mappings, official instrument/session evidence, rights review, historical point-in-time availability, and verified quality reports.


## 19. Next five priorities — pipeline hardening and row conservation (2026-11-25)

### Priority 1 — source adapter profile validation
- Hardened `backend/app/source_adapter_profile.py`: non-blank normalized/source-header mappings, distinct source headers, and exact reviewed-sample header presence are required before a mapping can be marked verified.
- Added regression tests for missing mapped headers and duplicate mapping targets.
- Commits: [673f476](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/673f47677d1b3637fbe073c4119e096b728c4dc1), [e0fdf2e](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/e0fdf2e207e9ce0d2145002bbe3eba7ff6981fdc).

### Priority 2 — canonical audit serialization hardening
- Hardened `backend/app/audit_bundle.py`: rejects dictionary-key collisions after string normalization and non-finite Decimal values; deterministically orders heterogeneous set members.
- Added regression tests for ambiguous keys, Decimal NaN and deterministic mixed-type set serialization.
- Commits: [fe7ef0a](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/fe7ef0a95dfa75b1c1756b54cdc7b75f499d6dc0), [e7a295b](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/e7a295bec8561ae61e6a6e1509fb929ba1f289b7).

### Priority 3 — stricter OHLCV security and availability evidence
- Hardened `backend/app/ohlcv_evidence_pipeline.py`: requires a nonblank stable security-master ID, rejects non-string availability timestamps and handles malformed lifecycle date types conservatively.
- Added regression tests for missing security-master ID and parser-rejected date rows.
- Commits: [a2a086a](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/a2a086a3325c7facffef8321817321bfbf7be7be), [31d599b](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/31d599b5425a3056cb3ded8af675604488ae5f58).

### Priority 4 — preserve rejected OHLCV input rows and enforce row conservation
- The OHLCV evidence pipeline now returns parser-rejected rows rather than silently omitting them and asserts `input_rows = parsed_rows + rejected_rows`.
- Output explicitly reports parser rejection count and row-conservation status. This is an ingestion audit guarantee, not a claim that parsed rows are exchange-valid.
- Commit: [0194593](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/01945936009c853617d58865ac2326a7cb2b0f14).

### Priority 5 — training-evidence finite coverage and lineage checks
- Hardened `backend/app/data_readiness_evidence.py`: historical coverage must be finite and within [0.98, 1.0]; source lineage requires a valid SHA-256 payload hash, source record ID and provenance hash.
- Added tests that NaN, infinity, values above one and negative coverage fail closed.
- Commits: [eb6c9ec](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/eb6c9ec400e0163ba6841dcac4912418a0ee6a01), [87853fc](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/87853fcdcf1df4c2f2e49e48cb29a59547a0b3ba).

### Verification and limitations
- The backend contract workflow remains configured to run on pushes affecting `backend/**`; the latest four test commits were queried for combined status and returned empty status arrays. No green CI result is claimed.
- Tests are committed but have not been executed in this session. No real publisher CSV has been supplied, so source mappings and historical rows remain unverified.
- The OHLCV evidence pipeline remains review-only; canonical promotion and training remain blocked until official session/universe evidence, rights, source availability and full real-data integrity checks pass.

- Test-fixture correction: the OHLCV parser-rejection regression fixture now uses actual newline delimiters (rather than literal backslash-n bytes), commit [2db8436](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/commit/2db84363a3fa4136e2843083e7e974fa332406b2). This correction is committed; CI execution remains unverified.


## 2026-11-25 continuation update — evidence and CI repair

### Completed in this work session

1. **Priority 1 calendar evidence advanced:** located and reviewed an official NEPSE-hosted market-session notice (NEPSE file API PDF: `https://www.nepalstock.com.np/api/nots/security/fetchFiles?fileLocation=santosh_thapa%2F2022-06-16%2Fmarket+session+notice_1655356331971.PDF`). It records the Board decision dated 2079/02/25 and the schedule effective Asar 1 (2022-06-16): Sunday–Thursday 11:00–15:00 and Friday 11:00–13:00. This supports the 2022 weekday candidate regime and Friday half-day sessions. It does not verify individual dates or holidays. Exact PDF bytes could not be downloaded into the working environment in this run; SHA-256 and immutable raw-copy capture remain outstanding. Research record updated in `docs/NEPSE_SESSION_CALENDAR_SOURCE_RESEARCH_2026-11-25.md`, commit `b4eb383ba7c249eac8df47bd0087f3008ad9ebc0`.
2. **Backend unit-test regression fixed:** latest backend CI had 278 tests with one failure because the positive training-readiness fixture omitted the required `provenance_sha256` evidence field. Added a valid 64-character fixture hash in `backend/tests/test_data_readiness_evidence.py`, commit `b04b3a66419666898b14b855bb5d76c41f68b34f`. The backend-tests workflow on that commit passed.
3. **Contract-test workflow dependency defect fixed:** the separate `.github/workflows/backend-contract-tests.yml` ran the full backend suite without installing `backend/requirements.txt`, causing import errors for `httpx` and `duckdb` (and related dependencies). Added the dependency-install step, commit `d287cd3fd36a726e292bc86dd198e1f6ed5e881d`. CI reruns `45538843851` and `45538843708` were in progress at the time of this entry; do not call them passed until results are checked.

### Current evidence state / blockers

- Calendar remains incomplete: the 2022 regime now has an official schedule notice; date-level closures and exceptional sessions still need evidence. The April 2026 Monday–Friday change is still supported by secondary reports in the captured research, not an original NEPSE circular.
- Repeated-row candidates remain review-only; no verified session calendar exists yet to classify the 196,784 candidates.
- 1,331 invalid OHLC rows and eight source conflicts remain quarantined; the 1,339-row JSON/CSV exception ledger remains local and not committed as data.
- The 281-equity + 47-fund manifest remains unverified; historical coverage and source rights are not cleared.
- No canonical/training data promotion and no production signals are authorized.

### Next execution order (carry forward)

1. Capture/hash official session notices and locate the primary NEPSE notice for the April 2026 Monday–Friday change.
2. Build the date-level evidence calendar with explicit `confirmed_open`, `confirmed_closed`, `exceptional_session`, and `unverified` states.
3. Validate and classify repeated-row candidates only where the calendar and source evidence support a disposition.
4. Commit or reproducibly regenerate the immutable 1,339-row exception ledger; investigate conflicts without altering raw values.
5. Continue official 281-equity + 47-fund registry acquisition and then rerun per-instrument coverage.
