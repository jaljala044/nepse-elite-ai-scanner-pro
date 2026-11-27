"""Research evidence gate; does not certify exchange calendars."""
from datetime import date
from zoneinfo import ZoneInfo
from .corporate_action_trade_plan import _time
from .unified_portfolio_event_engine import _available

def review_evidence_alignment(*,sessions,assessment_time,as_of_date,calendar_evidence,decisions=()):
    tz=ZoneInfo("Asia/Kathmandu")
    cutoff=_time(assessment_time)
    days=[date.fromisoformat(d) for d in sessions]
    if not days or days!=sorted(set(days)) or days[-1]!=date.fromisoformat(as_of_date) or days[-1]!=cutoff.astimezone(tz).date():
        raise ValueError("calendar_cutoff_mismatch")
    _available(calendar_evidence,cutoff,"calendar")
    if calendar_evidence.get("sessions")!=sessions:
        raise ValueError("calendar_evidence_mismatch")
    seen=set()
    results=[]
    for decision in decisions:
        did=decision["decision_id"]
        when=_time(decision["decision_time"])
        if not did or did in seen or when>cutoff or when.astimezone(tz).date() not in days:
            raise ValueError("invalid_decision_identity_or_time")
        seen.add(did)
        blockers=[]
        evidence=decision.get("evidence",[])
        if not evidence: blockers.append("missing_decision_evidence")
        for record in evidence:
            try:
                _available(record,when,"decision_evidence")
                if _time(record["observed_at"])>when:
                    raise ValueError("future_observation")
                if _time(record["observed_at"])>_time(record["available_at"]):
                    raise ValueError("observation_after_availability")
            except (ValueError,KeyError,TypeError):
                blockers.append("invalid_or_future_evidence")
        results.append(dict(decision_id=did,point_in_time_evidence_passed=not blockers,blockers=blockers))
    return dict(calendar_alignment_passed=True,decisions=results,
        all_decisions_passed=bool(results) and all(r["point_in_time_evidence_passed"] for r in results),
        production_eligible=False,classification="caller_attested_evidence_gate",
        limitations=["Calendar and evidence provenance not independently verified; gate does not replay or certify trading signals."])
