"""Conservative research-only multi-timeframe and horizon observations."""
from datetime import date, timedelta
from .scanner import quality_errors
from .market_structure import detect_structure


def evaluate_timeframes(rows, *, eligible=False, verified_sessions=None):
    if not eligible or quality_errors(rows) or not rows:
        return {"status":"unavailable","score":None}
    ordered = sorted(rows,key=lambda r:str(r["date"]))
    daily = detect_structure(ordered)
    # A later observed week closes the prior bucket; an independent calendar
    # must also establish all expected sessions, including holidays.
    buckets = {}
    for row in ordered:
        day = date.fromisoformat(str(row["date"]))
        start = day-timedelta(days=(day.weekday()+1)%7)
        buckets.setdefault(start,[]).append(row)
    weekly = []
    if verified_sessions is not None:
        sessions = {date.fromisoformat(str(d)) for d in verified_sessions}
        previous_start = None
        for start, group in sorted(buckets.items())[:-1]:
            if previous_start is not None and start != previous_start+timedelta(days=7):
                weekly = []
            previous_start = start
            expected = {d for d in sessions if start <= d < start+timedelta(days=7)}
            actual = {date.fromisoformat(str(r["date"])) for r in group}
            if not expected or expected != actual:
                weekly = []  # no structure across a missing week
                continue
            weekly.append(dict(date=group[-1]["date"],open=group[0]["open"],
                high=max(r["high"] for r in group),low=min(r["low"] for r in group),
                close=group[-1]["close"],volume=sum(r["volume"] for r in group)))
        if previous_start is not None and max(buckets) != previous_start+timedelta(days=7):
            weekly = []
    week = detect_structure(weekly) if weekly else None
    weekly_bias = week["bias"] if week and week["status"]=="screened" else None
    daily_bias = daily["bias"] if daily["status"]=="screened" else None
    alignment = ("aligned" if daily_bias==weekly_bias else "conflicting") if daily_bias in ("bullish","bearish") and weekly_bias in ("bullish","bearish") else "unavailable"
    recent = {str(r["date"]) for r in ordered[-5:]}
    events = [e for e in daily["events"] if e["date"] in recent]
    prior = ordered[-21:-1]
    baseline = sum(r["volume"] for r in prior)/20 if len(prior)==20 else 0
    rv = ordered[-1]["volume"]/baseline if baseline>0 else None
    # Research descriptors, not trade signals or the production SMC score.
    return {"status":"research_only","daily_bias":daily_bias,"weekly_bias":weekly_bias,
            "weekly_completed_bars":len(weekly),"alignment":alignment,"score":None,
            "t_plus_2":{"action":"NO TRADE","recent_events":events,"relative_volume":rv,
                        "missing":["execution_depth","short_term_broker_flow","validated_trade_plan"]},
            "swing":{"action":"NO TRADE","alignment":alignment,
                     "missing":["validated_trade_plan","liquidity","market_sector_confirmation"]},
            "limitations":["Weekly coverage requires an independently verified complete session calendar.",
                           "No score is assigned until confluence rules are validated."]}
