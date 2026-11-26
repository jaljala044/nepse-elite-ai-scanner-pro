"""Evidence-gated early accumulation/distribution research candidates; never trade instructions."""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

class EarlyCandidateError(ValueError): pass

def _num(value, field, signed=False):
    try: x=Decimal(str(value))
    except (InvalidOperation,TypeError,ValueError): raise EarlyCandidateError(f"invalid_{field}") from None
    if not x.is_finite() or (not signed and x<0): raise EarlyCandidateError(f"invalid_{field}")
    return x

def _time(value):
    try: x=datetime.fromisoformat(value.replace("Z","+00:00"))
    except (AttributeError,TypeError,ValueError): raise EarlyCandidateError("invalid_timestamp") from None
    if x.tzinfo is None or x.utcoffset() is None: raise EarlyCandidateError("timestamp_must_be_timezone_aware")
    return x

def classify_early_market_candidates(snapshot:dict, *, as_of_date:str, as_of_timestamp:str,
                                     min_coverage:Decimal=Decimal("0.95")) -> dict:
    if not isinstance(snapshot,dict): raise EarlyCandidateError("snapshot_required")
    try: cutoff=date.fromisoformat(as_of_date)
    except (TypeError,ValueError): raise EarlyCandidateError("invalid_as_of_date") from None
    available_cutoff=_time(as_of_timestamp); threshold=_num(min_coverage,"min_coverage")
    if threshold<=0 or threshold>1: raise EarlyCandidateError("invalid_min_coverage")
    for f in ("symbol","security_id","as_of_date","available_at","broker","price_volume","relative_strength","sector"):
        if f not in snapshot: raise EarlyCandidateError(f"missing_{f}")
    try: snapdate=date.fromisoformat(snapshot["as_of_date"])
    except (TypeError,ValueError): raise EarlyCandidateError("invalid_snapshot_date") from None
    snapavailable=_time(snapshot["available_at"])
    if snapdate>cutoff or snapavailable>available_cutoff:
        return {"symbol":snapshot.get("symbol"),"status":"withheld","reason":"snapshot_not_available_at_cutoff","action":"NO_TRADE","probability":None}
    if not isinstance(snapshot["symbol"],str) or not snapshot["symbol"].strip(): raise EarlyCandidateError("invalid_symbol")
    streams=("broker","price_volume","relative_strength","sector"); parsed={}; sources=[]
    for name in streams:
        item=snapshot[name]
        if not isinstance(item,dict): raise EarlyCandidateError(f"{name}_evidence_required")
        if item.get("status")!="verified":
            return {"symbol":snapshot["symbol"],"status":"withheld","reason":f"{name}_evidence_not_verified","action":"NO_TRADE","probability":None}
        src=item.get("source_id")
        if not isinstance(src,str) or not src.strip(): raise EarlyCandidateError(f"{name}_source_id_required")
        sources.append(src)
        coverage=_num(item.get("coverage"),f"{name}_coverage")
        if coverage>1: raise EarlyCandidateError(f"{name}_coverage_above_one")
        if coverage<threshold:
            return {"symbol":snapshot["symbol"],"status":"withheld","reason":f"{name}_coverage_below_threshold","action":"NO_TRADE","probability":None}
        if item.get("available_at") is None or _time(item["available_at"])>available_cutoff:
            return {"symbol":snapshot["symbol"],"status":"withheld","reason":f"{name}_not_available_as_of_cutoff","action":"NO_TRADE","probability":None}
        parsed[name]=item
    if len(set(sources))<3:
        return {"symbol":snapshot["symbol"],"status":"withheld","reason":"insufficient_independent_source_diversity","action":"NO_TRADE","probability":None}
    b,pv,rs,sector=(parsed[x] for x in streams)
    net=_num(b.get("net_amount"),"broker_net_amount",True); gross=_num(b.get("gross_amount"),"broker_gross_amount")
    persist=_num(b.get("positive_net_session_ratio"),"positive_net_session_ratio")
    if persist>1: raise EarlyCandidateError("persistence_above_one")
    excess=_num(rs.get("stock_return_1m"),"stock_return",True)-_num(rs.get("index_return_1m"),"index_return",True)
    sector_excess=_num(sector.get("sector_excess_return_1m"),"sector_excess_return",True)
    vol=_num(pv.get("volume_vs_20d_average"),"volume_ratio")
    location=_num(pv.get("close_position_20d_range"),"close_position")
    if location>1: raise EarlyCandidateError("close_position_above_one")
    structure=pv.get("structure"); absorption=pv.get("volume_demand_supply")
    if structure not in {"higher_low","bullish_bos","lower_high","bearish_bos","range","unknown"}: raise EarlyCandidateError("invalid_structure")
    if absorption not in {"demand_absorption","supply_absorption","neutral","unknown"}: raise EarlyCandidateError("invalid_absorption")
    acc={"broker_flow":net>0 and persist>=Decimal(".60"),
         "price_structure":structure in {"higher_low","bullish_bos"},
         "volume_confirmation":vol>=Decimal("1.20") and absorption=="demand_absorption",
         "relative_strength":excess>0,"sector_alignment":sector_excess>0,
         "price_location":location<=Decimal(".75")}
    dist={"broker_flow":net<0 and persist<=Decimal(".40"),
          "price_structure":structure in {"lower_high","bearish_bos"},
          "volume_confirmation":vol>=Decimal("1.20") and absorption=="supply_absorption",
          "relative_strength":excess<0,"sector_alignment":sector_excess<0,
          "price_location":location>=Decimal(".25")}
    ac=sum(acc.values()); dc=sum(dist.values())
    acc_core=all(acc[k] for k in ("broker_flow","price_structure","volume_confirmation"))
    dist_core=all(dist[k] for k in ("broker_flow","price_structure","volume_confirmation"))
    if acc_core and ac>=4 and ac>dc: label="early_accumulation_candidate"
    elif dist_core and dc>=4 and dc>ac: label="distribution_risk_candidate"
    else: label="no_confirmed_candidate"
    return {"symbol":snapshot["symbol"],"security_id":snapshot["security_id"],
      "as_of_date":snapdate.isoformat(),"available_at":snapavailable.isoformat(),
      "status":"research_candidate_only","classification":label,
      "action":"WATCH_FOR_CONFIRMATION" if label!="no_confirmed_candidate" else "NO_TRADE",
      "probability":None,
      "metrics":{"broker_net_amount":str(net),"broker_gross_amount":str(gross),
       "broker_net_to_gross_ratio":str(net/gross if gross else Decimal(0)),
       "broker_positive_net_session_ratio":str(persist),"relative_strength_excess_1m":str(excess),
       "sector_excess_return_1m":str(sector_excess),"volume_vs_20d_average":str(vol),
       "close_position_20d_range":str(location),"price_structure":structure,
       "volume_demand_supply":absorption},
      "accumulation_evidence":acc,"distribution_evidence":dist,
      "evidence_counts":{"accumulation":ac,"distribution":dc},"source_ids":sorted(set(sources)),
      "limitations":["not a BUY/SELL signal","no entry, stop or target generated",
       "broker flow does not prove ownership or intent","independent validation remains required"]}
