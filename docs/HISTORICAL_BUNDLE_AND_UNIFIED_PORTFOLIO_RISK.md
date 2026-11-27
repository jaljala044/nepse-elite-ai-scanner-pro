# Steps 44–45: Historical Dataset Bundles and Unified Portfolio Risk

## Step 44 — Repeatable historical acquisition

`nepse_source_bundle.py` accepts an explicit list of registered CSV endpoints. Each item is fetched only through the approved-source HTTPS connector, parsed from the exact captured bytes, SHA-256 recorded and checked against the existing dataset schema. A deterministic manifest hash records the requests accepted, failures and readiness result. The bundle then runs the historical dataset readiness assessment across OHLCV, session calendar, effective-dated universe and corporate-action rows, plus optional feeds.

No URL discovery, guessed endpoints, implicit pagination, or authentication is performed. The operator must enumerate archive pages/date partitions and provide the official source registry, rights approval and exact endpoints. Historical panel promotion is permitted only when the readiness result is READY and no acquisition request failed. PARTIAL/BLOCKED remains quarantined. Corporate-action two-source factor reconciliation remains a separate mandatory gate.

## Step 45 — Unified shared-capital risk

`scanner_unified_portfolio_risk.py` pools executions from strategy/horizon runs into one shared capital ledger, defaulting to untouched OOS only. It applies configurable gross, symbol, sector and open-symbol limits; checks verified point-in-time circuit bands for every fill; rejects missing market controls, out-of-band executions, duplicate execution IDs, insufficient shared cash and sells that exceed both internal holdings and verified sellable inventory. Accepted executions are valued through the daily mark-to-market engine.

This is a research allocation screen, not a live exchange router. The portfolio is shared across strategy/horizon candidates rather than summing six independent strategy equity curves.

## Evidence and limits

- The source bundle's capture manifest is SHA-256 reproducible and every row remains linked to a source receipt.
- No official endpoint is hardcoded or presumed. A READY test fixture is synthetic contract evidence, not a claim that NEPSE data was downloaded.
- Circuit bands and settlement sellability must be supplied from verified exchange/depository evidence available at execution time.
- OOS-only is the default; training/validation runs are rejected from the unified report.
- No taxes, price impact, hidden liquidity, exchange auctions, corporate-action cash entitlements or production routing are implemented.
- No live accuracy, strategy profitability or BUY/SELL claim is made.
