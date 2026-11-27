"""Descriptive risk confluence; never infer manipulation or authorize execution."""
from .portfolio_broker_memory import replay_broker_patterns
from .automatic_evidence_adapter import derive_chart_evidence
from .wyckoff_features import wyckoff_event_features
from .volume_vsa_features import volume_vsa_features
from .smc_features import smc_features
from .corporate_action_trade_plan import _time

def review_liquidity_trap(*,symbol,rows,benchmark_rows,sessions,assessment_time,
                          broker_records,broker_numbers):
    chart=derive_chart_evidence(symbol=symbol,rows=rows,benchmark_rows=benchmark_rows,
                                sessions=sessions,assessment_time=assessment_time)
    bars=sorted([dict(r,session_date=r["date"]) for r in rows],key=lambda r:r["session_date"])
    latest=bars[-1]["session_date"]
    wyckoff=wyckoff_event_features(bars)
    volume=volume_vsa_features(bars)
    smc=smc_features(bars)
    if not broker_numbers or any(type(b) is not int or b<=0 for b in broker_numbers) or len(set(broker_numbers))!=len(broker_numbers):
        raise ValueError("invalid_broker_cohort")
    replay=replay_broker_patterns(records=broker_records,sessions=sessions,assessment_time=assessment_time)
    matches=[h for h in replay["histories"] if h["symbol"]==symbol and h["broker_numbers"]==sorted(broker_numbers)]
    broker=matches[0] if matches else None
    broker_known=bool(broker and broker["coverage"]==1 and broker["observations"][-1]["date"]==latest)
    selling=bool(broker_known and broker["latest_streak"]<=-3)
    selling_strength=bool(broker_known and "SELLING_INTO_STRENGTH" in broker["observations"][-1]["flags"])
    upthrust=any(e["event"]=="upthrust" and e["session_date"]==latest for e in wyckoff.get("events",[]))
    sweep=any(e["event"]=="buy_side_liquidity_sweep" and e["session_date"]==latest for e in smc.get("liquidity_sweeps",[]))
    supply=volume.get("interpretation")=="supply_response_observed"
    structural=upthrust or sweep
    complete=broker_known and all(f.get("status")=="observed" for f in (wyckoff,volume,smc))
    action="UNKNOWN"
    if structural and supply and selling:
        action="DISTRIBUTION_RISK_REVIEW"
    elif structural:
        action="STRUCTURAL_WARNING"
    elif selling and selling_strength:
        action="BROKER_SELLING_INTO_STRENGTH_REVIEW"
    elif complete:
        action="NO_CONFLUENCE_OBSERVED"
    return dict(symbol=symbol,as_of_session=latest,action=action,complete_evidence=complete,
                flags=dict(upthrust=upthrust,buy_side_sweep=sweep,supply_response=supply,
                           persistent_broker_selling=selling if broker_known else None,
                           selling_into_strength=selling_strength if broker_known else None),
                chart=chart,wyckoff=wyckoff,volume=volume,smc=smc,broker=broker,
                production_eligible=False,execution_eligible=False,
                limitations=["Same-session candidate events only; no confirmed manipulation.",
                             "Broker cohort is caller-selected; complete supplied history required.",
                             "No market regime or sector gate, no calibrated probability.",
                             "No automatic sell order or confirmed structural stop."])
