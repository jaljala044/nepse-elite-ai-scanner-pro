"""Descriptive event review, not calibrated probability."""
from decimal import Decimal

def review_events(events,rows,as_of_session):
    bars={r["date"]:r for r in rows if r["date"]<=as_of_session}
    groups={}
    aliases={"jump_across_creek":"sos","backup_to_creek":"lps"}
    for e in events:
        day=e["session_date"]
        if day>as_of_session or day not in bars: raise ValueError("event_session_mismatch")
        kind=aliases.get(e["event"],e["event"])
        direction=e["direction"].lower()
        if direction not in ("bullish","bearish"): raise ValueError("invalid_direction")
        level=Decimal(str(e["reference_level"]))
        if not level.is_finite() or level<=0: raise ValueError("invalid_level")
        key=(day,kind,direction,level)
        groups.setdefault(key,[]).append(e["event"])
    result=[]
    for (day,kind,direction,level),names in sorted(groups.items()):
        later=[Decimal(str(b["close"])) for d,b in bars.items() if d>day]
        invalidated=any(x<level if direction=="bullish" else x>level for x in later)
        result.append(dict(session=day,event=kind,direction=direction,level=str(level),aliases=sorted(set(names)),invalidated=invalidated))
    return dict(events=result,unique_count=len(result),active_count=sum(not r["invalidated"] for r in result),production_eligible=False)

def idpat_proxy_direction(events):
    bull=bool(set(events)&{"SHAKEOUT_PROXY","BREAKOUT_PROXY","LOWER_REJECTION_HIGH_VOLUME_PROXY"})
    bear=bool(set(events)&{"FAILED_BREAKOUT_PROXY","UPPER_REJECTION_HIGH_VOLUME_PROXY"})
    return "UNKNOWN" if bull==bear else "BULLISH" if bull else "BEARISH"
