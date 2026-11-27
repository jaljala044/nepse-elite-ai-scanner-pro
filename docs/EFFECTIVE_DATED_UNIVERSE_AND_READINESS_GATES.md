# Effective-Dated Universe and Replay Readiness Gates

## Step 28 — point-in-time security universe
The universe timeline is keyed by permanent `security_id`, not ticker alone. Each row is a status event with `effective_from`, `listing_status`, and optional inclusive `effective_to`. Later IPOs enter only from their effective listing date. Suspended and delisted securities remain in the historical inventory but are not expected to produce OHLCV while inactive. Duplicate effective dates, invalid intervals and overlapping explicit intervals block admission.

The panel now measures expected OHLCV only on sessions where each security is active. It no longer requires every name to have existed at the sample start. This reduces, but does not by itself eliminate, survivorship bias: the supplied source still must include every historical and delisted security and permanent-ID changes must be reconciled.

## Step 29 — readiness, corporate actions and strategy gates
Panel assembly requires a point-in-time readiness report in READY or PARTIAL state. BLOCKED or missing readiness blocks panel creation. PARTIAL can admit the core research panel, but optional feeds are not imputed: a strategy is eligible only when its declared optional datasets are present. Broker-footprint, IDPAT broker/floorsheet and fundamental strategies are gated separately.

Corporate-action rows affecting a security must match a supplied two-source reconciliation artifact before adjusted history is admitted. Explicit reconciled factors are applied only to pre-effective-date bars; turnover is preserved. Unreconciled affected securities are excluded. Suspension/delisting membership is handled by the effective-dated universe timeline.

## Safety and limitations
This is research-only. No live data is fetched, no publisher authenticity is established, and no adjustment factor is inferred. Distinct publisher labels do not independently prove source independence. A complete timeline must include delisted securities; missing history remains a material bias risk. Replay blocks strategy/horizon/partition combinations whose required optional feeds are absent. No empirical performance, calibrated probability, production readiness or BUY/SELL recommendation is asserted.
