# July 24 2026 volume reconciliation evidence

## Pinned input references
- SocrateAI floorsheet blob da34731efb753fa3fdd5861e26b9006c5dd75d5e
- SocrateAI unadjusted stock OHLCV blob 055cb4f4a06194c835f4dbb5b255ce259df943cb (adjusted file has identical blob for this date).

## Computed totals
Floorsheet: 70,158 contracts, 13,769,100 shares, NPR 6,267,226,722.57 turnover, 353 distinct securities. All-market OHLCV volume: 12,530,775; difference: 1,238,325 (8.99% of floorsheet volume).
ShareSansar dated report corroborates contracts, shares and securities exactly and reports approximately NPR 6.26 billion: https://www.sharesansar.com/newsdetail/nepse-index-edges-up-by-788-points-on-last-trading-day-of-this-week-2026-07-24
Exact official exchange turnover not obtained. Aggregate agreement is not proof of contract-level independent provenance.

## External stock-volume corroboration
https://nepsetrading.com/insights/nepse-today-full-analysis-2026-07-24-index-movement-turnover-and-tomorrow-outlook

| Symbol | Archive OHLCV volume | Floorsheet volume | NEPSE Trading volume |
|---|---:|---:|---:|
| RIDI | 785180 | 824107 | 824107 |
| ECL | 240 | 250 | 250 |
| ANLB | 2613 | 3788 | 3788 |
| APHL | 35727 | 35842 | 35842 |
| BNL | 0 | 10 | 10 |

BNL is not a no-trade case. These are corroborated full-day volume observations, not approved OHLCV corrections.

## Classification and access limits
NEPSE API wrapper documents contract_type, trade_book_id and trade_time: https://nepse-api.readthedocs.io/en/stable/modules/nepse.market.html
The recovered CSV omits all three fields. Contract-number grouping and quantity threshold tests fail to reconcile the volume differences; cannot infer session type or open/close order. SocrateAI README https://github.com/socrateai-official/nepse-open-data/blob/main/README.md does not specify session aggregation methodology.
ShareHub historical API requires bearer authentication: https://sharehubnepal.com/data/nepse-data-documentation/
NepseAlpha offers historical price export https://nepsealpha.com/nepse-data/ but July 24 stock rows not retrieved in this pass. Chukul historical raw data not retrieved. No provider login bypass attempted.

## Disposition
Use floorsheet volume as a separately labeled full-day observation; preserve original OHLCV and do not replace its volume silently. Acquire timestamped market-type contracts and raw-price chart evidence, verify adjustment policy and official totals. No canonical or backtest promotion authorized. Part of issue #20 and draft PR #21.
