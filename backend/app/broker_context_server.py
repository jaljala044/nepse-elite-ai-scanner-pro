"""Conservative P438 server-owned evidence gate."""
from pathlib import Path
from datetime import date,timedelta
from .session_calendar import load_calendar
from .broker_context_integration import stamp,build_context
import json
ROOT=Path(__file__).resolve().parents[2]

def server_context(snapshot,prices,memberships,sector_prices,*,decision_time,expected_sessions):
    cutoff=stamp(decision_time)
    sessions=list(expected_sessions)
    if not sessions or sessions!=sorted(set(sessions)): raise ValueError("invalid sessions")
    start,end=map(date.fromisoformat,(sessions[0],sessions[-1]))
    if (end-start).days>3660: raise ValueError("window too long")
    registry=json.loads((ROOT/"data/reference/p443_equity_quarantine.json").read_text())
    q={(r["symbol"],date.fromisoformat(r["date"]).isoformat()) for r in registry["records"]}
    if registry["schema_version"]!=1 or len(q)!=1329 or len(registry["records"])!=1329: raise ValueError("invalid quarantine registry")
    cal=load_calendar(ROOT/"data/reference/nepse_session_calendar.csv")
    verified=[]
    day=start
    while day<=end:
        row=cal.get(day)
        if not row or row["scope"]!="market_wide" or stamp(row["verified_at_utc"])>cutoff:
            return {"status":"insufficient_evidence","reason":"trusted_calendar_incomplete","profiles":[],"production_eligible":False,"signals_enabled":False}
        if row["status"] in ("verified_open","verified_exceptional_open"): verified.append(day.isoformat())
        day+=timedelta(days=1)
    if verified!=sessions: raise ValueError("client calendar differs from server")
    return build_context(snapshot,prices,memberships,sector_prices,decision_time=decision_time,expected_sessions=verified,quarantine_keys=q)
