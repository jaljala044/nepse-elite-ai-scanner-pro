# Immutable market-data evidence store

## Purpose

The evidence store is a bronze layer between immutable raw capture and any
future canonical market-data tables. It records exactly what was received,
when it was received, where it came from, which parser version processed it,
and which normalized source row produced each observation.

It is deliberately separate from:
- the interactive API upload database (`backend/app/database.py`), which is
  user-upload history and not a canonical market-data store; and
- the source-separated research warehouse, which retains provider-specific
  Parquet/CSV tables for reconciliation.

## Persistence model

`backend/app/evidence_store.py` uses a dedicated DuckDB database
(`NEPSE_EVIDENCE_DATABASE`, defaulting to `backend/data/evidence.duckdb`)
and the existing content-addressed `raw_capture.persist_capture` filesystem
store.

| Table | Purpose |
|---|---|
| `raw_source_objects` | One immutable payload object per source ID and SHA-256 |
| `source_captures` | Capture event, source URL, request/receipt times, parser version, rights-status declaration and manifest |
| `normalized_evidence_records` | Row-level parsed observations linked to source object, fetch ID, row number and parser version |

Raw payload bytes and their manifest remain stored by source/date/SHA-256.
The DuckDB catalog indexes those objects; it does not replace or mutate them.

## Admission and safety rules

- SHA-256 and byte count are recomputed from the exact payload bytes and must
  match the supplied capture manifest.
- Request and receipt timestamps must be timezone-aware; request time cannot
  follow receipt time.
- Availability is assigned from capture receipt time, not an embedded source
  field. A row claiming availability after receipt is rejected.
- Source row numbers must be unique positive integers within a capture.
- Session dates, when present, must be ISO `YYYY-MM-DD`.
- Caller-supplied validation and finality labels are discarded. Every newly
  persisted row is forced to `source_validation_status=review_required` and
  `finality_status=provisional`.
- Re-importing an identical capture is idempotent. Reusing a fetch ID with
  different immutable metadata fails closed.
- Raw bytes are retained even when normalized records are rejected; they are
  evidence, not approved prices.

## Production boundary

This PR does **not** verify a publisher, source rights, exchange finality,
calendar membership, corporate actions, or data completeness. A source ID,
URL, rights label, parser success, payload hash, or passing test is not proof
that the underlying market record is authoritative.

The store has no public promotion endpoint. Its verified-only read filter
returns no rows until a separate source-trust and review process is designed
and implemented. Consequently:
- this layer is not yet the canonical silver/gold store;
- it is not connected to live scanner scoring or market-health components;
- no market score, trade signal, or BUY eligibility can be derived from it;
- current market-health readiness remains UNKNOWN / PRESERVE_CAPITAL.

## Capture pipeline integration

The fixture-oriented capture pipeline now persists raw capture metadata and
normalized observations through this store before building point-in-time
research features. The feature calculation remains a research fixture path;
persisted observations stay provisional and are not promoted by the feature
calculation.

Run backend tests from `backend/`:

```bash
python -m unittest tests.test_evidence_store tests.test_capture_pipeline
```

Synthetic fixtures validate persistence and fail-closed behavior only. They
do not establish live NEPSE data availability or source authority.
