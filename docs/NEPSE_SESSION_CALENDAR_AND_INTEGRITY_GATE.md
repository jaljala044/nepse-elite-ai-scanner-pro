# NEPSE historical session calendar and integrity gate

Status: implementation baseline; the full historical calendar is **not yet verified**.
This module intentionally refuses to infer a verified session from a weekday or an
OHLCV row. It provides the evidence-backed mechanism and a fail-closed row audit.

## Calendar contract

CSV columns: `date,status,source_id,evidence_uri,raw_evidence_sha256,published_at,retrieved_at_utc,verified_at_utc,scope,notes`. Raw evidence SHA-256, retrieval/verification UTC timestamps and affected scope are mandatory. Publication timestamp may be blank only when the source does not publish one; if present it must include a timezone.
Accepted statuses are `verified_open`, `verified_closed`, `verified_exceptional_open`, and `verified_exceptional_closed`. Exceptional-open dates are accepted by the OHLCV gate only when the date-specific evidence row is present. Every explicit row must
carry a source identifier, evidence URI and verification timestamp. Conflicting or
duplicate date rows fail calendar loading. Keep the source notice/document and its
hash in the evidence archive; do not cite a general public-holiday list as proof that
NEPSE actually closed.

The schedule regimes are candidate hints only:
- Through 2022-05-14: Sunday–Thursday regular-session candidates; Friday odd-lot excluded; Saturday closed.
- 2022-05-15 through 2022-06-14: temporary Monday–Friday candidates; Saturday/Sunday closed.
- 2022-06-15 through 2022-09-16: temporary Sunday–Friday candidates; Saturday closed.
- 2022-09-17 through 2026-04-05: Sunday–Thursday candidates; Friday/Saturday excluded.
- From 2026-04-06: Monday–Friday candidates; Saturday/Sunday excluded.

The 2022 transition from Sunday–Thursday to Monday–Friday was announced for the two-day weekend beginning 15 May; the next schedule change restored Sunday–Friday trading from 15 June. This makes 14 May the end of the first regime, not 5 May. Sources: [Nepal News, 29 April 2022](https://english.nepalnews.com/s/business/nepse-to-open-on-friday/), [Khabarhub, 13 June 2022](https://english.khabarhub.com/2022/13/257305/),
[The Himalayan Times, 13 June 2022](https://thehimalayantimes.com/business/nepse-to-operate-six-days-a-week-effective-june-15),
[ShareSansar, 16 June 2022](https://www.sharesansar.com/newsdetail/from-ashad-shares-will-be-traded-six-days-a-week-sunday-friday-2022-06-16),
and [ShareSansar, 4 September 2022](https://www.sharesansar.com/newsdetail/nepse-decides-to-close-trading-on-fridays-from-ashoj-2022-09-04).
The 2026 transition is reported by [The Himalayan Times, 8 April 2026](https://thehimalayantimes.com/business/nepse-shifts-to-mondayfriday-trading-week)
and [ShareSansar, 8 April 2026](https://www.sharesansar.com/newsdetail/nepal-stock-exchange-opens-monday-to-friday-under-new-government-timings-2026-04-08).
These sources establish schedule-regime changes, not the actual open/closed status
of every historical date. Daily closures and exceptional sessions still need dated
NEPSE evidence or independently verified exchange trading records.


## Source coverage matrix (inventory metadata only)

Build a date-by-date matrix from one or more JSONL manifests. Run from `backend/`:

```bash
python build_calendar_coverage_matrix.py \
  --manifest ../artifacts/source-manifests/urekmazino69_Nepse-floorsheet-and-indices_<revision>.jsonl \
  --calendar ../data/reference/nepse_session_calendar.csv \
  --start-date 2024-01-02 \
  --end-date 2026-08-26 \
  --output ../data/reports/nepse-calendar-coverage-matrix.json
```

Repeat `--manifest` for each independent source. The matrix records source file
counts and bytes by date, explicit calendar evidence, schedule-candidate notes,
and files found on dates explicitly marked closed. It rejects duplicate
source/path manifest entries and malformed dates. It does not treat file presence
as proof of a session, nor a weekday candidate without a file as proof of a missing
session. Review all closure conflicts and unverified candidate dates against dated
NEPSE notices or verified exchange records.

## OHLCV gate

Run from `backend/`:
```bash
python -m app.session_calendar --calendar ../data/reference/nepse_session_calendar.csv \
  --input ../data/raw/ohlcv --output ../data/reports/ohlcv-session-integrity.json
```
Every row must parse, have valid OHLC bounds and non-negative volume, and map to an
explicit `verified_open` calendar date. Duplicate symbol/date keys are quarantined,
including exact duplicates; conflicting values are never resolved by overwrite.
Original files remain untouched. Each file and calendar is SHA-256 fingerprinted.
A report pass is limited to the supplied files and explicit evidence; it does not
prove all expected archive files were supplied.

## Important limits / remaining evidence work

- Do not use Nepal Rastra Bank's bank-holiday calendar as a substitute for NEPSE's
  own notices. Government holidays may be modified by the exchange.
- Do not promote weekday candidates, repeated candles, filenames, or inferred dates.
- This gate does not yet perform cross-source reconciliation of the 25 differing
  Jaljala OHLCV files, corporate-action reconciliation, or source-completeness proof.
- Full calendar completion requires acquisition and review of dated NEPSE notices /
  exchange trading evidence for the entire target period, including exceptional
  openings, closures, schedule changes and historical gaps.
- Full data-integrity completion additionally requires the raw archives to be staged
  and all rows to be audited. Until those are done, canonical import and predictive
  intelligence remain blocked.

## 2026 calendar evidence review queue

A separate lead register now exists at
`data/reference/nepse_calendar_evidence_leads_2026.csv`. It records candidate
closure dates and source quality without promoting any row into the canonical
session calendar.

The first reviewed leads are:

- **21 Sep 2026:** ShareSansar reports NEPSE suspended trading after a Data Hub
  outage and resumed on 22 Sep. This is an exceptional exchange suspension, not
  a routine public holiday.
- **19–23 Oct 2026:** ShareSansar reports NEPSE closed Monday–Friday for Dashain.
- **9–12 Nov 2026:** ShareSansar reports NEPSE closed for Tihar, with trading
  resuming Friday 13 Nov.
- **16 Nov 2026:** ShareSansar's 13 Nov market report says the exchange would be
  closed Monday for Chhath and resume Tuesday 17 Nov.
- **28 Aug and 4 Sep 2026:** the Nepal Rastra Bank 2083 holiday list identifies
  government holidays, but this alone is not proof of a NEPSE closure.

These are secondary-source leads and/or government holiday candidates. The
canonical calendar remains empty until dated primary NEPSE notices or equivalent
exchange records are captured, preserved, hashed and reviewed. Do not mark any
candidate date verified solely from this lead file.

## Independent index/OHLCV date cross-check — implementation

The project now includes `backend/build_market_date_crosscheck.py`. It pins the
SocrateAI repository to a commit, inventories dated adjusted index CSVs, fetches
the most recent 120 daily index files, and validates the single
`NEPSE_index` row's date, numeric fields and OHLC bounds. It joins those dates
to date-level symbol coverage emitted by the Jaljala OHLCV audit. It can also
join floorsheet manifests when supplied. It labels results as observed-session
candidates only; it does not write the verified session calendar.

Initial repository-tree inspection on 2026-11-24 found **5,368 dated adjusted
index CSVs**, spanning **2003-07-17 to 2026-11-24**. The latest 120 distinct
index-file dates span **2026-05-18 to 2026-11-24**. There are **110** such
index-file dates from 2026-06-03 onward. This is an index-source candidate
window, not a claim of 120 exchange-certified sessions.

The index archive has no dated adjusted index files for the following reported
closure/suspension candidates inspected so far: **2026-09-21; 2026-10-19 to
2026-10-23; 2026-11-09 to 2026-11-12; and 2026-11-16**. Their absence is
consistent with the published closure reports but is not itself primary proof.
A valid 2026-11-24 adjusted index file was inspected and contains exactly one
`NEPSE_index` row; the automated validator now checks the full latest-120
window rather than extrapolating from this one sample.

The OHLCV audit report now emits per-date unique-symbol coverage for each pinned
source, allowing a direct date-level comparison rather than relying only on
per-symbol first/last dates. The OHLCV audit still has known invalid rows and
cross-source conflicts, so this date comparison is a coverage diagnostic, not
a data-quality pass.

CI runs the new validator and uploads
`market-date-crosscheck.json` alongside the OHLCV audit artifacts. A failed
OHLCV quality gate does not suppress the independent date diagnostic; the
cross-check runs when the audit report exists.

## First 120-index-date cross-check findings (pinned source snapshot)

An initial automated run against SocrateAI commit
`cfa92493e93211c7019a5cd0b2cbe7d400d9c4e3` selected 120 dated adjusted-index
files from **2026-05-18 through 2026-11-24**. The first strict validator accepted
117 NEPSE index rows and flagged three files for row-level anomalies. The
anomaly-aware validator now preserves every NEPSE row and distinguishes
duplicate and OHLC-bound problems rather than discarding them.

The three source anomalies were inspected directly:

- **2026-06-01:** two identical NEPSE_index rows in the same CSV. Preserve both
  and classify as an exact duplicate; do not silently deduplicate source data.
- **2026-07-03:** the single NEPSE_index row has high 2673.1493 below open
  2673.15 by 0.0007. Preserve the exact values and flag the OHLC-bound anomaly;
  no tolerance-based correction is applied.
- **2026-07-07:** two differing NEPSE_index rows are present. They disagree in
  high and volume, among other precision-level fields. Preserve both and classify
  as a conflicting duplicate; neither is selected as canonical.

Date coverage in the same 120-file window:

- Jaljala stock OHLCV: both repositories have files on **117** dates; one
  repository only on **2026-07-24**; neither has a file on **2026-11-23** or
  **2026-11-24**. The archive snapshots audited in this run end at 20 Nov 2026,
  so the last two dates are source freshness gaps, not evidence of exchange
  closure.
- Floorsheet filename manifests: both SocrateAI and SamirWagle have files on
  **112** dates. SocrateAI alone has files on **8** dates:
  2026-08-24, 2026-08-26, 2026-10-05, 2026-11-06, 2026-11-13,
  2026-11-17, 2026-11-18 and 2026-11-23. These are source-coverage differences,
  not proof that Samir is incomplete or that the SocrateAI files are complete.
- The manifest-only step did not download or validate any raw floorsheet rows.

The audit still reports 1,331 invalid SMC OHLC rows, 8 cross-source symbol/date
conflicts, 196,542 repeated-adjacent-date flags, and 25 differing common-path
Git blob identities. The two repositories' row-level date coverage is useful
for identifying freshness gaps, but these outstanding exceptions keep the
canonical OHLCV integrity gate closed.

Artifact containing the initial reports and the two floorsheet manifests:
GitHub Actions run 45408208927, artifact ID 14926338543. The report is pinned to
the source commit above; subsequent source changes require a new inventory and
audit rather than silently reusing this snapshot.

### Anomaly-aware rerun

The validator was updated to retain duplicate NEPSE_index rows and distinguish
exact duplicates, conflicting duplicates, and OHLC-bound errors. Its rerun
against the same pinned index commit produced:

- 120 index files observed; 117 single-row clean NEPSE index records.
- Three row-anomaly dates: 2026-06-01 (exact duplicate), 2026-07-03 (high below
  open by 0.0007), and 2026-07-07 (conflicting duplicate).
- Zero index-file download errors.
- The two floorsheet manifests were successfully regenerated in manifest-only
  mode and joined to the date matrix.

The backend test workflow passed **70 tests** at commit
`4ac2cdd92d6fbce99f0a3100407c723e30586697`. The full archive-audit workflow
remains failed by design while the underlying OHLCV gate and the three index-row
anomalies remain unresolved; its report artifact was still uploaded. Latest
anomaly-aware run: 45408479059, artifact ID 14925853863. This is a diagnostic
pass, not a calendar-integrity pass.

## Third-source index history: YONEPSE official-API mirror

A further independent archive was identified and pinned for cross-checking:
`Shubhamnpk/yonepse`, commit
`1bfa798e84c7170f826e473e7e1ec3957c81966c`. Its source code documents recent
index history as fetched from NEPSE's
`/api/nots/index/history/{id}` endpoint, with index ID **58** for NEPSE. Its
monthly shards contain NEPSE plus 16 sub-index series.

Important provenance limitations:

- This is a third-party mirror, not a signed NEPSE publication.
- Its builder notes that the upstream endpoint ignores the requested date range
  and returns roughly the trailing year; it filters the returned rows locally.
- The mirror's scraper constructs its NEPSE client with TLS certificate
  verification disabled. This weakens the chain of custody; use as corroboration,
  not as the sole canonical source.
- The mirror manifest currently marks 2026-11-24 as `provisional`; its NEPSE
  close value is zero in that day's shard. The latest row must not be treated as
  a final daily close.
- In the source schemas, YONEPSE maps upstream `turnoverValue` to its
  `turnover` field, while SocrateAI's index CSV labels the corresponding
  monetary total as `volume`. The comparison script records this mapping
  explicitly and does not compare it to YONEPSE share volume.

New script: `backend/crosscheck_index_history_yonepse.py`. It pins the mirror
commit, validates the monthly date-index envelope, preserves all values, skips
numeric comparison for the provisional latest date, and records exact or
differing OHLC/turnover fields against the SocrateAI rows. It never chooses a
canonical source or corrects a value. CI runs this comparison and uploads
`yonepse-index-crosscheck.json` alongside the other audit reports.

YONEPSE's README advertises an MIT repository license, but its sources page
states that the underlying market data remains the property of the respective
owners. The code license is therefore not treated as a data-reuse or
redistribution grant. This project currently uses the mirror only as a
provenance-tracked private comparison source; no YONEPSE raw dataset is
repackaged or redistributed.

### YONEPSE mirror comparison results — 120-date window

The first automated comparison against the pinned YONEPSE mirror commit
`1bfa798e84c7170f826e473e7e1ec3957c81966c` completed for all 120 selected
dates, with no monthly-shard download errors:

- **116** dates were numerically compared.
- **3** SocrateAI dates were withheld from numeric comparison because their
  source rows were anomalous: 2026-06-01, 2026-07-03 and 2026-07-07.
- **1** latest date (2026-11-24) was marked provisional by YONEPSE and excluded
  from final-value comparison.
- Among the 116 comparable dates, close matched exactly on **111** dates and
  differed on 5. Open matched exactly on 57, high on 10, and low on 7.
- The mapped turnover comparison had **zero exact matches**. Its median absolute
  difference was about NPR 89.3 million and maximum about NPR 4.86 billion.
  This is a material unresolved source/schema discrepancy; no turnover value is
  selected as canonical.
- High and low often differ by small precision amounts, but some differences
  are larger (maximum high difference 1.63 index points; maximum low difference
  0.97). Exact source values remain preserved.

This comparison does **not** establish that YONEPSE is correct or SocrateAI is
wrong. The YONEPSE publisher mirror is third-party, older monthly shards show
their own update timestamps, and its scraper's TLS-verification setting weakens
the source chain. The high close agreement is useful corroboration, but the
turnover/high/low differences remain unresolved. Latest report artifact:
run 45409066255, artifact ID 14927261450.

The YONEPSE mirror's monthly-shard timestamps also differ: May–August 2026
shards report `updatedAt=2026-10-11T00:45:08+05:45`, September reports
`2026-11-13T12:02:46+05:45`, and October/November report
`2026-11-24T12:04:02+05:45`. The comparison report now records each shard's
update timestamp, date count, date span and SHA-256. A shard's update timestamp
is publisher metadata, not proof of the original exchange publication time.

## Session-candidate register export

The audit workflow now exports
`data/reports/nepse-session-candidates.csv` from the two cross-check reports.
It joins SocrateAI index-row status, YONEPSE comparison/finality, OHLCV symbol
coverage and floorsheet manifest coverage for each date. Every row is explicitly
marked `not_verified_primary_exchange_evidence_missing`; this is a review
register, not the canonical calendar and not permission to treat all 120 dates
as verified trading sessions. The CSV is uploaded with the audit artifact.

The first exported candidate register contains 120 dates from 2026-05-18 through
2026-11-24: 116 observed but unverified candidates, three SocrateAI row-anomaly
dates, and one YONEPSE provisional latest date. The CSV is in workflow run
45409684161, artifact ID 14927377869. It records zero verified calendar dates
because no primary NEPSE date evidence has yet been admitted.

## Public NEPSE notice endpoint access test

The NEPSE client source identifies the general-notice endpoint as
`GET https://www.nepalstock.com/api/web/notice/`. We tested exactly one
unauthenticated HTTPS GET with certificate verification enabled and no redirects,
cookies, token generation, or alternate identity. On 2026-11-24 the endpoint
returned **HTTP 401**, content type `text/html;charset=UTF-8`, 87 response bytes,
SHA-256
`ee73a9a8cdc37c9dc5df7798e6ee814f7a2270a90c723dd64dd379790fd1c298`.
The raw response and probe report are preserved in GitHub Actions run
45410873060, artifact 14928081364.

The endpoint is therefore not publicly readable without authentication from this
runner. We will **not** reverse engineer its token generation, bypass the access
control, or reuse the YONEPSE mirror's TLS-verification-disabled approach to
claim primary provenance. Continue with openly accessible exchange publications,
search-indexed notice copies, and independently corroborated trading records.
The calendar remains unverified until evidence is archived and reviewed.

A second report of the 2026-09-21 suspension was found at Khabarhub. It explicitly
attributes the suspension to a NEPSE notice and identifies Rule 21(1), supporting
the event lead but not replacing the missing original notice PDF:
https://english.khabarhub.com/2026/21/568606/

## Full weekday-gap reconciliation for the 120-index-date window

The pinned SocrateAI index inventory spans **2026-05-18 to 2026-11-24**.
There are 137 Monday–Friday dates in this interval. Exactly 120 dates have a
dated index file; the other **17 weekday dates** are:

- **2026-05-28 and 2026-05-29:** Bakar Eid and Republic Day; ShareSansar
  reported both NEPSE closures.
- **2026-08-28:** Janai Purnima; ShareSansar reported NEPSE closure.
- **2026-09-04:** Krishna Janmashtami; ShareSansar reported NEPSE closure.
- **2026-09-08:** Gen Z Sahid Diwas; ShareSansar reported NEPSE closure.
- **2026-09-21:** Data Hub outage; Khabarhub reported NEPSE's suspension under
  Rule 21(1), and NEPSE resumption on 22 September was separately reported.
- **2026-09-25:** Indra Jatra; ShareSansar reported NEPSE closure.
- **2026-10-19 through 2026-10-23:** Dashain closure; ShareSansar reported
  NEPSE closed for the Monday–Friday block.
- **2026-11-09 through 2026-11-12:** Tihar closure; ShareSansar reported NEPSE
  closed and resumption on Friday 13 November.
- **2026-11-16:** Chhath-related closure; ShareSansar reported market closure
  and resumption on 17 November.

This is a strong coverage-consistency check: every missing weekday in the
candidate window now has a specific NEPSE-closure report, and the index archive
contains a dated file for every other weekday. It is **not yet a primary-source
calendar pass**: these are secondary reports of NEPSE announcements, and the
original exchange notices have not yet been archived. All 17 dates remain in
the evidence-lead register as unverified; none is written to the canonical
calendar. Relevant reports include:
https://www.sharesansar.com/newsdetail/nepse-to-remain-closed-for-two-days-as-government-declares-public-holiday-for-bakar-eid-and-republic-day-2026-05-28
https://www.sharesansar.com/newsdetail/nepse-to-remain-closed-today-govt-declares-public-holiday-on-the-occasion-of-gen-z-sahid-diwas-2026-09-08
https://www.sharesansar.com/newsdetail/nepse-to-remain-closed-today-govt-declares-public-holiday-on-the-occasion-of-indra-jatra-2026-09-25
https://www.sharesansar.com/newsdetail/nepse-to-remain-closed-today-for-janai-purnima-holiday-2026-08-28
https://www.sharesansar.com/index.php/newsdetail/nepse-to-remain-closed-on-friday-govt-declares-public-holiday-on-the-occasion-of-krishna-janmashtami-2026-09-04

The YONEPSE monthly-shard metadata also shows that the May–August shards
were last updated on **2026-10-11**, the September shard on **2026-11-13**, and
the October/November shards on **2026-11-24**. These are archive update
timestamps, not original exchange publication timestamps. They reinforce the
rule that this mirror is corroboration only and cannot establish point-in-time
availability of historical data.

## SamirWagle floorsheet date-provenance finding

The pinned SamirWagle scraper source
(`SamirWagle/Nepse-All-Scraper`, commit
`144cecb36f110bedb741f5d147c7857cdb24c958`,
`scraper/core/floorsheet.py`) assigns
`dt_date.today()` to every scraped floorsheet row and names the output file
`floorsheet_<today>.csv`. It scrapes the current Merolagani floorsheet page;
it does not accept a historical trade date for that retrieval.

Consequences for this audit:

- Its dated file manifest is a **capture-date inventory**, not reliable proof
  that a transaction occurred on the filename date.
- The pinned manifest contains files on **12 of the 17 weekday closure dates**
  identified above (May 28–29, Aug 28, Sep 4, Sep 8, Sep 21, Sep 25, and
  Oct 19–23). This is consistent with capture-date relabeling and makes these
  filenames unsafe as session evidence.
- The raw files have not been downloaded or row-validated; their contents are
  not assumed to be stale, duplicated, or complete without inspection.
- Exclude SamirWagle filename dates from calendar proof and from point-in-time
  broker-flow history until actual contract dates are independently verified
  from the transaction records and source semantics.

The acquisition pipeline therefore keeps SamirWagle as a discovery lead only;
it does not promote these dated filenames into canonical trade dates. Its
educational-use description also does not establish a separate data-reuse grant.

### Combined 137-weekday evidence register generated

The workflow now merges the 120 index-date candidates with the 17 reported
weekday closure leads into a single review register:
`data/reports/nepse-session-candidates.csv`.

Pinned output from workflow run **45411800853** contains **137 dates**:
- 116 observed-session candidates with a structurally valid SocrateAI index row
  and a non-provisional YONEPSE comparison;
- 3 observed dates with unresolved SocrateAI row anomalies;
- 1 latest provisional date (2026-11-24);
- 17 reported closure candidates, all still explicitly unverified.

The register has separate fields for closure-event descriptions, source IDs,
evidence levels and evidence URLs. A closure lead that overlaps an observed
index row is classified as a conflict rather than silently accepted. Every row
continues to say
`not_verified_primary_exchange_evidence_missing`; **verified calendar rows = 0**.

The evidence lead file now contains NEPSE-specific secondary reports for Janai
Purnima (2026-08-28) and Krishna Janmashtami (2026-09-04), in addition to the
government holiday list. This improves corroboration but does not replace the
original NEPSE notices.

## Per-security OHLCV coverage report

`backend/build_security_coverage_report.py` calculates expected and observed rows per in-scope security using an explicit security-universe CSV, the evidence-backed session calendar, and normalized OHLCV CSVs with `source_id,symbol,date` columns. Each publisher receives a separate coverage report; publishers are never combined into one coverage ratio. It reports equity and mutual-fund counts separately, per-security expected sessions, missing sessions, duplicate rows, observations on verified closures, and observations on dates without calendar evidence.

Example (run from `backend/`):

```bash
python build_security_coverage_report.py \
  --universe ../data/reference/security_master_snapshot.csv \
  --calendar ../data/reference/nepse_session_calendar.csv \
  --input ../data/normalized/ohlcv-source-a.csv \
  --start-date 2025-11-25 --end-date 2026-11-25 \
  --output ../data/reports/security-coverage.json
```

The universe CSV must explicitly provide `security_id,symbol,instrument_type,valid_from,valid_to,target_in_scope`. Only explicit `equity` and `mutual_fund` classes are accepted in the in-scope rows. The expected-session denominator includes only verified normal or exceptional open dates that fall within the security's effective interval. Unknown dates are excluded and reported separately; this tool does not infer missing sessions or authorize canonical promotion.

## Source-specific coverage and universe validation

The per-security coverage input now requires `source_id,symbol,date`. Each source is reported independently in `source_specific_reports`; when more than one publisher is supplied, the top-level combined coverage ratio is null to prevent double-counting. The report is diagnostic only.

A target universe snapshot can be validated with `app.universe_snapshot.validate_universe_snapshot`. It requires an official NEPSE/SEBON HTTPS URL, raw payload SHA-256, snapshot date, UTC retrieval timestamp, stable security IDs, explicit instrument type/status, effective dates and boolean target membership. The default target count is exactly 281 active equities and 47 active mutual funds; tests can pass smaller expected counts. The validator never infers instrument class and returns `promotion_allowed=false`.

## Official notice capture utility

Run from `backend/`:

```bash
python capture_official_notice.py \
  --url 'https://www.nepalstock.com.np/api/nots/security/fetchFiles?fileLocation=...' \
  --source-id nepse-notice-unique-id \
  --published-at 2026-04-08T10:00:00+05:45 \
  --output-dir ../data/evidence/notices
```

Only HTTPS NEPSE/SEBON hosts and approved redirect hosts are accepted. The utility saves raw response bytes content-addressed by SHA-256 and a metadata JSON with URL, retrieval time, response headers and byte count. It deliberately does not parse the notice or write a calendar row; human review is mandatory.

## Broker control-total reconciliation

`app.broker_aggregation.reconcile_source_control_totals` reconciles buyer/seller party observations against source-date control totals. It counts a contract's gross amount and quantity once only when exactly one buy and one sell observation agree; missing sides or conflicting amounts/quantities are reported as anomalies. Use source-provided control totals; do not substitute calculated totals as if they were independent source controls.

## Read-only training readiness CLI

Run from `backend/`:

```bash
python evaluate_training_readiness.py \
  --universe-report ../data/reports/universe-validation.json \
  --session-reports ../data/reports/session-evidence.json \
  --provenance-reports ../data/reports/source-provenance.json \
  --ohlcv-report ../data/reports/ohlcv-integrity.json \
  --broker-report ../data/reports/broker-identity.json \
  --point-in-time-report ../data/reports/point-in-time-audit.json \
  --corporate-action-reviewed \
  --holdout-protocol-id walk-forward-v1 \
  --historical-coverage 0.99 \
  --evidence-snapshot-id evidence-snapshot-2026-11-25 \
  --output ../data/reports/training-readiness.json
```

The CLI is read-only. Missing evidence yields explicit blockers and a nonzero exit code; it never writes canonical tables or starts training. A passing software test suite is not a substitute for passing real-source evidence.

## Source inventory, calendar reconciliation and adjustment basis

- `backend/audit_source_evidence_inventory.py` reads JSONL manifest rows (`source_id,path,sha256`, optional `local_path`) and verifies that each raw object exists under the declared raw root and matches its pinned SHA-256. Missing objects, hash mismatches, duplicate manifest keys and path escapes are reported; no repair or promotion occurs.
- `backend/build_calendar_coverage_matrix.py` compares source-date manifests against explicit calendar evidence. It flags source files on verified closed dates, source files on unverified dates, and verified open dates without source files. It does not infer session status from weekday patterns or file presence.
- `backend/audit_ohlcv_adjustment_basis.py` requires each normalized row to declare `adjusted`, `unadjusted` or `unknown`, then detects mixed bases within a source/security and cross-source basis differences. It never applies adjustment factors; corporate-action evidence must be reviewed separately.
- `backend/report_broker_identity_coverage.py` reports broker mapping coverage by date/security/side using both party-observation counts and gross-amount denominators, retaining unresolved rows.

## Integrated evidence audit workflow

`.github/workflows/integrated-evidence-audit.yml` runs the backend regression suite, then executes registry validation, calendar evidence validation, raw-source inventory, source-specific OHLCV daily reconciliation, per-security coverage, floorsheet-window row audit and broker identity coverage when their required evidence inputs are present. Missing inputs are recorded as skipped rather than treated as passes. The workflow always writes a readiness report and uploads the artifacts. It never promotes canonical data or starts model training.

## Raw source inventory and cross-source adjustment controls

- `backend/audit_source_evidence_inventory.py` validates JSONL source-object manifests against raw files under a pinned raw root. It checks path containment, existence and SHA-256 and reports missing or mismatched objects without repair.
- `backend/build_calendar_coverage_matrix.py` now distinguishes (a) files on verified closures, (b) files on dates with no calendar evidence and (c) verified open dates with no source files. The matrix remains an observation reconciliation, not a session classifier.
- `backend/audit_ohlcv_adjustment_basis.py` flags unknown, mixed and cross-source adjusted/unadjusted basis. It never modifies OHLCV prices.
- `backend/report_broker_identity_coverage.py` uses source-hashed input and reports verified/unresolved party observations and gross amount coverage by date/security/side.
- `backend/reconcile_broker_control_totals.py` persists immutable input-hashed party/control comparisons; contract gross totals are counted once only when buyer/seller observations agree.

The integrated workflow runs available registry, calendar, source inventory, calendar matrix, OHLCV daily totals, adjustment-basis, per-security coverage, floorsheet-window, broker identity and readiness audits. If required inputs are absent, it writes explicit `skipped_missing_input` status files. A successful workflow means the orchestration and tests completed; it does not mean missing datasets have been verified.

## Additional validation gates added in priorities 41–60

- Per-security OHLCV coverage reports source files by SHA-256 and byte count, exposes unknown symbols, and explicitly checks the required 281-equity / 47-mutual-fund target count. Excluded instrument classes can remain in the reference universe but cannot be target members.
- Calendar evidence timestamps must be chronologically consistent: publication <= retrieval <= verification. Calendar claims must have nonblank scope and unique nonblank captured source IDs.
- Point-in-time snapshots report missing `available_at` records separately from future records excluded after the decision cutoff.
- Floorsheet column mappings accept exactly the supported normalized fields and distinct, nonblank source-header names. OHLCV reconciliation rejects duplicate/unsupported headers, extra row cells, impossible OHLC ranges and malformed daily control totals.
- Corporate-action records require source tier, typed ex-date and ISO timestamp strings, and finite positive decimal factors. As-known reports preserve visible provisional/disputed/cancelled records as exclusions rather than reporting a misleading all-confirmed state.
- Walk-forward evaluation validates ISO dates, exact binary outcomes and finite [0,1] probabilities before fold construction. Footprint features reject invalid prices/volumes and duplicate security sessions; market breadth excludes and separately reports symbols outside the supplied target universe.

All outputs remain descriptive/audit-only. These guards do not establish exchange calendar completeness, source rights, universe membership or predictive performance.


## 2026 closure-evidence triage — 2026-11-25

This review advances the 2026 evidence queue but does **not** populate the
canonical calendar. The primary exchange notices have not yet been captured
as immutable raw evidence with SHA-256 and review timestamps.

### Five checks completed

1. **Government-holiday context checked against the Nepal Rastra Bank 2083
   holiday PDF.** It lists (among others) Bakar Eid 28 May, Republic Day
   29 May, Rakshabandhan 28 August, Krishna Janmashtami/Gaura 4 September,
   Indra Jatra 25 September, Dashain 17–23 October, Tihar 8–12 November and
   Chhath 15 November. This is a banking/government holiday list, not a
   NEPSE-specific trading calendar. It is context only.
2. **NEPSE-specific secondary reports cross-checked for 2026 closures.**
   ShareSansar reports NEPSE closed 28–29 May for Bakar Eid/Republic Day,
   8 September for Gen Z Sahid Diwas, 25 September for Indra Jatra,
   19–23 October for Dashain, 9–12 November for Tihar, and 16 November
   for Chhath. These remain secondary evidence leads until the underlying
   dated NEPSE notice or equivalent exchange record is archived.
3. **Exceptional operational suspension kept distinct from a holiday.**
   The 21 September Data Hub outage is an operational suspension lead, not
   a recurring holiday. It must be represented as an exceptional closure
   only after the specific exchange notice is archived and verified.
4. **Weekday regime cross-checked.** The schedule helper and this gate agree
   on the published candidate regimes: Sunday–Thursday through 5 April 2026,
   Monday–Friday from 6 April 2026. Weekday eligibility is still only a
   candidate; it does not establish that trading occurred.
5. **Fail-closed promotion rule rechecked in code.** The calendar loader
   accepts only explicit `verified_open`, `verified_closed`,
   `verified_exceptional_open`, or `verified_exceptional_closed` rows and
   requires source ID, evidence URI, raw evidence SHA-256, UTC retrieval and
   verification timestamps, and scope. The OHLCV audit quarantines every
   row whose date is not explicitly verified open. Secondary reports and
   government holiday lists cannot pass this gate by themselves.

### Reviewed public evidence

- Nepal Rastra Bank, *List of Holidays to be effective from 2026/04/14 to
  2027/04/13*: https://www.nrb.org.np/contents/uploads/2026/03/Holiday-List-2083-English.pdf
- ShareSansar, 28 May 2026 NEPSE closure report:
  https://www.sharesansar.com/newsdetail/nepse-to-remain-closed-for-two-days-as-government-declares-public-holiday-for-bakar-eid-and-republic-day-2026-05-28
- ShareSansar, 8 September 2026 Gen Z Sahid Diwas closure:
  https://www.sharesansar.com/newsdetail/nepse-to-remain-closed-today-govt-declares-public-holiday-on-the-occasion-of-gen-z-sahid-diwas-2026-09-08
- ShareSansar, 17 October 2026 Dashain closure:
  https://www.sharesansar.com/index.php/newsdetail/nepse-to-remain-close-to-mark-holiday-on-the-occasion-of-dashain-festival-2026-10-17
- Existing evidence-lead register:
  `data/reference/nepse_calendar_evidence_leads_2026.csv`

### Disposition

No 2026 closure lead has been promoted to the canonical calendar in this
review. No raw notice PDF or NEPSE-hosted announcement was archived and
hashed here, so there are no new evidence-complete calendar rows. The
calendar remains blocked. Next evidence task: obtain the original NEPSE
notice documents (not just article summaries), preserve their exact bytes,
compute SHA-256, and independently review each date/scope before adding
verified calendar rows.
