# Historical Data Vault — Architecture and Operating Rules

Status: design baseline (2026-11-24)
Owner-controlled data repositories: `jaljala044/nepse-smc-data`, `jaljala044/nepse-history-starter`.
Application repository: `jaljala044/nepse-elite-ai-scanner-pro`.

## Purpose

Build a reproducible, append-only archive for NEPSE market-wide and instrument-level history. Preserve source evidence independently from normalized datasets and derived research features. No source is treated as authoritative merely because it is available or internally owned.

## Repository roles

- `nepse-smc-data`: owner-controlled collection and research archive. Preserve its existing raw files and reports; do not overwrite or silently normalize them in place.
- `nepse-history-starter`: import/validation helper and user-maintained OHLCV source segment.
- `nepse-elite-ai-scanner-pro`: application code, schemas, ingestion adapters, QA reports, scanner logic and documentation. Large or licensed raw market datasets remain outside Git source control.
- `nepse-automation`: candidate location for workflow orchestration only after its current contents and existing schedules are reviewed.

## Data layers

1. **Source registry** — provider, repository or endpoint, dataset name, source-owner, access basis, terms/license URL and version, permitted use, redistribution status, expected schema, timezone, session-date semantics, known coverage and limitations.
2. **Raw archive** — immutable original bytes, source path/URL, retrieval timestamp (UTC), claimed session date, response headers where available, SHA-256, repository commit/tree reference, file size and ingestion run ID.
3. **Quarantine** — malformed, duplicate, conflicting, non-session, stale, incomplete, or rights-uncertain material. Preserve raw row and reason; do not silently delete it.
4. **Bronze** — parsed source-shaped records with all original fields and source values retained.
5. **Silver** — validated canonical records, source-specific and versioned. Never merge sources without retaining source identity and row-level lineage.
6. **Gold/research features** — derived indicators, broker aggregates, footprints, pattern labels, market regimes and scenario outputs. Each feature records input record IDs, code version, parameters, decision timestamp and calculation timestamp.

## Required dataset families

- Daily instrument OHLCV and turnover, separated by source and adjusted/unadjusted status.
- Exchange and sector indices, with index definitions and source timestamps.
- Daily market breadth, turnover and participation summaries.
- Floorsheet executions: contract, symbol, buyer/seller broker codes, quantity, rate, amount, trade date and execution time when genuinely supplied.
- Broker-session aggregates, with aggregation window and input floorsheet coverage stated.
- Corporate actions: dividends, bonus, rights, splits, mergers, symbol changes and effective dates.
- Listing/universe history, including ticker lifecycle and security type.
- Trading-session calendar and exceptions, sourced from verified evidence.

## Non-negotiable integrity rules

- Point-in-time/no-lookahead: a signal for session T may use only records demonstrably available by that decision cutoff. Later corrections or delayed uploads cannot leak into historical simulation.
- Distinguish event/session time, provider publication time, retrieval time and system ingestion time. Missing event time remains null; never invent it.
- Raw files are immutable. Any correction becomes a new version with a supersedes relationship and reason.
- Record SHA-256 for every raw file and retain repository commit/tree ID for Git-based sources.
- A file's date in its name is not proof of session date. Verify against row fields, contract encoding and a session calendar.
- Do not infer market sessions solely from weekday rules. Maintain a dated, evidence-linked calendar including changes and exceptional sessions.
- Validate OHLC bounds, positive prices, volume/turnover arithmetic, duplicates, symbol validity, session membership, row counts, coverage gaps and source overlaps.
- Preserve source-specific conflicts. Never average, choose newest, or silently overwrite a discrepancy.
- Corporate-action adjustments are a separate transformation ledger. Never mix adjusted and unadjusted prices.
- Broker codes identify exchange execution channels, not beneficial owners or intent. No claims of institutional accumulation/manipulation without independently justified evidence.
- Derived broker metrics must retain gross buys/sells, net quantities/values, coverage, aggregation window, and missing sessions.
- Keep large raw datasets and sensitive provider responses in private object storage or a private data volume, not public Git. Git should hold code, schemas, small synthetic fixtures, manifests and QA summaries.
- Never commit credentials, API tokens, cookies, private API responses without permission, or account exports containing personal information.
- For external repositories, code license and data license are distinct. Confirm rights to store, process, and redistribute separately before copying.

## Minimum source manifest fields

`source_id`, `provider`, `dataset`, `source_uri`, `source_commit`, `source_file_path`, `license_or_terms_uri`, `access_basis`, `storage_allowed`, `processing_allowed`, `redistribution_allowed`, `retrieved_at_utc`, `claimed_session_date`, `coverage_start`, `coverage_end`, `sha256`, `byte_size`, `schema_version`, `parser_version`, `ingestion_run_id`, `quality_status`, `quarantine_reasons`.

Unknown rights fields default to `unknown`, not `allowed`.

## Acceptance gates before canonical use

1. Source rights and access are documented.
2. Complete file inventory and coverage report exists.
3. Raw hashes and source revisions are recorded.
4. Schema and timezone/session semantics are documented.
5. All validation exceptions are categorized and reviewed.
6. Source overlap reconciliation is completed and discrepancies remain queryable.
7. Corporate-action and symbol-history handling is explicit.
8. Walk-forward tests prove no future data is read by a past decision.
9. Re-import is idempotent and produces the same canonical records and report.
10. Backups, retention, access control and recovery are tested.

## Immediate engineering sequence

- Inspect the existing collection and audit implementations in the app repository before adding duplicate pipelines.
- Inventory owner-controlled Jaljala repositories and pin the source commit for each collected batch.
- Audit existing OHLCV/floorsheet rows, especially repeated carry-forward dates, contract-date parsing, missing execution times and compact amount strings.
- Download only to private staging; produce a manifest and independent QA report first.
- Add source-specific bronze loaders and canonical silver tables only after the report passes review.
- Never push raw market history into this application repository by default.
