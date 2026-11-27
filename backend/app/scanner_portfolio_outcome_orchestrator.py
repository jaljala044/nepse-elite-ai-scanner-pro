"""Compose comparable OOS portfolio replays and append-only signal outcomes."""
from __future__ import annotations
from app.scanner_portfolio_replay import replay_portfolio
from app.scanner_signal_outcome_ledger import build_signal_outcome_ledger

def run_portfolio_outcome_comparison(*,replay_bundle,signals,partition="out_of_sample",portfolio_config=None):
    if not isinstance(replay_bundle,dict) or not isinstance(replay_bundle.get("runs"),list):
        raise ValueError("replay_bundle_with_runs_required")
    if partition not in {"train","validation","out_of_sample"}: raise ValueError("invalid_partition")
    if not isinstance(signals,list): raise ValueError("signals_must_be_list")
    config=dict(portfolio_config or {})
    selected=[r for r in replay_bundle["runs"] if isinstance(r,dict) and r.get("partition")==partition]
    portfolios=[]; replay_results=[]
    for run in selected:
        trade_records=run.get("trades",[])
        pending=run.get("pending_exits",[])
        if not isinstance(trade_records,list) or not isinstance(pending,list):
            raise ValueError("replay_run_trade_or_pending_records_invalid")
        portfolio=replay_portfolio(trades=trade_records,**config)
        portfolios.append({"strategy_id":run.get("strategy_id"),"horizon":run.get("horizon"),
            "partition":partition,"portfolio":portfolio})
        replay_results.append({"trades":trade_records,"pending_exits":pending})
    # The caller supplies only signals from the same partition. If a signal carries
    # a partition label, reject cross-partition leakage explicitly.
    for s in signals:
        if isinstance(s,dict) and s.get("sample_partition") not in (None,partition):
            raise ValueError("signal_partition_mismatch")
    ledger=build_signal_outcome_ledger(signals=signals,replay_results=replay_results)
    return {"schema_version":"nepse-portfolio-outcome-comparison-1.0.0",
        "partition":partition,"portfolio_run_count":len(portfolios),
        "portfolios":portfolios,"signal_outcome_ledger":ledger,
        "comparison_policy":"each strategy/horizon receives an independent portfolio with identical capital, risk, exposure, costs and liquidity assumptions",
        "production_enabled":False,"performance_claimed":False,
        "limitations":["Use only untouched out_of_sample results for final strategy selection.",
            "Pass only signals from the same partition; signal generation must be point-in-time.",
            "Portfolio drawdown is realized-only with open positions valued at cost.",
            "A missing per-trade liquidity cap is rejected by portfolio replay."]}
