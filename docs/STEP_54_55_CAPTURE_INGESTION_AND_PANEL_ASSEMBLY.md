# Steps 54–55 — captured OHLCV ingestion and panel assembly

## Step 54: raw capture ingestion

The importer now requires the exact manifest fingerprint emitted by the capture validator, matching capture/source/publisher identity, and a one-to-one match between manifest page locators and validator page proofs. It re-hashes the raw bytes again before CSV parsing. Duplicate page IDs, duplicate page numbers, missing or extra columns, malformed rows, duplicate symbol/session rows, changed manifests and changed payload bytes block the entire report.

OHLC values must be finite and positive, OHLC geometry must be valid, and volume must be a positive whole-share count. Non-finite values, zero/fractional volume, blank fields and malformed CSV rows are rejected rather than silently normalized away. A deterministic row fingerprint binds OHLCV to source, publisher, capture, payload, page, CSV line, raw hash and manifest hash.

## Step 55: deterministic panel assembly

Panel assembly verifies that every row's source/publisher/capture/manifest identity matches its ingestion report, validates timestamp and OHLCV types again, and recomputes the row fingerprint before using the row. It rejects duplicate raw-row locators and preserves every accepted source-row locator in the assembled panel.

The old minimum_independent_sources argument is retained for compatibility, but its threshold counts distinct publisher identifiers only. Different publisher IDs may still mirror or inherit the same upstream feed; that count is not proof of independence. Independent-source classification requires separate, reviewed publisher-lineage evidence.

## Evidence and authorization boundary

No real official capture payloads were present in this implementation run. Unit tests use synthetic fixtures only. Consequently no actual NEPSE historical panel is declared assembled or ready. SAIL remains unresolved until official first-day evidence is supplied. Backtest admission, canonical promotion and production remain disabled even when synthetic tests produce a ready bounded panel. Agreement between publisher records does not prove publisher independence or exchange source completeness. The manifest and row digests provide integrity/linkage checks, not cryptographic publisher authentication.
