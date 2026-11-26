"""Deterministic research signal records; storage and outcome linking are separate."""
import hashlib
import json
from datetime import datetime

HORIZONS={"t_plus_2","swing","positional","investment"}
ACTIONS={"BUY","SELL","HOLD","NO TRADE"}

def _timestamp(value):
    dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timezone-aware timestamp required")
    return dt

def freeze_signal(*,symbol,decision_time,horizon,action,methodology,evidence,details):
    cutoff=_timestamp(decision_time)
    if (not isinstance(symbol, str) or not symbol.strip()
            or not isinstance(methodology, str) or not methodology.strip()
            or horizon not in HORIZONS or action not in ACTIONS):
        raise ValueError("invalid signal identity")
    if not isinstance(evidence, list) or not isinstance(details, dict):
        raise ValueError("invalid evidence or details")
    for item in evidence:
        if (not isinstance(item, dict) or not isinstance(item.get("evidence_id"), str)
                or not item["evidence_id"].strip() or _timestamp(item.get("available_at")) > cutoff):
            raise ValueError("missing or future evidence")
    payload={"schema_version":1,"symbol":symbol,"decision_time":cutoff.isoformat(),
             "horizon":horizon,"action":action,"methodology":methodology,
             "evidence":evidence,"details":details,"classification":"research_only_not_execution"}
    encoded=json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)
    return {"signal_id":hashlib.sha256(encoded.encode()).hexdigest(),"record":json.loads(encoded)}

def verify_signal(envelope):
    try:
        encoded=json.dumps(envelope["record"],sort_keys=True,separators=(",",":"),allow_nan=False)
        return hashlib.sha256(encoded.encode()).hexdigest()==envelope["signal_id"]
    except (KeyError,TypeError,ValueError):
        return False
