"""Steps 140-149: public-web evidence admission and reconciliation."""
from datetime import date
from typing import Any

def validate_web_evidence_record(row: dict[str,Any]) -> dict[str,Any]:
    errors=[]
    try: date.fromisoformat(row["session_date"])
    except (KeyError,TypeError,ValueError): errors.append("invalid_session_date")
    keys=("open","high","low","close")
    try:
        vals={k:float(row[k]) for k in keys if row.get(k) is not None}
        if len(vals)!=4: errors.append("incomplete_ohlc")
        if any(v<=0 for v in vals.values()): errors.append("non_positive_price")
        if len(vals)==4 and (vals["low"]>min(vals["open"],vals["close"]) or vals["high"]<max(vals["open"],vals["close"]) or vals["low"]>vals["high"]): errors.append("invalid_ohlc_relationship")
        if row.get("volume") is not None and float(row["volume"])<0: errors.append("negative_volume")
    except (ValueError,TypeError): errors.append("non_numeric_price_or_volume")
    if row.get("scope")=="INTRADAY_SNAPSHOT" and row.get("admit_to_eod"): errors.append("intraday_snapshot_cannot_be_eod")
    return {"status":"REJECTED" if errors else "RESEARCH_ONLY_VALIDATED","errors":errors,"ohlcv_complete":not errors and row.get("volume") is not None,"production_admission_allowed":False}

def compare_close_observations(*,session_date:str,close_observations:list[dict[str,Any]],tolerance:float=0.0)->dict[str,Any]:
    if tolerance<0: raise ValueError("negative_tolerance")
    vals=[{"provider":x["provider"],"close":float(x["close"])} for x in close_observations]
    nums={x["close"] for x in vals}
    status="CONFLICT_REVIEW" if len(nums)>1 and max(nums)-min(nums)>tolerance else ("MATCHED" if len(vals)>1 else "SINGLE_SOURCE")
    return {"session_date":date.fromisoformat(session_date).isoformat(),"observations":vals,"status":status,"production_admission_allowed":False}

def classify_first_trade(*,scheduled_date:str,first_observed_date:str,complete_archive_covers_scheduled_date:bool,primary_exchange_evidence:bool)->dict[str,Any]:
    scheduled=date.fromisoformat(scheduled_date); observed=date.fromisoformat(first_observed_date)
    if observed<scheduled: status="OBSERVATION_PRECEDES_SCHEDULE"
    elif observed>scheduled: status="SCHEDULED_SESSION_NOT_OBSERVED"
    elif complete_archive_covers_scheduled_date and primary_exchange_evidence: status="VERIFIED"
    else: status="OBSERVED_ON_SCHEDULED_DATE_BUT_UNVERIFIED"
    return {"scheduled_date":scheduled.isoformat(),"first_observed_date":observed.isoformat(),"status":status,"first_trade_date_verified":status=="VERIFIED","production_admission_allowed":False}

def classify_snapshot(scope:str,*,source_table_rows_present:bool|None=None,summary_volume:float|None=None)->dict[str,Any]:
    if scope=="INTRADAY_SNAPSHOT": status="INTRADAY_NOT_EOD"
    elif scope=="SUMMARY_ONLY" and source_table_rows_present is False and (summary_volume or 0)>0: status="SOURCE_INTERNAL_CONFLICT"
    elif scope=="EOD": status="EOD_CANDIDATE"
    else: status="REVIEW_REQUIRED"
    return {"status":status,"production_admission_allowed":False}

def normalize_merger_candidate(record:dict[str,Any])->dict[str,Any]:
    required=("predecessors","successor","event_type","source_urls")
    missing=[k for k in required if not record.get(k)]
    return {"predecessors":record.get("predecessors",[]),"successor":record.get("successor"),"event_type":record.get("event_type"),"missing_fields":missing,"status":"SECONDARY_EVIDENCE_CANDIDATE" if not missing else "UNRESOLVED","production_identity_approved":False}
