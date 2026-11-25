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
