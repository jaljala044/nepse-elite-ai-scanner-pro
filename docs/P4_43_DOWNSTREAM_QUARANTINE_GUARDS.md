# Downstream quarantine guard — runtime contract and CI repair

## Enforcement points

- OHLCV persistence rejects row-level quarantine markers before opening the database.
- Runtime quarantine keys are loaded from a SHA-256-pinned exception ledger.
- When required, the ledger must also pin exact source commits for both the SMC data and history starter repositories.
- Invalid signatures/hashes, malformed ledger schema, duplicate exception IDs, noncanonical dates and stale source commits fail closed.
- Historical gaps that intersect an exception date block the entire affected symbol history; indicators and broker context must not bridge a quarantined session.
- Broker-memory promotion rejects explicit row quarantine markers, batch conflicts, pinned historical exceptions and invalid runtime ledger configuration.
- Feature snapshots remove all price and broker rows for affected symbols.
- Scenario metrics and walk-forward evaluation validate constituent-session lineage whenever the ledger is enabled or lineage is supplied.

## Configuration

- `NEPSE_QUARANTINE_LEDGER`: path to the retained exception ledger.
- `NEPSE_QUARANTINE_LEDGER_SHA256`: exact SHA-256 of the ledger bytes.
- `NEPSE_QUARANTINE_SOURCE_COMMITS`: JSON object pinning both source repository commit SHAs.
- `NEPSE_REQUIRE_QUARANTINE_LEDGER=1`: require all three settings; missing pins fail closed.

## CI repair

The initial backend test run exposed a real boundary bug: `persist_import` projected each row to only its date before calling the quarantine predicate, dropping row-level quarantine fields. The persistence guard now passes the complete row to the predicate. Regression coverage includes all marker variants, pinned source versions, digest tampering, duplicate exception IDs, noncanonical dates, symbol-history gaps, broker promotion, feature filtering, and scenario/walk-forward constituent lineage.

## Limitations

The ledger blocks records; it does not validate source correctness or promote any row to canonical status. Its source commit pins and SHA-256 establish reproducibility/integrity only. The runtime gate is optional unless `NEPSE_REQUIRE_QUARANTINE_LEDGER=1`; production deployment must explicitly set this flag and provide reviewed pins. No BUY/SELL recommendation or production admission is enabled by this change.
