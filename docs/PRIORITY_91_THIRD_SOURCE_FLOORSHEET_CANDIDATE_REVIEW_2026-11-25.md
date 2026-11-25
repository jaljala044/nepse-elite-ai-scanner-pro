# Priority 91 — third-source floorsheet and pipeline lead review (2026-11-25)

## Decision

Register Ankit Sanjyal's NEPSE Market Data dataset and its pipeline as a **high-priority independent source candidate for multi-date reconciliation**. This is a source-discovery result, not an ingestion or validation pass. No files from this dataset were downloaded or parsed in this review, and no data is promoted.

## Candidate references

- Dataset card: https://huggingface.co/datasets/AnkitSanjyal/nepse-market-data
- Pipeline repository: https://github.com/ANKITSANJYAL/nepse-pipeline
- Pipeline project notes: https://ankitsanjyal.github.io/projects/nepse-pipeline.html

## What the publisher currently claims

The public dataset card describes several separate tables:
- `floorsheet/`: executed-contract records, claimed source NEPSE, beginning 2026-08-19, with a stated gap from 2026-08-26 through 2026-11-18.
- `eod_price/`: NEPSE end-of-day prices, described as rolling 365-day history.
- `eod_history_ext/`: ShareSansar-compiled extended daily history, explicitly marked as a second source.
- `broker_flow_daily/`, `bars_1m/` and `daily_stats/`: derived tables, not raw independent sources.

The dataset card's viewer reports microsecond timestamp fields and broker-aware trade data. The card also describes the dataset as research/educational use and says commercial redistribution may require a NEPSE licence. Its metadata licence is shown as `other`; the code repository's MIT licence must not be treated as a licence for upstream market data.

The pipeline README describes an immutable bronze layer (raw gzipped API responses), typed silver Parquet and derived gold tables. It reports that the NEPSE floorsheet endpoint serves the current session rather than arbitrary historical dates, so missed daily captures cannot be backfilled. It also describes completeness checks against upstream row counts and quantity/turnover conservation. These are publisher/author claims pending independent verification.

## Why this source matters

This may provide a third comparison point beyond the existing Samir/MeroLagani-derived and SocrateAI files. It also appears to expose raw capture provenance and per-contract broker IDs, which could help validate timestamp semantics and broker footprints. The floorsheet coverage is recent and has a documented gap, so it does not replace the older archive or satisfy the 90–120-session historical target by itself.

## Required verification before use

1. Pin the exact dataset revision and recursively inventory all floor-sheet Parquet paths, sizes and hashes.
2. Download one overlapping date that is present in the existing SocrateAI and Samir archives; retain the original Parquet bytes and revision metadata.
3. Inspect the physical Parquet schema and sample rows. Confirm whether contract ID, business date, trade timestamp, symbol, buyer, seller, quantity, rate and amount are present and their actual types.
4. Reconcile contract IDs and all shared fields against both existing sources; separately compare daily contract count, quantity and turnover.
5. Check timestamp timezone, date boundary, duplicate semantics, pagination completeness evidence and any publisher-specific row exclusions.
6. Verify whether this dataset is genuinely independent of the other archives by tracing its raw capture route and source commit. Do not infer independence from a different publisher name.
7. Record rights state separately for code, raw exchange data and derived outputs. Do not assume the MIT code licence grants rights to market data.
8. Keep all findings review-only until provenance, rights and row-level reconciliation pass.

## Immediate blocker

This session could inspect the public dataset card and the pipeline README, but did not retrieve the Parquet payloads or pin a dataset revision/hash. Therefore Priority 91 is **source lead registered; data comparison pending**, not complete.

## References reviewed

- Hugging Face dataset card and Data Studio: https://huggingface.co/datasets/AnkitSanjyal/nepse-market-data
- Pipeline README: https://github.com/ANKITSANJYAL/nepse-pipeline/blob/main/README.md
- Pipeline technical overview: https://ankitsanjyal.github.io/projects/nepse-pipeline.html

