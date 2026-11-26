> **2026-11-26 owner decision — current-universe merger identity:** Use the 2026-11-25 current snapshot IDs for surviving successor equities; former merger/acquisition tickers are retired aliases and excluded from current scans. Seven successor mappings are recorded in [the current-universe successor ID policy](CURRENT_UNIVERSE_SUCCESSOR_ID_POLICY_2026-11-26.md): SLBSL/2804, NMLBBL/396, MATRI/694, SMATA/2761, SMPDA/2896, GBLBS/583 and PFL/236. Historical predecessor IDs and validity intervals are **not required for current-universe scanning**; they remain unresolved only for historical research. This does not authorize price-history splicing, cross-boundary indicators/backtests, or training. All other data-integrity, calendar, provenance, licensing and CI gates remain unchanged.

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


### CI confirmation — 2026-11-25

The dependency-install correction is verified: both GitHub Actions workflows passed on commit `d287cd3fd36a726e292bc86dd198e1f6ed5e881d`:
- [backend-tests run 45538843851](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45538843851) — success.
- [Backend contract tests run 45538843708](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45538843708) — success.

A later documentation-only progress-register commit `969d27b85b98ea94622368518461b01ab1f2ed32` triggered another backend-tests run `45538872570`; it was still in progress at the time of this update. The verified green result therefore applies to `d287cd3`, not yet to the later documentation commit.

## 2026-11-25 continuation — priorities 6–10 pipeline hardening

### Priority 6 — floorsheet ingestion row conservation and raw rejected-row retention
- Hardened `backend/app/floorsheet_csv_adapter.py` so parser-rejected rows and rows with extra unmapped columns retain the original raw CSV row plus physical source line number. The exact input payload SHA-256 remains attached to successfully parsed contracts.
- Hardened `backend/app/floorsheet_contract.py` to reject non-finite Decimal values (NaN and infinities), in addition to non-positive quantities/rates/amounts.
- Added regression coverage for raw-row preservation and non-finite contract values.
- Commits: `21fdb44c4595c2f71ef7f45dd38b7f30fcbdee1f`, `296c34285f4eaf7cc2d092d82eb8cd747f294fff`, `0009264d858b51fd5bdaf6b73dbdea2b4f8e4d98`, `922271f3445984864801b9046406c600f785170f`.

### Priority 7 — broker identity and aggregation safety
- Reviewed existing effective-dated broker identity resolution: only explicit verified links with evidence can resolve; overlapping mappings remain ambiguous; historical source names are retained.
- Hardened `backend/app/footprint_features.py` broker participation summary to use exact Decimal arithmetic, reject non-finite/negative amounts, reject unsupported statuses and reject unresolved rows carrying a canonical broker ID.
- Added exact-decimal and fail-closed identity tests. Existing broker aggregation continues to preserve unresolved observations and include them in coverage denominators.
- Commits: `a3a354a92186d5af40ca29fd5d705368703f3abb`, `81b031121679999629097d8f88eb92e82bda1a94`.

### Priority 8 — point-in-time feature store
- Re-inspected the as-of feature path. `build_feature_snapshot` filters records by timezone-aware `available_at` before deriving breadth, security and broker features; versioned snapshots include as-of security/corporate-action joins and content-addressed immutable persistence.
- No new feature store promotion or data ingestion is claimed. Inputs still require real-source lineage and the historical session calendar.

### Priority 9 — explainable market/security/broker footprints
- Re-inspected descriptive features: market breadth reports observed/eligible coverage; security footprints compare current volume against prior-only history; broker summaries report verified flow separately from unresolved observations.
- The broker summary now emits exact Decimal strings instead of binary floating-point totals. These remain descriptive features, not inferred intent or buy/sell signals.

### Priority 10 — chronological scenario validation
- Re-inspected expanding walk-forward splits and Brier/log-loss reporting. The fold baseline is derived from training-only outcomes; test dates remain chronological and are not used to calculate the baseline.
- Forecast validation still requires real point-in-time observations, a frozen prediction target/horizon and sufficient untouched chronological samples before any predictive claim.

### CI status and unresolved data gates
- Backend unit and contract workflows passed on commit `0009264d858b51fd5bdaf6b73dbdea2b4f8e4d98` (runs `45540805486`, `45540805517`).
- The parser row-retention change and regression test at `296c34285f4eaf7cc2d092d82eb8cd747f294fff` are verified green: backend run `45540886522` and contract run `45540886542` both completed successfully.
- The OHLCV archive workflow's exception-ledger build step succeeded, but the overall audit gate remains failed because the source audit still reports 8 cross-source conflicts and invalid OHLC rows. The workflow's separate latest-index coverage cross-check also failed. Neither issue is repaired by this pipeline work.
- No verified live floorsheet sample, official 281-equity/47-fund manifest, complete official session calendar, source-rights clearance or one-year instrument coverage has been established here. Canonical data promotion, training and production signals remain blocked.

### Next execution order
1. Confirm CI on `296c342` and fix any regression before further feature changes.
2. Download and inspect the newly generated exception-ledger artifact; verify row counts, source hashes and artifact integrity against the audit report.
3. Investigate the failed latest-index coverage cross-check and distinguish missing dates from session-calendar uncertainty.
4. Continue primary-source acquisition for the 281-equity + 47-fund universe and official session calendar.
5. Obtain a real, authorized floorsheet sample and complete source-specific mapping plus cross-publisher reconciliation before broker history aggregation.

### Artifact-level verification — OHLCV exception ledger and recent index dates

- Downloaded workflow artifact `nepse-ohlcv-row-audit` (run `45539332700`, artifact `14987713978`) and independently inspected the ZIP. ZIP SHA-256: `c4a6da683f97d97011605ec38e1eeb462ee89be06d83b747a743e8f713bdb0d2`.
- The generated JSON and CSV ledgers each contain 1,339 records: 1,331 invalid OHLC rows plus 8 cross-source conflict keys. All IDs are unique; every exception remains `quarantined_unresolved`.
- Verified the ledger's `source_audit_report_sha256` against the included audit report. All 1,331 invalid rows have source commit, path, file SHA-256, physical CSV line and raw row. All eight conflicts preserve both source versions with pinned commit/path/file hash and row. JSON and CSV record counts match.
- Ledger SHA-256 values: JSON `880b569bdd99bb6d37bd7b17a8646f36bb133815a9c12ff3d1d45b7e974b663c`; CSV `d3e2e0c8fc6dc0e003d68f6a7943081cdf643417dd9cd36548a942777d4bb3b8`.
- Third-source SocrateAI cross-check gives a candidate match to `nepse-history-starter` for the 2025-07-28 closes on MEHL, RAWA, RHGCL and ULHC, and the 2026-11-19 RHGCL close; it also supports the history-starter close on API and HRL for 2026-11-19 but shows small volume/low differences. These are third-party mirror matches, not NEPSE-primary confirmation, so all eight conflicts stay quarantined.
- Recent index cross-check is not a missing-file/transport failure: all 120 selected index files downloaded, 117 contain one valid row and 3 have anomalies (2026-06-01 exact duplicate rows; 2026-07-03 index high below OHLC; 2026-07-07 conflicting duplicate rows). The workflow step exits nonzero on those quality anomalies. No date-level exchange calendar is thereby verified.
- YONEPSE comparison is also a third-party mirror comparison. Its 120 dates classify as 116 numeric-difference cases, 3 SocrateAI row anomalies and 1 provisional latest date; numeric precision/turnover differences require separate field-level review, not automatic source selection.


### Latest 120-date OHLCV coverage drill-down

- The 120-date comparison spans 2026-05-18 through 2026-11-24. Across the two OHLCV archives, 117 dates have records in both; one date (2026-07-24) has records in only `nepse-smc-data`; two dates (2026-11-23 and 2026-11-24) have no records in either archive.
- On 2026-07-24, `nepse-smc-data` contains only 25 symbols (AHPC, API, BGWT, CHL, HDHPC, HIDCL, HLI, HRL, KDBY, KEF, MEHL, MEL, MERO, NIFRA, NRIC, RADHI, RAWA, RHGCL, SKBBL, SMJC, SOHL, SPDL, UAIL, ULHC and UNHPL); `nepse-history-starter` contains zero.
- Across the 120 index-date candidates, the two OHLCV archives each have median daily symbol counts around 347 (SMC 346.5; history-starter 347), with max 378. These are raw archive symbol counts, not coverage against the agreed 281 equities + 47 funds; mixed instrument types and lifecycle statuses remain unresolved.
- This separates two issues previously conflated by the failed workflow step: (a) the index-source quality gate fails on three malformed/duplicate index rows; and (b) the OHLCV archives have real date-level gaps/partial coverage on 2026-07-24 and no coverage for the latest two index dates. No missing date is assumed to be a holiday or closed session.


## 2026-11-25 continuation — floorsheet contract fail-closed validation

- `FloorsheetContract.from_mapping` now rejects missing/blank required text fields and invalid ISO trade dates before constructing a contract. This closes a gap where `str(None)` could otherwise turn a missing contract ID or broker code into the nonblank literal `None`.
- `reconcile_floorsheet_rows` now rejects negative or non-finite amount tolerances rather than silently marking every row as an amount exception.
- Added tests for missing contract identifiers, invalid dates, NaN/infinite values and invalid tolerances. Parser errors retain the raw source row and physical CSV line.
- Commits: `08a00211efa3bdd288059fac2cab0d5075f847bf`, `2d369e0aaf1e9345231a6d086a364b4f95749da6`, `5357ce24ece55d9bee2e137dff0d95f8191bf364`, `8bc236f40f87879b5a91e7a2ef79c1f62749bf26`.
- CI: both backend and contract workflows passed for `08a0021` (runs `45541272760`, `45541272833`), `2d369e0` (runs `45541281785`, `45541281784`), `5357ce2` (runs `45541289459`, `45541289472`) and `8bc236f` (runs `45541297422`, `45541297432`).

### Next five acceptance tasks
1. Finish CI verification for the latest floorsheet validation commits; fix any failures before further ingestion changes.
2. Obtain and hash a real, authorized floorsheet CSV sample; validate source headers, date format, row counts, control totals and duplicate/amount exceptions without guessing mappings.
3. Capture a primary NEPSE/SEBON instrument registry response with stable security IDs and instrument/lifecycle fields; reconcile the 281-equity + 47-fund target without inferring membership.
4. Capture primary NEPSE session notices and build a date-level `confirmed_open` / `confirmed_closed` / `exceptional_session` / `unverified` register.
5. Use the verified calendar and universe to classify the 196,784 repeated-row candidates and calculate per-instrument coverage; preserve all unresolved rows.


## 2026-11-25 continuation — next five acceptance tasks and additional pipeline hardening

### Five acceptance tasks: disposition
1. **CI verification:** passed for exceptional-session calendar changes at `da139aa3d1` (backend `45541490011`, contract `45541489993`) and `5cc262cf78` (backend `45541499282`, contract `45541499204`). Documentation-only follow-up commits `1c5f37a82e` and `4a876f682c` also passed backend tests (`45541523995`, `45541538847`).
2. **Authorized real floorsheet sample:** not completed. Existing acquisition tools require explicit rights confirmation; source MIT declarations do not independently verify original upstream rights. The user's Drive ZIP is not connected in this execution. No real sample is claimed acquired or audited.
3. **Primary instrument registry:** partially advanced. Official NEPSE stock-list and asset-list pages were located and the dated stock-list snapshot (2026-10-15) was documented. It is not a lifecycle registry and does not establish the exact 281 + 47 membership. No manifest is promoted.
4. **Session calendar:** implementation now supports `verified_exceptional_open` and `verified_exceptional_closed`; exceptional open rows can pass OHLCV calendar gating only with source ID, URI and timezone-aware UTC verification timestamp. Tests reject unsupported statuses and timestamps without UTC timezone. The official 2022 NEPSE schedule notice remains captured as a source lead; exact PDF byte hash and a complete date-level primary calendar remain outstanding. April 2026 Monday-Friday notice is still only secondary-source corroborated.
5. **Repeated-row and per-instrument coverage reconciliation:** blocked on the complete date-level session calendar and verified 281 + 47 instrument registry. All 196,784 repeat candidates remain review-only; no deletion or promotion.

### Additional engineering work beyond the five acceptance tasks
- Hardened `aggregate_broker_side` to use exact Decimal arithmetic, require integer non-negative quantities, reject non-finite/negative amounts, validate identity statuses, require entity IDs for verified rows and prohibit entity IDs on unresolved rows. Amounts serialize as exact decimal strings.
- Added tests for 0.1 + 0.2 exact aggregation, NaN rejection and unresolved identity/entity inconsistency. Commit `d113dd8454f0258f6773a0177b52877117f9afdc`; backend and contract CI were running when this entry was written.
- Calendar exceptional-session implementation and tests: `da139aa3d1f3886e871b044091bd8f63f9d01fca`, `5cc262cf786bc40d4752064a4b0422686a7b6db5`.
- Documentation commits: calendar status semantics `1c5f37a82efaa5f4e8b03d637aade2d259421094`; official stock-list evidence limitations `4a876f682c0768d4f44113cdc2f5ba5ffdcf33e9`.

### Next five engineering priorities (11–15)
11. Make broker aggregation fully source-lineage preserving at contract/party observation grain, with stable input-order-independent output and exact decimal totals.
12. Add security-master snapshot validation for stable IDs, duplicate symbols, instrument classes and lifecycle intervals; fail closed on unknown classes.
13. Add date-level session evidence ingestion that stores raw notice hash, publication time, retrieval time, scope and exceptional-session state; do not infer closure from missing files.
14. Build a reproducible coverage report that joins the approved universe, verified sessions and source manifests, reporting per-security expected/observed dates and explicit unknowns.
15. Add an end-to-end readiness gate that prevents canonical/training promotion unless source rights, registry, calendar, raw-file hashes, row reconciliation and point-in-time provenance all pass.

### Outstanding blocker
The project can continue engineering, but data acquisition and production-readiness cannot be marked complete until an authorized floorsheet sample and primary instrument/session evidence are actually captured and verified. The latest OHLCV archive audit still fails on known source anomalies; its failed status is not replaced by the passing unit tests.

## 2026-11-25 continuation — engineering priorities 11–20

### Priorities 11–15
11. Broker aggregation now validates ISO trade dates, uppercase symbols, 64-hex payload hashes, positive physical row numbers and identity evidence IDs; exact Decimal totals and unresolved identity buckets are preserved. Commits `2fa164e`, `06efce5`.
12. Security-master validator restricts instrument classes/statuses, validates lifecycle dates, and rejects overlapping conflicting lifecycle rows or symbol assignments. This is a validator, not an acquired official registry. Commits `827edac`, `7c22411`.
13. Calendar evidence schema requires raw evidence SHA-256, source ID/URI, retrieval and verification UTC timestamps, and scope; supports exceptional open/closed sessions. Commits `0d13d81`, `f868b38`, `ed87f4f`, `dbb6fdf`.
14. Added `backend/build_security_coverage_report.py` and tests. It calculates per-security expected/observed sessions using only explicitly verified open dates, reports gaps, duplicates, closure conflicts and unknown-calendar observations. Diagnostic only; promotion disabled. Commits `bde20e0`, `a1e60e8`, `b481f24`; docs `5053819`.
15. Training readiness rejects non-finite/out-of-range coverage and malformed provenance hashes. Commits `e08c1aa`, `9b9fa40`, `7e749a4`, `dddc1be`.

### Priorities 16–20
16. Corporate-action records require timezone-aware announcement/availability times, availability cannot precede announcement, and factors must be finite/positive. Commits `b26473b`, `71305c0`, `1f616f7`.
17. Versioned feature snapshots include per-record source ID, record ID, payload hash, physical row number and availability timestamp; incomplete lineage is explicitly labeled and included in snapshot hash. Commits `500a18b`, `29e25ec`.
18. Calendar coverage matrix carries raw hash, publication/retrieval/verification times and scope; exceptional closures flag files as anomalies. Commits `d04f7b4`, `f1951a8`, `d21ba8e`.
19. Readiness-gate edge cases reject NaN, infinity, negative/over-100% coverage and malformed provenance hashes; covered by the tests above.
20. Broker party-observation aggregation validates source hashes, ISO dates, symbol normalization, row number and identity evidence before aggregation. Commits `2fa164e`, `06efce5`.

### CI
- Full backend and contract test suites passed at `1f616f7`: backend run `45542179290`; contract run `45542179277`.
- Calendar evidence/coverage tests passed at `d21ba8e`: runs `45542037741`, `45542037664`.
- Broker observation lineage tests passed at `06efce5`: runs `45541998525`, `45541998592`.
- Intermediate red runs during the edits were corrected; the full suite passed at `1f616f7`.

### External evidence blockers remain
- No authorized real floorsheet sample acquired; the user's Drive archive is not connected in this run, and a dataset's MIT license does not independently prove upstream data rights.
- No primary NEPSE instrument lifecycle registry acquired; official stock-list discovery does not prove the 281-equity + 47-fund membership.
- Session calendar CSV remains header-only; no date-level open/closed rows have been promoted without captured and hashed primary evidence.
- Per-security coverage tool awaits verified universe, calendar and normalized source rows.
- OHLCV invalid rows, cross-source conflicts and index anomalies remain unresolved. Canonical/training promotion and production signals remain blocked.

### Next execution batch (21–25)
21. Build a raw official-notice capture utility recording URL, publication/retrieval timestamps, bytes, SHA-256 and source ID without auto-populating the calendar.
22. Add immutable universe-snapshot provenance validation and exact 281 + 47 checks when an explicit target snapshot is supplied.
23. Add source-specific per-security coverage so publishers are measured separately and never double-counted.
24. Add broker aggregation determinism and source control-total reconciliation tests.
25. Add a read-only readiness CLI that assembles evidence reports and prints blockers without mutating canonical or training data.

## 2026-11-25 continuation — engineering priorities 21–25

21. **Official notice capture:** added `backend/capture_official_notice.py`. It permits HTTPS NEPSE/SEBON hosts and approved redirects only, stores raw response bytes by SHA-256, records source URL, publication/retrieval timestamps, response metadata and byte count, and never auto-populates the session calendar. Tests cover hash integrity, off-domain rejection, redirects and timestamp validation. Commits `ebbd416`, `3e3b45a`, `0565b44`.
22. **Universe snapshot validation:** added `app.universe_snapshot.validate_universe_snapshot`. It requires primary NEPSE/SEBON HTTPS provenance, raw payload SHA-256, snapshot date, UTC retrieval time, stable security IDs, explicit instrument types/statuses, effective dates and target membership. Default validation requires exactly 281 active equities + 47 active mutual funds; no symbol/type inference. It still awaits a real official registry response. Commits `01b61ec`, `cc3bf97`.
23. **Source-specific per-security coverage:** coverage CSV now requires `source_id,symbol,date`; every publisher receives its own per-security report. Combined coverage is deliberately null when multiple sources are supplied, preventing false union coverage. Commits `c7d7281`, `95c57fe`, `a9c7d0e`; documentation `c36d9fd`.
24. **Broker control totals:** added exact Decimal reconciliation of buyer/seller party observations against source-date controls. A contract contributes gross amount/quantity once only when one buy and one sell row agree; missing sides and mismatches are explicit anomalies. Added input-order determinism tests. Commits `ff253f7`, `893868d`.
25. **Read-only training readiness CLI:** added `backend/evaluate_training_readiness.py`; it loads evidence reports, prints blockers and can write a readiness JSON, but never mutates canonical data or starts training. Missing evidence returns nonzero. Commits `8b5e470`, `aa67d3b`, `68c1608`.

### CI verification for priorities 21–25
- Full backend unit and contract test suites passed at `68c1608c3a4d17e8cc1508f165956e178599000f`: backend `45542491712`, contract `45542491720`.
- Notice capture / readiness CLI tests passed at `aa67d3b1a3e5a870f21b02ca6d9074336df307d8`: backend `45542480866`, contract `45542480904`.
- Broker control-total and deterministic aggregation tests passed at `893868dafb4f0812ec56c129c4ec14b09264e0e1`: backend `45542455502`, contract `45542455293`.
- Universe snapshot tests passed at `cc3bf97d74fc8298aa3d1ca86f8f7cd94ddc2cce`: backend `45542359540`, contract `45542359492`.
- Source-specific coverage tests passed at `a9c7d0e050bd5e4d5e4191026dbda0b0d4a54edc`: backend `45542407297`, contract `45542407213`.
- Intermediate red runs during source-specific refactoring were corrected; the subsequent complete suite passed at `68c1608`.

### External-data blockers unchanged
The new utilities and validators are ready, but no official notice bytes, full date-level NEPSE calendar, verified 281 + 47 registry snapshot, or authorized raw floorsheet sample have been acquired in this session. The user's large Drive ZIP is not available through a connected Drive integration here. No raw floorsheet sample, per-security historical coverage result, canonical dataset or production signal is claimed. Existing OHLCV invalid rows, cross-source conflicts and index anomalies remain quarantined.

### Next execution batch (26–30)
26. Add a testable official registry API capture adapter, but keep endpoint contract and response fields untrusted until an actual official response is captured.
27. Add an evidence manifest that links each calendar date to one or more raw notice capture IDs and detects conflicting overlapping scopes.
28. Add source-specific OHLCV daily control totals and duplicate/conflict reconciliation before coverage can be considered complete.
29. Add broker reconciliation output with per-source/date contract count, gross amount, quantity and party-row exceptions persisted as immutable artifacts.
30. Run the read-only readiness CLI against the current actual evidence and archive the blocker report, demonstrating that the current dataset remains not training-ready.

## 2026-11-25 continuation — engineering priorities 26–30

26. **Official registry capture adapter:** added `backend/capture_official_registry.py`. It captures JSON responses only from official NEPSE/SEBON HTTPS hosts, stores raw bytes by SHA-256 and records retrieval metadata. It explicitly labels schema `unreviewed` and `manifest_verified=false`; the candidate security endpoint is not presumed valid until an actual response is captured and reviewed. Commits `2d78b58`, `b650491`, `faec6e6`.
27. **Calendar evidence manifest:** added `app.calendar_evidence_manifest`. It links date/status/scope claims to captured notice IDs, validates official URLs, raw hashes, raw paths and UTC retrieval timestamps, and detects contradictory open/closed claims with overlapping scopes. It does not populate the calendar. Commits `5156ee0`, `6e5163a`, `99529d3`, `4849bd9`.
28. **OHLCV daily control reconciliation:** added `backend/reconcile_ohlcv_source_daily.py`. It reports source/date row counts and total volume, within-source duplicate symbol/date rows, cross-source exact matches/conflicts, and comparisons to source control totals—including controls for dates with no source rows. Commits `0414589`, `f3a13a5`, `7b15fea`, `599291b`, `ddbc3dd`.
29. **Immutable broker reconciliation artifact:** added `backend/reconcile_broker_control_totals.py`; it hashes every party input and control file, reconciles contract parties and writes a content-addressed report that cannot overwrite different existing content. Commits `17bf7b0`, `425c885`, `f20661f`.
30. **Current readiness run and archived blockers:** executed the read-only readiness workflow `45542756700`; artifact `14989249027` (`nepse-training-readiness-blockers`) was downloaded and inspected. ZIP SHA-256 `66a1553e3c8f8897714e320b5b53974487b882e792bd91c3a6baec01d0c105d7`; JSON SHA-256 `4423702fe5b93626324bedc67a97f17585e5235336fd1617a72669ddb9591a47`. The report explicitly says `training_ready=false`, `model_training_allowed=false`, and lists all 12 readiness blockers: universe, session calendar, rights, lineage, OHLCV integrity, broker identity, point-in-time leakage, corporate-action review, historical coverage, holdout protocol, OHLCV coverage threshold and broker identity coverage threshold. No model performance is claimed. This run had no committed evidence report inputs, so it demonstrates the fail-closed empty-evidence state—not an audit of unmounted Drive files.

### CI verification for priorities 26–30
- Full backend and contract tests passed at `ddbc3dd5c731db8b038d2ed27e0ecd614de6a7c0`: backend `45542820966`, contract `45542821029`.
- Broker immutable report tests passed at `f20661fd0122c65cf491f9f01908759b3be5394a`: backend `45542731187`, contract `45542731113`.
- OHLCV daily reconciliation tests passed at `7b15fea816f746e29c2e55fa1963fa223d216137`: backend `45542694225`, contract `45542694177`.
- Calendar evidence manifest tests passed after fixture provenance fields were added at `4849bd9d5186c9903f4549ca762625dfb79fed92`: backend `45542797749`, contract `45542797833`.
- Official registry capture tests passed at `faec6e66cf575dcb318b199ad44a65da9aeefc19` and were included in the later full passing suite.

### Still not acquired
The new adapters and reports are engineering tools, not source data. No actual official registry API response has been captured; the date-level session calendar remains header-only; no verified 281 + 47 instrument manifest exists; no authorized raw floorsheet sample is staged; and the OHLCV archive quality exceptions remain unresolved. The user's Google Drive archive remains inaccessible in this run. Training and canonical promotion remain blocked.

### Next execution batch (31–35)
31. Add a source-evidence inventory report that cross-checks every manifest path/hash against downloaded raw bytes and flags missing raw objects.
32. Add a verified exchange-session calendar reconciliation against source daily index and floorsheet dates, while retaining all dates as unverified until official evidence is linked.
33. Add source-specific corporate-action adjustment audit and detect adjusted/unadjusted OHLCV mixing before features.
34. Add a broker identity coverage report per date/security/side with both observation-count and gross-amount denominators.
35. Add an integration workflow that runs registry, calendar, OHLCV, floorsheet, broker and readiness audits in sequence and uploads all artifacts without promoting data.

## 2026-11-25 continuation — engineering priorities 31–35

31. **Raw source evidence inventory:** added `backend/audit_source_evidence_inventory.py` to check manifest paths against raw objects under a confined root, verifying file existence and SHA-256 and flagging missing/mismatched files, duplicate manifest keys and path traversal. Commits `7d26ca3`, `05c4272`, `838b87e`.
32. **Calendar versus observed source dates:** extended the calendar coverage matrix to flag (a) source files on verified closed dates, (b) source files on dates with no calendar evidence, and (c) verified open dates with no source files. No file-presence or weekday inference is promoted to a session. Commits `f2a7010`, `fcaa969`.
33. **Adjusted/unadjusted OHLCV mixing:** added `backend/audit_ohlcv_adjustment_basis.py`, requiring explicit adjusted/unadjusted/unknown basis and flagging within-source mixed series and cross-source basis differences. No adjustment is applied. Commits `2a4f277`, `0936fac`, `e0a226e`.
34. **Broker identity coverage:** added `backend/report_broker_identity_coverage.py`, reporting verified/unresolved observation counts and gross amounts by date/security/side, with source-file SHA-256. Commits `66ff6b9`, `8036eac`, `c024993`.
35. **Integrated evidence audit:** added `.github/workflows/integrated-evidence-audit.yml`. It runs the regression suite and then executes registry, calendar evidence, raw inventory, calendar date matrix, OHLCV daily totals, adjustment basis, per-security coverage, floorsheet window, broker identity and readiness audits when inputs exist. Missing inputs produce explicit skipped statuses; no canonical promotion or model training is possible. Commits `beb3df8`, `a8156ef`, `80ff8f9`, `d3b78b4`, `6676b29`, `e13f2c0`; acquisition manifest now records explicit source schema at `26c7b89`.

### CI and artifact verification
- Backend regression suite passed on final workflow commit `e13f2c06aaf73a97b764903daf4c7d9357fd8b03`: run `45543406700`.
- Integrated evidence audit workflow passed on the same commit: run `45543406762`.
- The integrated workflow artifact `nepse-integrated-evidence-audit` (artifact `14990182086`) was downloaded and inspected. ZIP SHA-256: `b4069f7a077c0b58d1fe892140fdfb2f470c41911a98d8d72074fd6906e079a6`. All seven artifact files parse as valid JSON.
- Input inventory confirms the official session calendar CSV is header-only; observed index date-list exists; registry snapshot, source object manifest/raw root, calendar evidence manifest, source-date manifest, normalized OHLCV, security universe CSV, floorsheet acquisition manifest and broker observations are absent from the repository checkout. Corresponding audits are explicitly marked skipped, not passed.
- Readiness report remains `training_ready=false`, `model_training_allowed=false`, with 12 blockers. The workflow is green because the audit ran correctly and archived the fail-closed result—not because data readiness passed.

### Next execution batch (36–40)
36. Capture and review the actual official NEPSE registry response using the new adapter; verify response schema and stable security IDs before creating any target manifest.
37. Acquire the user's raw floorsheet ZIP through an explicitly connected Drive/file path or obtain a separately rights-cleared official/public sample; hash it and run row-level audit.
38. Capture official daily session/holiday/exceptional-session notices as raw bytes and build date-level claims linked through the calendar evidence manifest.
39. Stage source-specific normalized OHLCV files and source controls; run daily totals, adjustment basis, per-security coverage and cross-source comparisons.
40. Re-run the integrated workflow with real inputs and only advance readiness gates when all required evidence is present and verified.

## 2026-11-25 continuation — execution of priorities 36–40

36. **Official registry response capture — blocked by endpoint access.** Re-attempted the candidate official NEPSE security endpoint and official stock-list URL; the research connector returned inaccessible/internal error, and the GitHub fetch connector only supports GitHub URLs. The capture adapter is tested and ready, but no official raw JSON response or schema is claimed captured.
37. **User floorsheet ZIP — blocked by Drive access.** The Google Drive connector search returned `DISABLED_BY_ADMIN` / `NOT_AVAILABLE` in this environment. No connected Drive tool could read the user's >1 GB ZIP. No raw sample is claimed inspected. A smaller directly attached CSV/sample or an enabled Drive integration is still required.
38. **Official date-level session notices — partially advanced, raw capture blocked.** The official NEPSE June 2022 schedule notice URL and its contents were already documented as a primary-source lead, but direct raw PDF download was retried and failed. Therefore no raw PDF SHA-256 or date-level holiday/closure rows were added. The current session calendar remains header-only.
39. **Source-specific OHLCV staging — blocked by missing verified inputs.** The main repository has no normalized OHLCV source directory or verified security-master CSV. Existing public archive audits and artifacts remain secondary source material; no new source-specific per-security coverage is calculated or promoted.
40. **Integrated workflow — executed with current checkout.** The final integration run `45543406762` passed and its artifact was inspected. It explicitly marks registry, raw source objects, calendar evidence manifest, source-date manifest, normalized OHLCV, universe CSV, floorsheet acquisition manifest and broker observations as missing/skipped. Session calendar header and observed-index date list are present. Readiness remains blocked with 12 gates false. This is an accurate empty-input result, not a real-data pass.

The current environment does not provide access to the user's Drive archive or the official registry endpoint. Engineering can continue, but the next data-dependent milestones cannot be truthfully completed without those source bytes. The project remains fail-closed: no canonical/training promotion and no production signals.

## 2026-11-25 continuation — priorities 41–50

41. **Universe-safe OHLCV coverage:** unknown symbols are now retained as explicit `unknown_symbol_observations` rather than silently disappearing from per-security coverage. Commits `d478b37`, `c2d0c54`.
42. **Corporate actions as-known:** point-in-time reports now distinguish all visible actions from confirmed actions, listing visible provisional/cancelled/disputed items and their evidence. Commits `f731a0b`, `38e1f65`.
43. **Corporate-action provenance:** source tier is now mandatory along with action, security, source and evidence IDs. Commits `5695db6`, `35a3397`.
44. **Historical coverage integrity:** reject non-finite/non-positive closes and expose rows outside the supplied verified session/security grid without allowing them to increase coverage. Commits `2668822`, `0b69bd4`.
45. **Broker aggregation input integrity:** reject whitespace-only broker entity IDs and grouping/lineage fields. Commits `d34c9b3`, `c28d4b3`.
46. **Reference universe lifecycle:** allow excluded instrument classes (including non-convertible debentures) to remain in the reference universe while fail-closing if any is marked in target scope. Commits `890ef83`, `a68d2df`.
47. **Target count assertion:** per-security coverage report now explicitly compares its target against the required 281 equities and 47 mutual funds; mismatch is visible and does not promote data. Commits `a2b00ac`, `95a7187`.
48. **Coverage source provenance:** each source CSV's path, byte count and SHA-256 are pinned in the coverage report. Commits `cf6d6b8`, `bad090e`.
49. **Raw evidence manifest digest validation:** source-object inventory now requires a 64-character hexadecimal SHA-256, not merely a 64-character string. Commits `0652e57`, `2847966`.
50. **Calendar claim references:** calendar evidence claims now reject duplicate/blank source IDs and missing scope values. Commits `725db58`, `ce4e685`.

## 2026-11-25 continuation — priorities 51–60

51. **Calendar evidence chronology:** enforce publication no later than retrieval and verification no earlier than retrieval. Commits `641eb6d`, `b5be7f9`.
52. **Point-in-time exclusion accounting:** snapshots now separately count records missing `available_at` and records excluded because they were published after the decision cutoff. Commits `c56ba03`, `9318044`.
53. **Floorsheet mapping contract:** require exactly the supported normalized fields and nonblank string source headers; reject extra normalized mapping keys. Commits `1062dc3`, `572523f`.
54. **OHLCV CSV schema:** reject duplicate headers and unsupported extra columns instead of silently ignoring them. Commits `525444b`, `f29a94e`, `20e3e23`, `6f86f30`, `2454a7e`.
55. **Corporate-action type safety:** validate `ex_date`, timestamp string types, nonblank identifiers and safely parse finite positive Decimal factors. Commits `68f5bc4`, `4e2abdd`.
56. **Walk-forward evaluation inputs:** validate ISO observation dates, exact binary labels (no fractional-to-integer truncation), and finite probabilities in [0,1] before splitting. Commits `c4e4315`, `701f59c`.
57. **OHLC range integrity:** daily source reconciliation now rejects impossible high/low bounds. Commits `d7a935c`, `6be39e8`.
58. **Daily control totals:** validate date, non-negative integer row count, finite non-negative volume, duplicate headers and extra cells. Commits `d8e49d5`, `07f3dde`.
59. **Footprint numeric/session integrity:** validate finite positive prices, finite non-negative volume, unique session dates and unique expected symbols. Commits `dd679e8`, `e0198e0`.
60. **Market breadth universe boundary:** exclude out-of-universe symbols from the breadth numerator and report them separately; this prevents coverage exceeding 100% or debt/fund extras inflating breadth. Commits `e311294`, `c9fb99f`, `8e8dc36`.

### CI verification and correction record
- Latest full backend suite passed: 401 tests, run `45545160738` at commit `8e8dc361de1ae9a66f632f48c208718e71f2058d`.
- Backend contract tests passed at the same commit: run `45545160526`.
- Integrated evidence audit passed at the same commit: run `45545160687`.
- Intermediate failures were not hidden: CI caught a literal-newline test fixture issue, an outdated error-message assertion, an unsupported-header test mismatch, and an expected-universe normalization ordering bug. These were corrected before the final passing run.
- These changes improve fail-closed validation only. No new primary NEPSE registry, official date-level calendar, rights-cleared floorsheet sample or verified 281+47 manifest was acquired. No training or canonical promotion is authorized.


## 2026-11-25 continuation — priorities 61–63

61. **Official registry capture redirect security:** registry capture now validates the initial URL and every redirect target against the approved NEPSE/SEBON HTTPS host allowlist before following the redirect. Rejects HTTP, off-domain targets, nonstandard ports and URL credentials. Raw response capture remains bounded, SHA-256 pinned and explicitly unreviewed until schema review. Commits: `38c1006`, `45e2190`.

62. **Large floorsheet ZIP preflight inventory:** added `backend/inspect_floorsheet_archive.py`. It streams the outer ZIP SHA-256 and reads central-directory metadata only; it does not extract or decompress members. It inventories file names, compressed/uncompressed sizes, CRC32, compression, timestamps, extensions and CSV count. It flags path traversal, absolute/backslash paths, duplicate and case-insensitive collisions, symlink/encrypted entries, suspicious compression ratios and configured size/count-limit violations. Commits: `6afc1ec`, `eb32d98`, `380eefe`, `0cd4ed4`.

63. **Archive inventory regression coverage and operating guide:** added tests for hash pinning, no extraction, unsafe paths, duplicate/case-insensitive names, symlinks, entry/member/total-size bounds and non-finite ratio limits. Added `docs/FLOORSHEET_ARCHIVE_INVENTORY_GUIDE_2026-11-25.md` with command, defaults and interpretation. Test and guide commits: `331aa89`, `4c57236`, `a4a0d67`, `fa5d683`.

### CI verification for priorities 61–63
- Backend unit suite passed: **414 tests**, run [45546031228](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45546031228), code commit `a4a0d6780940ec87fdaee91a123af5925af8d3b3`.
- Backend contract tests passed: run [45546031175](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45546031175).
- Integrated evidence audit passed: run [45546031178](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45546031178).
- An early intermediate backend run failed because the test fixture still patched the removed `urlopen` symbol after the implementation moved to a guarded opener. The fixture was corrected; subsequent backend, contract and integrated runs passed.
- The archive inventory is only a safe preflight. No user's >1 GB Drive ZIP was accessed or inspected in this run; no raw floorsheet sample, data rights, official registry manifest, verified calendar or 281+47 universe was acquired. No canonical/training promotion is authorized.

## Next execution wave — priorities 64–70

64. Validate the official NEPSE security-list and company-list payload schemas against a newly captured, dated primary response; keep source fields and unknown instrument types intact.
65. Add a reviewed instrument-type/lifecycle mapping for equity and mutual fund membership, retaining suspended/delisted history without allowing them into the active target set.
66. Build a small, user-supplied floorsheet CSV sample acceptance report: header mapping, encoding, date parsing, row counts, duplicate contracts, broker-code coverage and raw-row quarantine.
67. Add a ZIP member-selection and controlled extraction stage that requires a reviewed inventory and records per-member SHA-256, archive hash, CRC outcome and physical source path.
68. Inspect and reconcile the user's archive against the available Hugging Face/SocrateAI/Urek datasets without treating shared rows as independent provenance.
69. Reconcile broker code/name histories and source date coverage from a real sample, preserving unknown identities and as-known dates.
70. Re-run the 120-day and one-year coverage matrix against verified 281-equity + 47-mutual-fund membership and the date-level session evidence; keep unresolved dates/symbols visible.



## 2026-11-25 continuation — priorities 64–70

64. **Instrument manifest schema hardening:** malformed non-object rows, non-string identifiers/status/type fields, non-uppercase symbols and non-ISO effective dates now fail closed instead of crashing or being interpreted loosely. Primary-source and source-record evidence requirements remain mandatory for active target rows. Commits: `ed9bd82`, `9854ae3`.

65. **Universe snapshot provenance hardening:** snapshot inputs now require strict source types, exact ISO dates, approved official HTTPS hosts without credentials/nonstandard ports, valid SHA-256, and typed instrument/status/scope fields. Unknown/malformed rows are rejected rather than coerced. Commits: `67a7c49`, `b6f9d38`.

66. **Floorsheet sample acceptance report:** added `backend/app/floorsheet_sample_audit.py` to report sample date range, calendar-unverified dates, symbol and broker-code coverage, duplicates, amount exceptions, reject ratio, quantity and amount totals. A clean sample can pass only to rights review; it never authorizes canonical or training promotion. Commits: `8e55e5c`, `8d74af3`, `22cb457`.

67. **Reviewed CSV extraction:** added `backend/extract_reviewed_floorsheet_members.py` and CLI. Extraction requires a safe inventory, exact reviewed archive SHA-256 and explicit CSV member allowlist; it records member SHA-256 and ZIP CRC verification, applies byte limits and refuses overwrites. Follow-up hardening ensures pre-existing partial files are not deleted and target paths are not overwritten. Documentation: `docs/FLOORSHEET_SAMPLE_REVIEW_WORKFLOW_2026-11-25.md`. Commits include `64339ad`, `f1e6b57`, `1e5a9bb`, `f6714f5`, `a4f7ec9`, `7245b18`, `ca06105`, `66c3dde`, `dbb0210`.

68. **User archive reconciliation — blocked by source access:** Google Drive integration discovery reports that the Drive connector is disabled by the administrator in this environment. The user's >1 GB Drive archive has not been opened, downloaded, inventoried or compared. Do not imply that it was read. The safe intake and sample-review code is ready; actual source comparison still requires the archive bytes or a representative uploaded CSV sample.

69. **Broker identity input hardening:** effective-dated broker name observations, identity links and resolver inputs now reject malformed identifiers, invalid date types and non-ISO string as-of dates. Broker-side aggregation requires explicit session/security keys and keeps unresolved identities separate. Commits: `1b3b213`, `0cf1c5a`, `2473931`.

70. **Broker aggregate/control-total hardening:** party aggregation now requires typed grouping/lineage values, strict ISO trade dates, valid source hashes and nonblank evidence IDs. Source control counts are parsed as exact finite non-negative integers (fractional values are rejected, not truncated), including CSV string values. Commits: `9b9520e`, `96fdf02`, `2de751b`, `83aa5b0`, `24e8a65`, `f8aaeb6`.

### CI verification and remaining evidence boundary
- At commit `dbb0210fe5dd92875ddc0be366e139c4be81868c`, the backend suite passed **447 tests** (run [45546781957](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45546781957)).
- Backend contract tests passed (run [45546781843](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45546781843)).
- Integrated evidence audit passed (run [45546781889](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45546781889)).
- Drive archive contents, source licensing, a primary date-level NEPSE session calendar, a dated official 281+47 membership manifest and one-year/120-day verified data coverage remain outstanding. No canonical data promotion or model training is authorized.



## 2026-11-25 continuation — priorities 71–80

71. **Floorsheet contract field typing:** identifiers, source hashes, physical row numbers, Decimal values and symbols now require their exact expected types; booleans cannot masquerade as row numbers. Commit: `e15942d`.
72. **Canonical floorsheet dates and identity:** contract dates require a real `YYYY-MM-DD` calendar date and symbols must be uppercase/trimmed. Mapping construction validates source ID, payload digest and row number before constructing a contract. Commits: `2a03d93`, `9554949`.
73. **Sample-audit recomputation:** sample acceptance no longer trusts caller-supplied reconciliation output; it recomputes reconciliation from parsed contract rows and rejects mismatches. Commit: `d52305e`.
74. **Rejected-row provenance and session evidence uniqueness:** rejected rows must retain physical CSV line numbers, error text and raw source row; supplied verified session dates must be unique. Commit: `0e517f3`.
75. **Point-in-time timestamp strictness:** malformed timestamp types/strings and non-object records fail closed; missing availability is distinct from malformed availability. Commit: `cbe124e`.
76. **UTC chronological ordering:** selected point-in-time records are ordered by normalized UTC timestamps, not lexical local-offset strings. Commits: `aa70e85`, `4a6df78`.
77. **Floorsheet CSV adapter input safety:** parser requires bytes, a typed mapping, a nonblank source ID, valid delimiter/encoding and nonblank unique source headers. Commits: `a9bb36a`, `e661e3b`, `a293aa1`.
78. **CSV edge-case regression tests:** added checks for newline delimiters, blank headers, malformed payloads and mapping types; one initially incorrect test fixture was corrected after CI exposed it. Commits: `2063c64`, `e53411c`.
79. **Archive identity stability and report immutability:** ZIP inventory now checks the archive file identity and SHA-256 before and after inspection, rejecting a changed archive; CLI report creation uses exclusive mode and cannot overwrite existing evidence. Commits: `fea1fcb`, `1362e40`, `1933e96`.
80. **ZIP path ambiguity checks:** ZIP member names containing NUL bytes, empty path components, dot components or traversal are flagged; regression coverage includes these cases. Commits: `31eced4`, `af9edff`.

### Verification status for priorities 71–80
- Final code commit `1f09326dba1ad1e94c8120cc3ebb5d40f2936871`: backend suite **464 tests passed** (run [45549268913](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45549268913)); backend contract tests passed (run [45549268889](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45549268889)); integrated evidence audit passed (run [45549268906](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45549268906)).
- The NUL-byte path test is implemented against the validator directly because ZIP-writing libraries normalize/truncate NUL bytes in member names; the validator itself rejects the NUL byte.
- These changes improve validation and source handling only. They do not establish Drive archive access, source-data rights, official session dates, verified 281+47 membership, one-year history coverage, or model predictive performance. No canonical data promotion or training is authorized.


## 10. Work-session update — next data-pipeline priorities 81–90 (2026-11-25)

### Priority 81 — acquire and stage a bounded floorsheet sample

- The repository already has a one-session public-source smoke path for the Urek dataset. The documented 2024-01-02 run normalized **85,435 floorsheet rows** with zero parser rejects; this is a one-day parser/sample result, not full-history validation.
- The separate pinned acquisition workflow selects Urek revision \`11ef83a9c3cdbe78112f0245451cdc52bdb1a8f0\`, sample date \`2026-08-26\`, enforces per-file byte ceilings and acquires same-date index/SocrateAI comparison data.
- In this work session, the sample archive bytes were not downloaded or rehashed locally; raw sample SHA-256 and physical header review remain open. Do not represent the sample as reverified in this session.
- Dataset page checked on 2026-11-25: its preview displays the 11 source fields and rows dated 2024-01-02; its card declares MIT and states the source is compiled from public NEPSE data. It does not identify a primary endpoint or reproducible source chain.

### Priority 82 — verify sample source and provenance

Created [FLOORSHEET_SOURCE_PROVENANCE_REVIEW_2026-11-25.md](FLOORSHEET_SOURCE_PROVENANCE_REVIEW_2026-11-25.md).

- Urek: public publisher claim and MIT declaration located; exact upstream collection method/endpoint not documented in reviewed card.
- SocrateAI: public README and MIT licence file inspected; reviewed README does not document the original acquisition endpoint. Earlier matching overlap with Urek does not prove independent lineage.
- SamirWagle: inspected the scraper code. It explicitly requests \`https://merolagani.com/Floorsheet.aspx\`, paginates its table, and stamps each row with \`date.today()\`. This is a Merolagani-derived daily capture path, not evidence of historical trade dates for a backfill.
- YONEPSE source credits identify NEPSE's official API for live floorsheets and trailing-year index history, and SocrateAI for older index series. This is third-party source documentation, not an exchange API contract.
- Result: the candidate source chain is better documented, but independent lineage and upstream data rights remain unresolved.

### Priority 83 — map real source headers to the canonical contract

Added:
- \`backend/app/floorsheet_source_profiles.py\`
- \`backend/tests/test_floorsheet_source_profiles.py\`
- \`docs/FLOORSHEET_SOURCE_PROFILE_UREK_2026-11-25.md\`

Explicit Urek mapping: \`calculation_date\` → trade date; \`contract_no\` → contract ID; \`stock_symbol\` → symbol; \`buyer\` and \`seller\` → broker codes; and quantity/rate/amount → corresponding canonical values. The source-only fields \`time\`, \`sector\` and \`id\` are not fabricated into canonical fields; the immutable raw CSV retains them. Contract numbers are kept as strings. Five unit tests were added, including schema mismatch and synthetic adapter round-trip checks.

**Important limitation:** the mapping is marked \`publisher_schema_declared_raw_header_not_yet_reviewed\`. The tests use a synthetic fixture. A physical sample CSV header and hash must be checked before setting the source mapping to reviewed.

### Current execution state for priorities 81–90

| Priority | Status at this update |
|---|---|
| 81. Acquire bounded sample | Earlier one-day parser smoke exists; pinned sample bytes/hash not reverified in this session |
| 82. Verify source/provenance | Source-level review documented; independent lineage/rights unresolved |
| 83. Map source headers | Explicit profile and tests added; physical header verification pending |
| 84. Reconcile contracts/control totals | Not started in this sequence; reuse existing audit code after raw sample verification |
| 85. Verify broker-code coverage | Not started in this sequence |
| 86. Compare overlapping dates/sources | Prior 70-date archive comparison exists; rerun one-day row-level evidence after sample bytes are available |
| 87. Identify missing trading dates | Needs primary date-level NEPSE calendar; existing candidate dates remain unverified |
| 88. Verify active universe | Official dated 281 + 47 registry still missing |
| 89. Assess one-year / six-month coverage | Blocked on verified universe and session dates |
| 90. Produce source-backed readiness report | Final readiness remains blocked until priorities 84–89 are evidenced |

Commits for the new Urek source profile, tests and profile documentation:
- \`5b3a895b01a6e671f1d08808e55bd89bffdecedb\`
- \`3f1fc33a068d7194e0c75e7be33d4d03109a9216\`
- \`e7b80947ee8cbc8616b27845e51962270eb12155\`

The added unit-test commit has not yet exposed a GitHub status check through the current connector (combined status returned no check records). Do not claim CI passed until an actual workflow run is inspected.


### Priority 84 — contract reconciliation and independent control totals (engineering path implemented)

- Confirmed existing modules \`floorsheet_contract.reconcile_floorsheet_rows\`, \`floorsheet_sample_audit.build_floorsheet_sample_acceptance_report\`, and \`broker_aggregation.reconcile_source_control_totals\`.
- Extended \`backend/app/floorsheet_pipeline.py\` with optional independently sourced daily control totals.
- Controls are reconciled against **all parseable source contracts**, including duplicate and amount-exception contracts. This avoids comparing an independent daily total against the filtered subset used for broker-feature aggregation.
- With no independent controls, pipeline output is explicitly \`not_run\`; it does not claim a pass. With controls, contract count, gross amount and party-observation count are checked. Differences are reported without source repair.
- Integration tests added for an exact two-contract sample and a deliberate gross-amount control mismatch.

### Priority 85 — broker-code coverage and identity aggregation (engineering path improved)

- Confirmed existing \`floorsheet_broker_join.resolve_contract_brokers\` uses effective-dated identity links as of each contract's trade date, and existing \`broker_aggregation.aggregate_broker_observations\` retains unresolved observations.
- Found a grouping defect: distinct unresolved broker codes could be merged into a single null-entity bucket. Corrected the group key to retain unresolved \`source_id\` + \`source_broker_code\` separately.
- Verified canonical broker entities now aggregate across multiple source-specific broker codes, while their source codes remain listed in \`source_broker_codes\`. The source IDs and evidence IDs remain preserved.
- Added regression coverage for separate unresolved broker codes, merged verified canonical identities, and a Urek-style 11-column CSV fixture through the existing end-to-end pipeline.
- A separate duplicate adapter created during implementation was removed; the existing \`floorsheet_broker_join\` remains the single broker-party bridge.

Commits:
- Broker aggregation correction: \`b47d1bda71fa6a46f361eee13ad5485ce72156b3\`
- Broker aggregation regression tests: \`a8c93ed9f2b8a16e79946fbe6ff1b3381c8d443c\`
- Independent-control pipeline extension: \`444780b2e32d0aaf851791cf19531f77a04e8841\`
- Urek-schema integration and control-total tests: \`0a3d8b4c31e3fc7a3209ef131fb387f9b7c48352\`

### Updated priority state (work session 2026-11-25)

| Priority | Status |
|---|---|
| 81. Acquire bounded sample | Prior 2024-01-02 sample smoke evidence exists; no new physical sample bytes/hash verified in this work session |
| 82. Verify source/provenance | Source-level research recorded; independent upstream lineage and rights unresolved |
| 83. Map source headers | Urek profile and synthetic tests added; physical raw header/hash verification pending |
| 84. Reconcile contracts/control totals | Existing row reconciliation integrated with independent daily controls in the end-to-end pipeline; tests added; live sample control result still pending |
| 85. Verify broker-code coverage | Source-specific unresolved broker codes retained distinctly; verified cross-code broker aggregation and tests added; actual sample identity coverage remains unmeasured |
| 86. Compare overlapping dates/sources | Earlier 70-date comparison exists; new raw-sample comparison not rerun in this session |
| 87. Identify missing trading dates | Still blocked by a date-level primary NEPSE session calendar |
| 88. Verify active universe | Official dated 281-equity + 47-mutual-fund registry still missing |
| 89. Assess one-year / six-month coverage | Still blocked by verified universe and session calendar |
| 90. Produce source-backed readiness report | Engineering parts advanced; final coverage readiness report remains blocked by priorities 81, 86–89 evidence |

### Verification caveat

The repository connector returned no CI status records for the new test commits at the time of this update. The code and tests are committed to \`main\`, but **the new tests have not been confirmed as passing in GitHub Actions**. Do not count them as passed until an actual workflow run/job result is retrieved. No sample bytes, canonical data or model-training data were promoted by this work session.


## 11. Data acquisition and reconciliation pipeline — priorities 81–90 (2026-11-25)

### Priority 81 — bounded floorsheet sample acquisition

Acquired and fully inspected two pinned, same-date source CSVs for **2026-11-24**.

**SamirWagle / MeroLagani-derived file**
- Repository commit: \`e6160adc6bdf3d19562167388e3d9d4f645c455a\`
- Path: \`data/floorsheet/floorsheet_2026-11-24.csv\`
- Git blob SHA-1: \`22eaa891b30aac2fe4cf197053efa014953351c0\`
- Size: 3,538,179 bytes; SHA-256: \`2687b7ed6bc5ebd737fa459ca8dd620941bb3ec1da6613fbd620550495018f55\`
- 52,369 unique contracts; 347 symbols; quantity 14,662,346; gross amount NPR 5,551,668,556.66.
- 0 malformed rows, duplicate contract IDs, blank cells or quantity × rate vs amount exceptions. The scraper writes \`date.today()\` to the \`date\` field; the field is therefore capture-date evidence, not an exchange-supplied trade timestamp.

**SocrateAI same-date file**
- Repository commit: \`cfa92493e93211c7019a5cd0b2cbe7d400d9c4e3\`
- Path: \`floorsheet/floorsheet_2026-11-24.csv\`
- Git blob SHA-1: \`e7150873219d66a21345df2dfbd78f6c5a4b1152\`
- Size: 3,058,892 bytes; 52,387 unique contracts; quantity 14,670,177; gross amount NPR 5,553,019,249.46.
- The complete raw CSV payloads were retrieved and analyzed in memory; neither raw source was copied into the project repository because upstream lineage and rights remain unresolved.

Acceptance: **one-day sample acquired and pinned**. Historical completeness and licensing still require separate acceptance.

### Priority 82 — source provenance and rights

- Added \`docs/FLOORSHEET_SOURCE_PROVENANCE_REVIEW_2026-11-25.md\`.
- The pinned Samir scraper requests \`https://merolagani.com/Floorsheet.aspx\`, paginates the rendered source table and stamps \`date.today()\`. Its source route is traceable to MeroLagani, but its own README uses an “Educational” label and the pinned tree has no explicit LICENSE/COPYING file.
- SocrateAI's same-day copy is row-consistent with Samir plus 18 additional contracts; its original acquisition route has not yet been proven independent or primary.
- Neither repository's public licence label alone proves rights to every upstream record.
- Acceptance: **publisher and code provenance substantially traced; upstream independence and intended-use rights open**.

### Priority 83 — source header mapping

- Added the Urek 11-column profile and Samir 9-column observed profile in \`backend/app/floorsheet_source_profiles.py\`.
- Added profile tests and profile-specific documents. The raw \`time\`, \`sector\`, \`id\` and \`sn\` fields remain source-only and are not fabricated into canonical fields.
- Contract IDs are preserved as strings. The Samir \`date\` field remains provisional because it is scraper-generated. Urek mapping remains publisher-schema-declared until its physical sample header is checked.
- Acceptance: **mapping code added; Samir header observed; Urek physical header review open**.

### Priority 84 — independent daily contract/control reconciliation

- Extended \`backend/app/floorsheet_pipeline.py\` and \`backend/app/broker_aggregation.py\` to accept independent daily controls for contract count, party observations, quantity and gross amount.
- A control result is \`not_run\` when controls are absent. It does not silently pass. Available controls are compared exactly with Decimal values; mismatches are reported, not repaired.
- The one-day source comparison shows SocrateAI's quantity and gross amount match MeroLagani's indexed daily summary exactly. Samir's file does not.
- Acceptance: **single-day source-control comparison performed; repeated historical per-date controls still open**.

### Priority 85 — broker-code coverage and identity history

- The two 2026-11-24 files contain 91 distinct numeric broker codes across buyer and seller columns. All 91 match a number in the current CDSC List of Clearing Members (the CDSC directory also contains code 55, not used in this sample).
- Added \`data/reference/broker_code_crosswalk_candidates_2026-11-25.csv\` with 91 unique code rows, current CDSC names and explicit candidate-only identity status.
- Added \`docs/BROKER_CODE_COVERAGE_AND_IDENTITY_REVIEW_2026-11-25.md\` and artifact tests.
- Code 91 is Citizens Share Broker Limited, formerly CBIL Securities. Company financial statements record the name-change resolution on 2025-01-21 and registrar recording on 2025-04-01.
- Code 8 is listed as Brilliant Securities in the current directory; MeroLagani also shows a separate \`8_RWS\` Ashutosh branch listing. The records are not collapsed without effective-dated branch/legal-identity proof.
- The aggregation grouping defect fixed earlier in this batch keeps distinct unresolved source codes apart; evidence-backed canonical IDs can still combine multiple source codes.
- Acceptance: **91/91 number coverage for this date; no code is auto-promoted to a verified historical legal-entity link**.

### Priority 86 — contract-level overlapping-source comparison

For 2026-11-24:
- Samir: 52,369 contract IDs.
- SocrateAI: 52,387 contract IDs.
- Shared contracts: 52,369; exact shared-row matches: 52,369; shared field conflicts: 0.
- Samir-only contracts: 0; SocrateAI-only contracts: 18.
- The 18 extra SocrateAI contracts contribute exactly 7,831 shares and NPR 1,350,692.80, closing the difference to the MeroLagani page's published quantity and amount.
- Added a reusable contract-level comparator: \`backend/compare_floorsheet_source_csvs.py\`, its tests and a pinned-source workflow.
- Full evidence: \`docs/MEROLAGANI_FLOORSHEET_CAPTURE_AUDIT_2026-11-24.md\`.
- Acceptance: **one-day contract comparison complete; the same comparison has not yet been run over every shared date**.

### Priority 87 — missing trading dates and session calendar

- Added further primary/secondary source notes in \`docs/NEPSE_SESSION_CALENDAR_SOURCE_RESEARCH_2026-11-25.md\`.
- The 2022 NEPSE notice supports a weekly session regime, and secondary sources report an April 2026 weekday change, but a primary date-level exchange calendar with each open/closed date was not obtained.
- A missing archive file is not assumed to be a holiday; a present date file is not assumed to be a complete session.
- Acceptance: **blocked on primary NEPSE date-level calendar evidence**.

### Priority 88 — target security universe

- Added regulator-side catalogue evidence and limitations in \`docs/ACTIVE_UNIVERSE_SOURCE_RESEARCH_2026-11-25.md\`.
- SEBON MFS Approved, MFS Pipeline and Securities Registered catalogues were reviewed. These do not provide a single dated NEPSE trading list crosswalked to security ID, instrument type and lifecycle status.
- Project target remains 281 equities + 47 mutual funds, but is not independently verified as a dated exchange universe.
- Acceptance: **blocked on official dated NEPSE instrument/lifecycle register**.

### Priority 89 — one-year and six-month archive date-file assessment

Pinned repository tree counts:
| Date-file window | SocrateAI | SamirWagle | Shared | SocrateAI only | Samir only |
|---|---:|---:|---:|---:|---:|
| 2025-11-25 to 2026-11-25 | 228 | 179 | 157 | 71 | 22 |
| 2026-05-25 to 2026-11-25 | 115 | 119 | 107 | 8 | 12 |

These are file-date manifest counts, not verified trading-session counts and not per-security coverage. Neither date set is a superset of the other. The 2026-11-24 completeness difference demonstrates why filename/date inventory alone is insufficient.

- Assessment: \`docs/FLOORSHEET_ARCHIVE_DATE_COVERAGE_ASSESSMENT_2026-11-25.md\`.
- Acceptance: **date-file availability established; one-year/six-month session and security completeness not established**.

### Priority 90 — source-backed data readiness report

Created \`docs/NEPSE_DATA_PIPELINE_READINESS_2026-11-25.md\`.

**Readiness decision: REVIEW_REQUIRED.** The 2026-11-24 SocrateAI copy is the best current completeness candidate for that single date, and broker-code-number coverage is 91/91. Do not promote it to canonical or model-training data until upstream lineage/rights, official session calendar, dated target universe and repeated per-session/per-security controls are accepted.

### Verification caveat

New unit tests and workflows were added for the source profiles, independent controls, source comparison and 91-code crosswalk. The GitHub connector did not expose workflow run/status records for the new commits during this session. **The new tests are not claimed as passing** until an actual GitHub Actions run or a local reproducible test run is recorded. Earlier backend suite result of 464 passed tests predates this batch.

No raw floorsheet file was committed to the project repository, no source was selected as a canonical dataset for all dates, and no training data was promoted.


### Final CI verification — priorities 81–90

After correcting one case-sensitive assertion in \`test_broker_code_crosswalk_artifact.py\` (the official CDSC directory stores "CITIZENS" uppercase), the final code commit is:

\`4ae7d5d04e261f2a392840dfd61506bc98f4aa7f\`

Verified GitHub Actions:
- Backend suite: **497 tests passed** — [run 45553280566](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45553280566).
- Backend contract tests: **passed** — [run 45553280557](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45553280557).
- Integrated evidence audit: **passed** — [run 45553280453](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45553280453).
- Pinned-source comparison workflow: **passed** — [run 45553060979](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45553060979).
- Pinned Samir/MeroLagani sample-audit workflow: **passed** — [run 45551652712](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45551652712).

The earlier failures on commits before \`4ae7d5d\` were due to the case-sensitive test assertion and are superseded by the successful final runs above. No test or audit result changes the source-rights, official-calendar or official-universe blockers. The final data readiness status remains \`REVIEW_REQUIRED\`.


## 12. Multi-date floorsheet comparison — priorities 91–100 (2026-11-25)

The next batch moved the pipeline from a one-day contract comparison to a bounded, reproducible multi-date comparison.

### Completed in this work session

| Priority | Work | Result |
|---|---|---|
| 91 | Add manifest-driven multi-date contract comparison | Implemented in `backend/compare_floorsheet_manifest.py`; emits per-date comparisons and aggregate status |
| 92 | Acquire pinned overlapping archive files | Added `backend/acquire_floorsheet_overlap.py`; selects bounded date overlap from pinned repository trees |
| 93 | Verify source payload identity | Recomputes Git blob SHA-1 before parsing and records payload SHA-256 in manifest; path traversal, hash mismatch, duplicate dates and invalid dates fail closed |
| 94 | Enforce manifest date consistency | Both source row-date fields must match the manifest date; mismatches are retained as review failures |
| 95 | Execute ten-date source comparison | Latest 10 common dates in the one-year candidate window acquired and compared |
| 96 | Quantify repeated source asymmetry | 571,619 shared contracts matched exactly; SocrateAI had 262 additional contracts; zero Samir-only contracts; zero shared-row field conflicts |

### Ten-date execution evidence

Dates: 2026-10-28, 2026-10-29, 2026-10-30, 2026-11-02, 2026-11-03, 2026-11-04, 2026-11-05, 2026-11-19, 2026-11-20 and 2026-11-24.

- Samir: 571,619 contracts.
- SocrateAI: 571,881 contracts.
- Shared IDs and exact shared-row matches: 571,619.
- SocrateAI-only: 262; Samir-only: 0; shared conflicts: 0.
- SocrateAI quantity surplus: 187,674 shares.
- SocrateAI gross-turnover surplus: NPR 19,958,116.86.
- Both sources: zero malformed rows, duplicate contract IDs and quantity-rate-amount formula exceptions in this sample; all row dates match the manifest dates.
- These are source-to-source differences, not independently verified missing-trade counts. No independent daily controls were supplied for these ten dates.

Detailed report: `docs/FLOORSHEET_MULTI_DATE_OVERLAP_AUDIT_2026-11-25.md`.

Workflow and artifact:
- Multi-date workflow [run 45596074299](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45596074299) passed.
- Backend suite [run 45596074194](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45596074194): **506 tests passed**.
- Artifact ID `15013057991`; ZIP SHA-256 `c0c0153df5534876fa3346ddbf3e66ec94f42ad36e3a3181bfde0a449d301c6a`.
- Report SHA-256 `5c743bec5e0535817304e142e88fa8942d4f2b411cea42e17da3ed10eebab15e`.
- Manifest SHA-256 `14fe0a9cf4c0298a6b1c7b93f53bef1f7f5f27731357571c23e0f3d76563df81`.

### Remaining priorities in this batch

| Priority | Next action | Acceptance requirement |
|---|---|---|
| 97 | Build a per-date exception ledger for the 262 source-only contracts | **Complete:** 262 hash-linked SocrateAI-only rows; all unresolved and no auto-resolution |
| 98 | Compare broker-code distributions and code presence across the ten dates | **Complete:** same 91-code union across both archives; each date's code set matches; no legal-identity inference |
| 99 | Compare observed symbols against a dated official target register | **Partial:** NEPSE stock-list and SEBON approved/pipeline evidence refreshed; dated 281 + 47 exchange register still unavailable |
| 100 | Extend the bounded sample to all shared one-year dates and issue an updated readiness decision | **Partial:** 100 of 157 shared date files compared in four batches; one published daily control passes SocrateAI and fails Samir; 57 dates remain |

**Readiness remains REVIEW_REQUIRED.** The multi-date result improves source-comparison evidence but does not resolve source rights/lineage, the primary NEPSE session calendar, the dated 281-equity + 47-mutual-fund registry, or independent daily control totals. No canonical data or model-training data was promoted.


### Priority 97 — hash-linked exception ledger

- Added `backend/build_floorsheet_source_exception_ledger.py` and regression tests.
- The bounded overlap workflow now creates JSON and CSV ledgers for source-only rows and shared-field conflicts, linked to both source revisions and both file hashes.
- For this ten-date run: **262** exceptions, all `right_source_only` / SocrateAI-only; zero conflict entries; all remain unresolved.
- Artifact [15012988544](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45596489553) contains the report, manifest and exception ledger. ZIP SHA-256: `2433f2b88396f5461efefb60096a766d15c39a0943f28e6d8f42655476fc0056`.
- Backend suite: **509 tests passed** [run 45596489636](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45596489636); contract tests and integrated evidence audit also passed [run 45596451411](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45596451411) and [run 45596451157](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45596451157).

Priorities 98–100 remain open: cross-date broker-code distribution, dated official instrument-universe reconciliation, and expanding from the 10-date pilot to all shared one-year dates with independent controls.


### Priority 98 — broker-code coverage across the ten-date sample

- Added `backend/analyze_floorsheet_broker_code_coverage.py` and tests.
- The ten-date run found the same **91 distinct raw broker codes** in both archives; no code appears in only one publisher's files.
- Each date has identical buyer/seller code presence across sources. Six dates contain 91 codes; four dates (2026-11-02 to 2026-11-05) contain 90.
- Activity counts are retained per date, source, side and raw broker code. No legal identity is inferred.
- Artifact [15013881435](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45596771362) contains the code-coverage JSON and activity CSV. ZIP SHA-256: `dfd2d18a5266421e10394affe77619551da2afbaed79a20e385471c623214fc9`.
- Backend suite: **512 tests passed** [run 45596771034](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45596771034).

Priority 99 remains focused on the official dated target-security register; priority 100 remains the bounded expansion to the complete one-year shared-date set with independent controls.


### Priority 99 — official target-universe evidence refresh (partial)

- Refreshed NEPSE's official stock-list evidence: the indexed snapshot is dated 2026-10-15 and reports 349 scrips traded in that session. This is a mixed-market daily trading count, not a 281-equity + 47-fund register.
- Retrieved the official SEBON MFS Approved PDF dated 2026-10-28 and MFS Scheme Pipeline PDF dated 2026-10-30. These show approval/registration and pipeline events, including open-end and closed-end schemes, but do not prove current NEPSE listing/trading status.
- Secondary sources disagree on listed-fund counts (45 trading in one 2026-11-08 report vs 43 in a 2026-11-24 directory); neither is authoritative.
- The 2026-11-24 floorsheet sample has 347 distinct symbols, 19 above the arithmetic 328-symbol target. No symbol is discarded or relabeled from that difference.
- Updated source research: `docs/ACTIVE_UNIVERSE_SOURCE_RESEARCH_2026-11-25.md`.

Priority 99 remains partial until a dated NEPSE security-ID / instrument-type / lifecycle export is captured and reconciled. Priority 100 remains the bounded expansion to all shared one-year dates with independent controls.


### Priority 100 — 30-date expansion and cumulative 40-date audit (partial)

- Added deterministic `--skip-latest` batching to avoid repeating the same dates.
- Compared the 30 shared dates immediately preceding the first ten-date pilot (2026-09-02 through 2026-10-27).
- Results: 1,489,600 shared contract rows matched exactly; SocrateAI had 1,203 additional contracts; zero Samir-only rows and zero shared-row conflicts.
- Combined latest 40 shared dates: 2,061,219 Samir rows; 2,062,684 SocrateAI rows; 1,465 SocrateAI-only rows; zero Samir-only rows; zero shared-row conflicts; quantity surplus 1,391,155 and gross-turnover surplus NPR 95,442,892.48.
- Broker-code coverage remained identical: same 91-code union across both archives, with identical per-date code sets.
- Workflow [45597195384](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45597195384) passed; backend suite [45597195251](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45597195251) passed with **513 tests**.
- Artifact [15014345535](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45597195384) includes the 30-date comparison, manifest, 1,203-row exception ledger and broker-code activity evidence.

The full one-year candidate overlap contains 157 common date files. **40/157 have now been compared**; 117 remain. Independent daily controls, official session calendar and official 281 + 47 instrument register remain open. No canonical data or training data has been promoted.


### Priority 100 — third 30-date batch; 70/157 shared dates compared

- Compared the next 30 older shared date files: 2026-07-17 through 2026-09-01.
- Samir: 1,649,223 physical rows but 1,648,223 unique contract IDs; SocrateAI: 1,650,258 rows/unique IDs.
- Shared exact contracts: 1,648,223; SocrateAI-only: 2,035; Samir-only: 0; shared conflicts: 0.
- Raw quantity and turnover surplus: 1,994,322 shares and NPR 1,756,482,535.19.
- A duplicate physical-row ledger isolated **1,000 duplicated contract IDs** in Samir's 2026-07-17 file. Each appears twice; all 1,000 pairs have identical transaction fields excluding source sequence `sn`. The duplicate extra rows represent 182,280 shares and NPR 89,427,317.60 in raw Samir totals. Both rows remain preserved and unresolved; no auto-deduplication.
- Broker-code coverage remains the same 91-code union with no source-only codes and identical per-date sets.
- Workflow [45598359940](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45598359940) passed; backend suite [45598359945](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45598359945) passed with **516 tests**; contract tests and integrated evidence audit passed.
- Artifact [15014282629](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45598359940) contains the 30-date comparison, source exception ledger, broker activity report and physical-row duplicate ledger.

Cumulative latest 70 common dates: 3,709,442 shared exact contract rows, 3,500 SocrateAI-only contracts, zero Samir-only contracts, zero shared conflicts, and 1,000 Samir duplicate extra physical rows. Raw totals show 3,385,477-share and NPR 1,851,925,427.67 SocrateAI surplus, with the Samir duplicate rows still included.

**87 of the 157 shared date files remain unprocessed.** The complete 157-date set is still not equivalent to verified exchange sessions, and independent daily control totals plus the official dated 281 + 47 security register remain blockers.


### Priority 100 — fourth 30-date batch; 100/157 shared dates compared

- Fourth batch: 2026-06-05 through 2026-07-16.
- Samir 1,619,124 rows; SocrateAI 1,668,638 rows; 1,619,124 shared exact contracts; 49,514 SocrateAI-only contracts; zero Samir-only and zero shared conflicts.
- 48,917 of the 49,514 source-only contracts occur on 2026-06-24, where Samir has exactly 24,000 rows and SocrateAI has 72,917.
- Added a sourced independent control for 2026-06-24: quantity 10,777,582, transaction count 72,917, gross amount NPR 4,418,607,486.62. SocrateAI passes all three exact checks; Samir fails all three.
- Source evidence is documented in `docs/INDEPENDENT_DAILY_CONTROL_CROSSCHECK_2026-06-24.md` and pinned in `data/independent_controls/floorsheet_daily_controls_2026-11-25.json`.
- Overall readiness remains REVIEW_REQUIRED because one source fails the daily control, other dates lack controls, and source lineage/rights and official session/universe records remain open.
- Workflow [45599320707](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45599320707) passed; backend suite [45599320697](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45599320697) passed with **517 tests**.

Cumulative latest 100 shared dates: 5,328,566 shared exact contract rows, 53,014 SocrateAI-only contracts, zero Samir-only contracts, zero shared conflicts and 1,000 Samir duplicate extra physical rows. Raw totals show a SocrateAI surplus of 11,182,588 shares and NPR 7,159,881,183.48.

**57 of 157 common date files remain.** Only one date has a published daily control attached; no canonical data or model-training data has been promoted.


### H. Priority 92 follow-up — Yonepse 2026-11-24 payload retrieved; independence unresolved

- Retrieved and parsed `Shubhamnpk/yonepse/data/floor_sheet/daily/2026-11-24.json` through GitHub Contents API.
- 52,387 unique contracts; recomputed quantity 14,670,177 and turnover NPR 5,553,019,249.459984 match the payload summary.
- Exact comparison against SocrateAI pinned commit `cfa92493e93211c7019a5cd0b2cbe7d400d9c4e3`: 52,387/52,387 contract IDs and buyer/seller/quantity/rate/amount fields match; no row conflicts.
- Comparison against Samir pinned commit `e6160adc6bdf3d19562167388e3d9d4f645c455a`: all 52,369 Samir contracts match; Yonepse has 18 additional contracts; no shared-field conflicts.
- This is not independent confirmation because the exact Yonepse–SocrateAI match may reflect shared upstream data or copying/derivation. Stock-ID-to-symbol mapping was not validated.
- Payload content was retrieved in-session but not stored as a pinned raw artifact and no independent SHA-256 was computed. Google Drive remains disabled by workspace admin; Hugging Face candidate remains metadata-only.
- Updated report: [Priority 92 acquisition status](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/blob/main/docs/PRIORITY_92_THIRD_SOURCE_ACQUISITION_STATUS_2026-11-25.md), commit `1ed3f610255da3bff9dd72b63b4cad8c2f277bd6`.

**Priority 92 state: partially complete for one-day retrieval and reconciliation; not complete for durable byte pinning, independent source lineage, historical coverage or rights. No canonical promotion.**

- Yonepse file is now pinned to file commit `1bfa798e84c7170f826e473e7e1ec3957c81966c`, tree `33e7fc54f0b225e92d148f0ef362fbb67045abcd`, Git blob SHA-1 `2a758194c470048e3b22aefc8954365397d9c48d`, size 3,037,252 bytes. Re-fetch at the pinned commit reproduces the 52,387-row summary. Independent SHA-256 and local raw-byte retention remain open. Priority 92 report updated again at commit `32dbea91e8fae817f4419a954cd928fcdf1e1e5d`.

### I. Priority 93 — Yonepse reference mapping audit

- On the pinned 2026-11-24 Yonepse payload, 350 distinct stock IDs were observed; 346 mapped through the same-commit community securities registry, four remained unmapped (`8111`, `469`, `700`, `661`).
- Mapped traded instruments comprised 279 Equities, 43 Mutual Funds and 24 Non-Convertible Debentures. The debentures are retained for raw audit only and excluded from the active target scanner universe. These are traded IDs on one date, not proof of full target-universe membership.
- 91/91 observed buyer/seller broker codes mapped to `brokers.json.memberCode`; all matched directory entries were marked active in that snapshot. This is a current directory candidate, not historical legal-identity proof.
- Report: [Priority 93 Yonepse reference mapping audit](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/blob/main/docs/PRIORITY_93_YONEPSE_REFERENCE_MAPPING_AUDIT_2026-11-25.md), commit `7275800d84e26b09ae978a61d372e53f33941d3d`.
- Official dated instrument registry, four unresolved stock IDs, and effective-dated broker identity remain open. No canonical promotion.


## Work-session update — 2026-11-26 (connected GitHub review)

### Verified corrections and actions

1. **SocrateAI floorsheet audit report — existing artifact verified, prior empty-file claim corrected.**
   - Historical-data-vault workflow run: `45419878883`, completed successfully.
   - SocrateAI audit step: 120 expected / 120 acquired / 120 audited dates; 6,407,328 rows; zero invalid days; zero file errors; status `complete_row_validated_window`.
   - The committed `data/reports/socrateai-floorsheet-window-audit.json` blob is 1,126,238 bytes. A content-fetch response was empty because the file exceeds the connector's retrieval limit; the Git tree confirms the non-zero blob size.
   - Corrected automation issue #2 with this evidence. Its first acceptance criterion (non-empty machine-generated audit report) is satisfied. Calendar, missing-date, index-anomaly, provenance-independence and rights gates remain open.

2. **Daily floorsheet collector — dependency root cause isolated; repair proposed, not yet production-verified.**
   - Latest scheduled run `45607824763` failed before network access with `ModuleNotFoundError: No module named 'nepse'`.
   - Workflow installed PyPI `nepse-scraper`, which is not the upstream package that exports `from nepse import AsyncNepse`; it also used Python 3.10 although the upstream NepseUnofficialApi project requires Python >=3.11.
   - Open PR: https://github.com/jaljala044/nepse-automation/pull/3. It switches to Python 3.11, pins the upstream client to commit `180a550c60f1959983b854659e650a4c189a3c0f`, and adds an import smoke-test workflow.
   - The PR has not yet been executed in CI or merged. No live NEPSE fetch or Google Sheets write is claimed. TLS verification remains enabled. Staged worksheet replacement, raw-response hashing and session-date verification remain required before production approval.

3. **Active-equity universe — third discrepancy identified and documented.**
   - The 2026-11-26 company-list CSV has 281 rows but 278 unique active-equity symbols: USLB is repeated once and SYPNL twice.
   - The 278 unique symbols exactly match the 278-symbol equity candidate list.
   - The separate 281-symbol provisional OHLCV coverage set differs by NESDO, ULBSL and YMHL.
   - The 2026-11-25 security snapshot records status A and IDs NESDO/8041, ULBSL/8063 and YMHL/9342. That snapshot does not independently prove their instrument type or lifecycle dates.
   - Documentation correction merged in main via PR #16, merge commit `ca33e16ce84bcb393ba760d7f46eff1fbcaa6be7`. These three remain candidates, not canonical universe promotions.

### Data-safety statement

No raw OHLCV or floorsheet records were changed in this work session. The owner-finalized 2025-07-28 records for BGWT, MEHL, RAWA, RHGCL and ULHC remain authoritative and unchanged. No canonical data promotion or P2 model-training approval is made.

### Next execution priorities

1. Verify instrument type and effective lifecycle evidence for NESDO, ULBSL and YMHL; obtain a complete row-level official instrument register rather than relying on the duplicated rendered table.
2. Run and inspect the dependency smoke test for automation PR #3, then address the collector's staged-write/raw-capture/session-date safeguards before any production run.
3. Continue the 616-session calendar recovery and primary NEPSE notice capture.
4. Continue the OHLCV exception and corporate-action review without overwriting raw values or owner-finalized records.
5. Continue floorsheet source lineage, missing-date and index-anomaly adjudication; keep canonical promotion blocked until all gates pass.


## Work-session update — 2026-11-26 (Priority 94 equity classification)

- Reviewed the three symbols that differ between the 278-symbol candidate list and 281-symbol provisional OHLCV coverage set: NESDO, ULBSL and YMHL.
- ShareSansar company profiles identify NESDO and ULBSL as microfinance-sector companies with listed shares, and YMHL as a hydropower company with listed shares. ShareSansar's YMHL notice records NEPSE listing on 2026-06-19 and trading commencement on 2026-06-22. NEPSE's stock-list page also included all three symbols in its 2026-10-15 snapshot.
- Microfinance is a sector, not a mutual-fund instrument classification. NESDO and ULBSL are company-share equities, not mutual funds. YMHL is a hydropower equity.
- Report: [Priority 94 NESDO/ULBSL/YMHL equity classification evidence](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/blob/main/docs/PRIORITY_94_NESDO_ULBSL_YMHL_EQUITY_CLASSIFICATION_2026-11-26.md), commit `a458485be6c4c1d62de10959be24bf966435389e`.
- **Disposition:** approved-provider evidence supports all three as equity inclusion candidates. Canonical promotion remains blocked pending dated symbol-to-security-ID reconciliation and effective lifecycle evidence; 2026-11-25 snapshot IDs NESDO/8041, ULBSL/8063 and YMHL/9342 are not yet a complete historical security master. No canonical universe or raw OHLCV/floorsheet data changed. No P2 training approval.

### Updated next execution priorities

1. Reconcile NESDO/8041, ULBSL/8063 and YMHL/9342 against dated security-master evidence and the active-equity universe's as-of date; then correct the candidate universe if the identity mapping is validated.
2. Execute and inspect automation PR #3 dependency smoke test; then implement staged writes, immutable raw-response capture, session-date checks and end-to-end validation before production.
3. Continue the 616-session calendar recovery and primary NEPSE notice capture.
4. Continue OHLCV exception and corporate-action review without overwriting raw values or owner-finalized records.
5. Continue floorsheet source-lineage, missing-date and index-anomaly adjudication; keep canonical promotion blocked until all gates pass.


## Work-session update — 2026-11-26 (automation PR #3 CI check)

- Rechecked [automation PR #3](https://github.com/jaljala044/nepse-automation/pull/3), "Fix floorsheet collector NEPSE client dependency". It remains open, unmerged, and marked mergeable by GitHub.
- The PR-head dependency-check workflow run 45803065619 completed with conclusion failure. The associated job 139851025320 is also failed.
- The GitHub job-steps endpoint returned an empty list and the job-log download returned a BlobNotFound/404 response. Therefore the failure cause is not established; do not assume the dependency pin or import itself is wrong.
- Safety decision: do not merge PR #3 or claim the smoke test passed. Obtain a rerunnable/retained diagnostic run and inspect the exact failing step before changing the dependency or enabling production collection. Even after the import test passes, staged writes, immutable raw-response capture, session-date validation and live end-to-end verification remain production gates.
- No live NEPSE request, Google Sheets write, raw-data change, or canonical promotion was performed.

### Next execution priorities (revised)

1. Diagnose the failed dependency-check run for automation PR #3; rerun or add a minimal diagnostic workflow that preserves step output, then only proceed when the import check passes.
2. Reconcile the three equity inclusion candidates NESDO/8041, ULBSL/8063 and YMHL/9342 against dated security-master evidence and the active-equity universe's as-of date.
3. Continue the 616-session calendar recovery and primary NEPSE notice capture.
4. Continue OHLCV exception and corporate-action review without overwriting raw values or owner-finalized records.
5. Continue floorsheet source-lineage, missing-date and index-anomaly adjudication; keep canonical promotion blocked until all gates pass.


## Work-session update — 2026-11-26 (P1 calendar evidence expansion)

- Expanded the secondary-source cross-check for the two 616-date candidates missing from the pinned SocrateAI index archive: 2025-04-03 and 2026-11-20.
- For 2025-04-03, added HimalPress and Expert Nepal historical index-table records alongside Kathmandu Post. For 2026-11-20, added Nepse Decode's date-stamped daily summary and a NepseTrading date-specific close report alongside NepseIQ and ShareSansar.
- Machine-readable cross-check updated in commit `3b96c0783426fe776c20ba6decf0faefd4615e8a`; detailed recovery report updated in commit `662b12bef6673666ff3e36a63e64d2186d909ab1`.
- This increases secondary corroboration but does not satisfy the primary NEPSE date-by-date evidence requirement. All 616 dates remain candidate_unverified; zero canonical dates promoted; exact identity with the original extraction list remains unresolved; P2 training remains blocked.


## Work-session update — 2026-11-26 (historical equity identity)

- Expanded evidence for NESDO, ULBSL and YMHL: dated listing and first-trading timelines plus multiple provider classifications now recorded in `data/reference/nepse_equity_candidate_additions_2026-11-26.json` (commit `b78a9fca080b0763d8ffdcae2d6e1e826ab5ae5c`).
- Added detailed assessment and guardrails to `docs/UNIVERSE_AND_SYMBOL_RECONCILIATION_REVIEW_2026-11-26.md` (commit `d3c7cdd5f03d12120347888360cd8247f1ffa5dc`).
- NESDO and ULBSL are microfinance-sector equities, not mutual funds; YMHL is a hydropower equity. Listing dates are NESDO 2022-03-27, ULBSL 2022-05-26, YMHL 2026-06-19. First trading dates recorded as 2022-03-28, 2022-05-27 and 2026-06-22 respectively.
- Their security IDs (8041, 8063, 9342) are supported by the 2026-11-25 snapshot and 2026-11-19 OHLCV capture. This does not prove unbroken historical stable-ID continuity or complete 281-member membership.
- No raw OHLCV data or owner-finalized historical records changed; canonical manifest promotion remains blocked pending complete dated universe reconciliation and source-provenance gates.


## Work-session update — 2026-11-26 (collector CI diagnostics)

- Automation PR #3 remains open and unmerged. Its dependency-check run `45803065619` and rerun both concluded failure; the available GitHub job-step/log endpoints returned no diagnostic content, so the failing step remains unknown.
- Added verbose dependency-install diagnostics, runner version capture, pinned-commit reachability check, package metadata/import checks, and an always-uploaded 14-day diagnostics artifact in automation commit `323c7c1e9906e26a8418ed47ca4a0fbce7ea9d94`.
- Posted the diagnostic follow-up to [automation PR #3](https://github.com/jaljala044/nepse-automation/pull/3). The new commit has not yet produced a visible workflow run in the available PR-run query. Do not mark dependency validation passed or merge the PR.
- Collector remains blocked from production scheduling: replace-in-place sheet writes, date validation against returned records, immutable raw response retention/hash, and live end-to-end verification are still required.


## Work-session update — 2026-11-26 (Priority 95: four Yonepse IDs resolved)

- Resolved all four previously unmapped stock IDs from the dated 2026-11-25 security-ID snapshot:
  - 8111 → HIDCLP — Hydorelectricity Investment and Development Company Limited Promoter
  - 469 → NIMBPO — Nepal Investment Mega Bank Ltd. Promoter Share
  - 700 → HEIP — Himalayan Everest Insurance Limited Promoter
  - 661 → NMLBBLP — Nerude Mirmire Laghubitta Bittiya Sanstha Limited Promoter
- All four are marked active in the snapshot and have OHLCV files, but their security names explicitly identify promoter/promoter-share instruments. Do not silently treat them as ordinary public-share universe members.
- Mapping coverage for the four previously unmapped IDs is now 4/4 at the 2026-11-25 snapshot level. Effective-dated historical identity and promoter-share inclusion policy remain open.
- Detailed report: [Priority 95 unmapped Yonepse IDs resolved](docs/PRIORITY_95_UNMAPPED_YONEPSE_IDS_RESOLVED_2026-11-26.md), commit `cd08a1c4af0b7196f2fd76e464886df84c38509b`.
- No raw floorsheet/OHLCV records changed; no canonical target-universe or training-data promotion.



## Work-session update — 2026-11-26 (Priority 96: promoter-share classification guardrail)

- Added `promoter_share` as an explicit recognized non-target instrument class in both instrument-manifest and universe-snapshot validation.
- Promoter-share rows remain available for lifecycle/audit retention but are excluded from equity/mutual-fund target counts; the snapshot validator rejects any promoter-share row marked in-scope.
- Added regression tests for audit retention, exclusion from active targets and rejection of target promotion.
- Report: `docs/PRIORITY_96_PROMOTER_SHARE_CLASSIFICATION_GUARDRAIL_2026-11-26.md`.
- This is a validator-only change. No promoter-share ticker was added to the canonical universe; no raw OHLCV/floorsheet data changed; no training-data promotion.
- Tests are committed but await CI execution; do not claim they pass until a workflow confirms.


## Work-session update — 2026-11-26 (Priority 97: merger timeline evidence expansion)

- Added source-backed joint-transaction start dates for six equity predecessor symbols in `data/reference/nepse_historical_identity_evidence_2026-11-26.json` (commit `31d14f61908c2c71c75a3dbde088dbe25b39c650`):
  - BPW → Samudayik Laghubitta: 2024-03-06 (24 Falgun 2080).
  - MMFDB and NLBBL → Nerude Mirmire Laghubitta: 2024-03-13 (30 Falgun 2080).
  - JALPA and KLBSL → Matribhumi Laghubitta: 2024-07-11 (27 Ashad 2081).
  - MKLB → Samata Gharelu Laghubitta: 2024-07-08 (24 Ashad 2081).
- Sources include ShareSansar merger/listing notices and Merolagani's Matribhumi merger announcement. The dates describe joint corporate operations, not proven last-trading/first-trading boundaries or stable-ID validity windows.
- The JSON continues to mark `effective_date_verified=false` and `stable_id=null`; no historical prices were spliced, no aliases renamed, and no raw data changed.
- Next step: obtain exchange suspension/resumption notices and effective-dated security IDs for these predecessor/successor pairs. Do not promote identity intervals until those records are corroborated.


- Follow-up to Priority 97: added joint-operation dates for SABSL/SDLBSL → SMPDA (2024-07-14), SAMAJ → GBLBS (2025-10-19), and SFCL → PFL (2026-07-10), with secondary evidence links. Data commit `c1f5129b7e9658698621fb866ed9a88036e12ae6`; report commit `18fde7c6f07d4b3237df2911c02b5aaf4f8dd1ad`.
- Nine merger predecessor symbols now have documented joint-operation dates across the two Priority 97 batches. These remain corporate-operation dates, not verified exchange-trading boundaries or stable-ID intervals. `stable_id` remains null and `effective_date_verified` remains false; no raw history or canonical manifest changed.


## Final closure review — 2026-11-26

**Disposition: NOT CLOSED — release/production gates remain open.** This is an explicit closure assessment, not a claim that the whole NEPSE AI Scanner Pro is finished.

### Completed in this work session
- Priority 96 promoter-share classification guardrail committed; promoter-share records can be retained as non-target audit rows.
- Priority 97 merger timeline evidence expanded for nine predecessor symbols. Joint-operation dates are recorded, but not treated as exchange trading boundaries or stable-ID intervals.
- Automation safety containment committed to `jaljala044/nepse-automation` (`4b245c4db3dedc1603e676132060d1a45e2cda2d`): scheduled floorsheet writes removed; manual workflow is gated by repository variable `NEPSE_FLOORSHEET_PRODUCTION_ENABLED == 'true'`; Python upgraded to 3.11; unrelated `nepse-scraper` dependency replaced by pinned upstream client and import smoke test added. This is a fail-closed containment measure, not production readiness.

### Still open — cannot honestly mark complete
1. **CI validation:** Priority 96 tests have not been confirmed by a successful GitHub Actions run. The automation dependency PR #3 remains open and unmerged; its latest recorded diagnostic run failed without retrievable step logs.
2. **Floorsheet collector safety:** `fetch_floorsheet.py` still clears the final worksheet before upload and writes directly to the destination. Staging/verification, immutable raw response/hash, idempotency, and response-session-date validation are not implemented. Production variable must remain unset.
3. **Historical equity identity:** nine predecessor symbols have joint-operation dates, but exact last trading dates, successor first trading dates and effective-dated security IDs remain unresolved. The records retain `stable_id: null` and `effective_date_verified: false`.
4. **Session calendar:** 616 candidate session dates remain unverified against a complete date-level primary exchange calendar; two more dates have secondary corroboration only.
5. **Canonical universe:** exact 281-equity membership and full dated lifecycle evidence are not yet verified. Do not promote the candidate list to canonical.
6. **Data quality and governance:** 1,331 invalid OHLC rows and eight cross-source conflicts remain quarantined; floorsheet provenance/coverage and data rights remain unresolved; no final point-in-time/no-lookahead release validation exists.

### Closure rule
Project may be marked closed only after each open gate has a committed evidence artifact, passing automated validation where applicable, an explicit disposition, and no unresolved production safety issue. Until then, status remains **engineering/evidence work in progress; production and model-training promotion blocked**.

### Immediate safety instruction
Keep `NEPSE_FLOORSHEET_PRODUCTION_ENABLED` unset. Do not merge automation PR #3 or enable unattended writes until the dependency check passes and the collector is made non-destructive and independently validated.


### Next-step execution — merger trading-suspension evidence (2026-11-26)
- Added explicit secondary-source trading-suspension effective dates for BPW (2024-03-06), MMFDB/NLBBL (2024-03-13), SAMAJ (2025-10-19), and SFCL (2026-07-10) to `data/reference/nepse_historical_identity_evidence_2026-11-26.json`.
- Each record includes the source URL and interpretation basis. These dates are not labelled as last-trading dates.
- Data commit: `ba06db49fac96999da8f92a105bfac240b379c6e`.
- Report update: `a3f626dcd4f5396a9e57e029dd0abf20d274bbcb`.
- Evidence: ShareSansar notices dated 2024-03-06, 2024-03-12, 2025-10-17 and 2026-07-09 respectively.
- JALPA/KLBSL and MKLB/SAMATA suspension-effective dates remain unresolved. Last actual trade dates, successor first trade dates and effective-dated security IDs remain open for all affected merger groups. No stable IDs or canonical mappings were promoted.


## Priority 97 follow-up — predecessor last-trade evidence (2026-11-26)

Added secondary historical last-recorded-trade evidence for JALPA (2024-07-10), KLBSL (2024-07-10), and MKLB (2024-07-07) to `data/reference/nepse_historical_identity_evidence_2026-11-26.json`. JALPA/KLBSL successor MATRI shares were reported listed 2024-08-12 and available for trading 2024-08-13. Sources include Laganilab, Merolagani, and NepseAlpha; the detailed evidence and interpretation are in `docs/PRIORITY_97_HISTORICAL_EQUITY_MERGER_TIMELINES_2026-11-26.md`.

These are secondary-source observations, not exchange-primary certified lifecycle intervals. No stable IDs were populated, no price history was spliced, and no raw OHLCV/floorsheet data changed. Priority 97 remains open pending dated security-ID validity evidence, raw history boundary checks, and equivalent last-trade evidence for remaining predecessor groups.


## Priority 97 follow-up — OHLCV boundary validation (2026-11-26)

Read-only OHLCV boundary inspection completed for JALPA, KLBSL, MATRI, MKLB and SMATA in `nepse-smc-data` and `nepse-history-starter`. All 17 merger-set CSV blobs present in both repositories have identical SHA-1 blob IDs and file sizes; the archives therefore replicate the same files and do not constitute independent source confirmation.

Observed: JALPA and KLBSL end on 2024-07-10; MATRI begins 2024-08-13. MKLB ends 2024-07-07, while SMATA's existing series begins 2024-03-04, predating the acquisition integration. This confirms the acquisition case is not a simple predecessor-to-new-successor concatenation. Detailed rows, hashes and dispositions are in `docs/PRIORITY_97_HISTORICAL_EQUITY_MERGER_TIMELINES_2026-11-26.md`; JSON observations are in `data/reference/nepse_historical_identity_evidence_2026-11-26.json`.

No raw OHLCV data was modified. The boundary check validates the archive contents only; it does not certify NEPSE-origin data, security-ID continuity, or effective-dated legal identity. `stable_id` remains null and `effective_date_verified` false. No history splice or canonical/training promotion is authorized.


## Priority 97 follow-up — expanded OHLCV boundary review (2026-11-26)

Extended read-only predecessor OHLCV boundary review to BPW, MMFDB, NLBBL, SAMAJ, SFCL, SABSL and SDLBSL. BPW has a nonzero-volume row on the reported suspension-effective date (2024-03-06), so notice timing must be reconciled before asserting last trade. MMFDB/NLBBL files end 2024-03-12; SFCL ends 2026-07-09. SABSL/SDLBSL files extend to 2024-07-13 but rows on 12–13 July repeat the 11 July OHLCV exactly. SAMAJ's rows on 17–18 October 2025 repeat 16 October exactly. Repeated terminal rows must not be treated as actual trades without session evidence.

Successor series SLBSL, GBLBS and PFL already existed before the merger integration events; they are not newly-started ticker histories. NMLBBL and SMPDA file starts are 2024-05-19 and 2024-08-18 respectively, but file starts alone do not establish legal first trading dates. Full row-level notes are in the Priority 97 report and JSON evidence. No raw data was edited, no price histories were spliced, and canonical/training promotion remains blocked pending independent source lineage, exchange-session confirmation and dated security-ID validity.


## Priority 97 follow-up — successor security-ID snapshot reconciliation (2026-11-26)

Attached dated 2026-11-25 successor security-ID observations from `data/reference/nepse_security_id_snapshot_2026-11-25.csv`: SLBSL 2804, NMLBBL 396, MATRI 694, SMATA 2761, SMPDA 2896, GBLBS 583, PFL 236. These are current snapshot observations only and do not prove historical ID validity or continuity with predecessor instruments. Predecessor symbols remain unresolved in `nepse_unmatched_symbol_review_2026-11-26.csv`; no predecessor IDs inferred, no stable IDs populated, and no history splice or canonical/training promotion performed. See Priority 97 report and JSON evidence for details.


## Priority 97 — historical security-ID recovery assessment (2026-11-26)

Repository archive search did not locate dated historical security-master snapshots for predecessor symbols BPW, JALPA, KLBSL, MKLB, MMFDB, NLBBL, SABSL, SDLBSL, SAMAJ and SFCL. ShareHub documentation identifies a current stock-table `nepseSecurityId` field, but access requires a licensed authenticated account and IP allow-listing; its documented companies endpoint does not include a security ID in each company row. No authenticated response was acquired. Current successor IDs remain date-scoped observations only. Added acquisition-gap metadata and regression guard tests; no IDs inferred, no history splice, no canonical/training promotion. See `docs/PRIORITY_97_HISTORICAL_SECURITY_ID_RECOVERY_2026-11-26.md`.


## Priority 97 — historical instrument identity regression framework (2026-11-26)

Added 13 unittest cases in `backend/tests/test_historical_identity_regression.py` (commit 418f719838b7aa44dc898b78e079db93215b2bc8). Checks include duplicate IDs/symbols, inclusive interval conflicts, missing source, invalid ID/date order, merger splice denial and unresolved equity predecessor preservation. Independent inspection of the dated snapshot found 573 rows, 573 unique symbols and 573 unique IDs, with no detected duplicate or invalid ID. Snapshot includes non-equities; observations are date-scoped. Python tests are committed but execution has not been confirmed. This is a test-local framework, not yet a production ingestion gate; no historical IDs inferred or raw prices changed. Next: run tests and integrate reusable validation into canonical promotion path. Priority 97 remains open.


### Priority 97 follow-up — additional predecessor last-trade evidence (2026-11-26)

- Added secondary-reported last-recorded-trade dates for BPW (2024-03-06), MMFDB (2024-03-12) and NLBBL (2024-03-12) to the historical identity evidence JSON.
- Evidence combines Laganilab/Merolagani historical company pages with ShareSansar dated company-history observations. BPW's last-trade date coincides with the reported suspension-effective date; MMFDB/NLBBL last-trade dates precede the reported 2024-03-13 suspension date.
- Updated evidence report: `docs/PRIORITY_97_HISTORICAL_EQUITY_MERGER_TIMELINES_2026-11-26.md`.
- Evidence remains secondary-source level; no historical predecessor security IDs, effective intervals, or legal stable IDs are certified. No canonical promotion, training promotion, or price-history splice is authorized.


### Priority 97 follow-up — successor-side listing evidence (2026-11-26)

- Added secondary-source listing observations for post-merger SLBSL (256,050 shares) and NMLBBL (13,977,643 shares), both reported listed on 2024-05-17 by ShareSansar.
- The report gives opening price ranges for first transactions, but does not establish the first executed trading session. NMLBBL's company profile records operation date 2024-05-19; this is kept separate from exchange trading date.
- first_trading_date remains null for both. Next evidence needed: dated daily OHLCV/floorsheet first trade row or explicit exchange/secondary notice confirming first execution.
- No stable IDs/effective intervals inferred; no canonical/training promotion or price splice. Priority 97 remains open.


### Priority 97 follow-up — expanded successor listing evidence (2026-11-26)

- Added successor-side listing records for MATRI, SMATA, SMPDA, GBLBS and PFL to the evidence JSON. MATRI: NepseAlpha dated 2024-08-13 explicitly says trading from today; retained as a secondary-reported first-trading date pending OHLCV/floorsheet confirmation. SMATA: 2.6m acquisition shares listed 2024-08-02, exact first execution unknown. SMPDA: 7,008,584 shares listed 2024-08-15, exact first execution unknown. GBLBS: 10,053,500 shares listed 2025-12-22. PFL: 19,014,680 shares listed 2026-09-15.
- Flagged date contradictions: GBLBS listing report's Ashwin 23, 2082 joint-transaction date conflicts with 17 Oct 2025 suspension report's Kartik 2, 2082 effective date. PFL listing report also states Ashwin 23, 2082, conflicting with 9 Jul 2026 suspension/integration report. Dates remain separate source observations, not normalized.
- First-trading dates for SMATA/SMPDA/GBLBS/PFL remain null. No stable IDs/validity intervals inferred; no price splice or canonical/training promotion. Priority 97 remains open.


### Priority 97 — project OHLCV first-session cross-check (2026-11-26)

- Inspected exact symbol CSVs in `jaljala044/nepse-smc-data/03_stock_charts_ohlcv` and captured blob SHAs plus nonzero-volume boundary rows.
- First post-listing/resumption session candidates: SLBSL 2024-05-19 (722 shares), NMLBBL 2024-05-19 (864), MATRI 2024-08-13 (1,391), SMPDA 2024-08-18 (5,314), GBLBS 2025-12-23 (51,250), PFL 2026-09-16 (33,240).
- SMATA's acquisition share addition is explicitly not treated as a new ticker first-trade event: the symbol already had active OHLCV rows by 2024-07-20, before the 2024-08-02 additional listing.
- These are project archive OHLCV observations, not independent trade-level verification. Exact floor-sheet contract corroboration is still required; first_trading_date_verified remains false. Repeated carry-forward OHLCV rows are a known caveat.
- No stable IDs/validity intervals inferred, no price series modified/spliced, no canonical or training promotion. Priority 97 remains open.


### Priority 97 — identity snapshot cross-check and acceptance decision (2026-11-26)

- Cross-checked 573-row `nepse_security_id_snapshot_2026-11-25.csv`. Current successor snapshot IDs: SLBSL 2804, NMLBBL 396, MATRI 694, SMATA 2761, SMPDA 2896, GBLBS 583, PFL 236 (all status A). These are recorded as snapshot IDs only; `stable_id` remains null.
- Former symbols BPW, MMFDB, NLBBL, JALPA, KLBSL, MKLB, SABSL, SDLBSL, SAMAJ and SFCL are absent from this current snapshot. This is not evidence of no historical ID; historical IDs remain unresolved.
- Corrected report to reconcile earlier null statements: six positive-volume OHLCV first-session candidates are now recorded in JSON (SLBSL/NMLBBL 2024-05-19; MATRI 2024-08-13; SMPDA 2024-08-18; GBLBS 2025-12-23; PFL 2026-09-16), all unverified pending historical floorsheets. SMATA is an additional-share event on an existing symbol.
- Acceptance decision: Priority 97 is partially evidenced but NOT CLOSED. Missing: historical predecessor security IDs, historical security-master payload, independent contract-level floorsheet confirmation, and legal effective-date boundaries. No canonical ID assignment, price splice or training promotion.


## Priority 98 — historical security-master source audit (2026-11-26)

**CLOSED — source-discovery task only. Historical ID recovery remains blocked and Priority 97 remains NOT CLOSED.** Searched available scanner, NEPSE SMC data, history-starter and automation repository archives/code for dated predecessor security-master snapshots and symbol-to-ID crosswalks. No dated historical security master for BPW, MMFDB, NLBBL, JALPA, KLBSL, MKLB, SABSL, SDLBSL, SAMAJ or SFCL was located. ShareHub's current API schema documents `nepseSecurityId` on its `/stocks` endpoint, but access requires a licensed Data API account, Bearer authentication and server-IP allow-listing; no authenticated payload was acquired. No IDs or validity intervals were inferred; no canonical assignments, price splices, raw-data edits or training promotion. Reopen only on receipt of dated provider/NEPSE security-master evidence and boundary corroboration. Full report: `docs/PRIORITY_98_HISTORICAL_SECURITY_MASTER_SOURCE_AUDIT_2026-11-26.md`.

### Current successor-ID policy implementation — 2026-11-26

- Added `docs/CURRENT_UNIVERSE_SUCCESSOR_ID_POLICY_2026-11-26.md` (commit `fe5bc0f926087d703e36d7be75047f678c724e11`) with the seven successor IDs and retired-alias rules.
- Added the owner-scope clarification to the historical source audit (commit `60457339d3944748576a7c00eba12ca98f79c569`).
- Added a regression test asserting all seven exact IDs, 2026-11-25 snapshot date, active status, OHLCV presence and absence of the ten former symbols from that snapshot (commit `95af5937646ae8eb5c572043b1fb2c9ed0030c53`).
- Updated this register with the owner decision (commit `3dd1e0ea312a65400553daa9501c648e02181f2d`).
- Test execution/CI result has **not** been confirmed in this work session. No price history was spliced and no canonical/training data was promoted.

### Current successor identity regression — verified 2026-11-26

- Focused GitHub Actions workflow `Historical identity regression`: **SUCCESS**, run [45824348509](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45824348509); **14 tests passed**, including the seven exact successor IDs, dated snapshot fields, retired alias exclusion, predecessor quarantine and no-splice guardrail.
- Full backend unit suite: **SUCCESS**, run [45824451318](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45824451318); **603 tests ran**, workflow conclusion success.
- Backend contract tests: **SUCCESS**, run [45824451415](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45824451415).
- Integrated evidence audit: **SUCCESS**, run [45824451368](https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45824451368).
- Initial full-suite failure was traced to DuckDB timezone support requiring `pytz`; added `pytz>=2024.1` to `backend/requirements.txt` (commit `c8ee30754e586f704886e9ed7bdd554928ed6384`). All three workflows above then passed on that commit.
- Historical predecessor IDs remain intentionally out of scope for current-universe scanning under the project-owner decision. No predecessor IDs were fabricated, no historical prices were spliced, and no historical continuity/backtest/training promotion is authorized.
- This completion does **not** close the separate release gates already listed in this register (including calendar, universe provenance/lifecycle, quarantined OHLC conflicts, floorsheet production safety, rights/corporate-action validation and other CI/release controls). Those remain open until separately evidenced.


## 2026-11-26 continuation — equity calendar and low-coverage lifecycle review

- Reviewed the equity session-calendar evidence inventory in `jaljala044/nepse-smc-data`: 225 positive-trade observations for sampled security ID 8108 (2025-11-25 to 2026-11-19), 41 explicit 2026 closure rows, and a 401-date bounded calendar. The calendar conservatively retains 26 candidate weekdays; those are not confirmed open sessions. Sample reconciliation found no overlap between the 225 observed dates and the captured 2025 holiday / 2026 closure dates. Evidence: [calendar review](https://github.com/jaljala044/nepse-smc-data/blob/main/reference/nepse_equity_session_calendar_evidence_review_2026-11-26.md), [reconciliation](https://github.com/jaljala044/nepse-smc-data/blob/main/reference/nepse_session_date_reconciliation_2026-11-26.md), [bounded calendar methodology](https://github.com/jaljala044/nepse-smc-data/blob/main/reference/nepse_canonical_session_calendar_2025-2026.md).
- The 281-symbol observed-date overlap audit is complete as a bounded proxy: mean 94.38%, median 99.11%, 26 symbols below 90%, 13 below 50%. This is not an expected-session completeness score because security 8108's sample is not a universal market calendar and symbol lifecycle/trade frequency vary. Evidence: [coverage report](https://github.com/jaljala044/nepse-smc-data/blob/main/reference/equity_observed_date_coverage_audit_2026-11-26.md).
- Added a lifecycle review for three low-overlap cases: PFL's 2026-07-10 to 2026-09-15 merger suspension/relisting window is corroborated by dated ShareSansar notices; BNL's 2024-12-17 suspension and 2024-12-18 release are documented but do not explain all sparse overlap; NLO's OHLCV archive has only 43 rows and ends 2026-09-30 despite a 2026-11-25 Merolagani bonus-share listing notice. No raw OHLCV was changed and no canonical/training promotion was made. Report commit: `bae0d967d40f73d0287e7fa65bfbf143eb6e6fea`; [low-coverage lifecycle review](https://github.com/jaljala044/nepse-smc-data/blob/main/reference/equity_low_coverage_lifecycle_review_2026-11-26.md).
- Remaining: obtain current NLO EOD/floorsheet and resolve archive freshness; investigate BNL's wider sparse history; validate the complete 281-equity universe/lifecycle; perform full row-level checks on both archives; reconcile invalid OHLC/cross-source conflicts, corporate actions, provenance and licensing. Calendar candidate weekdays must remain unpromoted until date-level evidence exists. Model training and production scanning remain blocked.


### NLO sparse-trading investigation — 2026-11-26

- Resolved the suspected NLO archive-staleness exception: 43-row trade-only NLO OHLCV has latest executed trade 2026-09-30 (volume 60), but Hamroshare and Sajilo report zero trades on 2026-11-25 and QuantNepal reports zero volume / unchanged carried-forward close on 2026-11-25 and 2026-11-26. Project 2026-11-25 EOD audit reports 356 traded securities; NLO is absent from the day's broker-summary and price-gap-fill rows. This supports sparse trading / no recent execution, not a proven collector outage. Confidence medium; no zero-volume OHLC bars fabricated.
- Current identity is NLO, security ID 198, active in 2026-11-25 snapshot. NLO excluded from BUY eligibility until repeated execution and adequate liquidity return. Carried-forward NPR 279.40 is not a fresh trade or executable price.
- Corporate-action conflict remains: ShareSansar reports 1,363,637 bonus units and a 20% bonus distribution for FY 2081/82, while ShareHub/Merolagani renderings show 145,725.36 units and inconsistent 15%/20% labels; Hamroshare lists a different FY 2082/83 15% bonus + 6.053% cash context. No adjustment factor or historical price rewrite authorized until primary listing notice, fiscal year, book-close date and quantity are reconciled.
- New report: [NLO sparse-trading vs archive-staleness review](https://github.com/jaljala044/nepse-smc-data/blob/main/reference/NLO_sparse_trading_vs_archive_staleness_review_2026-11-26.md), commit `1f0da79b67fcdac1e0b5adbd75e864bc8bede538`. Lifecycle review corrected in commit `4057f80aea03b22632407cb5232dc9fb36d8e6e3`.
- Next: investigate BNL's wider sparse history, then extend symbol-level trade/no-trade and OHLCV row validation across all 281 equities. Do not classify missing OHLCV rows as missing sessions without execution evidence.


### BNL sparse-history reconciliation — 2026-11-26

- BNL current identity: security ID 195, active in 2026-11-25 snapshot. Project OHLCV has 605 rows and ends 2026-11-19 (blob `01bd01a6e8242b7c0f07143b2164de981b2b7ab6`). NepView and Sajilo independently report a 2026-11-23 trade at NPR 14,600, volume 10; this trade is absent from the project file. This is a confirmed archive freshness/coverage gap, unlike NLO's no-trade explanation.
- ArthaKendra reports a further 2026-11-24 trade at NPR 14,600, volume 10, but this is single-source and remains provisional. Hamroshare and Sajilo report no trade on 2026-11-25. Do not add provisional rows to raw OHLCV.
- BNL is active but extremely illiquid; exclude from ordinary BUY eligibility until trade frequency, turnover and depth satisfy scanner liquidity criteria. 2024-12-17/18 suspension/release explains that event window only, not all historical coverage gaps.
- Report: [BNL sparse-history reconciliation](https://github.com/jaljala044/nepse-smc-data/blob/main/reference/BNL_sparse_history_and_missing_trade_reconciliation_2026-11-26.md), commit `eca287455d4825502948540dbc05c9f32523b167`. Lifecycle report updated in commit `3fef6b18f95f26ac93cb1ec85c5d4891e9eab22d`.
- Next: build a symbol-level reconciliation queue for all low-overlap equities, distinguishing executed trades, no-trade sessions, suspension/corporate-action intervals, and source/archive omissions. Require at least two independent records for trade-row promotion; keep unresolved rows quarantined.


### 26-symbol low-overlap triage — 2026-11-26

- Created a triage register separating the 26 below-90% overlap symbols into 3 reviewed cases (NLO, BNL, PFL), 12 later-start candidates requiring listing/first-trade date verification, and 11 mid-2026-start / low-overlap unresolved cases (including UNL, which warrants a separate older-history audit). The 225-date security-ID-8108 benchmark remains a screening proxy, not a universal expected-session denominator.
- Register: [equity low-overlap triage](https://github.com/jaljala044/nepse-smc-data/blob/main/reference/equity_low_overlap_triage_register_2026-11-26.md), final wording commit `3fd16a798c10598d5d19b92b73f156bec2936b58`.
- Updated the original observed-date audit to reflect NLO sparse trading and BNL's confirmed missing 23 Nov trade: commit `b8a3df878ae4be1a56ccc43ca08bf9654f31c860`.
- No raw OHLCV was modified. Next work is lifecycle verification for later-start candidates and per-symbol trade/no-trade evidence for remaining low-overlap names, then full OHLCV row/value checks across both repositories.


### BENH late-listing validation — 2026-11-26

- BENH's 7.11% overlap is explained by late listing/trading commencement: ShareSansar reports IPO shares listed 2026-10-13 and regular trading commencing 2026-10-14; ArthaKendra and Sun Securities show first executed OHLCV row on 2026-10-15 (O 273, H 313.9, L 273, C 313.9, V 90). The 14 October execution status remains to be checked. No dates before the security's trading commencement should count against its completeness.
- Report: [BENH listing and first-trade validation](https://github.com/jaljala044/nepse-smc-data/blob/main/reference/BENH_listing_and_first_trade_validation_2026-11-26.md), commit `a1f74d1d33ed82e43bffea2eba430c008805541e`.
- Triage register now has 4 reviewed cases and 11 later-start candidates pending verification; update commit `c29f62d8b42f37415eb9ce512110dce77ee3a742`.


### Later-start equity lifecycle validation — 2026-11-26

- Reviewed all 11 low-overlap later-start candidates against dated secondary listing/debut notices and first positive-volume rows in the pinned `nepse-history-starter` OHLCV archive.
- Nine align: SAPIL 2026-08-13; MEPDL 2026-08-12; ECL 2026-07-17; KAHL/SGHL 2026-07-02; SNORL 2026-06-26; TPKHL/YMHL 2026-06-22; SOPL 2026-06-08. Archive first positive-volume rows and volumes are recorded in the evidence report.
- APHL: published commencement 2026-06-09, archive first positive-volume row 2026-06-10 (110 shares). KHPL: published scheduled commencement 2026-05-25, Merolagani reports debut 2026-05-26, archive first positive-volume row 2026-05-26 (40 shares). Both one-session discrepancies remain quarantined pending floorsheet/date-level trade evidence; no automatic date normalization.
- Added [later-start lifecycle validation](https://github.com/jaljala044/nepse-smc-data/blob/main/reference/later_start_equity_lifecycle_validation_2026-11-26.md), commit `992f424c223d83373a80ce707b4b5cba8a23aba6`; updated [low-overlap triage register](https://github.com/jaljala044/nepse-smc-data/blob/main/reference/equity_low_overlap_triage_register_2026-11-26.md), commit `0c3359724d1507bc0ac345898a08f1c71e2838d6`.
- This resolves the *pre-commencement denominator issue* for nine symbols; it does not validate all expected sessions, independent contract-level execution, archive completeness after commencement, or OHLCV row quality. APHL/KHPL boundary checks remain open. No raw OHLCV was edited; no canonical/training promotion or BUY eligibility is implied.
- Next: validate listing/first-trade boundaries for the 11 mid-2026-start names (PCIL, SIPD, SKHEL, RLEL, SKHL, BJHL, SOHL, HFIN, SABBL, RSML) and perform dedicated UNL history/source coverage review; then run full row-level OHLCV checks across both repositories.


### Mid-2026 low-overlap equity archive boundary review — 2026-11-26

- Inspected first/last OHLCV rows for PCIL, SIPD, SKHEL, RLEL, SKHL, BJHL, SOHL, HFIN, SABBL, RSML and UNL in the pinned History Starter archive. All first rows have positive volume; this is archive evidence, not independent floorsheet verification.
- PCIL/SIPD first rows align with published 2026-04-10 commencement; SKHEL/RLEL align with Merolagani's reported first pre-open transactions on 2026-03-29. SKHL, BJHL, SOHL, HFIN, SABBL and RSML have first archive rows after published listing/scheduled commencement references and remain date-boundary exceptions pending trade evidence.
- UNL archive begins 2024-03-05 although the issuer is long-established; this is a dedicated historical source-coverage issue, not a listing date. A 2018 suspension/resumption notice does not explain the 2024 archive start.
- Added [mid-2026 boundary review](https://github.com/jaljala044/nepse-smc-data/blob/main/reference/mid_2026_low_overlap_equity_archive_boundary_review_2026-11-26.md), commit `386cd8bc15ca2633005d7d2e2f3216e9b4110e50`.
- No raw OHLCV edited, synthesized or normalized. No canonical/training promotion. Next: obtain dated trade evidence for six boundary exceptions; conduct dedicated UNL alternate-source/history audit; continue row-level OHLCV validation across both repositories.


### First-trade boundary reconciliation — APHL, KHPL and six mid-2026 equities — 2026-11-26

- APHL scheduled commencement was 2026-06-09, but Merolagani's dated first-trade report says no matching occurred that day and the first transaction matched on 2026-06-10; project archive first positive-volume row is 2026-06-10 (110 shares). This is a reconciled scheduled-vs-actual debut, not an archive omission.
- KHPL scheduled commencement was 2026-05-25, but Merolagani reports the first special pre-open transaction on 2026-05-26; project archive first positive-volume row is 2026-05-26 (40 shares). Scheduled date is not proof of execution.
- SKHL (2026-03-25), BJHL (2026-03-22), SOHL (2026-03-15), HFIN (2026-03-12), SABBL (2026-02-16), RSML (2026-02-16): project archive first positive-volume rows align with dated secondary debut/commencement evidence.
- Evidence report: https://github.com/jaljala044/nepse-smc-data/blob/main/reference/first_trade_boundary_reconciliation_2026-11-26.md (commit `7011860a405d2f047ff6c69af1053cd2e3ae094b`). Triage update `fb1384021a336d55e2faeb5b8b4e50994d3e6b42`; boundary review update `d8bca6a0b43135618ffe61587a48b1ad208e8712`.
- All eight reviewed boundaries now match actual first-trade/debut observations on available secondary evidence. This does not establish full daily archive completeness or exchange-authenticated contract-level provenance. No raw OHLCV changed, no synthetic rows, no canonical/training promotion.
- Next priority: dedicated UNL historical source-coverage audit, then reconcile remaining low-overlap symbols against symbol-specific executed-trade evidence and execute row-level OHLCV validation.
