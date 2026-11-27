"""Research-only broker pattern evaluation with immutable decision inputs."""
from .scanner_broker_rotation_bridge import freeze_pattern
from .broker_pattern_calibration import calibrate_broker_patterns
from .corporate_action_trade_plan import _time

def evaluate_cohort_history(*,decisions,price_rows_by_symbol,sessions,assessment_time,test_start,horizon=5):
    cutoff=_time(assessment_time)
    signals=[]; seen=set(); decision_keys=set()
    for inputs in sorted(decisions,key=lambda x:_time(x["decision_time"])):
        key=(inputs["symbol"],_time(inputs["decision_time"]),tuple(sorted(inputs["selection"]["broker_numbers"])))
        if key in decision_keys or key[1]>cutoff: raise ValueError("invalid_decision")
        decision_keys.add(key)
        for signal in freeze_pattern(cohort_inputs=inputs):
            if signal["signal_id"] in seen: raise ValueError("duplicate_signal")
            seen.add(signal["signal_id"]); signals.append(signal)
    result=calibrate_broker_patterns(signals=signals,price_rows_by_symbol=price_rows_by_symbol,sessions=sessions,assessment_time=assessment_time,test_start=test_start,horizon=horizon)
    return dict(result,signals=signals,decision_count=len(decision_keys),production_eligible=False)
