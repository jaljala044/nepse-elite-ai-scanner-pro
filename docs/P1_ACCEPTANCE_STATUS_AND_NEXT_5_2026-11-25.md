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
