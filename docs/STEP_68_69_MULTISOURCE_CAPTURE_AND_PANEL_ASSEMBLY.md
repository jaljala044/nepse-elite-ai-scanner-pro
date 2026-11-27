# Steps 68–69 — multi-source capture and panel quality review

## Step 68 — required dataset capture set

The multi-source coordinator accepts only separately reviewed source-contract reports and matching operator-injected transports. It captures the required dataset types sequentially, enforces unique capture IDs, validates every raw package against its own approved registry entry and reports missing/failed dataset types. Supported contract dataset types include official EOD OHLCV, market calendar, security master, corporate actions, floorsheet, CDSC first-trade evidence, sector indices and broker summaries.

It does not guess endpoints, share credentials, infer source schemas or normalize non-OHLCV datasets. Dataset-specific parsers and independent source reconciliation remain separate gates. A capture set cannot claim publisher authenticity or exchange-wide completeness.

## Step 69 — panel quality-review orchestration

The panel pipeline requires a passing source-reconciliation report and fully accepted OHLCV ingestion reports before invoking the existing lifecycle panel assembler, replay preflight and quality dashboard. It returns the deterministic dataset fingerprint and coverage diagnostics. A ready panel is still only ready for independent human review; it does not auto-admit historical replay, promote canonical data or enable production.

## Verification boundary

Tests use synthetic payloads and data.example.test. No actual NEPSE/CDSC source, credential, endpoint or historical dataset is included. Real source contracts, licensing, secure transport, durable raw storage, official session and identity evidence, corporate-action verification and independent completeness review remain prerequisites.
