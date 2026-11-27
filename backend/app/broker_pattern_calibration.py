"""Chronological descriptive validation, not a trading profitability model."""
from .broker_pattern_outcomes import evaluate_broker_patterns
from .corporate_action_trade_plan import _time
from .unified_portfolio_event_engine import _day

def calibrate_broker_patterns(*, signals, price_rows_by_symbol, sessions,
                              assessment_time, test_start, horizon=5):
    boundary=_day(test_start,"test_start")
    days=[_day(d,"session") for d in sessions]
    if boundary not in days or boundary==days[0] or type(horizon) is not int or horizon<1:
        raise ValueError("invalid_test_boundary")
    train,test,purged=[],[],[]
    seen=set()
    for signal in signals:
        sid=signal["signal_id"]
        if sid in seen: raise ValueError("duplicate_signal")
        seen.add(sid)
        decision=_time(signal["decision_time"]).date()
        if decision>=boundary:
            test.append(signal)
        else:
            future=[d for d in days if d>decision]
            if len(future)<=horizon or future[horizon]>=boundary:
                purged.append(sid)
            else:
                train.append(signal)
    args=dict(price_rows_by_symbol=price_rows_by_symbol,sessions=sessions,
              assessment_time=assessment_time,horizon=horizon)
    # Validate all input signals, including purged records, before reporting.
    evaluate_broker_patterns(signals=signals,**args)
    return dict(classification="chronological_descriptive_validation",
                train=evaluate_broker_patterns(signals=train,**args),
                test=evaluate_broker_patterns(signals=test,**args),
                purged_signal_ids=purged,test_start=boundary.isoformat(),
                execution_eligible=False,
                limitations=["Fixed pattern rules; no parameter fitting or optimization.",
                             "Training prices are reviewed retrospectively, not frozen at split date.",
                             "Overlapping outcomes are dependent; no profitability or calibrated probability."])
