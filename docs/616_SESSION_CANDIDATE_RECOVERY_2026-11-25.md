# 616-session date-candidate recovery — 2026-11-25

## Outcome

A pinned, append-only NEPSE EOD archive yielded **616 unique date-file candidates** in the exact date window and with the exact count stated by the starter backfill manifest:

- Window: **2024-03-04 through 2026-11-20**, inclusive.
- 2024 (from 2024-03-04): **189** dates.
- 2025: **225** dates.
- 2026 (through 2026-11-20): **202** dates.
- Total: **616** date filenames; **616 unique dates**; zero duplicate dates.

This is a substantial recovery lead and an exact count/window match. It is **not yet proof** that the recovered dates are byte-for-byte the same list used by the original scanner extraction. Every row remains `candidate_unverified`; no candidate was promoted into the canonical calendar.

## Pinned source

- Repository: https://github.com/srijankarki07/nepse-data
- Immutable revision: `e6e6fe77cd3378204c7938e66601cee2339a8b7a`
- Revision commit date/message: 2026-11-20, `data: 2026-11-20 end-of-day prices`
- Date files: `data/daily/{2024,2025,2026}/YYYY-MM-DD.csv`
- Per-file Git blob SHA-1 and byte count are recorded in `data/evidence/candidates/nepse-616-session-date-candidates-2024-2026.csv`.
- The source README describes this as an append-only EOD archive scraped from ShareSansar. Its data is not covered by the repository's MIT code license.

## Reconciliation checks

1. **Official NEPSE holiday API:** the 616 candidates have zero overlap with the explicit holiday records archived for 2024, 2025 and 2026 (124 source records reviewed). This is a contradiction check only; absence from a holiday list does not itself prove that a date was open.
2. **Starter market summary:** 195 of the 202 dates in the 2026 candidate set overlap the 2026 market-summary file through the 2026-11-20 cutoff. Seven candidate dates have no market-summary row:
   2026-02-05, 2026-03-10, 2026-03-12, 2026-03-30, 2026-04-05, 2026-07-02, 2026-08-17.
3. The three market-summary dates outside the candidate cutoff are 2026-11-23, 2026-11-24, 2026-11-25 and are correctly excluded from the 2024-03-04 through 2026-11-20 comparison.
4. The source's date-file inventory is a scraped EOD archive, not a primary exchange trading-session register. The starter stock-history source also derives from ShareSansar; this is not independent source-lineage corroboration.

## Interpretation

The exact 616 count and exact window are consistent with the backfill manifest's `calendar_approved_sessions=616`. The recovered set is a high-value candidate reconstruction, but there is no surviving original calendar path/blob/hash or generator input tying it conclusively to the original extraction. The seven 2026 candidate-only dates and any upstream stale/misdated records must be checked before acceptance.

## Required next checks

- Compare all 616 dates against the original extraction's retained outputs, source-date manifest, workflow artifacts, PR attachments and local backups if available.
- Compare against an independently sourced NEPSE index/trading-day archive and date-scoped floorsheet records; distinguish common ShareSansar lineage from independent evidence.
- Investigate the seven candidate-only 2026 dates listed above.
- Obtain primary NEPSE daily trading records/notices or other authoritative date-scoped evidence for open-session claims.
- Only after date-by-date review may any rows be promoted to `verified_open`. Keep the canonical calendar fail-closed.

## Decision

**616-session count recovery: candidate set found; exact original identity not yet proven.**
**Canonical open dates promoted: 0.**
**P1: remains active; P2 training remains blocked.**


## Separate-repository index-date cross-check — 2026-11-25

A second repository snapshot was inspected: `socrateai-official/nepse-open-data`, immutable commit `f602a5b61e68582d28834d16f71151a4bae98d5b`, index tree `d5effd0801a112a611da6105122ee126ef7a9725`.

- 614 of the 616 candidate dates have a corresponding `ohlc_index/adj_YYYY-MM-DD.csv` file in that pinned tree.
- The two candidate dates without an index file are **2025-04-03** and **2026-11-20**.
- There are zero index-only dates in the 2024-03-04 through 2026-11-20 window (the index date set is a strict subset of the 616 candidate set).
- All seven 2026 candidate dates absent from the starter market-summary file do have an index file. Each of those seven files was fetched and contained exactly one `NEPSE_index` row; their file blob SHAs are recorded in the cross-check CSV.
- The index archive's README identifies it as an open-source dataset but does not establish a primary NEPSE source chain in the inspected text. Treat this as separate-repository corroboration with lineage not fully verified, not primary exchange proof.

The 614/616 match strengthens the candidate reconstruction, and the seven market-summary gaps now have a second date-file witness. The two missing index dates remain unresolved. File presence alone still does not prove the index rows are correct or that the exact original scanner calendar has been recovered.

Machine-readable file: `data/evidence/candidates/nepse-616-session-index-crosscheck-2024-2026.csv`.


## Secondary session-report check for the two index-date gaps — 2026-11-25

The two dates absent from the pinned SocrateAI index tree both have contemporaneous secondary reports describing NEPSE trading sessions:

- **2025-04-03:** Kathmandu Post reported NEPSE's index movement, traded shares and transaction count on Thursday 3 April 2025: https://kathmandupost.com/money/2025/04/03/nepse-index-increases-by-3-35-points-trading-volume-reaches-rs7-84-billion.
- **2026-11-20:** NepseIQ reported the completed 20 November session: https://nepseiq.com/nepse-today/2026-11-20. ShareSansar also published a same-day close report: https://www.sharesansar.com/newsdetail/nepse-index-slides-down-by-738-points-only-two-sector-closes-at-green-2026-11-20. The latter shares lineage risk with the ShareSansar-scraped EOD candidate source.

These reports strengthen the two dates as session candidates, but neither is primary NEPSE evidence. They remain `candidate_unverified`; no canonical `verified_open` rows are added. Machine-readable references: `data/evidence/candidates/nepse-session-secondary-report-crosscheck.csv`.


## Weekday-regime consistency check — 2026-11-25

All 616 candidate dates were checked against the documented NEPSE schedule-regime weekday candidates. Result: **zero weekday-regime violations** and zero Saturday dates. The weekday distribution is Sunday 96, Monday 118, Tuesday 128, Wednesday 127, Thursday 120, Friday 27, Saturday 0. The 27 Friday dates are in the Monday-Friday regime after 2026-04-06; no Friday candidate falls in the earlier Sunday-Thursday regime.

This check detects impossible weekday assignments under the documented schedule but does not establish that every candidate date was actually open; holidays and exceptional suspensions still require date-specific evidence.
