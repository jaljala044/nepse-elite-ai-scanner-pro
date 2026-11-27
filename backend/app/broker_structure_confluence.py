"""Research comparison of frozen broker patterns and supplied technical evidence."""
from .broker_pattern_calibration import calibrate_broker_patterns
from .corporate_action_trade_plan import _time
from .unified_portfolio_event_engine import _available

def compare_broker_structure(*, signals, confirmations, price_rows_by_symbol,
                             sessions, assessment_time, test_start, horizon=5):
    now=_time(assessment_time)
    by_id={}
    for item in confirmations:
        sid=item["signal_id"]
        if sid in by_id: raise ValueError("duplicate_confirmation")
        by_id[sid]=item
    ids={s["signal_id"] for s in signals}
    if set(by_id)-ids: raise ValueError("orphan_confirmation")
    comparable,confirmed=[],[]
    unknown=[]
    for signal in signals:
        sid=signal["signal_id"]
        decision=_time(signal["decision_time"])
        item=by_id.get(sid)
        if item is None:
            unknown.append(sid)
            continue
        _available(item,decision,"confirmation")
        if decision>now or item["symbol"]!=signal["symbol"]:
            raise ValueError("confirmation_mismatch")
        fields=("wyckoff","smc","volume","relative_strength","sector")
        if any(item.get(f) not in ("BULLISH","BEARISH","NEUTRAL","UNKNOWN") for f in fields):
            raise ValueError("invalid_confirmation")
        if any(item[f]=="UNKNOWN" for f in fields):
            unknown.append(sid)
            continue
        comparable.append(signal)
        direction="BULLISH" if signal["pattern"]=="ACCUMULATION_PATTERN" else "BEARISH"
        if all(item[f]==direction for f in fields):
            confirmed.append(signal)
    args=dict(price_rows_by_symbol=price_rows_by_symbol,sessions=sessions,
              assessment_time=assessment_time,test_start=test_start,horizon=horizon)
    baseline=calibrate_broker_patterns(signals=signals,**args)
    matched=calibrate_broker_patterns(signals=comparable,**args)
    confluence=calibrate_broker_patterns(signals=confirmed,**args)
    return dict(classification="descriptive_confluence_comparison",
                broker_only=baseline,complete_evidence_baseline=matched,
                confluence=confluence,unknown_confirmation_ids=unknown,
                confirmed_signal_ids=[s["signal_id"] for s in confirmed],
                execution_eligible=False,
                limitations=["Five-way agreement is a fixed uncalibrated rule.",
                             "Confirmation labels are caller-attested, not independently computed.",
                             "Selected subsets differ; comparison does not establish causal improvement.",
                             "No transaction costs, fills or portfolio drawdown in forward-close metrics."])
