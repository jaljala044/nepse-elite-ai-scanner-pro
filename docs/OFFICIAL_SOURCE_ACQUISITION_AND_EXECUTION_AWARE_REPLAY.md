# Official Source Acquisition and Execution-Aware Replay

## Step 42 — Governed source acquisition

`backend/app/nepse_source_connectors.py` adds a public HTTPS GET adapter around the existing source registry and raw-capture intake. It requires an explicitly approved registry record, dataset authorization, matching canonical host, approved rights status, point-in-time timestamps, a bounded response size, HTTP 200, and no cross-host redirect. The captured bytes are passed through the existing SHA-256 receipt and CSV schema validation.

No NEPSE/CDSC endpoint is guessed or hardcoded. Operators must supply and review the actual canonical host and endpoint after confirming that access and reuse are permitted. The connector supports no credentials, cookies, private endpoints or authenticated sessions. It does not establish publisher authenticity or independent corroboration; registry governance and external source verification remain mandatory. The default transport is standard-library HTTPS with redirects disabled; tests use an injected transport.

## Step 43 — Integrated execution-aware replay

`backend/app/scanner_execution_aware_replay.py` groups orders independently by six-strategy ID, horizon and sample partition. Each order is passed through the verified event queue simulator. Only resulting queue fills become executions, and each execution inherits the event's source/evidence provenance. Those fills then flow into the daily mark-to-market engine, including cash, inventory, transaction costs and unrealized drawdown.

Sell orders are rejected unless caller-supplied settlement/inventory evidence is verified, available by order time, and explicitly says the quantity was sellable by then. Opening holdings and cost basis must also be seeded from verified point-in-time inventory evidence so sell fills are accounted for correctly. The module does not invent a T+2 calendar or infer sellable quantity. Every open position must have a verified daily mark; missing marks block valuation. Strategy/horizon/partition portfolios are isolated to avoid leakage and capital cross-contamination.

## Validation and limits

- Deterministic unit tests cover host allowlists, redirects, HTTP errors, response limits, content-length checks, provenance, queue fills, settlement evidence, partial fills, missing marks and partition isolation.
- This is a research adapter and simulator, not a live order router.
- No live NEPSE/CDSC endpoint has been configured or accessed by these changes.
- No real exchange event feed, official historical panel, circuit-lock/auction matching, market impact, hidden liquidity, taxes or corporate-action processing is supplied.
- No strategy accuracy, probabilities, backtest performance or BUY/SELL recommendations are claimed.
- Production remains disabled.
