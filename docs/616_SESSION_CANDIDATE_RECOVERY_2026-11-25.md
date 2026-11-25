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
