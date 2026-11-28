# Steps 72–73 — schema profiles and cross-dataset reconciliation

## Step 72: versioned source schema profiles
- Adds a profile validator requiring a stable profile ID/version, source and publisher IDs, dataset kind, explicit semantic-to-source column mapping, reviewer, approval reference and timezone-aware approval timestamp.
- Enforces required semantic fields, rejects unknown fields and duplicate/blank source columns, and emits a deterministic SHA-256 profile fingerprint.
- A valid profile records human approval only; it does not authenticate a publisher or prove that a mapping matches an official endpoint.

## Step 73: cross-dataset reconciliation
- Compares bounded OHLCV against official calendar open/closed dates, effective-dated security lifecycle, corporate-action ex-dates, CDSC first-trade dates, floorsheet scope, sector sessions and broker-summary OHLCV keys.
- Emits severity-tagged blockers/warnings and per-dataset coverage counts. Broker IDs remain execution-channel identifiers; anomalies are not manipulation proof.
- Never silently adjusts prices, treats missing corporate-action rows as proof of no events, or promotes data.

## Verification boundary
Synthetic tests only. No real NEPSE/CDSC endpoint or records were acquired. Human review, source authenticity, completeness, licensing and capture remain external prerequisites. Backtest admission, canonical promotion and production stay disabled.
