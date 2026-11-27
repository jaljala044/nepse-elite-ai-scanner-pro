"""Descriptive SMC outcome research, not fitted calibration or executable returns."""
from .broker_pattern_outcomes import evaluate_broker_patterns
from .corporate_action_trade_plan import _time
from .unified_portfolio_event_engine import _available, _day

def evaluate_smc_outcomes(*,signals,price_rows_by_symbol,sessions,assessment_time,test_start):
    now=_time(assessment_time)
    boundary=_day(test_start,"test_start")
    days=[_day(d,"session") for d in sessions]
    if boundary not in days or days!=sorted(set(days)) or days[-1]>now.date():
        raise ValueError("invalid_split_calendar")
    seen=set()
    mapped=[]
    for signal in signals:
        _available(signal,now,"smc_signal")
        sid=signal["signal_id"]
        if not sid or sid in seen: raise ValueError("duplicate_signal")
        seen.add(sid)
        decision=_time(signal["decision_time"])
        if _time(signal["available_at"])>decision or decision>now:
            raise ValueError("signal_lookahead")
        if signal.get("event") not in ("bos","choch") or signal.get("direction") not in ("bullish","bearish"):
            raise ValueError("unsupported_smc_event")
        mapped.append(dict(signal,pattern="ACCUMULATION_PATTERN" if signal["direction"]=="bullish" else "DISTRIBUTION_PATTERN"))
    output={}
    for name,horizon in (("t_plus_2",5),("swing",20),("positional",63)):
        train,test,purged=[],[],[]
        for s in mapped:
            day=_time(s["decision_time"]).date()
            if day>=boundary: test.append(s)
            elif len([d for d in days if day<d<boundary])>horizon: train.append(s)
            else: purged.append(s["signal_id"])
        def evaluate(items):
            result=evaluate_broker_patterns(signals=items,price_rows_by_symbol=price_rows_by_symbol,
                sessions=sessions,assessment_time=assessment_time,horizon=horizon)
            # The shared evaluator uses legacy broker labels internally; expose SMC direction only.
            for row in result["results"]:
                row["direction"]="bullish" if row.pop("pattern")=="ACCUMULATION_PATTERN" else "bearish"
            result["metrics"]={("bullish" if k=="ACCUMULATION_PATTERN" else "bearish"):v for k,v in result["metrics"].items()}
            return result
        output[name]=dict(train=evaluate(train),test=evaluate(test),purged_signal_ids=purged)
    return dict(horizons=output,classification="smc_descriptive_outcome_research",
                calibrated_score=None,production_eligible=False,
                limitations=["Frozen caller-attested BOS/CHoCH signals only.",
                             "Single chronological split; no fitted calibration or regime stratification.",
                             "Forward close references exclude costs, fills and false-breakout path analysis."])
