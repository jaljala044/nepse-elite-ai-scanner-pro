# Jaljala repository integration plan

Updated: 2026-11-24

## Confirmed account access

The linked GitHub account has owner/admin/push access to:
- `jaljala044/nepse-smc-data` (public, main)
- `jaljala044/nepse-history-starter` (public, main)
- `jaljala044/Nepse-master-data` (public, main)
- `jaljala044/nepse-automation` (private, main)
- `jaljala044/nepse-elite-ai-scanner-pro` (private, main)

The account owner has confirmed that the Jaljala account and its repositories belong to them and authorizes NEPSE AI to store and use their repository data.

## Initial content inspection

- `nepse-smc-data/AI_UPLOAD_PACKAGE.txt` was readable from GitHub. It contains a 2026-11-20 scanner package and multi-session broker summary fields. The figures are treated as source claims, not independently verified ground truth.
- Earlier repository inspection reported 500 stock OHLCV files / 279,007 bars (2024-03-04 to 2026-11-20), 195 market summaries, 138 benchmark records, 1,558 sector records, 105 index OHLC records, 1,390 index closes, and 41 daily broker summaries. These counts require a fresh reproducible inventory before canonical import.
- The earlier sample showed repeated adjacent OHLCV rows on non-session dates. Keep those rows in raw storage and quarantine them from session-level analytics unless the date is verified as an actual exchange session.
- The sampled floorsheet file has contract number, symbol, buyer, seller, quantity, rate and display-formatted amount. That sample contains no explicit execution-time field; execution time must remain null.
- `nepse-history-starter` is an OHLCV validation/import helper. It is not itself a feed or source of independent authoritative history.
- The private scanner repository already has source registry docs, bounded resumable HF collectors, daily CSV.GZ normalizers, Parquet inspection, a DuckDB source-separated loader and tests. Extend these instead of creating a second pipeline.

## Rights and storage

Owner authorization covers the owner's own repositories. It does not automatically grant rights to redistribute third-party provider data included in those repositories. Keep source provenance and any upstream terms. Keep raw datasets in private object storage/private staging or a private data repository. Do not commit bulk raw data to the application repo. Unknown external-data redistribution rights default to unknown/not approved.

## Integration sequence

1. Pin the commit SHA of each Jaljala source repo at collection time.
2. Inventory all files and sizes; produce SHA-256 for each file and an immutable batch manifest.
3. Audit every OHLCV, index and floorsheet file independently. Report session coverage, gaps, duplicate keys, OHLC anomalies, repeated carry-forward rows, contract-date parsing, amount parsing and quantity × rate reconciliation.
4. Maintain explicit null execution times where no timestamp exists.
5. Compare Jaljala source rows with the Ankit, Urek, Samir and other available archives without choosing a winner silently.
6. Quarantine duplicate/conflicting or unverified non-session rows; retain original bytes and rejection reason.
7. Build bronze tables per source; only build canonical silver after audit acceptance and documented source semantics.
8. Store broker data as broker-code execution channel aggregates; do not infer beneficial owner, institutional identity or intent.
9. Validate the data availability timestamp before allowing any historical scanner feature to use it.
10. Publish an auditable report and link each accepted canonical row back to source file hash, row identity and parser version.

## Acceptance gates

- [ ] Pinned commits and source manifest are recorded for every imported batch.
- [ ] Full file inventory reconciles to all retrieved files.
- [ ] 100% of rows have parser outcome (accepted or quarantined with reason).
- [ ] Calendar exceptions and repeated carry-forward dates are resolved or quarantined.
- [ ] Contract key/date semantics are independently verified.
- [ ] Floorsheet amounts are normalized without discarding the original display field.
- [ ] Missing execution times remain null.
- [ ] Source conflicts are exposed in a reconciliation report.
- [ ] Corporate actions and symbol changes are separate ledgers.
- [ ] Re-import is idempotent.
- [ ] Point-in-time backtests enforce event, publication, retrieval and availability cutoffs.
- [ ] No bulk data or credentials are committed into application source control.

## Current status

Repository ownership/access is confirmed and the application repository now contains the Historical Data Vault architecture and this integration plan. This commit does not itself download or import data. Full archival ingestion, database writes, live provider integration and automated scheduling remain unverified and are not marked complete.
