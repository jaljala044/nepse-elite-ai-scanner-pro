# 616-session calendar recovery investigation — 2026-11-25

## Outcome

The exact 616-date approved session list has **not** been recovered. The
reported count remains an aggregate assertion in the backfill manifest, not a
reproducible calendar artifact. No dates have been promoted to confirmed
sessions as a result of this investigation.

## Evidence inspected

1. `scanner_inputs/audit/backfill_manifest_2026-11-22.json` reports
   `prior_stock_history.calendar_approved_sessions = 616`. It pins a
   repository base commit (`2ebbe980c635181291d32fc8a731203c17b76726`) and
   several source revisions, but contains no calendar path, calendar blob SHA,
   exact date list, or calendar-generation command.
2. `scanner_inputs/README.md` states that the original scanner extraction
   excludes non-session records according to its pinned session calendar.
   The README does not identify that calendar's path or revision.
3. The inspected `nepse_history_import.py` validates Gregorian date syntax
   and OHLCV/floorsheet structure, but does not consult a session calendar.
   It is an import utility and cannot independently substantiate the
   historical 616-session filter.
4. `scanner_inputs/market_summary_daily.csv` contains 198 dated market
   summary rows for 2026. These are candidates only; this file is not the
   616-session calendar.
5. The starter archive's supplemental README separately reports 195 market
   summary sessions with totals and 20 broker sessions in the backfill
   context. These counts are different datasets and must not be treated as
   equivalent to the 616 stock-history calendar dates.

## Important distinction

The 616 figure is a count of calendar-approved sessions associated with a
prior stock-history audit. It is not evidence that 616 sessions are present
for every symbol, that all stock rows are valid, or that the entire market
archive is complete. The 525 matched ticker filenames are also file-level
inventory, not proof of row-level coverage.

## Required recovery path

- Retrieve the original extraction script/configuration and its pinned
  calendar file from the repository state identified by
  `repository_base`, or from the commit that generated the backfill.
- Record the exact calendar path, Git blob SHA, commit SHA, date range,
  row count, status vocabulary, and review/exclusion notes.
- Re-run the original filter from that pinned input and verify that it yields
  exactly 616 unique approved dates.
- Compare the recovered list against dated EOD, market-summary, and
  floorsheet evidence. Keep disagreements as conflicts until reviewed.
- Only then import rows into the canonical calendar with per-date provenance.

## Current disposition

- 616-session count: reported, not independently reproduced.
- Exact 616 dates: unavailable in inspected artifacts.
- 198 2026 market-summary dates: candidate_unverified only.
- Confirmed sessions added by this investigation: 0.
- Canonical calendar remains blocked; do not use inferred weekdays or file
  presence to fill the gap.


## Expanded immutable-tree recovery search

A second path-level search was performed against the exact repository base
commit named by the backfill manifest:

- Repository: `jaljala044/nepse-history-starter`
- Base commit: `2ebbe980c635181291d32fc8a731203c17b76726`
- Recursive tree entries: 573
- No path matching calendar, session, 616, holiday or equivalent was present.
- The pinned later starter revision
  `2bd6976cbbb0d40cf60f77c0f712e0b708dc4dbe` has 621 tree entries and likewise
  no calendar/session/616/holiday artifact path.
- The pinned `nepse_history_import.py` and
  `scanner_inputs/prepare_scanner_inputs.py` were inspected; neither contains
  a calendar path, calendar loader, 616 constant or session-date generator.
- The backfill manifest remains the only inspected artifact asserting 616
  approved sessions; it names neither a calendar blob nor a generator input.

This narrows the recovery path: the 616 list was likely an external/local
preprocessing input or a transient extraction artifact not committed in either
inspected tree. This is a finding about the inspected commits only, not proof
that no other branch, fork, workflow artifact or local backup contains it.

## Updated disposition

- Exact 616-date list: still not recovered.
- Calendar file/path in both inspected immutable trees: none found.
- Confirmed sessions promoted: 0.
- Next recovery targets: original operator's local workspace/backups, workflow
  artifacts around the original backfill, pull-request attachments, forks and
  commit history around the 616-session extraction. Do not reconstruct the
  exact list from OHLCV file presence or weekdays.


## Official NEPSE holiday listing retrieval attempt

The official NEPSE Holiday Listing endpoint
(`https://www.nepalstock.com/holiday-listing`) was queried again on
2026-11-25. The page title was returned, but the page contained no readable
holiday rows or downloadable notice bytes in the available retrieval. No
holiday date was promoted and no raw evidence hash was created from this
attempt. This confirms the page location, not the underlying holiday schedule.



## Primary NEPSE holiday API capture — 2026-11-25

The official NEPSE API was successfully reached through its public client
authentication flow after the unauthenticated endpoint probe returned HTTP
401. The raw API response was captured before parsing:

- Endpoint: `https://nepalstock.com.np/api/nots/holiday/list?year=2026`
- Retrieval: 2026-11-25 13:13:17.600880 UTC; HTTP 200; JSON.
- 4,932 raw bytes; SHA-256
  `dd1777e3c61623048e00dc170d860659b14b8821ffabff8338002ccafdb2ea8f`.
- 41 unique holiday dates; `instrumentTypeId=null` on all records.
- 40 normal closure entries and one exceptional closure:
  2026-09-21, described by NEPSE as `Emergengy Market Close`.
- The raw response, response headers, parsed JSON, checksum, capture report
  and source-object manifest entry are archived under
  `data/evidence/raw/nepse/holiday-api-authenticated/2026-11-25/`.
- Evidence claims are in
  `data/evidence/acquired/calendar-evidence-manifest-2026.json`.
- Reconciliation report:
  `data/reports/nepse-holiday-calendar-reconciliation-2026.json`.

The 41 dates were compared against the pinned floorsheet publisher manifest
and the 198-date market-summary candidate list. There are zero publisher
manifest `status=ok` overlaps and zero market-summary candidate overlaps.
Twenty dates have publisher-manifest status `missing`; 21 dates have no
entry in that manifest. These publisher values are corroborative checks only,
not the basis for closure claims.

The canonical calendar now contains 41 explicit closure rows: 40
`verified_closed` and one `verified_exceptional_closed`. No dates absent
from the API response were inferred open. The 616-date historical session
list is still unrecovered; this 2026 holiday API response does not replace
that historical input or establish 2015-era session dates.


## P1 616-date candidate recovery update — 2026-11-25

A pinned ShareSansar-scraped EOD archive yielded 616 unique date-file candidates from 2024-03-04 through 2026-11-20, exactly matching the count and window asserted in the starter backfill manifest. See `docs/616_SESSION_CANDIDATE_RECOVERY_2026-11-25.md` and the 616-row candidate CSV.

A separate SocrateAI index repository tree contains index-date files for 614 of the 616 candidates; the missing index files are 2025-04-03 and 2026-11-20. All seven candidate dates absent from the starter 2026 market-summary file have one inspected `NEPSE_index` row in the separate-repository index files. This is corroboration with source lineage not fully verified, not primary exchange evidence.

The candidate list is preserved as `candidate_unverified`; no `verified_open` dates were promoted and the canonical calendar is unchanged. Exact identity with the original extraction input and primary date-by-date proof remain open. P1 remains blocked.

## Eligibility evaluator provenance hardening — 2026-11-27

The single-instrument segment evaluator now requires a separate session_evidence record for every date in the caller-supplied expected-session grid. Each date must carry:
- a status matching the explicit session_statuses classification;
- a non-empty source ID and source-record reference;
- an HTTPS source URL and SHA-256 of the retained evidence object;
- approved source-rights status; and
- timezone-aware source availability and retrieval timestamps, with source availability no later than the decision cutoff.

Missing, mismatched, unlicensed, unhashed or post-cutoff session evidence is classified as unknown/ineligible. Evidence records outside the expected grid are rejected. This closes a contract gap where a caller could previously label a date "verified" without the evaluator requiring date-level provenance.

The unit tests use synthetic fixture evidence only. They demonstrate fail-closed behavior and do not certify any real NEPSE session date. The 616-date reconstruction remains candidate-only; primary exchange open-session evidence and the original calendar identity are still unresolved. No 120-session audit or backtest promotion is claimed.

## Additional evaluator provenance controls — 2026-11-27

A follow-up review identified that caller-supplied identity/lifecycle booleans,
bare OHLCV hashes and arbitrary HTTPS hosts were not sufficient provenance
contracts. The evaluator has now been hardened to require:

- primary-source evidence envelopes for instrument identity and lifecycle
  boundary decisions, not only boolean flags;
- a primary-source evidence envelope for every traded OHLCV row, including
  source ID, record reference, HTTPS URL on the NEPSE host allowlist, matching
  evidence/payload SHA-256 declarations, approved rights status, and
  timezone-aware availability/retrieval timestamps;
- the same allowlisted source and envelope checks for each session-date record;
- retrieval no earlier than source availability and availability no later
  than the decision cutoff;
- an explicit positive factor, factor version and effective date evidence
  whenever the selected adjustment basis is `verified_adjusted`; and
- whole-share integer volume (fractional or zero volume is rejected).

The envelope checks are intentionally not described as raw-byte verification:
the evaluator receives metadata and matching digest declarations, not the
retained source bytes, so an independent acquisition/re-hash step is still
required before any real source record can be accepted as verified. The
synthetic fixtures only exercise rejection behavior; they are not NEPSE
market evidence. The NEPSE host allowlist also does not itself prove that a
specific endpoint or record is authoritative. Rights approval and source
record correctness require independent evidence review.

New exact-head CI is required for the latest implementation and regression
tests. No calendar dates, security identities, lifecycle intervals, OHLCV
records or corporate-action factors were promoted by these code changes.


## Corporate-action feed discovery — PFL and NLO — 2026-11-27

A structured third-party mirror of NEPSE exchange-message records was inspected at
`https://raw.githubusercontent.com/Shubhamnpk/yonepse/main/data/notify/exchange_messages.json`.
This is a discovery lead, not a primary-source capture; the mirror's records
must not be treated as authoritative exchange evidence.

- PFL record ID `208780`, symbol `PFL`, title “Listing Shares of Pokhara
  Finance Limited (PFL) after merger.”, published `2026-09-15T15:37:00.507`.
  The mirror says the first-transaction open-price range is NPR 366.58 and
  links the purported NEPSE letter:
  `https://www.nepalstock.com.np/api/nots/security/fetchFiles?fileLocation=nabaraj_listing/2026-09-15/PFL%20p_1789465894643.pdf`.
  A direct content-extraction attempt against that URL returned an empty text
  body (no PDF bytes, parsed text, or independently computed digest). Thus
  the date and notice details remain a secondary-mirror lead; no lifecycle
  boundary or merger factor is promoted by this capture.
- NLO record ID `208846`, symbol `NLO`, title “Listing 20% Bonus Shares of
  Nepal Lube Oil Limited”, published `2026-11-25T11:26:07.24`, reports
  145,725.36 bonus units. A separate NLO price-adjustment record ID
  `208784` reports a 15% bonus adjustment (NPR 241.22 from NPR 277.40),
  published `2026-09-18T15:38:18.423`. These are different event dates and
  potentially different corporate actions; the mirror alone does not resolve
  the 15% versus 20% notices or the quantity/ratio basis. No adjustment factor
  or historical price is accepted from this feed.

The official-host PDF URL is a useful acquisition target, but the attempted
fetch did not retrieve its bytes. Required next evidence is the actual NEPSE
PDF response, response headers, retrieval timestamp, SHA-256 recomputed from
retained bytes, and independent extraction/review of the notice fields. Keep
PFL's 2026-07-10 to 2026-09-15 suspension/relisting interval and NLO's bonus
share treatment in review-only status until those artifacts and the relevant
security-master identity records are verified. This discovery does not
recover the 616-date open-session calendar or any per-instrument 120-session
manifest.
