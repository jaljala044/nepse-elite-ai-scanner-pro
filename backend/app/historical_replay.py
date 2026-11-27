"""Historical replay: observations only, never simulated fills or performance."""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo
from .scanner import quality_errors
from .scanner_eligibility import assess, REVIEWED_ROWS
from .idpat_v3 import evaluate_provisional
from .market_structure import detect_structure, add_event_evidence

from .point_in_time import eligible_as_of
from .smc_multitimeframe import evaluate_multitimeframe

METHOD = "point_in_time_replay_v2"

def calendar_as_of(records, day, cutoff, first_input=None):
    """Accept only dated, evidence-linked calendar decisions visible at cutoff."""
    if records is None:
        return None
    selected = {}
    for record in records:
        try:
            session = date.fromisoformat(record["date"])
            if session > day or not eligible_as_of(record, cutoff):
                continue
            if record.get("status") not in {"verified_open","verified_exceptional_open","verified_closed"}:
                continue
            if not isinstance(record.get("evidence_id"),str) or not record["evidence_id"].strip():
                continue
            if session in selected:
                return None
            selected[session] = record["status"]
        except (ValueError,TypeError,KeyError,AttributeError):
            return None
    if not selected:
        return None
    # Every civil day in the covered interval must have a decision.
    from datetime import timedelta
    start = min(selected)
    if first_input is not None and start > min(first_input.replace(day=1), first_input-timedelta(days=6)):
        return None
    if any(start + timedelta(days=i) not in selected for i in range((day-start).days+1)):
        return None
    return sorted(d for d,status in selected.items() if status != "verified_closed")

def replay(symbol, rows, *, reviewed=None, decision_dates=None, calendar_records=None):
    reviewed = REVIEWED_ROWS if reviewed is None else reviewed
    errors = quality_errors(rows)
    result = {"method":METHOD,"symbol":symbol,"status":"unavailable",
              "observations":[],"excluded":[],"performance":None}
    if errors or not rows:
        return dict(result, reasons=errors or ["no_rows"])
    ordered = sorted(rows,key=lambda r:str(r["date"]))
    decisions = sorted({date.fromisoformat(str(d)) for d in decision_dates}) if decision_dates is not None else [date.fromisoformat(str(r["date"])) for r in ordered]
    calendar_records = None if calendar_records is None else list(calendar_records)
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
        sessions = calendar_as_of(calendar_records, day, cutoff.isoformat(), date.fromisoformat(str(prefix[0]["date"])))
        frames = evaluate_multitimeframe(prefix, eligible=True, verified_sessions=sessions, as_of=day)
        result["observations"].append({"decision_date":day.isoformat(),
            "decision_time":cutoff.isoformat(),"input_count":len(prefix),
            "max_input_date":str(prefix[-1]["date"]),
            "provisional":evaluate_provisional(prefix,eligible=True),
            "structure":structure,"multitimeframe":frames,"action":"NO TRADE"})
    result["status"] = "research_only" if result["observations"] else "no_eligible_observations"
    return result
