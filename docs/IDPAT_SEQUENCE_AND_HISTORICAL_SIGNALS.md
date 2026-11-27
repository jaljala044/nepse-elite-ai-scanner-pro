# IDPAT Sequence Confirmation and Historical Signal Generation

## Step 16 — Sequential IDPAT/Wyckoff event candidates
The IDPAT feature engine now emits sequential LPS, LPSY, Backup-to-Creek and Jump-Across-Creek candidates when a later OHLCV retest follows a candidate SOS/SOW. They remain descriptive, uncalibrated candidates. A true Wyckoff diagnosis still requires base duration/cause, supply absorption, context and independent validation.

## Step 17 — Historical strategy signal generation
`generate_historical_research_signals` consumes the point-in-time feature series and a separate trusted context ledger keyed by decision time, symbol, strategy and horizon. It applies strategy score/coverage thresholds, seven timestamped evidence gates, the verified trade-plan builder, execution snapshot and shared risk sizing. Missing context or any failed gate produces NO_TRADE. Each decision is retained in a signal tracking log.

## Data contract and safety
Context keys use canonical UTC decision timestamps and contain gates, verified levels, explicit costs/slippage, execution snapshot and risk inputs. The server must source these values from the trusted evidence ledger. This module does not fabricate levels or provenance and does not send orders.

## Limitations
No real NEPSE historical panel is bundled. No validated backtest performance is claimed. Portfolio concurrency, partial fills, circuit queues, market impact and settlement-aware portfolio replay remain future work. A research BUY is not production-enabled.

## Integration sequence contract
The feature snapshot stores IDPAT output under `idpat_features` for each symbol. Historical signal contexts use canonical UTC decision-time keys of the form `timestamp|SYMBOL|strategy_id|horizon`. Gate evidence and level provenance are checked against that decision cutoff. Signal logs preserve NO_TRADE outcomes as well as research BUY candidates so later replay can measure false positives and missed moves without survivorship filtering.
