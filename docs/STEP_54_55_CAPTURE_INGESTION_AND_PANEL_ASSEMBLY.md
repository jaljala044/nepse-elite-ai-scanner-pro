# Steps 54–55 — captured OHLCV ingestion and pilot panel assembly

## Step 54: raw capture ingestion

Added `backend/app/historical_pilot_ingest.py`. It accepts only a capture report already marked CAPTURE_VALIDATED, re-hashes the exact raw page bytes, requires an explicit one-to-one source-column map, parses CSV OHLCV, validates dates/prices/volume, preserves page/capture/source IDs and hashes, and records deterministic row fingerprints. A changed payload, future capture, missing column, malformed row or duplicate symbol/session blocks the ingestion report. It does not fetch URLs or infer source schemas.

## Step 55: deterministic panel assembly

Added `backend/app/historical_pilot_assembler.py`. It joins validated ingestion reports to effective-dated permanent security identities and the evidence-backed expected-session calendar. Identical cross-publisher bars can be combined with full source provenance; conflicting bars are quarantined. An optional minimum independent-publisher threshold can be enforced. The existing panel-readiness validator then checks complete symbol/session coverage, point-in-time timestamps and corporate-action reconciliation.

## Evidence and authorization boundary

No real official capture payloads were present in this implementation run. Unit tests use synthetic fixtures only. Consequently no actual NEPSE historical panel is declared assembled or ready. SAIL remains unresolved until official first-day evidence is supplied. Backtest admission, canonical promotion and production remain disabled even when synthetic tests produce a ready bounded panel. Agreement between publisher records does not prove publisher independence or exchange source completeness.
