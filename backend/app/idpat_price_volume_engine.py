"""IDPAT price/volume events and sequential Wyckoff structure candidates.

All derived levels are OHLCV-inferred. Events are candidates, not calibrated
signals or verified order-book liquidity.
"""
from __future__ import annotations
from decimal import Decimal, InvalidOperation

def _d(v):
    try: x=Decimal(str(v))
    except (InvalidOperation,TypeError,ValueError): return None
    return x if x.is_finite() else None

def _row_ok(r):
    if not isinstance(r,dict): return False
    vals={k:_d(r.get(k)) for k in ("open","high","low","close","volume")}
    return all(v is not None for v in vals.values()) and vals["low"]>0 and vals["volume"]>=0 and vals["high"]>=max(vals["open"],vals["close"],vals["low"]) and vals["low"]<=min(vals["open"],vals["close"])

def idpat_price_volume_features(rows, *, lookback=20, level_tolerance_pct=Decimal("0.5")):
    if isinstance(lookback,bool) or not isinstance(lookback,int) or lookback<5: raise ValueError("lookback_must_be_at_least_5")
    tol=_d(level_tolerance_pct)
    if tol is None or tol<0 or tol>5: raise ValueError("level_tolerance_pct_out_of_range")
    if not isinstance(rows,list) or len(rows)<5:
        return {"status":"insufficient_evidence","reason":"minimum_five_valid_sessions_required","history_sessions":len(rows) if isinstance(rows,list) else 0,"score":None,"events":[],"hidden_levels":[]}
    ordered=sorted(rows,key=lambda r:str(r.get("session_date","")))
    dates=[str(r.get("session_date","")) for r in ordered]
    if any(not d for d in dates) or len(set(dates))!=len(dates):
        return {"status":"insufficient_evidence","reason":"missing_or_duplicate_session_dates","history_sessions":len(rows),"score":None,"events":[],"hidden_levels":[]}
    if any(not _row_ok(r) for r in ordered):
        return {"status":"insufficient_evidence","reason":"invalid_ohlcv_rows","history_sessions":len(rows),"score":None,"events":[],"hidden_levels":[]}
    events=[]; breakouts=[]; breakdowns=[]
    for i,r in enumerate(ordered):
        x={k:_d(r[k]) for k in ("open","high","low","close","volume")}
        prior=ordered[max(0,i-lookback):i]
        if len(prior)<4: continue
        prior_high=max(_d(p["high"]) for p in prior); prior_low=min(_d(p["low"]) for p in prior)
        avg_vol=sum((_d(p["volume"]) for p in prior),Decimal("0"))/Decimal(len(prior))
        spread=x["high"]-x["low"]; loc=(x["close"]-x["low"])/spread if spread>0 else Decimal("0.5")
        rv=x["volume"]/avg_vol if avg_vol>0 else None; day=r["session_date"]
        if x["low"]<prior_low and x["close"]>prior_low:
            events.append({"event":"spring_candidate","session_date":day,"level":str(prior_low),"evidence":"swept_prior_range_low_then_closed_above","relative_volume":str(rv) if rv is not None else None,"status":"heuristic_candidate"})
        if x["high"]>prior_high and x["close"]<prior_high:
            events.append({"event":"upthrust_candidate","session_date":day,"level":str(prior_high),"evidence":"swept_prior_range_high_then_closed_below","relative_volume":str(rv) if rv is not None else None,"status":"heuristic_candidate"})
        if x["close"]>prior_high and loc>=Decimal("0.7") and rv is not None and rv>=Decimal("1.5"):
            events.append({"event":"SOS_candidate","session_date":day,"level":str(prior_high),"evidence":"close_above_prior_range_with_volume_expansion","relative_volume":str(rv),"status":"heuristic_candidate"})
            breakouts.append((i,prior_high))
        if x["close"]<prior_low and loc<=Decimal("0.3") and rv is not None and rv>=Decimal("1.5"):
            events.append({"event":"SOW_candidate","session_date":day,"level":str(prior_low),"evidence":"close_below_prior_range_with_volume_expansion","relative_volume":str(rv),"status":"heuristic_candidate"})
            breakdowns.append((i,prior_low))
        if spread>0 and rv is not None and rv>=Decimal("2"):
            if loc>=Decimal("0.75"):
                events.append({"event":"demand_effort_candidate","session_date":day,"evidence":"high_volume_wide_spread_close_near_high","relative_volume":str(rv),"status":"heuristic_candidate"})
            elif loc<=Decimal("0.25"):
                events.append({"event":"supply_effort_candidate","session_date":day,"evidence":"high_volume_wide_spread_close_near_low","relative_volume":str(rv),"status":"heuristic_candidate"})
    # Sequential tests: a later retest must hold the original breakout/breakdown level.
    for i,level in breakouts:
        for j in range(i+1,min(len(ordered),i+lookback+1)):
            r=ordered[j]; low=_d(r["low"]); close=_d(r["close"]); high=_d(r["high"])
            if low<=level*Decimal("1.01") and low>=level*Decimal("0.97") and close>level:
                events.append({"event":"LPS_candidate","session_date":r["session_date"],"level":str(level),"evidence":"post_SOS_retest_holds_breakout_level","status":"heuristic_candidate"})
                events.append({"event":"Backup_to_Creek_candidate","session_date":r["session_date"],"level":str(level),"evidence":"post_creek_breakout_retest_holds_above_creek","status":"heuristic_candidate"})
                break
    for i,level in breakdowns:
        for j in range(i+1,min(len(ordered),i+lookback+1)):
            r=ordered[j]; high=_d(r["high"]); close=_d(r["close"])
            if high>=level*Decimal("0.99") and high<=level*Decimal("1.03") and close<level:
                events.append({"event":"LPSY_candidate","session_date":r["session_date"],"level":str(level),"evidence":"post_SOW_retest_rejects_breakdown_level","status":"heuristic_candidate"})
                break
    # A strong close above the most recent prior creek is a Jump Across Creek candidate.
    for e in list(events):
        if e["event"]=="SOS_candidate":
            row=next(x for x in ordered if x["session_date"]==e["session_date"])
            events.append({"event":"Jump_Across_Creek_candidate","session_date":e["session_date"],"level":e["level"],"evidence":"SOS_close_above_prior_range_creek_with_expansion","status":"heuristic_candidate"})
    hidden=[]
    for field,label in (("high","equal_swing_highs"),("low","equal_swing_lows")):
        pivots=[]
        for i in range(1,len(ordered)-1):
            a=_d(ordered[i-1][field]); b=_d(ordered[i][field]); c=_d(ordered[i+1][field])
            if (b>=a and b>=c) if field=="high" else (b<=a and b<=c): pivots.append((ordered[i]["session_date"],b))
        for i,(day,price) in enumerate(pivots):
            matches=[(d,p) for d,p in pivots[:i] if abs(price-p)/p*100<=tol]
            if matches:
                hidden.append({"type":label,"price":str(price),"first_seen":matches[0][0],"last_seen":day,"touch_count":len(matches)+1,"status":"inferred_chart_level","evidence":"repeated_swing_pivots_within_tolerance","verified_order_book":False})
    events.sort(key=lambda e:(e["session_date"],e["event"]))
    return {"status":"observed_descriptive_only","history_sessions":len(ordered),"lookback_sessions":lookback,"level_tolerance_pct":str(tol),"events":events,"hidden_levels":hidden,"score":None,"interpretation":"IDPAT and Wyckoff sequential candidates; uncalibrated and descriptive only","limitations":["LPS/LPSY/Backup to Creek/Jump Across Creek are rule-based candidates, not confirmed Wyckoff diagnoses.","No cause-building/base-duration or supply-absorption context is inferred beyond supplied OHLCV.","Equal highs/lows are chart-inferred, not verified order-book liquidity.","No broker ownership, operator activity or manipulation inference.","No calibrated score or probability is produced."]}
