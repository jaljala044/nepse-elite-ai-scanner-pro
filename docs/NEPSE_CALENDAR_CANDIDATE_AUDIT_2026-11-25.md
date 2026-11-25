# NEPSE session-calendar candidate audit — 2026
Generated: 2026-11-25

## Result
- Candidate dates extracted: 198
- Unique candidate dates: 198
- Date range: 2026-01-01 through 2026-11-25
- Confirmed sessions: 0
- Confirmed non-sessions: 0
- Conflicts: 0
- Status assigned to every row: `candidate_unverified`

## Source
- Repository: `jaljala044/nepse-history-starter`
- File: `scanner_inputs/market_summary_daily.csv`
- File blob SHA: `f53c192a0ab30a09a4a21c323a7492b11cf5b6f9`
- Source rows: 198 dated rows, all unique.

## Interpretation
Each row is a dated market-summary record and therefore a useful candidate for calendar reconciliation. This source alone is not promoted to an authoritative exchange calendar. No weekday rule, assumed holiday calendar, or inferred missing date was used. The CSV deliberately retains `candidate_unverified` for every row.

## Next evidence needed
1. Locate the pinned source calendar behind the starter archive's reported 616 calendar-approved stock-history sessions.
2. Recover its exact date list, provenance, source revision and any review/exclusion notes.
3. Compare that list with these 2026 candidates and the pinned EOD/floorsheet evidence.
4. Keep any disagreement as `conflict` until independently resolved.
5. Only after review, promote individual dates to `confirmed_session` or `confirmed_non_session`.

## Output
`data/reference/nepse-session-calendar-candidates-2026.csv` is an input to reconciliation, not a canonical session calendar.
