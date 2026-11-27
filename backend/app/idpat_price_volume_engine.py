"""IDPAT-style price/volume event research and hidden-level mapping.

Rules are descriptive, uncalibrated heuristics. Levels are inferred from OHLCV,
not verified order-book depth. No ownership/manipulation claims are made.
"""
from __future__ import annotations
from decimal import Decimal, InvalidOperation

def _d(v):
    try: x=Decimal(str(v))
    except (InvalidOperation,TypeError,ValueError): return None
    return x if x.is_finite() else None

def _row_ok(r):
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
    events=[]; levels=[]
    for i,r in enumerate(ordered):
        x={k:_d(r[k]) for k in ("open","high","low","close","volume")}
        prev=ordered[i-1] if i else None
        prior=ordered[max(0,i-lookback):i]
        if len(prior)<4: continue
        prior_high=max(_d(p["high"]) for p in prior); prior_low=min(_d(p["low"]) for p in prior)
        avg_vol=sum((_d(p["volume"]) for p in prior),Decimal("0"))/Decimal(len(prior))
        spread=x["high"]-x["low"]
        close_location=(x["close"]-x["low"])/spread if spread>0 else Decimal("0.5")
        relative_volume=x["volume"]/avg_vol if avg_vol>0 else None
        date=r["session_date"]
        if x["low"]<prior_low and x["close"]>prior_low:
            events.append({"event":"spring_candidate","session_date":date,"evidence":"low_swept_prior_range_low_then_closed_above","relative_volume":str(relative_volume) if relative_volume is not None else None,"status":"heuristic_candidate"})
        if x["high"]>prior_high and x["close"]<prior_high:
            events.append({"event":"upthrust_candidate","session_date":date,"evidence":"high_swept_prior_range_high_then_closed_below","relative_volume":str(relative_volume) if relative_volume is not None else None,"status":"heuristic_candidate"})
        if x["close"]>prior_high and close_location>=Decimal("0.7") and relative_volume is not None and relative_volume>=Decimal("1.5"):
            events.append({"event":"SOS_candidate","session_date":date,"evidence":"close_above_prior_range_with_volume_expansion","relative_volume":str(relative_volume),"status":"heuristic_candidate"})
        if x["close"]<prior_low and close_location<=Decimal("0.3") and relative_volume is not None and relative_volume>=Decimal("1.5"):
            events.append({"event":"SOW_candidate","session_date":date,"evidence":"close_below_prior_range_with_volume_expansion","relative_volume":str(relative_volume),"status":"heuristic_candidate"})
        if spread>0 and relative_volume is not None and relative_volume>=Decimal("2"):
            if close_location>=Decimal("0.75"):
                events.append({"event":"demand_effort_candidate","session_date":date,"evidence":"high_volume_wide_spread_close_near_high","relative_volume":str(relative_volume),"status":"heuristic_candidate"})
            elif close_location<=Decimal("0.25"):
                events.append({"event":"supply_effort_candidate","session_date":date,"evidence":"high_volume_wide_spread_close_near_low","relative_volume":str(relative_volume),"status":"heuristic_candidate"})
        levels.append((date,x["high"],x["low"]))
    # Cluster repeated swing pivots; label as inferred chart liquidity, never order-book data.
    for field,label in (("high","buy_side_liquidity_candidate"),("low","sell_side_liquidity_candidate")):
        pivots=[]
        for i in range(1,len(ordered)-1):
            a=_d(ordered[i-1][field]); b=_d(ordered[i][field]); c=_d(ordered[i+1][field])
            if (b>=a and b>=c) if field=="high" else (b<=a and b<=c):
                pivots.append((ordered[i]["session_date"],b))
        clusters=[]
        for day,price in pivots:
            found=None
            for cluster in clusters:
                anchor=cluster[0][1]
                if anchor and abs(price-anchor)/anchor*100<=tol:
                    found=cluster; break
            if found is None: clusters.append([(day,price)])
            else: found.append((day,price))
        for cluster in clusters:
            if len(cluster)>=2:
                avg=sum((p for _,p in cluster),Decimal("0"))/Decimal(len(cluster))
                levels.append((cluster[-1][0],avg,avg))
                # Separate structure below in the return object.
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
    return {
        "status":"observed_descriptive_only","history_sessions":len(ordered),
        "lookback_sessions":lookback,"level_tolerance_pct":str(tol),
        "events":events,"hidden_levels":hidden,"score":None,
        "interpretation":"IDPAT-style heuristic event candidates; uncalibrated and descriptive only",
        "limitations":["Spring/upthrust/SOS/SOW are candidates requiring context and follow-through.","No LPS/LPSY, Backup to Creek or Jump Across Creek confirmation is asserted without validated structure context.","Equal highs/lows are inferred from historical OHLCV, not order-book liquidity.","No broker ownership, operator activity or manipulation inference.","No calibrated score or probability is produced."]
    }
