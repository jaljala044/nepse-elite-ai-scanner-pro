"""Effective-dated NEPSE instrument status timeline.

Permanent security IDs are authoritative. Unknown intervals and simultaneous
ticker reuse are surfaced rather than silently treated as valid membership.
"""
from __future__ import annotations
from datetime import date

ACTIVE = {"ACTIVE", "LISTED", "TRADING"}
INACTIVE = {"SUSPENDED", "DELISTED", "WITHDRAWN", "CANCELLED"}

def _day(value):
    try: return date.fromisoformat(str(value))
    except (TypeError, ValueError): return None

def build_effective_universe(*, universe_rows, session_dates):
    if not isinstance(universe_rows, list) or not universe_rows:
        return {"status":"blocked","errors":["universe_rows_missing"],"security_ids":[],"symbols_by_security":{},"active_by_session":{},"inactive_history":[]}
    sessions=sorted({_day(x) for x in session_dates if _day(x)})
    if not sessions:
        return {"status":"blocked","errors":["session_dates_missing"],"security_ids":[],"symbols_by_security":{},"active_by_session":{},"inactive_history":[]}
    events={}; errors=[]; symbols={}
    for i,row in enumerate(universe_rows):
        if not isinstance(row,dict):
            errors.append("universe_row_not_object:"+str(i)); continue
        sid=str(row.get("security_id","")).strip().upper()
        symbol=str(row.get("symbol","")).strip().upper()
        effective=_day(row.get("effective_from"))
        end=_day(row.get("effective_to")) if row.get("effective_to") not in (None,"") else None
        status=str(row.get("listing_status","")).strip().upper()
        if not sid or not symbol or effective is None or status not in ACTIVE|INACTIVE:
            errors.append("universe_event_invalid:"+str(i)); continue
        if end is not None and end<effective:
            errors.append("universe_interval_invalid:"+sid); continue
        events.setdefault(sid,[]).append((effective,end,status,symbol))
        symbols.setdefault(sid,set()).add(symbol)
    active_by_session={d.isoformat():{} for d in sessions}; inactive_history=[]
    for sid,items in events.items():
        items.sort(key=lambda x:x[0])
        dates=[x[0] for x in items]
        if len(dates)!=len(set(dates)):
            errors.append("duplicate_universe_effective_date:"+sid); continue
        for current,nxt in zip(items,items[1:]):
            if current[1] is not None and current[1]>=nxt[0]:
                errors.append("overlapping_universe_intervals:"+sid)
            if current[1] is not None and any(current[1] < session < nxt[0] for session in sessions):
                errors.append("uncovered_universe_interval:"+sid)
        for session in sessions:
            eligible=[x for x in items if x[0]<=session and (x[1] is None or session<=x[1])]
            if not eligible: continue
            event=max(eligible,key=lambda x:x[0])
            latest=max((x for x in items if x[0]<=session),key=lambda x:x[0])
            if latest is not event: event=latest
            if event[1] is not None and session>event[1]: continue
            if event[2] in ACTIVE:
                active_by_session.setdefault(session.isoformat(),{})[sid]=event[3]
            else:
                inactive_history.append({"security_id":sid,"symbol":event[3],"session_date":session.isoformat(),"status":event[2]})
    # A ticker may change owners over time, but cannot identify two active securities
    # on the same session. Keep permanent IDs as keys in the canonical membership map.
    for day,members in active_by_session.items():
        owners={}
        for sid,symbol in members.items():
            owners.setdefault(symbol,[]).append(sid)
        for symbol,ids in owners.items():
            if len(ids)>1: errors.append("simultaneous_symbol_collision:"+day+":"+symbol)
    return {"status":"validated_for_research" if not errors and any(active_by_session.values()) else "blocked",
        "errors":sorted(set(errors)),"security_ids":sorted(events),
        "symbols_by_security":{k:sorted(v) for k,v in symbols.items()},
        "active_by_session":active_by_session,"inactive_history":inactive_history,
        "inactive_security_count":sum(1 for sid,items in events.items() if any(x[2] in INACTIVE for x in items)),
        "policy":"permanent security IDs; status events apply from effective_from; effective_to is inclusive; delisted/suspended securities retained; gaps and simultaneous symbol collisions are errors"}
