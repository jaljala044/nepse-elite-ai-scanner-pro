"""Historical replay: observations only, never simulated fills or performance."""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo
from .scanner import quality_errors
from .scanner_eligibility import assess, REVIEWED_ROWS
from .idpat_v3 import evaluate_provisional
from .market_structure import detect_structure, add_event_evidence

METHOD = "point_in_time_replay_v1"

def replay(symbol, rows, *, reviewed=None, decision_dates=None):
    reviewed = REVIEWED_ROWS if reviewed is None else reviewed
    errors = quality_errors(rows)
    result = {"method":METHOD,"symbol":symbol,"status":"unavailable",
              "observations":[],"excluded":[],"performance":None}
    if errors or not rows:
        return dict(result, reasons=errors or ["no_rows"])
    ordered = sorted(rows,key=lambda r:str(r["date"]))
    decisions = sorted({date.fromisoformat(str(d)) for d in decision_dates}) if decision_dates is not None else [date.fromisoformat(str(r["date"])) for r in ordered]
    for day in decisions:
        cutoff = datetime.combine(day,time.max,ZoneInfo("Asia/Kathmandu"))
        prefix = [r for r in ordered if date.fromisoformat(str(r["date"]))<=day]
        issues = assess(symbol,prefix,cutoff.isoformat(),reviewed)
        if issues:
            result["excluded"].append({"date":day.isoformat(),"reasons":issues})
            continue
        evidence = [reviewed[(symbol,str(r["date"]))] for r in prefix]
        structure = detect_structure(prefix)
        add_event_evidence(structure,evidence)
        result["observations"].append({"decision_date":day.isoformat(),
            "decision_time":cutoff.isoformat(),"input_count":len(prefix),
            "max_input_date":str(prefix[-1]["date"]),
            "provisional":evaluate_provisional(prefix,eligible=True),
            "structure":structure,"action":"NO TRADE"})
    result["status"] = "research_only" if result["observations"] else "no_eligible_observations"
    return result
