# Verified historical bundles and exchange execution simulation

## Step 38 — Reproducible historical dataset bundle
The bundle builder accepts exact captured CSV bytes for the canonical dataset types, uses the existing strict intake validator, computes SHA-256 from the bytes, runs historical dataset readiness and reconciles corporate actions using the existing independent-publisher requirement. It emits a deterministic bundle manifest and explicit research-assembly eligibility. It does not download or authenticate source data. A READY manifest is only a research-data admission gate.

## Step 39 — Exchange-aware execution scenario
The execution simulator consumes timestamped, provenance-checked price bands, order-book depth and traded volume. It models partial fills, volume participation, limit-price constraints, tick rounding, simple market impact, halted sessions, upper-circuit buy locks, lower-circuit sell locks and sellable-inventory limits. Unfilled quantity remains unfilled; no candle-close fill is invented.

## Limits and governance
Queue priority, order cancellations, hidden depth, auction matching and intraday order-book evolution are not modeled. Price bands and sellable inventory must be supplied as verified evidence; this code does not assert current exchange or settlement rules. No live order routing, real historical dataset, strategy accuracy or performance claim is created.
