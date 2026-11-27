"""Strict schema adapters for point-in-time NEPSE source datasets.

These adapters validate supplied, already captured records; they do not fetch
or authenticate publishers. All outputs are research-only.
"""
from __future__ import annotations
from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal, InvalidOperation

SCHEMAS = {
 "ohlcv": ("security_id","session_date","open","high","low","close","volume","turnover"),
 "session_calendar": ("session_date","session_status"),
 "instrument_universe": ("security_id","symbol","effective_from","listing_status"),
 "corporate_actions": ("security_id","action_type","announcement_date","effective_date","status"),
 "floorsheet": ("security_id","session_date","transaction_id","broker_code","side","quantity","price"),
 "broker_summary": ("security_id","session_date","broker_code","side","quantity","turnover"),
 "sector_membership": ("security_id","sector_id","effective_from","status"),
 "sector_index": ("sector_id","session_date","close","turnover"),
 "fundamentals": ("security_id","period_end","metric","value","unit"),
}
_NUMERIC = {"open","high","low","close","volume","turnover","quantity","price","value"}

def _timestamp(value):
    if not isinstance(value,str): return None
    try: parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError: return None
    if parsed.tzinfo is None or parsed.utcoffset() is None: return None
    return parsed.astimezone(timezone.utc)

def _date(value):
    try: return date.fromisoformat(str(value)).isoformat()
    except (TypeError,ValueError): return None

def _row_date_field(dataset_kind):
    return {
        "ohlcv": "session_date",
        "session_calendar": "session_date",
        "floorsheet": "session_date",
        "broker_summary": "session_date",
        "sector_index": "session_date",
        "instrument_universe": "effective_from",
        "sector_membership": "effective_from",
        "corporate_actions": "announcement_date",
        "fundamentals": "period_end",
    }[dataset_kind]


def validate_nepse_dataset(*, dataset_kind, rows, source_envelope, decision_cutoff):
    """Validate schema, provenance, point-in-time availability and row semantics."""
    if dataset_kind not in SCHEMAS: raise ValueError("unsupported_dataset_kind")
    cutoff=_timestamp(decision_cutoff)
    if cutoff is None: raise ValueError("decision_cutoff_must_be_timezone_aware")
    env=source_envelope if isinstance(source_envelope,dict) else {}
    errors=[]
    for field in ("source_id","publisher","source_uri","evidence_id","raw_sha256","available_at","rights_status","source_validation_status","finality_status","registry_review_id"):
        if not env.get(field): errors.append("source_envelope_missing:"+field)
    digest=str(env.get("raw_sha256","")).lower()
    if len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest): errors.append("raw_sha256_invalid")
    cutoff_local_date=cutoff.astimezone(ZoneInfo("Asia/Kathmandu")).date()
    available=_timestamp(env.get("available_at"))
    if available is None: errors.append("available_at_must_be_timezone_aware")
    elif available>cutoff: errors.append("source_available_after_decision_cutoff")
    if env.get("rights_status")!="approved": errors.append("source_rights_not_approved")
    if env.get("source_validation_status")!="verified": errors.append("source_not_verified")
    if env.get("finality_status")!="final": errors.append("source_not_final")
    if not isinstance(rows,list) or not rows: errors.append("dataset_rows_missing")
    accepted=[]; quarantined=[]; seen=set()
    for i,row in enumerate(rows if isinstance(rows,list) else []):
        why=[]
        if not isinstance(row,dict): why=["row_not_object"]
        else:
            for field in SCHEMAS[dataset_kind]:
                if field not in row or row[field] is None or row[field]=="": why.append("missing:"+field)
            date_field = _row_date_field(dataset_kind)
            row_day = _date(row.get(date_field))
            if row_day is None:
                why.append("invalid_" + date_field)
            elif date.fromisoformat(row_day) > cutoff_local_date:
                why.append("row_effective_after_decision_cutoff")
            if dataset_kind=="ohlcv" and not why:
                try:
                    o,h,l,c,v,t=[Decimal(str(row[k])) for k in ("open","high","low","close","volume","turnover")]
                    if any(not x.is_finite() for x in (o,h,l,c,v,t)) or min(o,h,l,c)<=0 or v<=0 or t<0 or h<max(o,c,l) or l>min(o,c,h):
                        why.append("ohlcv_values_invalid")
                except (InvalidOperation,TypeError,ValueError): why.append("ohlcv_values_invalid")
            for field in _NUMERIC.intersection(row if isinstance(row,dict) else {}):
                try:
                    n=Decimal(str(row[field]))
                    if not n.is_finite() or n<0: why.append("invalid_numeric:"+field)
                except (InvalidOperation,TypeError,ValueError): why.append("invalid_numeric:"+field)
            if dataset_kind in {"floorsheet","broker_summary"} and row.get("side") not in {"BUY","SELL"}: why.append("broker_side_invalid")
            if dataset_kind=="corporate_actions" and row.get("action_type") not in {"bonus","rights","split","dividend","merger","suspension","delisting","other"}: why.append("corporate_action_type_invalid")
            if dataset_kind=="ohlcv":
                key=(row.get("security_id"),_date(row.get("session_date")))
                if key in seen: why.append("duplicate_security_session")
                seen.add(key)
        (quarantined if why else accepted).append({"row_index":i,"reasons":why} if why else dict(row))
    status="validated_for_research" if not errors and not quarantined else "blocked_or_partial"
    return {"dataset_kind":dataset_kind,"status":status,"accepted_rows":accepted,
      "quarantined_rows":quarantined,"accepted_count":len(accepted),"quarantined_count":len(quarantined),
      "source_id":env.get("source_id"),"evidence_id":env.get("evidence_id"),
      "available_at":available.isoformat() if available else None,"envelope_errors":errors,
      "research_review_allowed":status=="validated_for_research",
      "production_promotion_allowed":False,
      "limitations":["Validates supplied records, not publisher authenticity or source independence.",
       "No live retrieval, scraping, beneficial ownership inference or manipulation finding.",
       "Dataset-specific completeness and cross-source reconciliation remain separate gates."]}
