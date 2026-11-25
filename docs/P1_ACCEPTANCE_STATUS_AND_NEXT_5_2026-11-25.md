# P1 acceptance status and next five execution tasks

Updated: 2026-11-25

## Decision

P1 (historical data integrity) is **not complete**. The software controls and CI
orchestration are substantially implemented and now pass, but the real-source
evidence needed to certify the canonical history is absent or unresolved. P1
must remain active; P2 training/market-intelligence promotion remains gated.

## Verified software and CI results

The following changes were pushed at commit
`5c6269d90b2f94c0dc4bcb34b35a3556d460f077`:

- Fixed two malformed CSV fixtures in
  `backend/tests/test_ohlcv_reconciliation.py`. The fixtures had literal
  backslash-n text rather than line breaks. The production parser was correct;
  the tests were wrong.
- Re-fetched the test file from GitHub and verified the fixtures contain
  actual newline escapes in Python source.
- GitHub Actions run `45614983067` (backend-tests): **532 tests passed**.
- GitHub Actions run `45614983156` (backend contract tests): **532 tests passed**.
- GitHub Actions run `45614983065` (integrated evidence audit): **532 tests
  passed**, audit orchestration completed, and artifact uploaded.
- GitHub Actions run `45614983465` (historical data integrity): focused
  collector, coverage-matrix and OHLCV-reconciliation tests passed; pinned
  Hugging Face inventory completed; coverage report uploaded.

These results verify software behavior for the tested paths. They do not prove
that all historical source data is present, accurate, licensed or exchange
verified.

## Inventory artifact actually inspected

Artifact: `nepse-historical-data-audit`
- Run: `45614983465`
- Artifact ID: `15021448665`
- SHA-256: `fd732de784f7fbcd42d63c45201bb1688b1efc146ba1a5a15d1ebb4a60cb6339`
- Inventory mode: metadata-only; no raw data files downloaded.

Pinned inventories:
- `urekmazino69/Nepse-floorsheet-and-indices`, revision
  `11ef83a9c3cdbe78112f0245451cdc52bdb1a8f0`: 7,032 files
  (603 floorsheet files and 6,429 index files), listing and inventory complete.
- `AnkitSanjyal/nepse-market-data`, revision
  `a05d0b4f7693b06d6c43d6003253e1ff9dedd357`: 312 files across the
  configured dataset groupings; listing and inventory complete.

The associated candidate coverage report contains 198 calendar dates, all
`candidate_unverified`; confirmed sessions = 0. All dated files in the
inventory therefore remain unverified against an authoritative session
calendar. Inventory completeness means the repository listing was complete,
not that the underlying source data is complete or valid.

## Integrated evidence audit — real-data status

Artifact: `nepse-integrated-evidence-audit`
- Run: `45614983065`
- Artifact ID: `15021687998`
- SHA-256: `c2d8c428e91fb68d0c0d356210e2620e036dab8dd3b322465a9fe951d99741df`

The workflow completed successfully, but its report explicitly skipped
real-source checks because required evidence inputs are absent:
- source-object manifest and staged raw source root;
- calendar evidence manifest and source-date manifest;
- normalized OHLCV input files and security-universe snapshot;
- floorsheet acquisition manifest and broker party observations.

The canonical `data/reference/nepse_session_calendar.csv` currently contains
only its header (zero verified rows). The training-readiness report returns
`training_allowed=false` and lists all ten evidence gates plus the OHLCV and
broker-identity coverage thresholds as blockers. Canonical promotion is false.

## Primary exchange calendar evidence

The official NEPSE Holiday Listing page was located:
https://www.nepalstock.com/holiday-listing

The page returned no readable records in this review, so no date-specific
primary notice bytes or hashes were captured. Government holiday PDFs and
secondary publisher reports remain evidence leads only. No calendar dates are
promoted from those sources.

## Next five P1 execution tasks

1. **Stage immutable raw source objects and manifests.** Acquire the authorized
   source files, record exact repository revision/path/blob or LFS OID, local
   SHA-256 and byte count, retrieval time, rights status and source lineage.
   Do not claim inventory metadata is downloaded data.
2. **Capture primary NEPSE calendar evidence.** Retrieve the actual exchange
   holiday/suspension notices (including exceptional operational suspensions),
   preserve exact bytes, calculate SHA-256, record source URI and UTC retrieval
   time, and review each date/scope before adding verified calendar rows.
3. **Recover the 616-session source calendar.** Find the exact pinned calendar
   file and generator inputs behind the starter backfill manifest; reproduce
   exactly 616 unique dates and compare against independent EOD/index/floorsheet
   evidence. Do not infer missing dates from weekday regimes.
4. **Resolve historical price and corporate-action conflicts.** Trace the
   adjustment basis and provenance of the 25 longer legacy SMC files; resolve
   the eight same-date conflicts for API, BGWT, HRL, MEHL, RAWA, RHGCL and ULHC
   using primary exchange/issuer evidence and a complete action/lifecycle
   review. Keep all unresolved source values quarantined.
5. **Run the complete evidence acceptance audit.** Populate the required
   manifests/raw roots, run the integrated audits at source/date/symbol/row
   grain, verify source rights and point-in-time availability, reconcile broker
   control totals, and require every P1 acceptance criterion to pass before
   promoting any canonical dataset or starting P2 learning.

## Release rule

A green CI run means the implemented checks executed successfully. It does not
override skipped inputs, empty calendar evidence, unresolved source conflicts,
unknown licensing, or incomplete corporate-action records. P1 remains blocked
until the real-data acceptance audit has no unresolved critical blockers.


## P1 execution increment — evidence acquisition contracts

Created and pushed empty, explicit templates (not fabricated records):
- `data/evidence/templates/source-object-manifest.template.jsonl`
- `data/evidence/templates/source-file-date-manifest.template.jsonl`
- `data/evidence/templates/calendar-evidence-manifest.template.json`
- `data/evidence/templates/corporate-action-review.template.csv`
- `data/evidence/templates/ohlcv-conflict-ledger.template.csv`
- `data/evidence/templates/broker-party-observations.template.csv`

Added `docs/P1_EVIDENCE_MANIFEST_CONTRACTS_2026-11-25.md`, documenting the
required fields, provenance rules, raw-byte SHA-256 requirements, date coverage
semantics, calendar evidence scope/conflict handling, corporate-action review,
OHLCV quarantine, broker party observation contract and promotion rules.

These six templates and the contract make the next acquisition work
reproducible, but contain no real captured source objects or verified claims.
They do not clear any P1 evidence gate. Canonical session calendar remains at
zero verified rows and the 616-session source list remains unrecovered.

## Next five execution tasks after the contract increment

1. Acquire and hash a bounded raw floorsheet sample from a pinned publisher
   revision; retain the immutable bytes and source metadata, and check terms.
2. Acquire a pinned EOD sample for the same date and reconcile contract/date
   coverage without treating vendor agreement as independent provenance.
3. Capture original NEPSE calendar notices (including the September 21
   exceptional suspension), archive bytes and populate claims only after review.
4. Retrieve the original 616-session generator inputs/calendar and reproduce
   the exact date set; retain disagreements as unresolved.
5. Populate the corporate-action, OHLCV conflict and broker observation ledgers
   from real source evidence, then rerun the integrated acceptance audit.


## P1 raw-source acquisition — pinned floorsheet sample

Acquired and preserved one complete source file from a pinned public
community-maintained repository:

- Source: `rajeevpaudel/nepse-history`
- Immutable revision: `927a15986012b31dba6c29c2266fb17f966a087b`
- Original path: `data/floorsheet/2026/2026-11-19.csv`
- Original Git blob OID: `4bbe20319f12b993218b27047f8e46567cfb8cbf`
- Preserved project path:
  `data/raw/acquired/rajeevpaudel-nepse-history/2026/2026-11-19-floorsheet.csv`
- Byte count: 2,300,941
- SHA-256 of raw bytes:
  `771d856187844f5608cb31225c03d065a4ce13fe655601d465c4e167a7b62e15`
- Rows: 40,818 trade contracts; all rows have date 2026-11-19 and the expected
  eight CSV columns. Structural validation found zero malformed rows.
- Verified copied file Git blob OID and byte count exactly match the pinned
  source object.

Source limitation and rights review: upstream README says historical data is
collected via Merolagani; it documents per-day row shortfalls on 2,427 of about
4,100 days, 112 failed date-fetch attempts later retried, and no intraday trade
timestamps. It describes the underlying trade data as public market
information but explicitly advises independent verification of NEPSE and
Merolagani terms for redistribution/commercial use. Therefore this sample is
community-maintained corroborating data, not a primary exchange record; no
completeness, beneficial ownership or commercial redistribution claim is made.

Manifests created:
- `data/evidence/acquired/source-object-manifest.jsonl`
- `data/evidence/acquired/source-file-date-manifest.jsonl`

The source sample is staged and hash-verified, but one date does not establish
historical coverage, session validity, broker identity or source completeness.
The calendar, 616-session recovery, corporate-action reconciliation, OHLCV
conflicts and broad floorsheet coverage remain unresolved. P1 remains blocked.

## Next five execution tasks after first source acquisition

1. Capture the source repository's per-date `manifest.json` and discrepancy
   records at the same immutable revision; link its status/row counts to this
   sample and assess source completeness for the date.
2. Acquire a same-date independent EOD/index record and compare trade-derived
   aggregates with published daily values, retaining source lineage caveats.
3. Convert the 40,818 contracts into separately hashed buyer/seller execution-
   channel observations, without assigning beneficial owners; reconcile row
   counts and amount/quantity controls.
4. Capture primary NEPSE calendar notices and recover the exact 616-session
   generator inputs/calendar; no weekday-only inference.
5. Expand pinned source acquisition across a stratified historical sample,
   populate corporate-action and OHLCV conflict evidence, then rerun the full
   integrated acceptance audit.


### Same-date source manifest and derived EOD cross-check

The pinned source's `manifest.json` and `data/discrepancies.csv` were also
preserved at the same revision and registered with raw SHA-256 values. For
2026-11-19, the source manifest reports `source=merolagani`, `status=ok`,
`row_count=40,818`, `retries=0`, and notes that NEPSE did not return the date
and that the source-reported grid shortfall was 19. The discrepancy log records
40,837 reported rows versus 40,818 written rows (shortfall 19). This means the
acquired file is structurally sound but known incomplete against the
publisher's own reported total.

Also preserved the same repository's derived EOD file
`data/ohlcv/2026/2026-11-19.csv` (346 symbol rows, 20,376 bytes) and registered
its source blob OID and raw SHA-256. This OHLCV is derived from the same
floorsheet pipeline, so it is useful for internal reconciliation but is not
an independent witness. Its API, HRL and RHGCL Close values are 331.8, 483.9
and 258.0 respectively, matching the previously reviewed starter/Srijan
values rather than the conflicting SMC values. This adds same-lineage
corroboration only; it does not resolve the conflicts with primary exchange
proof.

Additional preserved objects:
- `data/raw/acquired/rajeevpaudel-nepse-history/manifest.json`
- `data/raw/acquired/rajeevpaudel-nepse-history/data/discrepancies.csv`
- `data/raw/acquired/rajeevpaudel-nepse-history/2026/2026-11-19-derived-ohlcv.csv`

Updated source object and date manifests are under `data/evidence/acquired/`.


## P1 execution increment — broker derivation, external EOD and stratified audit

### Broker-party derivation implementation

Added `backend/derive_broker_party_observations.py` with explicit source
header mapping for the pinned source schema:

`date,transaction_no,symbol,buyer,seller,quantity,rate,amount`.

The script verifies the exact source SHA-256, expected date and row count;
rejects duplicate transaction IDs and malformed identifiers; uses Decimal for
quantity/rate/amount; emits one buy-side and one sell-side observation per
contract; preserves broker codes as source execution-channel identifiers;
leaves broker entity IDs null and identity status `unmapped`; and aggregates
by date/security/source broker code/side. It does not assign beneficial owners
or infer historical legal-entity identity.

Added unit tests for two-sided observations, leading-zero broker codes, hash
mismatch and duplicate contract rejection. The broker-party template now
includes `source_broker_code`. The data-integrity workflow runs this test and
produces a downloadable party-observation CSV plus aggregate JSON artifact
from the pinned raw sample. CI has been triggered by the workflow changes;
record its actual conclusion and artifact digest after completion.

An independently calculated aggregate snapshot is preserved at
`data/evidence/acquired/broker-aggregates-2026-11-19.json`:

- 40,818 contracts and 81,636 buyer/seller party observations represented.
- 91 distinct source broker codes and 346 securities.
- 15,466 broker/security/side aggregate rows.
- Quantity 9,435,392 and gross amount NPR 3,877,623,296.62, each contract
  counted once (not double-counting both parties).
- Zero duplicate transaction IDs and zero quantity × rate / amount exceptions.
- All 91 codes remain unmapped to canonical legal entities.

These are source-file internal controls, not independent exchange totals. The
publisher reports 40,837 expected rows, so the known 19-contract shortfall
remains. No completeness claim is made.

### Independent-repository EOD cross-check

A separate daily EOD object was inspected from
`srijankarki07/nepse-data`, pinned revision
`e6e6fe77cd3378204c7938e66601cee2339a8b7a`, path
`data/daily/2026/2026-11-19.csv`, blob
`79fbb09935a1b704a3e247a06c1c2ed55220dcba`, 17,912 bytes, SHA-256
`98a12d21865c80cb96362fbb8a33631c55fc1ca49d61528b8255409f20bbb732`.

Numeric OHLCV comparison against the floorsheet publisher's own derived EOD
file found 346 common symbols, one extra Srijan symbol (RSY2), and 77 common
symbols with at least one differing field: Open 4, High 7, Low 72, Close 1,
Volume 0. This is a distinct repository lineage but its README states its data
is scraped from ShareSansar and the dataset is not covered by the repository's
MIT license; ShareSansar's terms are described as permitting reading rather
than republication. The raw EOD file was therefore removed from this project
repository after review; only the source pointer, blob OID, hash, and comparison
metrics are retained in `docs/P1_EXTERNAL_EOD_CROSSCHECK_2026-11-25.json`.
This is not primary NEPSE proof and does not resolve the 77 differences.

### Stratified historical source sample review

Pinned-revision samples from 2015 and 2026 were inspected without copying the
additional raw files into the project while redistribution rights remain
unverified. Results are in
`data/evidence/acquired/stratified-floorsheet-sample-audit.json`:

- 2015-01-04: 2,343 rows, 126 symbols, 49 broker codes, zero malformed rows,
  one quantity × rate / amount exception.
- 2026-11-18: 41,594 rows, 344 symbols, 91 broker codes, zero malformed rows,
  zero amount exceptions; publisher manifest reports a 33-row shortfall.
- 2026-11-19: 40,818 rows, 346 symbols, 91 broker codes, zero malformed rows,
  zero amount exceptions; publisher manifest reports a 19-row shortfall.

The 2015 and 2026-11-18 source blobs, sizes and SHA-256 values are recorded;
their raw copies are not staged. Their dates remain candidate_unverified until
authoritative session evidence is acquired.

### 616-session recovery search update

The exact base commit named by the starter backfill manifest was recursively
searched (573 tree entries), as was the later pinned starter revision (621 tree
entries). Neither tree contains a calendar/session/616/holiday artifact path.
The pinned import and scanner-preparation scripts also contain no calendar
loader or 616-date generator. The exact list remains unrecovered; see
`docs/616_SESSION_CALENDAR_RECOVERY_AUDIT_2026-11-25.md`.

### Status after this increment

P1 remains blocked. Improvements are source-preserving code, broker-side
observations/aggregates, and better quantified external disagreements. Still
missing: primary NEPSE calendar notices and the exact 616-date input, licensed
or primary raw source coverage across history, independent same-day exchange
controls, effective-dated broker legal-entity history, corporate-action
reconciliation, and primary resolution of OHLCV conflicts.

### Next five execution tasks

1. Verify the new CI run and inspect/download its broker-party artifact; hash
   the artifact and reconcile 81,636 party observations to 40,818 unique
   contracts without double-counting market turnover.
2. Obtain a primary or licensed same-day exchange control for 2026-11-19
   (contract count, quantity, gross turnover and, if available, per-symbol
   totals); do not substitute the publisher's own derived EOD file.
3. Retrieve the 616-date input from original operator backups, workflow
   artifacts, pull-request attachments, forks or other retained build outputs.
4. Acquire dated primary NEPSE notices and build the evidence-backed calendar;
   do not promote 2015-01-04, 2026-11-18 or 2026-11-19 based only on file presence.
5. Obtain rights-cleared multi-year floorsheet samples and primary corporate-
   action/issuer evidence; then reconcile the 25 cross-repository OHLCV files
   and rerun the integrated P1 audit.


### Broker derivation CI verification — completed

The broker derivation implementation and full backend suite have now passed:

- Backend tests run: `45617995122`, conclusion `success`, head commit
  `16bffbfd4faa5a1093d72499ac76791ba1068dbb`; **535 tests passed**.
- Historical data-integrity run: `45617821684`, conclusion `success`,
  code/workflow commit `b77379fd542c98428a3b059e684280b2334eb62a`.
- Artifact ID: `15023870425`, size 2,299,648 bytes, ZIP SHA-256
  `074a627f3d7ee403e8bffcfba31a4a9cdbcd45822a9076189c5ce0b53a5bdcc6`.
- Artifact URL:
  https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45617821684/artifacts/15023870425
- The artifact contains the 81,636-row party CSV and aggregate JSON. After
  download, independent checks found 40,818 unique contracts, exactly 40,818
  buy and 40,818 sell observations, zero contract-pair anomalies, 91 broker
  codes, no non-empty canonical broker IDs, and 15,466 aggregate rows.
- Party CSV: 13,192,868 bytes; SHA-256
  `050139c4f6c4ecc65a49c762f2e7cce0b7d7ad2d75c193349a7d1b0e7fefe9d0`.
- Aggregate JSON: 7,449,669 bytes; SHA-256
  `9c4cec23837cba310a6202080f8e7ec6ac36d0397913cdee88073d80037725e0`.

The full backend suite at the latest main commit also passed 535 tests. The
integrity workflow passed its focused collector, coverage, OHLCV and broker
party derivation steps and uploaded the artifact. This verifies the code and
one sample run only; it does not prove historical completeness or canonical
identity resolution.
