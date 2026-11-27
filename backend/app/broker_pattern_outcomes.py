"""Descriptive forward returns, not executable strategy backtests."""
from collections import defaultdict
from .corporate_action_trade_plan import _time, _number
from .unified_portfolio_event_engine import _available, _day

def evaluate_broker_patterns(*, signals, price_rows_by_symbol, sessions, assessment_time, horizon=5):
    now=_time(assessment_time)
    days=[_day(d,"session") for d in sessions]
    if not days or days!=sorted(set(days)) or days[-1]>now.date() or type(horizon) is not int or horizon<1:
        raise ValueError("invalid_calendar_or_horizon")
    bars={}
    for symbol,rows in price_rows_by_symbol.items():
        lookup={}
        for row in rows:
            _available(row,now,"price")
            day=_day(row["date"],"price_date")
            if day in lookup or day not in days or _time(row["available_at"]).date()<day:
                raise ValueError("invalid_price_date")
            lookup[day]=row
        bars[symbol]=lookup
    seen=set()
    results=[]
    groups=defaultdict(list)
    for s in signals:
        _available(s,now,"pattern")
        sid=s["signal_id"]
        if not sid or sid in seen: raise ValueError("duplicate_signal")
        seen.add(sid)
        decision=_time(s["decision_time"])
        if _time(s["available_at"])>decision or decision>now:
            raise ValueError("pattern_lookahead")
        kind=s["pattern"]
        if kind not in ("ACCUMULATION_PATTERN","DISTRIBUTION_PATTERN"):
            raise ValueError("unsupported_pattern")
        future=[d for d in days if d>decision.date()]
        lookup=bars.get(s["symbol"],{})
        result=dict(signal_id=sid,pattern=kind,status="UNKNOWN",forward_return=None)
        if len(future)>horizon:
            window=future[:horizon+1]
            if all(d in lookup and lookup[d].get("price_basis")=="corporate_action_reviewed" for d in window):
                first,last=lookup[window[0]],lookup[window[-1]]
                if first.get("basis_id") and all(lookup[d].get("basis_id")==first["basis_id"] for d in window):
                    ret=float(_number(last["close"])/_number(first["close"])-1)
                    result.update(status="EVALUATED",forward_return=ret,
                                  direction_hit=ret>0 if kind=="ACCUMULATION_PATTERN" else ret<0)
        results.append(result)
        groups[kind].append(result)
    metrics={}
    for kind,items in groups.items():
        valid=[r for r in items if r["status"]=="EVALUATED"]
        metrics[kind]=dict(sample_size=len(valid),withheld=len(items)-len(valid),
                           directional_hit_rate=sum(r["direction_hit"] for r in valid)/len(valid) if len(valid)>=30 else None)
    return dict(classification="descriptive_forward_close_returns",execution_eligible=False,
                horizon=horizon,results=results,metrics=metrics,
                limitations=["Next-session close reference, not executable entry.",
                             "30 observations is a reporting floor, not statistical independence.",
                             "Caller-attested price basis and frozen signals; no costs or verified fills."])
