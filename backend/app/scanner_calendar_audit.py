"""Candidate weekdays are diagnostics, not proof of trading."""
from datetime import date

def candidate(day):
    d=date.fromisoformat(day)
    if "2022-05-15"<=day<="2022-06-14" or day>="2026-04-06":
        return d.weekday()<5
    if "2022-06-15"<=day<="2022-09-16":
        return d.weekday()!=5
    return d.weekday() in (6,0,1,2,3)

def audit_dates(dates,verified_sessions=None):
    days=list(dates)
    flagged=sorted(set(d for d in days if not candidate(d)))
    verified=set(verified_sessions or [])
    return dict(rows=len(days),candidate_flags=flagged,
        absent_from_supplied_calendar=sorted(set(days)-verified) if verified_sessions is not None else None,
        backtest_eligible=False,reason="weekday_candidates_do_not_certify_sessions_or_provenance")
