"""Independent-source reconciliation and explicit-factor corporate-action adjustment."""
from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import re

_HASH=re.compile(r"^[0-9a-f]{64}$")
_FIELDS=("security_id","action_type","announcement_date","effective_date","status",
    "price_adjustment_factor","volume_adjustment_factor")

def _time(v):
    if not isinstance(v,str): return None
    try: x=datetime.fromisoformat(v.replace("Z","+00:00"))
    except ValueError: return None
    if x.tzinfo is None or x.utcoffset() is None: return None
    return x.astimezone(timezone.utc)

def _day(v):
    try: return date.fromisoformat(str(v))
    except (TypeError,ValueError): return None

def _dec(v):
    try: x=Decimal(str(v))
    except (InvalidOperation,TypeError,ValueError): return None
    return x if x.is_finite() else None

def reconcile_corporate_actions(*, action_records, decision_cutoff):
    """Require two independent, verified publishers agreeing on event terms and factors."""
    cutoff=_time(decision_cutoff)
    if cutoff is None: raise ValueError("decision_cutoff_must_be_timezone_aware")
    if not isinstance(action_records,list): raise ValueError("action_records_must_be_list")
    grouped={}; rejected=[]
    for i,row in enumerate(action_records):
        if not isinstance(row,dict): rejected.append({"index":i,"reason":"record_not_object"}); continue
        missing=[k for k in _FIELDS if row.get(k) in (None,"")]
        available=_time(row.get("available_at"))
        factor_p, factor_v=_dec(row.get("price_adjustment_factor")),_dec(row.get("volume_adjustment_factor"))
        if missing: rejected.append({"index":i,"reason":"missing:"+",".join(missing)}); continue
        if available is None or available>cutoff: rejected.append({"index":i,"reason":"evidence_unavailable_at_cutoff"}); continue
        if row.get("rights_status")!="approved" or row.get("source_validation_status")!="verified" or row.get("finality_status")!="final":
            rejected.append({"index":i,"reason":"source_not_approved_verified_final"}); continue
        if not isinstance(row.get("source_id"),str) or not row["source_id"].strip() or not isinstance(row.get("publisher"),str) or not row["publisher"].strip() or not isinstance(row.get("evidence_id"),str) or not row["evidence_id"].strip():
            rejected.append({"index":i,"reason":"source_provenance_missing"}); continue
        if not isinstance(row.get("raw_sha256"),str) or not _HASH.fullmatch(row["raw_sha256"].lower()):
            rejected.append({"index":i,"reason":"raw_sha256_invalid"}); continue
        if factor_p is None or factor_v is None or factor_p<=0 or factor_v<=0:
            rejected.append({"index":i,"reason":"explicit_positive_adjustment_factors_required"}); continue
        announcement,effective=_day(row.get("announcement_date")),_day(row.get("effective_date"))
        if announcement is None or effective is None or effective<announcement:
            rejected.append({"index":i,"reason":"invalid_action_dates"}); continue
        if effective>cutoff.date(): rejected.append({"index":i,"reason":"action_effective_after_decision_cutoff"}); continue
        key=(str(row["security_id"]).strip(),str(row["action_type"]).lower(),announcement.isoformat(),effective.isoformat())
        normalized=tuple(str(row[k]).strip().lower() if k=="status" else str(row[k]).strip() for k in _FIELDS)
        grouped.setdefault(key,[]).append((row,normalized,factor_p,factor_v))
    reconciled=[]; withheld=[]
    for key,records in sorted(grouped.items()):
        sources={r[0]["source_id"] for r in records}
        publishers={r[0]["publisher"] for r in records}
        terms={(r[1],r[2],r[3]) for r in records}
        if len(sources)<2 or len(publishers)<2:
            withheld.append({"event_key":key,"reason":"two_independent_publishers_required"}); continue
        if len(terms)!=1:
            withheld.append({"event_key":key,"reason":"source_terms_or_adjustment_factors_disagree"}); continue
        row,_,fp,fv=records[0]
        reconciled.append({"event_key":key,"security_id":key[0],"action_type":key[1],
            "announcement_date":key[2],"effective_date":key[3],"status":row["status"],
            "price_adjustment_factor":str(fp),"volume_adjustment_factor":str(fv),
            "source_ids":sorted(sources),"publishers":sorted(publishers),
            "evidence_ids":sorted({r[0]["evidence_id"] for r in records}),
            "available_at":max(r[0]["available_at"] for r in records),
            "reconciliation_status":"two_source_terms_agree","confidence":"HIGH"})
    return {"schema_version":"nepse-corporate-action-reconciliation-1.0.0",
        "reconciled_events":reconciled,"withheld_events":withheld,"rejected_records":rejected,
        "status":"validated_for_research" if reconciled and not withheld and not rejected else "blocked_or_partial",
        "independent_source_requirement":2,"price_factors_inferred":False,"production_enabled":False,
        "limitations":["Two distinct source IDs and publisher names are required; actual independence still needs governance review.",
            "Adjustment factors must be explicitly supplied and agreed by both sources; this module does not derive theoretical ex-rights prices.",
            "Only events effective by the decision cutoff are admitted."]}

def apply_reconciled_adjustments(*, bars, reconciled_events, decision_cutoff):
    """Adjust pre-event OHLC and volume using agreed explicit factors; preserve turnover."""
    cutoff=_time(decision_cutoff)
    if cutoff is None: raise ValueError("decision_cutoff_must_be_timezone_aware")
    if not isinstance(bars,list) or not isinstance(reconciled_events,list): raise ValueError("bars_and_events_must_be_lists")
    events=[]
    for event in reconciled_events:
        if not isinstance(event,dict) or event.get("reconciliation_status")!="two_source_terms_agree" or event.get("confidence")!="HIGH":
            raise ValueError("unreconciled_action_cannot_adjust_prices")
        available=_time(event.get("available_at")); effective=_day(event.get("effective_date"))
        fp,fv=_dec(event.get("price_adjustment_factor")),_dec(event.get("volume_adjustment_factor"))
        sources=event.get("source_ids"); publishers=event.get("publishers"); evidence=event.get("evidence_ids")
        if (available is None or available>cutoff or effective is None or effective>cutoff.date()
            or fp is None or fv is None or fp<=0 or fv<=0
            or not isinstance(sources,list) or len(set(sources))<2
            or not isinstance(publishers,list) or len(set(publishers))<2
            or not isinstance(evidence,list) or len(set(evidence))<2
            or not event.get("security_id") or not event.get("event_key")):
            raise ValueError("action_not_valid_at_cutoff_or_independent_provenance_missing")
        events.append((event, effective, fp, fv))
    output=[]
    for bar in bars:
        day=_day(bar.get("session_date"))
        if day is None: raise ValueError("invalid_bar_session_date")
        prices={k:_dec(bar.get(k)) for k in ("open","high","low","close")}
        volume,turnover=_dec(bar.get("volume")),_dec(bar.get("turnover"))
        if any(v is None or v<=0 for v in prices.values()) or volume is None or volume<0 or turnover is None or turnover<0:
            raise ValueError("invalid_bar_values")
        price_factor=Decimal(1); volume_factor=Decimal(1); applied=[]
        for event,effective,fp,fv in events:
            if event["security_id"]==str(bar.get("security_id")) and day<effective:
                price_factor*=fp; volume_factor*=fv; applied.append(event["event_key"])
        output.append({**bar,**{k:str(v*price_factor) for k,v in prices.items()},
            "volume":str(volume*volume_factor),"turnover":str(turnover),
            "adjustment_event_keys":applied,"adjustment_status":"explicit_reconciled_factors" if applied else "unadjusted_no_pre_event_factor"})
    return {"bars":output,"adjusted_bar_count":sum(bool(x["adjustment_event_keys"]) for x in output),
        "turnover_policy":"preserve recorded traded turnover; do not recompute from adjusted price and adjusted volume",
        "factor_policy":"multiply only bars strictly before each effective date using explicit reconciled price and volume factors",
        "performance_claimed":False,"production_enabled":False}
