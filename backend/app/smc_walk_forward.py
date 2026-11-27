"""Research-only rolling SMC diagnostics; no fitted probability or production score."""
from .smc_outcome_research import evaluate_smc_outcomes
from .corporate_action_trade_plan import _time, _number
from .unified_portfolio_event_engine import _available, _day

def walk_forward_smc(*,signals,price_rows_by_symbol,sessions,assessment_time,test_starts):
    now=_time(assessment_time)
    days=[_day(d,"session") for d in sessions]
    starts=[_day(d,"test_start") for d in test_starts]
    if not starts or starts!=sorted(set(starts)) or any(d not in days for d in starts):
        raise ValueError("invalid_fold_boundaries")
    if days!=sorted(set(days)) or days[-1]>now.date():
        raise ValueError("invalid_calendar")
    # Validate all signals before selecting folds.
    evaluate_smc_outcomes(signals=signals,price_rows_by_symbol=price_rows_by_symbol,
        sessions=sessions,assessment_time=assessment_time,test_start=test_starts[0])
    folds=[]
    for i,start in enumerate(starts):
        end=starts[i+1] if i+1<len(starts) else None
        selected=[s for s in signals if end is None or _time(s["decision_time"]).date()<end]
        result=evaluate_smc_outcomes(signals=selected,price_rows_by_symbol=price_rows_by_symbol,
            sessions=sessions,assessment_time=assessment_time,test_start=start.isoformat())
        # Training outcome availability is not frozen at fold start, so do not fit.
        folds.append(dict(test_start=start.isoformat(),test_end_exclusive=end.isoformat() if end else None,
                          horizons=result["horizons"]))
    return dict(folds=folds,calibrated_score=None,production_eligible=False,
                limitations=["Disjoint test decision dates; outcome windows may overlap.",
                             "Retrospective descriptive folds, not fitted walk-forward calibration.",
                             "Training evidence revisions are not frozen at each fold boundary."])

def review_breakout_failure(*,signal,rows,sessions,assessment_time,horizon=5):
    now=_time(assessment_time)
    _available(signal,now,"signal")
    decision=_time(signal["decision_time"])
    if decision>now or _time(signal["available_at"])>decision:
        raise ValueError("signal_lookahead")
    if signal.get("event") not in ("bos","choch") or signal.get("direction") not in ("bullish","bearish"):
        raise ValueError("unsupported_event")
    level=_number(signal["level"])
    if level<=0 or type(horizon) is not int or horizon<1: raise ValueError("invalid_level_or_horizon")
    days=[_day(d,"session") for d in sessions]
    if days!=sorted(set(days)) or not days or days[-1]>now.date(): raise ValueError("invalid_calendar")
    future=[d for d in days if d>decision.date()][:horizon]
    lookup={}
    for row in rows:
        _available(row,now,"bar")
        day=_day(row["date"],"bar")
        if day in lookup or day not in days or row.get("symbol")!=signal["symbol"] or _time(row["available_at"]).date()<day:
            raise ValueError("invalid_bar")
        lookup[day]=row
    result=dict(status="UNKNOWN",failure_date=None,production_eligible=False)
    if len(future)!=horizon or not signal.get("basis_id") or any(d not in lookup or
        lookup[d].get("price_basis")!="corporate_action_reviewed" or lookup[d].get("basis_id")!=signal["basis_id"] for d in future):
        return result
    for day in future:
        close=_number(lookup[day]["close"])
        if close<=0: raise ValueError("invalid_close")
        if (signal["direction"]=="bullish" and close<level) or (signal["direction"]=="bearish" and close>level):
            return dict(result,status="FAILED_BREAK_CANDIDATE",failure_date=day.isoformat())
    return dict(result,status="LEVEL_HELD_ON_CLOSES")
