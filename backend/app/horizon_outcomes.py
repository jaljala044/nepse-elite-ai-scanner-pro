"""Forward close-reference outcomes, not trade fills or strategy returns."""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo
from .scanner import quality_errors
from .scanner_eligibility import assess, REVIEWED_ROWS

HORIZONS = {"t_plus_2":(3,5),"swing":(5,20),"positional":(21,126),"investment":(126,504)}

def evaluate_outcomes(symbol, rows, observation, *, verified_sessions=None,
                      evaluation_date, reviewed=None):
    reviewed = REVIEWED_ROWS if reviewed is None else reviewed
    result = {"method":"forward_close_reference_v1","symbol":symbol,
              "classification":"research_reference_not_execution","horizons":{}}
    if verified_sessions is None or quality_errors(rows) or not rows:
        return dict(result,status="data_unavailable")
    decision = date.fromisoformat(observation["decision_date"])
    end = date.fromisoformat(str(evaluation_date))
    if end < decision:
        return dict(result,status="invalid_evaluation_date")
    sessions = sorted({date.fromisoformat(str(d)) for d in verified_sessions})
    by_day = {date.fromisoformat(str(r["date"])):r for r in rows}
    if decision not in sessions or decision not in by_day:
        return dict(result,status="decision_session_unverified")
    prefix = [by_day[d] for d in sorted(by_day) if d<=decision]
    if assess(symbol,prefix,datetime.combine(decision,time.max,ZoneInfo("Asia/Kathmandu")).isoformat(),reviewed,verified_sessions=verified_sessions):
        return dict(result,status="decision_evidence_unverified")
    forward = [d for d in sessions if decision<d<=end]
    cutoff = datetime.combine(end,time.max,ZoneInfo("Asia/Kathmandu")).isoformat()
    base = by_day[decision]["close"]
    for horizon, offsets in HORIZONS.items():
        measurements=[]
        for n in offsets:
            item={"sessions":n,"return_pct":None}
            if len(forward)<n:
                item["status"]="insufficient_followup"
            else:
                required=forward[:n]
                if any(d not in by_day for d in required):
                    item["status"]="missing_session"
                elif assess(symbol,[by_day[d] for d in required],cutoff,reviewed,verified_sessions=verified_sessions):
                    item["status"]="outcome_evidence_unverified"
                else:
                    item.update(status="observed",date=required[-1].isoformat(),
                                return_pct=100*(by_day[required[-1]]["close"]/base-1))
            measurements.append(item)
        result["horizons"][horizon]=measurements
    return dict(result,status="research_only",decision_date=decision.isoformat(),
                evaluation_date=end.isoformat(),reference_close=base)
