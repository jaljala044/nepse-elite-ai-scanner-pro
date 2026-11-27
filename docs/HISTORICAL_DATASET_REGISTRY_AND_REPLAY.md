# Historical Dataset Registry and Six-Scanner Replay

## Scope
Steps 10–11 add a fail-closed registry for admitted historical datasets and a common replay coordinator for six strategy engines across T+2, swing, positional and investment horizons. This is orchestration and validation infrastructure, not a claim that live NEPSE data has been acquired.

## Dataset admission
`build_dataset_registry` consumes captured-byte intake reports. Required datasets are OHLCV, official session calendar, effective-dated instrument universe and corporate actions. Optional datasets are floorsheet, broker summaries, sector membership/index and fundamentals. It checks report status, point-in-time availability, source/evidence IDs, raw SHA-256 format, rights, validation and finality. Missing optional sources remain explicitly missing; required-source gaps block readiness.

A registry marked ready only permits historical-panel assembly. It does not prove publisher authenticity, licensing, source independence, complete coverage or corporate-action reconciliation. Continue using the existing panel and independent corporate-action reconciliation gates.

## Replay orchestration
`run_six_strategy_replay` iterates six strategies × four horizons × requested partitions (train, validation, out-of-sample by default), using the same admitted universe, OHLCV map, costs, slippage and settlement scenario. It passes only signals for eligible symbols to the existing point-in-time replay engine. Missing signal batches are reported as empty samples; malformed batches and replay errors are listed as blocked runs.

The coordinator does not generate indicators or signals. Signal generation must use point-in-time features and provenance. Walk-forward folds must be identical across strategies; preserve a final untouched holdout if repeated model selection risks contaminating out-of-sample results.

## Current data and performance status
No actual NEPSE historical files are bundled or fetched by this change. No win rate, profit factor, expectancy, drawdown, strategy winner or probability is claimed. Empty replay batches are not performance evidence. Research-only; production remains disabled.

## Remaining external dependencies
- Authorized, licensed historical OHLCV and official session calendar.
- Effective-dated listing/universe history, including delisted securities to mitigate survivorship bias.
- Independently reconciled corporate actions and adjustment ledger.
- Floorsheet and broker summary history with reliable broker-code semantics.
- Sector membership/index history and point-in-time fundamentals.
- Verified source registry review and captured raw files with timestamps and hashes.
- Feature-generation integration for currently unsupported IDPAT hidden levels, accumulation/distribution, broker persistence and fundamentals.
