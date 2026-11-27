# Scanner comparison client contract (research v1)

POST /v1/research/scanners/portfolio-comparison

Request: candidates keyed by IDPAT, WYCKOFF, SMC, BROKER, MINERVINI_MOMENTUM, MASTER; common_inputs follows run_portfolio_backtest except signals and scenario_runner. Each method must cover the same symbol/horizon/decision-date universe.

Response: schema_version, methods, matched_decisions, ranking (null), production_eligible (false), data_quality (CALLER_ATTESTED), live_trading_enabled (false), limitations. Each method has portfolio, buy_count, unknown_count, other_count, performance_eligible. Portfolio metrics include net_return_pct, trade_count, withheld_signal_count, metrics.max_drawdown_pct and risk-adjusted metrics when available.

Clients must render null as unavailable, distinguish unknown from abstention, and not rank ineligible results. Show hypothetical scenario label and evidence limitations. HTTP 422 means invalid request; do not substitute zero returns.

Readiness gates: real historical point-in-time evidence, complete corporate-action review, verified calendar and historical cost assumptions, end-to-end integration tests, authentication/resource limits before public deployment, web/mobile implementation and acceptance testing. This contract does not implement client screens.
