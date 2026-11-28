# Issue #5 — next five highest-incidence explicit-closure review batches

Generated 2026-11-28 from the pinned full-archive candidate artifact **15231005676**.

Input candidate CSV SHA-256: `a343c1a4c87fb305415b0ce2b62427753250152e74d69cdbb0558b13153cbef1`.

The workload was recomputed by grouping the original 196,784-row candidate CSV by `current_date`, excluding the ten date batches already registered in the preceding top-five and next-five packages. Counts below are candidate-pair incidences, not unique source rows or exchange sessions.

## Ranked batches

| Current date | Candidate pairs | Symbols | Previous date | Previous session | Current session |
|---|---:|---:|---|---|---|
| 2026-02-18 | 680 | 352 | 2026-02-17 | project_accepted_open | verified_closed |
| 2026-02-19 | 680 | 352 | 2026-02-18 | verified_closed | verified_closed |
| 2026-02-20 | 680 | 352 | 2026-02-19 | verified_closed | not_listed_in_project_calendar |
| 2026-05-28 | 679 | 352 | 2026-05-27 | project_accepted_open | verified_closed |
| 2026-05-29 | 679 | 352 | 2026-05-28 | verified_closed | verified_closed |

**Total: 3,398 candidate-pair incidences across five current-date batches.**

## Evidence and classification limits

- The source candidate artifact labels closure evidence as `NEPSE_OFFICIAL_HOLIDAY_API_2026`. This report preserves that evidence ID exactly; it does not independently reacquire or re-hash the underlying NEPSE API response.
- Dates whose current session is `verified_closed` are explicitly classified that way in the pinned project calendar. The preceding date can still be a ShareSansar-derived `project_accepted_open` research-baseline session, not exchange certification.
- 2026-02-20 is **not** listed in the project calendar in the source artifact. The closure evidence ID in these candidate rows belongs to the preceding 2026-02-19 date; do not infer that 2026-02-20 itself was closed. Its current-date state remains UNKNOWN / review-only.
- These are repeated-signature pairs adjacent in source CSV rows. Identical OHLCV does not prove false trading, carry-forward, manipulation, or invalid source data.

## Controls

- Every batch remains `REVIEW_ONLY`; 2026-02-20 is separately marked `REVIEW_ONLY_CURRENT_DATE_UNKNOWN`.
- No project calendar status is changed by this report.
- No raw OHLCV row is edited, deleted, forward-filled, repaired, canonicalized, or admitted to training/scanner eligibility.
- Individual row decisions require date-matched source payloads and complete provenance, not date-level counts alone.

## Reproducibility

- Source artifact: `15231005676`.
- Source CSV SHA-256: `a343c1a4c87fb3054158b13153cbef1` (full digest above).
- Grouping key: `current_date`.
- Excluded previously registered current dates: 2026-06-27, 2026-06-28, 2026-02-21, 2026-05-31, 2026-06-20, 2026-05-03, 2026-06-13, 2026-06-14, 2026-05-16, 2026-05-17.
