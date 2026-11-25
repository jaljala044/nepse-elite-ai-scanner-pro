# Phase B acceptance plan — historical calendar and coverage matrix
Updated: 2026-11-25

## Purpose

Build an auditable, point-in-time coverage layer before canonical historical imports or predictive research. This document defines the next implementation unit; it does not claim that the underlying archives have been downloaded or accepted.

## Evidence currently available

- The 2026-11-22 starter backfill manifest records 616 calendar-approved sessions for the prior stock-history audit, 202 audited market sessions, 195 market totals added, 40 sessions with transaction counts, and 40 broker sessions after update. These are separate counts and must not be conflated.
- The starter archive reports 525 matching Jaljala OHLCV filenames; 25 corresponding files differ between the SMC and history-starter repositories. Preserve both source versions until row-level comparison.
- Urekmazino69/Nepse-floorsheet-and-indices has 603 floorsheet files (publisher/tree range 2024-01-02 to 2026-08-26) and 6,429 index files. The inventory is path-level metadata, not proof of trading-session completeness.
- The archive inventory records 658 SocrateAI floorsheet files through 2026-11-19 and 179 SamirWagle floorsheet files through 2026-11-24. Rights/provenance restrictions differ by source; do not infer permission from public accessibility.
- Existing one-session Urek validation covers 2024-01-02 only. It must not be generalized to the full archive.

## Deliverable A — canonical session calendar

Create a versioned calendar table with one row per candidate date and at least:

- `session_date` (ISO Gregorian date)
- `calendar_status`: `confirmed_session`, `confirmed_non_session`, `candidate_unverified`, or `conflict`
- `evidence_source`, immutable source ref/commit, source record locator, and evidence hash
- `evidence_type`: official exchange notice, complete market tape, independently corroborated EOD, or secondary publisher
- `observed_at` and `known_at` timestamps, where available
- `decision_reason`, reviewer, and revision

Rules:
1. Never infer a session from weekday patterns or a date-stamped file alone.
2. Prefer official exchange evidence; where unavailable, require independent corroboration and label the evidence tier.
3. Keep conflicting evidence visible; do not force a binary answer.
4. Preserve calendar revisions so historical decisions can be reconstructed as-of a past date.
5. Keep Nepal local session date distinct from UTC retrieval timestamp.

## Deliverable B — source coverage matrix

Produce a source-separated matrix at (source, dataset/table, date, symbol/instrument) grain where the source supports that granularity. Include:

- expected session status from the versioned calendar
- file/partition presence, source path, pinned commit/revision, blob SHA or LFS SHA-256, byte size
- rows seen, accepted, quarantined, duplicate keys, invalid keys, and audit result
- symbol count and instrument-universe mapping version
- earliest/latest observation and retrieval timestamp
- rights/provenance status: `cleared`, `restricted`, `unknown`, or `review_required`
- overlap status against each other source: identical, compatible, conflict, or not comparable
- explicit missing-session reason; absence of a file is not automatically a missing exchange session

Do not collapse source coverage into one percentage. Report separate file coverage, confirmed-session coverage, row-validation coverage, instrument coverage, and cross-source reconciliation coverage.

## Deliverable C — Hugging Face metadata manifest

Extend the manifest-only inventory (no download by default) to persist one record per file with:

- dataset repo and immutable revision/commit
- repository path, dataset/table category, path-derived date (nullable)
- Hub blob OID, LFS SHA-256 (when present), declared byte size
- inventory timestamp and listing completeness/pagination status
- download status (not_requested, downloaded, skipped, failed), local SHA-256 and byte count only after an actual download

A missing LFS hash or missing path date must remain null, not be synthesized. Manifest generation must be deterministic for the same pinned revision.

## Source-specific controls

- Keep raw floorsheet trades separate from broker/day aggregates.
- Broker codes identify execution channels, not beneficial owners.
- Keep adjusted and unadjusted EOD in separate tables and attach corporate-action evidence before any adjustment.
- Preserve the 25 differing Jaljala ticker files as separate source versions until row-level reconciliation.
- Quarantine repeated carry-forward OHLCV bars unless a valid session calendar and independent source confirm the row.
- Treat SamirWagle data as cross-check only until storage/use rights are established.
- Do not ingest ShareSansar-derived archives whose data rights are not established by the software license.
- Keep Ankit derived broker flow distinct from raw floorsheet and mark its documented coverage gaps.

## Acceptance gates

1. Calendar: every confirmed session has cited evidence; unresolved dates remain explicit.
2. Manifest: every listed file is pinned, hashed where the source supplies a hash, and inventory pagination is complete or marked incomplete.
3. Coverage: expected sessions are computed only from confirmed calendar rows; candidate/unverified dates are excluded from missing-session claims.
4. Validation: all row counts reconcile to per-file audits; rejected rows are retained in quarantine with reasons.
5. Reconciliation: identical, compatible, conflicting, and non-comparable overlaps are reported separately; no silent overwrite.
6. Rights: restricted/unknown sources cannot be promoted to canonical storage or redistributed.
7. Point-in-time: every derived record has source availability/known-at metadata; backtests cannot see information unavailable at the decision timestamp.

## Immediate implementation sequence

1. Extract and pin the actual approved session-date list behind the starter archive's reported 616 sessions; verify its source and date range.
2. Reconcile that list with the dated market-summary, index, broker, floorsheet, and EOD evidence. Do not infer dates from weekday schedules.
3. Add manifest-only Hugging Face inventory output with immutable revision and file-level hash metadata.
4. Generate source-separated date coverage and conflict reports from the manifests.
5. Only then start bounded bulk downloads for confirmed gaps and row-level audit.

## Explicitly not accepted yet

- Full Urek archive normalization/audit.
- A complete authoritative NEPSE calendar.
- Complete 2014–2026 floorsheet history.
- Canonical OHLCV/floorsheet promotion.
- Complete corporate-action ledger.
- Broker beneficial-owner inference.
- Predictive model training or claims of validated signal accuracy.
