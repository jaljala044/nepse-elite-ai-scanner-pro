# Operator source-evidence intake — 2026-11-27

This is an intake specification, not a claim that data has been collected or verified.

## Required inputs before Step 56 can pass

Supply one immutable capture artifact for every key configured in the pilot run:
- capture manifest JSON;
- exact raw response bytes for every page, preserved without normalization;
- SHA-256 for each raw page;
- final-page marker and contiguous page numbers beginning at 1;
- request URL, HTTP status and content type;
- capture ID, source ID, publisher ID;
- captured_at, available_at, window_start and window_end with timezone offsets;
- explicit capture_complete declaration and expected_page_count;
- operator-reviewed approved source registry entry with source_id, publisher_id, review_status=approved and allowed_hosts.

For each pilot cohort symbol, supply official first-contract evidence:
- symbol and permanent security_id;
- official contract_id and source_record_id;
- trade_date, quantity and price;
- exact raw SHA-256 and source capture reference;
- final and verified record status;
- available_at and captured_at;
- proof the official day's capture is complete.

## Intake controls
1. Preserve raw bytes; never rewrite or re-encode before hashing.
2. Do not invent endpoint URLs, source IDs, publisher identities or completeness claims.
3. Record failed requests and missing pages; never silently omit them.
4. Keep first-trade boundary, daily completeness, publisher authenticity and exchange-wide completeness as separate assertions.
5. Do not infer first listing or first trade from the oldest available chart candle.
6. If any required artifact is absent, mismatched, duplicated or after the decision cutoff, leave the cohort blocked.
7. A passing technical reconciliation is still not human approval, canonical promotion, permission to backtest or production approval.

## Required reports
- per-capture validation report with exact errors and verified page hashes;
- first-trade report per cohort symbol, including unresolved symbols;
- source reconciliation status;
- replay preflight status and deterministic dataset manifest hash;
- independent reviewer decision, reviewer identity, decision timestamp and scope.

## Current status
The Steps 56–57 workflow tests use synthetic fixtures. No real official NEPSE/CDSC artifacts were supplied in that run. The actual source reconciliation therefore remains blocked until the operator supplies the required raw artifacts and reviewed registry. No historical replay has been executed and no dataset has been promoted.
