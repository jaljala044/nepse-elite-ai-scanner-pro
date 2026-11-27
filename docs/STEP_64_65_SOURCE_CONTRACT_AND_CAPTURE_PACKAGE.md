# Steps 64–65 — source contract governance and capture package acceptance

## Step 64 — reviewed source contract

The source-contract validator requires an operator-supplied publisher/source identity, explicit dataset kind, HTTPS endpoint on an exact host allowlist, declared content types and pagination behavior, date window, rate limit, credential reference (never secret values), authority-evidence reference, licence/access-policy review and dated human approval. It rejects embedded credentials/secrets and contracts reviewed after the decision cutoff.

A passing contract produces a minimal approved-registry record and capture-runner specification. This is a workflow approval assertion, not independent proof of publisher authenticity. No endpoint, credential or licence is guessed; no network access occurs in this step.

## Step 65 — raw capture package acceptance

The package gate joins the approved contract, completed capture-runner result and exact raw payload bytes. It verifies source/publisher/capture identity, endpoint, window, content type, payload inventory, page hashes and the existing strict official-capture manifest validator. Only a complete validated package is eligible for dataset-specific panel ingestion.

It does not automatically ingest arbitrary dataset kinds, promote canonical data, admit backtests or enable production. OHLCV ingestion still requires explicit column mapping and downstream permanent identity, official session, corporate-action and point-in-time checks.

## Evidence boundary

Tests use synthetic payloads and example hostnames. No live NEPSE/CDSC endpoint, credentials, publisher contract or actual historical data is included. Operator governance, licensing, secure credential retrieval, transport configuration, durable immutable storage and independent completeness review remain required.
