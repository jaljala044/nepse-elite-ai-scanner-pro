"""Research-only multi-timeframe structure with explicit calendar completeness."""
from datetime import date, timedelta
from .scanner import quality_errors
from .market_structure import detect_structure
from .ipda_features import ipda_ranges
from .zone_lifecycle import zone_lifecycle

TRANSITION = date(2026, 4, 6)

def week_key(day):
    if day < TRANSITION:
        return day - timedelta(days=(day.weekday()+1)%7)
    return day - timedelta(days=day.weekday())

def aggregate_complete(rows, sessions, as_of, period):
    key = week_key if period == "weekly" else lambda d: d.replace(day=1)
    expected, actual = {}, {}
    for d in sessions:
        if d <= as_of:
            expected.setdefault(key(d), set()).add(d)
    for row in rows:
        day = date.fromisoformat(str(row["date"]))
        actual.setdefault(key(day), []).append(row)
    output, excluded = [], []
    for bucket, dates in sorted(expected.items()):
        if bucket == key(as_of):
            excluded.append(str(bucket))
            continue
        group = actual.get(bucket, [])
        if {date.fromisoformat(str(r["date"])) for r in group} != dates:
            output = []
            excluded.append(str(bucket))
            continue
        output.append(dict(date=str(group[-1]["date"]), open=float(group[0]["open"]),
            high=max(float(r["high"]) for r in group), low=min(float(r["low"]) for r in group),
            close=float(group[-1]["close"]), volume=sum(float(r["volume"]) for r in group)))
    return output, excluded

def evaluate_multitimeframe(rows, *, eligible=False, verified_sessions=None, as_of=None):
    base = {"status":"unavailable","production_score":None,"action":"NO TRADE","timeframes":{}}
    if not eligible or verified_sessions is None or as_of is None:
        return dict(base, reason="eligibility_calendar_or_cutoff_missing")
    cutoff = date.fromisoformat(str(as_of))
    sessions = [date.fromisoformat(str(d)) for d in verified_sessions]
    if sessions != sorted(set(sessions)):
        raise ValueError("calendar must be unique and ascending")
    if quality_errors(rows):
        return dict(base, reason="invalid_history")
    bars = sorted((r for r in rows if date.fromisoformat(str(r["date"])) <= cutoff),
                  key=lambda r: str(r["date"]))
    if not bars or cutoff not in sessions or str(bars[-1]["date"]) != str(cutoff):
        return dict(base, reason="missing_current_session")
    observed = {date.fromisoformat(str(r["date"])) for r in bars}
    expected = {d for d in sessions if min(observed) <= d <= cutoff}
    if not observed <= expected:
        return dict(base, reason="non_calendar_rows")
    # Do not bridge missing daily sessions. Keep only the latest contiguous run.
    daily = []
    indexed = {date.fromisoformat(str(r["date"])): r for r in bars}
    for d in sorted(expected):
        if d not in indexed:
            daily = []
        else:
            daily.append(indexed[d])
    frames = {"daily":daily}
    excluded = {}
    # Include the full first calendar bucket in expected coverage, never infer it.
    relevant = [d for d in sessions if week_key(d) >= week_key(min(observed)) or d.replace(day=1) >= min(observed).replace(day=1)]
    for period in ("weekly","monthly"):
        frames[period], excluded[period] = aggregate_complete(bars, relevant, cutoff, period)
    for name, series in frames.items():
        structure = detect_structure(series)
        base["timeframes"][name] = {"bars":len(series),"structure":structure,
            "ipda":ipda_ranges(series,eligible=True),"zones":zone_lifecycle(series,eligible=True)}
    biases = [base["timeframes"][k]["structure"]["bias"] for k in frames]
    alignment = ("aligned" if len(set(biases)) == 1 else "conflicting") if all(b in ("bullish","bearish") for b in biases) else "unavailable"
    return dict(base,status="research_only",as_of=str(cutoff),alignment=alignment,
        excluded_periods=excluded,missing_daily_sessions=len(expected-observed),
        limitations=["Latest weekly/monthly bucket excluded conservatively.",
                     "Calendar supplied by caller; independent certification required.",
                     "IPDA lookbacks count bars of the selected timeframe.",
                     "No production score or recommendations."])
