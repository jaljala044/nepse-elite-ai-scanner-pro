"""Research-only bridge; upstream feature contracts remain authoritative."""
from .feature_pipeline import build_feature_snapshot
from .integrated_research_pipeline import run_integrated_research
from .scoring_engine import COMPONENT_WEIGHTS
from .corporate_action_trade_plan import _time

def review_scanner(*, records, decision_time, expected_symbols, sector_membership,
                   expected_sector_members, session_dates, snapshot, as_of_date):
    if not expected_symbols or snapshot["symbol"] not in expected_symbols:
        raise ValueError("symbol_not_in_expected_universe")
    if not session_dates or session_dates[-1]!=as_of_date or _time(decision_time).date().isoformat()<as_of_date:
        raise ValueError("as_of_session_mismatch")
    features=build_feature_snapshot(records,decision_time,expected_symbols=expected_symbols,
        sector_membership=sector_membership,expected_sector_members=expected_sector_members,
        session_dates=session_dates)
    symbol=snapshot["symbol"]
    candidates=features["component_candidates"].get(symbol,{})
    components={name:candidates.get(name) for name in COMPONENT_WEIGHTS}
    coverage=sum(weight for name,weight in COMPONENT_WEIGHTS.items() if components[name] is not None)
    # Do not turn numeric feature scores into directional confirmations.
    # In particular experimental SMC must not silently authorize a BUY.
    decision=run_integrated_research(snapshot=snapshot,as_of_date=as_of_date,
                                    as_of_timestamp=decision_time,confirmation=None)
    return dict(symbol=symbol,component_scores=components,coverage_pct=coverage,
                missing_components=[k for k,v in components.items() if v is None],
                score=features["aggregate_scores"].get(symbol),
                feature_evidence=features["component_feature_bundles"].get(symbol,{}),
                input_contracts=features["input_contracts"],
                horizon_review=decision,production_eligible=False,
                limitations=["No calibrated SMC score or automatic directional confluence.",
                             "Caller-supplied snapshot is not independently reconciled with feature records.",
                             "No live order authorization."])
