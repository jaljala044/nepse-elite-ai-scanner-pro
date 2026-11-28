# Steps 98–99 — trusted distribution sources and BENH history

## Step 98: NEPSE-derived distribution source policy
Per project-owner instruction, ShareHub, Chukul, ShareSansar, Punji, Merolagani, NepseAlpha, ChartNepali and Bullhouse are registered as trusted NEPSE-derived distribution channels for collection and research. This is a project trust assumption about their data lineage, not an independently audited certification statement.

Do not reject a record solely because it is distributed by one of these providers or because a primary NEPSE PDF is not attached to every row. Collect useful records and validate them using:
- provider, URL/page/endpoint and capture time;
- raw payload and SHA-256;
- symbol/security identity, session date and field schema;
- duplicates, missing sessions, impossible OHLC, volume/turnover anomalies;
- comparison with other available websites/apps and exchange records where available.

Statuses distinguish quarantined, trusted-distribution pending cross-check and corroborated. Pending records may support research with provenance and confidence labels; production signal eligibility requires corroboration in this initial policy. A conflicting record is not silently averaged.

## Step 99: BENH first-trade reconciliation
Compare earliest BENH ShareHub/other chart candle with earliest BENH floorsheet execution. Track floorsheet archive coverage bounds and any official listing date separately. A first trade is corroborated only when chart and floorsheet earliest dates agree, coverage is established, and no date precedes the official listing date. Chart history alone remains a usable price-history candidate but does not prove the listing date or complete first-trade history.

## Boundaries
This implementation adds deterministic policy and reconciliation logic. It does not itself download ShareHub/Chukul/Punji records, establish real archive coverage, or verify BENH dates. No actual BENH records were inserted. Production signal eligibility still requires the project's remaining data, risk and OOS gates.
