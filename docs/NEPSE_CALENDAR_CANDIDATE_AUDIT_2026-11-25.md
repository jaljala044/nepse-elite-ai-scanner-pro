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



## Update — official NEPSE 2026 closure evidence acquired

The official NEPSE holiday API response was captured on 2026-11-25 and
contains 41 unique dates. The canonical calendar now records 40
`verified_closed` dates and one `verified_exceptional_closed` date
(2026-09-21, the API's emergency market closure entry). The raw response
SHA-256 is
`dd1777e3c61623048e00dc170d860659b14b8821ffabff8338002ccafdb2ea8f`.
All raw bytes and date-level claims are archived in
`data/evidence/raw/nepse/holiday-api-authenticated/2026-11-25/` and
`data/evidence/acquired/calendar-evidence-manifest-2026.json`.

The 198 market-summary dates remain candidate records; none of those 198
rows is automatically promoted. There are no overlaps between the 41
official holiday dates and those market-summary candidates, and no
`status=ok` overlap in the pinned floorsheet publisher manifest. This
supports the closure claims but does not prove unlisted dates were open.

Current calendar coverage from this capture: 41 verified closure dates,
zero verified open dates. The exact 616-session historical list remains
unrecovered.
