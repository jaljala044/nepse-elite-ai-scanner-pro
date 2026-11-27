"""Read-only correction review. No registry mutation or production release."""
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from .historical_quarantine import QUARANTINE

FIELDS=("open","high","low","close","volume")

def review_corrections(records):
    if not isinstance(records,list) or not records:
        return {"status":"blocked","records":[],"approved_corrections":[]}
    seen=set()
    results=[]
    for row in records:
        reasons=[]
        key=None
        try:
            if not isinstance(row,dict):
                raise ValueError("invalid_record")
            symbol=row["symbol"]
            day=row["date"]
            if not isinstance(symbol,str) or symbol!=symbol.strip().upper() or date.fromisoformat(day).isoformat()!=day:
                raise ValueError("invalid_key")
            key=(symbol,day)
            if key in seen:
                reasons.append("duplicate_key")
            seen.add(key)
            if key not in QUARANTINE:
                reasons.append("not_quarantined")
            vals=[Decimal(str(row[f])) for f in FIELDS]
            if not all(v.is_finite() and v>0 for v in vals):
                raise ValueError("invalid_numeric")
            o,h,l,c,v=vals
            if not (l<=o<=h and l<=c<=h and v==v.to_integral_value()):
                reasons.append("invalid_ohlcv")
            if not re.fullmatch(r"[0-9a-f]{64}",str(row.get("source_sha256",""))):
                reasons.append("missing_source_hash")
            if type(row.get("contracts")) is not int or row["contracts"]<=0:
                reasons.append("invalid_contract_count")
            if type(row.get("target_errors")) is not int or row["target_errors"]!=0:
                reasons.append("target_validation_failed")
            if type(row.get("session_errors")) is not int or row["session_errors"]!=0:
                reasons.append("session_validation_failed")
        except (KeyError,ValueError,TypeError,InvalidOperation) as exc:
            reasons.append("invalid_record")
        # Caller flags and hashes alone cannot authenticate external evidence.
        reasons.extend(["independent_evidence_not_authenticated","execution_order_not_authenticated","release_authority_not_implemented"])
        results.append({"key":list(key) if key else None,"reasons":reasons,"admission_allowed":False})
    return {"status":"blocked","records":results,"approved_corrections":[]}
