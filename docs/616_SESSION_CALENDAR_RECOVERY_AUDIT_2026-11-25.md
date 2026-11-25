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
