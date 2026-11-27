"""Conservative whole-window quarantine; never silently bridge missing sessions."""
import json
from pathlib import Path
from datetime import date
from .scanner import quality_errors

PATH=Path(__file__).resolve().parents[2]/"data/reference/p443_equity_quarantine.json"
def load():
    obj=json.loads(PATH.read_text())
    if obj["schema_version"]!=1: raise ValueError("quarantine schema")
    keys=[(r["symbol"],date.fromisoformat(r["date"]).isoformat()) for r in obj["records"]]
    if len(keys)!=1329 or len(set(keys))!=1329: raise ValueError("quarantine coverage")
    return frozenset(keys)
QUARANTINE=load()

def window_errors(symbol, rows, sessions=None, *, require_calendar=True):
    errors=quality_errors(rows)
    if errors or not rows:return errors or ["no_rows"]
    days={str(r["date"]) for r in rows}
    symbol=str(symbol).strip().upper()
    blocked=sorted(d for s,d in QUARANTINE if s==symbol and min(days)<=d<=max(days))
    errors.extend("historical_quarantine:"+d for d in blocked)
    if sessions is None:return errors+(["verified_session_calendar_required"] if require_calendar else [])
    try:
        cal=[date.fromisoformat(str(d)).isoformat() for d in sessions]
        if not cal or cal!=sorted(set(cal)):return errors+["invalid_session_calendar"]
        expected={d for d in cal if min(days)<=d<=max(days)}
        if expected!=days:errors.append("session_continuity_failed")
    except (TypeError,ValueError):errors.append("invalid_session_calendar")
    return errors
