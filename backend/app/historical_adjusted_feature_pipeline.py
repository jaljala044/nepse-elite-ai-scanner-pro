"""Point-in-time corporate-action adjustment for historical feature snapshots."""
from __future__ import annotations
import hashlib, json, math
from datetime import date, datetime, timezone
from typing import Mapping
from app.versioned_feature_store import build_versioned_feature_snapshot, _json_default

PRICE_FIELDS=("open","high","low","close","previous_close")

def _aware(value: str, field: str) -> datetime:
    if not isinstance(value,str) or not value.strip(): raise ValueError(f"{field} must be a nonblank ISO-8601 timestamp")
    try: parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc: raise ValueError(f"{field} must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None: raise ValueError(f"{field} must be timezone-aware")
    return parsed.astimezone(timezone.utc)

def _verified_factor_events(events: list[Mapping], cutoff: datetime) -> tuple[list[dict],list[dict]]:
    accepted=[]; rejected=[]; seen_hashes=set()
    for index,raw in enumerate(events):
        if not isinstance(raw,Mapping):
            rejected.append({"index":index,"reason":"event_not_object"}); continue
        try:
            if raw.get("status")!="VERIFIED_TERMS_FACTOR_CALCULATED": raise ValueError("event_not_verified_by_step_74")
            if raw.get("factor_method")!="THEORETICAL_EX_PRICE_V1": raise ValueError("unsupported_factor_method")
            symbol=str(raw["symbol"]).strip().upper(); ex_date=date.fromisoformat(str(raw["ex_date"]))
            available=_aware(str(raw["available_at"]),"available_at"); factor=float(raw["adjustment_factor"])
            sources={str(x).strip() for x in raw.get("source_ids",[]) if str(x).strip()}
            publishers={str(x).strip() for x in raw.get("publisher_ids",[]) if str(x).strip()}
            event_hash=str(raw.get("event_sha256","")).lower()
            if not symbol or len(sources)<2 or len(publishers)<2: raise ValueError("two_independent_sources_and_publishers_required")
            if not math.isfinite(factor) or factor<=0: raise ValueError("factor_must_be_finite_and_positive")
            canonical=json.dumps({k:v for k,v in raw.items() if k!="event_sha256"},sort_keys=True,separators=(",",":"),default=str)
            expected_hash=hashlib.sha256(canonical.encode()).hexdigest()
            if event_hash!=expected_hash: raise ValueError("event_hash_mismatch")
            if event_hash in seen_hashes: raise ValueError("duplicate_event_hash")
            seen_hashes.add(event_hash)
            if available>cutoff or ex_date>cutoff.date():
                rejected.append({"index":index,"symbol":symbol,"reason":"not_yet_knowable_or_effective_at_cutoff"}); continue
            accepted.append({"symbol":symbol,"ex_date":ex_date.isoformat(),"factor":factor,
                "available_at":available.isoformat().replace("+00:00","Z"),"event_sha256":event_hash,
                "source_ids":sorted(sources),"publisher_ids":sorted(publishers)})
        except (KeyError,TypeError,ValueError,OverflowError) as exc:
            rejected.append({"index":index,"reason":str(exc)})
    accepted.sort(key=lambda x:(x["symbol"],x["ex_date"],x["event_sha256"]))
    return accepted,rejected

def build_adjusted_versioned_feature_snapshot(records: list[dict],decision_time: str,
        security_records: list,corporate_action_records: list,
        verified_adjustment_events: list[Mapping],expected_symbols: list[str]|None=None) -> dict:
    """Apply only hash-valid Step-74 factors known and effective by decision_time."""
    cutoff=_aware(decision_time,"decision_time")
    events,rejected=_verified_factor_events(verified_adjustment_events,cutoff)
    by_symbol={}
    for event in events: by_symbol.setdefault(event["symbol"],[]).append(event)
    adjusted_records=[]; applied=[]
    for index,original in enumerate(records):
        row=dict(original); symbol=str(row.get("symbol","")).strip().upper()
        try: session_day=date.fromisoformat(str(row.get("session_date")))
        except (TypeError,ValueError):
            adjusted_records.append(row); continue
        factor=1.0; contributing=[]
        for event in by_symbol.get(symbol,[]):
            if session_day<date.fromisoformat(event["ex_date"]):
                factor*=event["factor"]; contributing.append(event["event_sha256"])
        if contributing:
            if not math.isfinite(factor) or factor<=0:
                rejected.append({"record_index":index,"symbol":symbol,"reason":"combined_factor_invalid"})
                adjusted_records.append(row); continue
            raw_prices={}; adjusted_prices={}
            for field in PRICE_FIELDS:
                value=row.get(field)
                if value is None: continue
                number=float(value)
                if not math.isfinite(number): raise ValueError(f"record {index}: non-finite {field}")
                raw_prices[field]=value; adjusted_prices[field]=number*factor
                row[f"raw_{field}"]=value; row[field]=adjusted_prices[field]
            row["price_adjustment_factor"]=factor
            row["price_basis_status"]="verified_adjusted"; row["corporate_action_status"]="adjusted_verified"
            row["adjustment_event_hashes"]=sorted(contributing)
            applied.append({"record_index":index,"symbol":symbol,"session_date":session_day.isoformat(),
                "factor":factor,"event_hashes":sorted(contributing),"raw_prices":raw_prices,
                "adjusted_prices":adjusted_prices})
        adjusted_records.append(row)
    snapshot=build_versioned_feature_snapshot(adjusted_records,decision_time,security_records,
                                               corporate_action_records,expected_symbols)
    body={key:value for key,value in snapshot.items() if key!="snapshot_sha256"}
    body["schema_version"]=2; body["ohlcv_adjustment_applied"]=bool(applied)
    body["corporate_action_adjustment_audit"]={
        "status":"APPLIED_WITH_REJECTIONS" if applied and rejected else "APPLIED" if applied else "NO_ELIGIBLE_ADJUSTMENTS",
        "decision_time":cutoff.isoformat().replace("+00:00","Z"),"verified_event_count":len(events),
        "adjusted_record_count":len(applied),"adjustments":applied,"rejected_or_deferred_events":rejected,
        "raw_price_fields_preserved":True,"volume_and_turnover_adjusted":False,
        "source_universe_completeness_verified":False,"backtest_admission_allowed":False,"production_enabled":False}
    canonical=json.dumps(body,sort_keys=True,separators=(",",":"),default=_json_default)
    return {**body,"snapshot_sha256":hashlib.sha256(canonical.encode("utf-8")).hexdigest()}
