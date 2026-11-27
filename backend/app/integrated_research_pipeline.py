"""Research orchestration; upstream evidence remains caller-attested."""
from .early_entry_exit_signals import generate_early_entry_exit_signals
from .signal_tracking import freeze_signal
from .execution_backtest import simulate_execution_scenario, aggregate_execution_scenarios
from .unified_portfolio_event_engine import _available
from .corporate_action_trade_plan import _time

def run_integrated_research(*, snapshot, as_of_date, as_of_timestamp,
                            confirmation=None, execution_by_horizon=None):
    cutoff=_time(as_of_timestamp)
    decision=generate_early_entry_exit_signals(snapshot,as_of_date=as_of_date,
                                                as_of_timestamp=as_of_timestamp)
    fields=("wyckoff","smc","volume","relative_strength","sector")
    aligned=False
    confluence_status="UNKNOWN"
    if confirmation is not None:
        _available(confirmation,cutoff,"confirmation")
        if confirmation["symbol"]!=snapshot["symbol"]:
            raise ValueError("confirmation_symbol_mismatch")
        labels=[confirmation.get(f,"UNKNOWN") for f in fields]
        if any(v not in ("BULLISH","BEARISH","NEUTRAL","UNKNOWN") for v in labels):
            raise ValueError("invalid_confirmation_label")
        aligned=all(v=="BULLISH" for v in labels)
        confluence_status="ALIGNED" if aligned else "UNKNOWN" if "UNKNOWN" in labels else "CONFLICTING"
    records,scenarios=[],[]
    actions={}
    for horizon in ("t_plus_2","swing","positional","investment"):
        plan=decision.get("horizons",{}).get(horizon,{})
        exit_review=decision.get("exit_reviews",{}).get(horizon,{})
        if exit_review.get("action")=="SELL_OR_REDUCE":
            actions[horizon]="EXIT_REVIEW"
            continue
        if plan.get("action")!="BUY" or not aligned:
            actions[horizon]="UNKNOWN" if confluence_status=="UNKNOWN" or decision.get("status")=="withheld" or horizon=="investment" else "WAIT"
            continue
        evidence=[]
        for name in ("market","sector","liquidity","broker","price_volume","candidate"):
            item=snapshot[name]
            for sid in item.get("source_ids") or [item["source_id"]]:
                evidence.append(dict(evidence_id=sid,available_at=item["available_at"],component=name))
        evidence.append(dict(evidence_id=confirmation["source_id"],available_at=confirmation["available_at"],component="confluence"))
        frozen=freeze_signal(symbol=snapshot["symbol"],decision_time=as_of_timestamp,
            horizon=horizon,action="BUY",methodology="integrated-research-v1",
            evidence=evidence,details=dict(decision_date=as_of_date,
                plan=dict(entry=plan["entry"],stop=plan["stop"],targets=[t["price"] for t in plan["targets"]])))
        records.append(frozen)
        actions[horizon]="BUY_RESEARCH"
        config=(execution_by_horizon or {}).get(horizon)
        if config is not None:
            scenarios.append(simulate_execution_scenario(signal=frozen["record"],**config))
    return dict(classification="integrated_research_only",actions=actions,
                upstream_decision=decision,confluence_aligned=aligned,confluence_status=confluence_status,
                frozen_signals=records,execution_scenarios=scenarios,
                execution_summary=aggregate_execution_scenarios(scenarios),
                production_eligible=False,
                limitations=["Upstream evidence and confluence labels are caller-attested.",
                             "No investment model or live orders; trade scenarios are not portfolio returns."])
