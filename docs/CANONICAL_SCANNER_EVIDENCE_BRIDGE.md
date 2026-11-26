# Canonical evidence to scanner feature bridge

The build_canonical_feature_snapshot function is the only supported bridge from bronze evidence into the descriptive feature pipeline.

- Revalidates the pinned source registry, hash-chained promotion ledger, reviewer HMAC attestation, source policy, row identity, raw payload digest and point-in-time availability.
- Only accepted promotions reach build_feature_snapshot; bronze/provisional rows and secondary-source fallback are never supplied.
- Accepted, signed revocations supersede earlier promotions. Rejected or unsigned revocations do not change canonical state.
- OHLCV, index, market-summary and floorsheet promotions additionally require an exchange_finality=passed attestation before canonical finality is emitted.
- The session calendar is loaded from a server-side evidence CSV whose exact bytes must match a trusted deployment SHA-256 pin. Only explicitly verified-open dates whose retrieval and verification timestamps are no later than decision time are passed downstream.
- Missing canonical rows or calendar evidence returns UNKNOWN / PRESERVE_CAPITAL. The bridge never authorizes BUY and always marks production source claims false.

This is an integration seam, not proof that any live NEPSE source is activated. The runtime source registry remains empty until independently reviewed source policies and reviewer keys are provisioned.


## Official capture ingestion

The command-line importer backend/import_nepse_market_summary_capture.py accepts the existing official market-summary capture report and exact response-body.bin. It verifies the official endpoint, HTTP 200/origin flags, response length and SHA-256, then writes normalized market-summary rows into the bronze evidence store. These rows remain review_required/provisional and cannot enter the canonical feature path until separately promoted. Invalid rows and duplicate session summaries are counted as rejections; missing OHLCV is not synthesized from turnover/trade-count data.

Example:
python backend/import_nepse_market_summary_capture.py --capture-report data/evidence/raw/nepse/market-summary-history/2026-11-26/capture-report.json --storage-root data/evidence/bronze-raw --database backend/data/evidence.duckdb

This is a manual import adapter. The scheduled capture workflow does not yet automatically populate the application evidence database, and the official market-summary source is not yet activated in the trust registry.
